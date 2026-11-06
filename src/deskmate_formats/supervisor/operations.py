"""Bind app-server mutations and turn observations to durable S0 receipts."""

from .ledger import LedgerError, MUTATIONS
from .protocol import Notification, ProtocolError, RemoteError, TransportError, entity_id


class Operations:
    """Single-owner coordinator. Callers supply stable operation IDs."""

    def __init__(self, client, ledger):
        self.client = client
        self.ledger = ledger
        self.generation = client.generation
        self.ledger.register(client)
        self.ledger.uncertain(None)

    def execute(self, operation_id, method, params):
        if type(method) is not str or method not in MUTATIONS:
            raise ProtocolError("expected a supported mutation")
        def before_send(identifier):
            prepared = self.ledger.prepare(
                operation_id, method, self.generation, identifier, params.get("threadId"),
                params.get("turnId", params.get("expectedTurnId")),
            )
            self._transition(prepared, "sent-unknown", "write-ahead")

        try:
            result = self.client.request(method, params, before_send=before_send)
        except RemoteError:
            self._transition(self.ledger.get(operation_id), "failed", "remote-error")
            raise
        except TransportError:
            self.disconnect()
            raise
        try:
            self._acknowledge(operation_id, method, result)
        except (LedgerError, ProtocolError):
            self.disconnect()
            raise
        return result

    def _transition(self, receipt, state, evidence, **identities):
        return self.ledger.transition(receipt, state, evidence, self.generation, **identities)

    def _acknowledge(self, operation_id, method, result):
        receipt = self.ledger.get(operation_id)
        thread_id = result["thread"]["id"] if method in {"thread/start", "thread/resume"} else None
        turn_id = result.get("turnId") if method == "turn/steer" else None
        if method == "turn/start":
            turn_id = result["turn"]["id"]
        receipt = self._transition(receipt, "acknowledged", "remote-result", thread_id=thread_id, turn_id=turn_id)
        if method == "turn/start":
            self._apply_status(receipt, result["turn"]["status"], "remote-result")
        elif method != "turn/interrupt":
            self._transition(receipt, "completed", "remote-result")

    def next_event(self, *, timeout=0):
        try:
            event = self.client.next_event(timeout=timeout)
            if isinstance(event, Notification) and event.method in {"turn/started", "turn/completed"}:
                thread_id = entity_id(event.params["threadId"])
                turn = event.params["turn"]
                for receipt in self.ledger.matching_turn(self.generation, thread_id, entity_id(turn["id"])):
                    self._apply_status(receipt, turn["status"], "turn-notification")
            return event
        except (TransportError, ProtocolError):
            self.disconnect()
            raise

    def disconnect(self):
        self.ledger.uncertain(self.generation)

    def _apply_status(self, receipt, status, evidence):
        if receipt.method == "turn/interrupt":
            if status == "interrupted":
                return self._transition(receipt, "completed", evidence)
            if status != "inProgress" and receipt.state != "needs-reconciliation":
                return self._transition(receipt, "needs-reconciliation", evidence)
        elif status == "inProgress":
            if receipt.state == "acknowledged":
                return self._transition(receipt, "running", evidence)
        else:
            state = "completed" if status == "completed" else "failed"
            return self._transition(receipt, state, evidence)
        return receipt

    def reconcile(self, operation_id):
        """Check exact saved identities using read-only RPCs. No mutation is retried."""
        receipt = self.ledger.get(operation_id)
        if receipt is None:
            raise LedgerError("unknown operation ID")
        if receipt.state != "needs-reconciliation" or not receipt.acknowledged:
            return receipt
        if receipt.method in {"thread/start", "thread/resume", "turn/steer"}:
            return self._transition(receipt, "completed", "saved-acknowledgement")
        try:
            view = self.client.request("thread/read", {"threadId": receipt.thread_id})
            if view["thread"]["id"] != receipt.thread_id:
                return receipt
            page = self.client.request("thread/turns/list", {
                "threadId": receipt.thread_id, "itemsView": "notLoaded", "limit": 50,
            })
        except RemoteError:
            return receipt
        except TransportError:
            self.disconnect()
            raise
        matches = [turn for turn in page["data"] if turn["id"] == receipt.turn_id]
        if len(matches) != 1:
            return receipt
        return self._apply_status(receipt, matches[0]["status"], "server-turn-history")
