"""Bounded, verified guest input with evidence that is never stronger than its source.

Four things are routinely conflated between "we sent a key" and "the application
did what we meant". This module keeps them apart and records each separately:

``acknowledged``
    The emulator replied to the socket request. Nothing about the guest follows.

``delivered``
    The build's ``key`` command is timed: it forwards the first event, emits the
    rest ``KEY_GAP_MS`` (2) emulated milliseconds apart, and only replies from
    ``end_timed`` after the last event's gap. The reply means the emulated
    keyboard device was handed every event. It says nothing about the guest.

``accepted``
    Read from the guest BIOS keyboard ring, and interpreted honestly. ``INT 09h``
    stores *translated keystroke words* at TAIL and advances TAIL; ``INT 16h``
    reads at HEAD and advances HEAD, so occupancy is ``(tail - head) mod size``.
    The ring therefore counts translated keystrokes, not raw scan-code events:
    a bare modifier never enters it, and a program that hooks ``INT 09h`` or
    polls the controller bypasses it entirely. ``True`` therefore requires
    affirmative evidence: the ring was sampled non-empty (``peak``) and then
    drained. A ring that reads empty throughout - because the guest consumed the
    input before the first sample, or because it was never translated at all -
    leaves ``accepted`` as ``None``. ``False`` means the ring kept the input.

    The field is also reported as ``translated``, which is the accurate name: a
    drained ring shows that the guest BIOS translated and consumed keystroke
    words. It does not show that the application accepted or even received every
    event the request carried. A guest that hooks ``INT 09h`` never inserts into
    the ring at all, so this observation is unavailable there; that limitation is
    recorded explicitly (``Evidence.limitations``) and the caller must select an
    appropriately qualified profile rather than read an empty ring as success.

``observed``
    Only set when the caller supplied an expectation and it was met: an exact
    anchored text row plus the BIOS cursor at the end of the expected text, or a
    declared screen state. A redraw alone is never recorded as success.

Recovery is narrow by construction. It happens only when the observation is a
strict prefix of the intended text, the BIOS ring is provably empty, the
insertion point is exactly at the end of that prefix, and the observation was
stable across two samples. Everything else stops with a classified result
instead of replaying input.
"""
from dataclasses import dataclass, field
import hashlib

from .client import FeatureUnavailable

TEXT_MODES = (0, 1, 2, 3, 7)
# How translated keystrokes are observed. `bios_ring` requires a readable ring;
# `bypass` is the qualified alternative for a guest or application that hooks
# INT 09h, where ring occupancy carries no information at all.
KEYBOARD_RING = 'bios_ring'
KEYBOARD_BYPASS = 'bypass'
BIOS_CURSOR = 0x450
BIOS_KEY_HEAD = 0x41A
BIOS_KEY_TAIL = 0x41C
BIOS_KEY_START = 0x480
BIOS_KEY_END = 0x482

# Report outcomes.
OBSERVED = 'observed'
UNCHANGED = 'unchanged'
PENDING = 'pending'
AMBIGUOUS = 'ambiguous'
WITHHELD = 'withheld'      # nothing was transmitted: a precondition failed


@dataclass
class Evidence:
    """What each layer actually established, kept separate per layer.

    ``accepted`` is the compatibility name and ``translated`` the accurate one:
    ring occupancy and drainage describe translated keystrokes in the guest
    BIOS. Neither name claims application consumption.
    """

    acknowledged: bool = False
    delivered: bool = False
    accepted: object = None      # True, False or None (unknown / not applicable)
    observed: object = None      # True, False or None (no expectation given)
    limitations: list = field(default_factory=list)

    @property
    def translated(self):
        """Ring-observed translation of keystrokes; the accurate name for accepted."""
        return self.accepted

    def as_dict(self):
        return {'acknowledged': self.acknowledged, 'delivered': self.delivered,
                'accepted': self.accepted, 'translated': self.translated,
                'observed': self.observed, 'limitations': list(self.limitations)}


@dataclass
class Report:
    """One bounded input operation and the support for its conclusion."""

    operation: str
    status: str
    sent: str
    evidence: Evidence = field(default_factory=Evidence)
    observed: object = None
    missing: object = None
    bursts: int = 0
    recoveries: int = 0
    cursor: object = None
    queue: object = None
    automation: object = None
    detail: object = None
    steps: list = field(default_factory=list)

    def as_dict(self):
        return {'operation': self.operation, 'status': self.status, 'sent': self.sent,
                'evidence': self.evidence.as_dict(), 'observed': self.observed,
                'missing': self.missing, 'bursts': self.bursts,
                'recoveries': self.recoveries, 'cursor': self.cursor,
                'queue': self.queue, 'automation': self.automation,
                'detail': self.detail, 'steps': list(self.steps)}


class VerifiedInput:
    """Drive one held machine with bounded bursts, verification and evidence."""

    def __init__(self, client, *, chunk=8, settle_step_ms=40, settle_quiet=2,
                 observe_quiet_ms=150, drain_timeout_ms=1000, verify_timeout_ms=1500,
                 max_bursts=4096, max_recoveries=2, keyboard=KEYBOARD_RING):
        if type(chunk) is not int or not 1 <= chunk <= 64:
            raise ValueError('chunk must be 1..64 characters')
        if type(settle_step_ms) is not int or not 1 <= settle_step_ms <= 1000:
            raise ValueError('invalid settle step')
        if type(settle_quiet) is not int or settle_quiet < 1:
            raise ValueError('invalid settle quiet count')
        if type(max_bursts) is not int or not 1 <= max_bursts <= 100000:
            raise ValueError('max_bursts must be 1..100000')
        if type(max_recoveries) is not int or not 0 <= max_recoveries <= 8:
            raise ValueError('max_recoveries must be 0..8')
        if type(observe_quiet_ms) is not int or not 0 <= observe_quiet_ms <= 5000:
            raise ValueError('observe_quiet_ms must be 0..5000')
        if keyboard not in (KEYBOARD_RING, KEYBOARD_BYPASS):
            raise ValueError('keyboard must be bios_ring or bypass')
        self.client = client
        self.chunk = chunk
        self.settle_step_ms = settle_step_ms
        self.settle_quiet = settle_quiet
        self.drain_timeout_ms = drain_timeout_ms
        self.verify_timeout_ms = verify_timeout_ms
        self.observe_quiet_ms = observe_quiet_ms
        self.max_bursts = max_bursts
        self.max_recoveries = max_recoveries
        self.keyboard = keyboard
        self.limitations = [] if keyboard == KEYBOARD_RING else ['bios_keyboard_ring_bypassed']
        self.evidence = []

    # ---- observation helpers ----

    def frame(self):
        """Return the current native PNG bytes; the caller keeps them as evidence."""
        png, meta = self.client.framebuffer()
        return png, meta

    def frame_digest(self):
        png, meta = self.frame()
        return hashlib.sha256(png).hexdigest(), meta

    def basis(self):
        """Return which observable a snapshot uses: ``text`` or ``frame``.

        Text-mode guests are compared by their character rows. A blinking cursor
        changes rendered pixels without changing the text, so a frame digest
        cannot separate "the screen changed" from "the cursor blinked".
        """
        return 'text' if self.client.status().get('bios_mode') in TEXT_MODES else 'frame'

    def settle_frame(self, max_ms=2000):
        """Advance until the framebuffer stops changing, and return its digest.

        A quiet run means the guest stopped redrawing. It does not mean the guest
        has drawn anything yet: an unpainted black screen is perfectly stable,
        which is why ``await_render`` exists.
        """
        if type(max_ms) is not int or max_ms < 0:
            raise ValueError('invalid settle budget')
        spent, quiet, previous = 0, 0, None
        while True:
            digest, meta = self.frame_digest()
            if digest == previous:
                quiet += 1
                if quiet >= self.settle_quiet:
                    return digest, meta
            else:
                quiet, previous = 0, digest
            if spent >= max_ms:
                return digest, meta
            self.client.step(self.settle_step_ms)
            spent += self.settle_step_ms

    def await_render(self, budget_ms=10000, slice_ms=100):
        """Step until the guest draws something different from the first sample.

        A settled frame only proves the screen stopped changing; a guest that has
        not started drawing yet satisfies that trivially. This proves at least one
        redraw happened while the caller was watching.
        """
        if type(budget_ms) is not int or budget_ms < 0:
            raise ValueError('invalid render budget')
        if type(slice_ms) is not int or not 1 <= slice_ms <= 2000:
            raise ValueError('invalid render slice')
        first, _ = self.settle_frame()
        spent = 0
        while spent < budget_ms:
            self.client.step(slice_ms)
            spent += slice_ms
            digest, _ = self.frame_digest()
            if digest != first:
                return True
        return False

    def snapshot(self):
        """Hash the current observable state using the guest's own basis."""
        if self.basis() == 'text':
            rows = '\n'.join(self.text_lines())
            return {'basis': 'text', 'digest': hashlib.sha256(rows.encode('utf-8')).hexdigest()}
        digest, _ = self.settle_frame()
        return {'basis': 'frame', 'digest': digest}

    def text_lines(self):
        return self.client.text()['lines']

    def cursor(self):
        """Return the guest BIOS cursor as ``(row, col)``.

        The protocol reports it from the BIOS data area, so it is the cursor the
        guest believes it has, not something inferred from pixels.
        """
        position = self.client.text()['cursor']
        if (not isinstance(position, list) or len(position) != 2
                or any(type(value) is not int or value < 0 for value in position)):
            raise ValueError('invalid cursor reply')
        return tuple(position)

    def bios_keyboard_queue(self):
        """Read the guest BIOS keyboard ring using producer/consumer semantics.

        ``INT 09h`` stores the translated keystroke word at TAIL and advances
        TAIL; ``INT 16h`` reads at HEAD and advances HEAD. Occupancy is therefore
        ``(tail - head) mod size``. The ring holds one word per *translated*
        keystroke: its low byte is the ASCII code (0 for extended keys) and its
        high byte the scan code. A bare modifier is never stored, and a program
        that hooks ``INT 09h`` bypasses the ring, so an empty ring cannot show
        that any particular scan code was consumed.
        """
        bda = self.client.memory(BIOS_KEY_START, 4)
        start = int.from_bytes(bda[0:2], 'little')
        end = int.from_bytes(bda[2:4], 'little')
        head = int.from_bytes(self.client.memory(BIOS_KEY_HEAD, 2), 'little')
        tail = int.from_bytes(self.client.memory(BIOS_KEY_TAIL, 2), 'little')
        result = {'start': start, 'end': end, 'head': head, 'tail': tail,
                  'size': None, 'depth': None, 'valid': False, 'reason': None}
        size = end - start
        if not 2 <= size <= 64 or size % 2:
            result['reason'] = 'implausible extents'
        elif not (start <= head < end and start <= tail < end):
            # The BIOS end offset is exclusive: pointers wrap to `start` when they
            # reach `end`, so a pointer equal to `end` is out of range.
            result['reason'] = 'pointer outside extents'
        elif (head - start) % 2 or (tail - start) % 2:
            result['reason'] = 'unaligned pointer'
        else:
            result.update(size=size, valid=True, depth=((tail - head) % size) // 2)
        return result

    def automation_queue(self):
        """The automation interface's own queue state, or None on a stock build.

        This is a different queue from the BIOS ring: it counts events the
        interface still owes to the keyboard controller.
        """
        return self.client.input_state()

    def wait_queue(self, timeout_ms=None):
        """Wait, bounded, for the automation queue to drain; None if unsupported."""
        budget = self.drain_timeout_ms if timeout_ms is None else timeout_ms
        try:
            return self.client.wait_queue(budget)
        except FeatureUnavailable:
            return None

    def _drain(self):
        """The ring drain for the selected profile; None when the ring is unused."""
        return self.wait_drained() if self.keyboard == KEYBOARD_RING else None

    def wait_drained(self, timeout_ms=None):
        """Advance until the BIOS ring reports empty, or the budget ends.

        Empty is a negative observation: it excludes queued translated keystrokes
        at this instant, and the ring can refill immediately afterwards.
        """
        budget = self.drain_timeout_ms if timeout_ms is None else timeout_ms
        spent, state = 0, self.bios_keyboard_queue()
        peak = state['depth'] or 0
        while state['depth'] not in (0, None) and spent < budget:
            slice_ms = min(50, max(1, budget - spent))
            self.client.step(slice_ms)
            spent += slice_ms
            state = self.bios_keyboard_queue()
            peak = max(peak, state['depth'] or 0)
        # `peak` is what makes acceptance affirmative rather than assumed: a ring
        # that was seen holding keystrokes and then emptied proves consumption,
        # while a ring that was never seen holding any proves nothing.
        return dict(state, peak=peak)

    def row_info(self, anchor, occurrence='only'):
        """Locate `anchor` on screen and return the raw characters after it.

        Nothing is stripped: unused cells are spaces in the guest's text memory
        and an intentional trailing space is also a space, so the caller's
        comparison uses an exact slice and the cursor decides the rest.
        """
        if not isinstance(anchor, str) or not anchor:
            raise ValueError('anchor must be a non-empty string')
        if occurrence not in ('only', 'last', 'first'):
            raise ValueError('occurrence must be only, last or first')
        matches = []
        for index, line in enumerate(self.text_lines()):
            column = line.find(anchor)
            if column >= 0:
                matches.append({'row': index, 'col': column,
                                'after': line[column + len(anchor):]})
        if not matches:
            raise ValueError(f'anchor {anchor!r} matched no row')
        if len(matches) > 1 and occurrence == 'only':
            raise ValueError(f'anchor {anchor!r} matched {len(matches)} rows')
        return matches[-1] if occurrence == 'last' else matches[0]

    def row_after(self, anchor, occurrence='only'):
        """Return the raw characters after `anchor` on the row that holds it."""
        return self.row_info(anchor, occurrence)['after']

    # ---- operations ----

    def type_text(self, text, *, anchor, occurrence='only', pace_ms=None,
                  require_cursor=True):
        """Type `text` after a text-mode anchor, verifying and recovering suffixes.

        Success requires the anchored row to read exactly `text` and, by default,
        the BIOS cursor to sit at the end of it. A short observation is retried
        only as a proven-missing suffix when the ring is empty and the insertion
        point is exactly where the prefix ends. Anything else stops.
        """
        if not isinstance(text, str) or not text:
            raise ValueError('text must be a non-empty string')
        if self.basis() != 'text':
            raise ValueError('anchor verification requires a text-mode guest')
        report = Report('type_text', UNCHANGED, text)
        report.evidence.limitations = list(self.limitations)
        before, cursor, reason = self._insertion_point(anchor, occurrence)
        if before is None:
            report.status = WITHHELD
            report.cursor = list(cursor) if cursor else None
            report.detail = reason
            report.evidence.observed = False
            return report
        start_col = before['col'] + len(anchor)
        report.cursor = list(cursor)
        pending = text
        confirmed = ''          # what has been verified as present, so far
        while pending:
            if report.bursts >= self.max_bursts:
                report.status, report.detail = AMBIGUOUS, 'burst budget exhausted'
                return report
            guard = self.readiness()
            report.queue, report.automation = guard['queue'], guard['automation']
            if not guard['ok']:
                report.status = PENDING if guard['pending'] else WITHHELD
                report.detail = guard['reason']
                if not guard['pending']:
                    report.evidence.observed = False
                return report
            burst = pending[:self.chunk]
            self.client.type_ascii(burst, pace_ms=pace_ms)
            report.evidence.acknowledged = True
            report.evidence.delivered = True
            report.bursts += 1
            queue = self._drain()
            report.queue = queue
            # An instrumented build also reports its own queue draining. When it
            # says events are still being forwarded, observing the screen now
            # would describe a half-delivered burst.
            automation = self.wait_queue(self.drain_timeout_ms)
            if automation is not None and automation['matched'] is False:
                report.status = PENDING
                report.detail = 'automation queue still forwarding; not resending'
                report.steps.append({'burst': report.bursts, 'sent': burst,
                                     'queue': queue, 'automation': automation,
                                     'ms': self.client.status()['ms']})
                return report
            # Acceptance is only claimed from affirmative evidence: the ring was
            # seen holding keystrokes and then emptied. An empty ring proves
            # nothing, because the guest may have consumed the input before the
            # first sample, or may never have translated it at all.
            if queue and queue['valid'] and queue['peak']:
                report.evidence.accepted = queue['depth'] == 0
            observed, cursor = self._observe(anchor, occurrence, start_col)
            expected = confirmed + burst
            report.observed, report.cursor = observed, cursor
            report.steps.append({'burst': report.bursts, 'sent': burst,
                                 'expected': expected,
                                 'observed': observed, 'cursor': cursor,
                                 'queue': queue, 'automation': automation,
                                 'ms': self.client.status()['ms']})
            if observed == text:
                # Visible agreement is not enough: a keystroke can still be on
                # its way, and a screen that matches now can regress when it
                # arrives. Re-read the ring, the automation queue, the anchor
                # and the cursor at the instant success would be claimed.
                completion = self._completion(anchor, occurrence, before, start_col, text)
                report.steps[-1]['completion'] = completion
                report.queue, report.automation = completion['queue'], completion['automation']
                if not completion['ok']:
                    report.status = PENDING if completion['pending'] else AMBIGUOUS
                    report.detail = completion['reason']
                    report.evidence.observed = False
                    return report
                if require_cursor and cursor != (before['row'], start_col + len(text)):
                    report.status = AMBIGUOUS
                    report.evidence.observed = False
                    report.detail = 'text matches but the cursor is not at its end'
                    return report
                report.status = OBSERVED
                report.evidence.observed = True
                return report
            # Input that is still queued can still arrive. Nothing new is sent
            # while the guest owes us characters, and a quiet prefix proves
            # nothing until the queue is empty.
            if queue and queue['depth']:
                report.status = PENDING
                report.evidence.observed = False
                report.detail = 'input still queued; not resending'
                return report
            if observed == expected:
                # A burst that landed completely is ordinary progress and does not
                # spend recovery allowance.
                confirmed = expected
                pending = text[len(expected):]
                continue
            if observed and text.startswith(observed):
                if confirmed and not observed.startswith(confirmed):
                    # A longer prefix was verified earlier and has since shrunk
                    # or changed. Resending now could duplicate what actually
                    # landed, so progress is never allowed to regress silently.
                    report.status = AMBIGUOUS
                    report.evidence.observed = False
                    report.detail = 'previously verified text regressed'
                    return report
                # The burst landed only partly, even if what did land is new text.
                # That is a partial delivery, and it must pass the same
                # prerequisites as any other resend.
                allowed, gate = self._recovery_gate(anchor, occurrence, before,
                                                    start_col, observed)
                report.steps[-1]['gate'] = gate
                if not allowed:
                    report.status = PENDING if gate['pending'] else AMBIGUOUS
                    report.detail = gate['reason']
                    return report
                if report.recoveries >= self.max_recoveries:
                    report.status, report.detail = AMBIGUOUS, 'recovery budget exhausted'
                    return report
                report.recoveries += 1
                # The gate just verified this row and cursor, so the observed
                # prefix is now the floor: anything shorter is a regression.
                confirmed = observed
                pending = text[len(observed):]
                continue
            report.status = UNCHANGED if not observed else AMBIGUOUS
            report.evidence.observed = False
            report.missing = text
            if observed:
                divergence = next((i for i in range(min(len(observed), len(text)))
                                   if observed[i] != text[i]), min(len(observed), len(text)))
                report.missing = text[divergence:]
                report.detail = f'diverged at character {divergence}'
            return report
        report.status = AMBIGUOUS
        report.detail = 'no progress'
        return report

    def press(self, *codes, expect=None, reference=None, pace_ms=None):
        """Send key make/break events and report what the screen did.

        ``expect='changed'`` reports only that the screen differs from the
        snapshot taken before the press. That is an arbitrary redraw and it never
        sets ``evidence.observed``. ``expect='state'`` or ``'restore'`` compares
        against `reference`, a snapshot the caller captured earlier, and only that
        comparison can claim the intended application state.
        """
        if not codes:
            raise ValueError('at least one scancode is required')
        if expect not in (None, 'changed', 'state', 'restore'):
            raise ValueError('expect must be changed, state, restore or None')
        before = self.snapshot()
        if expect in ('state', 'restore'):
            if not isinstance(reference, dict) or reference.get('basis') != before['basis']:
                raise ValueError('state comparison needs a snapshot of the same basis')
        report = Report('press', UNCHANGED, ' '.join(hex(code) for code in codes))
        for code in codes:
            self.client.tap(code)
            report.evidence.delivered = True
            if pace_ms is not None:
                self.client.step(pace_ms)
        report.evidence.acknowledged = report.evidence.delivered
        after = self.snapshot()
        changed = after['digest'] != before['digest']
        report.observed = after['digest']
        report.steps.append({'basis': before['basis'], 'before': before['digest'],
                             'after': after['digest'], 'ms': self.client.status()['ms']})
        if expect in (None, 'changed'):
            report.status = 'changed' if changed else UNCHANGED
            return report
        satisfied = after['digest'] == reference['digest']
        report.status = OBSERVED if satisfied else (UNCHANGED if not changed else AMBIGUOUS)
        report.evidence.observed = satisfied
        return report

    def pointer(self, dx, dy, buttons=0, *, expect=None, reference=None, settle_ms=None):
        """Move the configured mouse and optionally press buttons; observe the frame.

        A changed frame proves the pointer was redrawn, not that a control was hit.
        Only ``expect='state'`` against a caller snapshot can claim an application
        state; a click's effect needs that comparison, not a difference.
        """
        if expect not in (None, 'changed', 'state', 'restore'):
            raise ValueError('expect must be changed, state, restore or None')
        before = self.snapshot()
        if expect in ('state', 'restore'):
            if not isinstance(reference, dict) or reference.get('basis') != before['basis']:
                raise ValueError('state comparison needs a snapshot of the same basis')
        report = Report('pointer', UNCHANGED, f'{dx},{dy},{buttons}')
        self.client.mouse(dx, dy, buttons)
        report.evidence.delivered = True
        report.evidence.acknowledged = True
        if settle_ms is not None:
            self.client.step(settle_ms)
        after = self.snapshot()
        changed = after['digest'] != before['digest']
        report.observed = after['digest']
        report.steps.append({'basis': before['basis'], 'before': before['digest'],
                             'after': after['digest'], 'ms': self.client.status()['ms']})
        if expect in (None, 'changed'):
            report.status = 'changed' if changed else UNCHANGED
            return report
        satisfied = after['digest'] == reference['digest']
        report.status = OBSERVED if satisfied else (UNCHANGED if not changed else AMBIGUOUS)
        report.evidence.observed = satisfied
        return report

    def readiness(self):
        """Re-read the delivery prerequisites: queue occupancy and profile.

        ``ok`` means input may be transmitted now. ``pending`` means the guest or
        the interface still owes events. ``limited`` means no queue is observable
        at all (a stock build under the bypass profile), so pending input cannot
        be excluded and no recovery may be attempted.
        """
        ring = self.bios_keyboard_queue() if self.keyboard == KEYBOARD_RING else None
        automation = self.automation_queue()
        result = {'ring': ring, 'queue': ring, 'automation': automation,
                  'pending': False, 'limited': False, 'reason': None, 'ok': False}
        if ring is not None and not ring['valid']:
            result['reason'] = 'keyboard ring unreadable; input withheld'
            return result
        if ring is not None and ring['depth']:
            result['pending'] = True
            result['reason'] = 'keystrokes still queued in the BIOS ring'
            return result
        if automation is not None and automation['queue']:
            result['pending'] = True
            result['reason'] = 'automation queue still forwarding'
            return result
        if ring is None and automation is None:
            result['limited'] = True
            result['reason'] = 'no translation or automation queue is observable'
        result['ok'] = True
        return result

    def _insertion_point(self, anchor, occurrence):
        """Establish, before any input, that the cursor is at the anchor's end.

        An empty region after an anchor does not show where the cursor is: the
        insertion point could be anywhere on the row, or on another row with the
        same anchor. Two concordant reads are required so a screen caught
        mid-redraw cannot authorise the first burst either.
        """
        # The first read raises for an absent or ambiguous anchor: that is a
        # caller or screen-selection error, not a state the facility can wait
        # out. Later reads may legitimately lose the row, so they are reported.
        info = self.row_info(anchor, occurrence)
        cursor = self.cursor()
        previous = None
        for _ in range(3):
            start_col = info['col'] + len(anchor)
            if info['after'].strip(' '):
                return None, cursor, 'anchor is not followed by an empty input position'
            if cursor != (info['row'], start_col):
                return None, cursor, 'cursor is not at the anchor end'
            sample = (info['row'], info['col'], cursor)
            if previous == sample:
                return info, cursor, None
            previous = sample
            self.client.step(self.settle_step_ms)
            try:
                info = self.row_info(anchor, occurrence)
                cursor = self.cursor()
            except ValueError:
                return None, cursor, 'the insertion point became unreadable'
        return None, cursor, 'the insertion point did not stabilise'

    def _completion(self, anchor, occurrence, original, start_col, text):
        """Re-read every prerequisite at the instant success would be claimed.

        A burst that was written and drained can still be followed by a late
        event, and a row that matches now can move when it arrives. The ring and
        the automation queue must both be empty, the anchor must still be at its
        original row and column, the row must still read exactly `text`, and the
        cursor must still be at its end.
        """
        self.client.step(self.settle_step_ms)
        guard = self.readiness()
        result = {'queue': guard['queue'], 'automation': guard['automation'],
                  'cursor': None, 'ok': False, 'pending': guard['pending'],
                  'limited': guard['limited'], 'reason': guard['reason']}
        if not guard['ok']:
            result['reason'] = result['reason'] or 'input pending at completion'
            return result
        try:
            info = self.row_info(anchor, occurrence)
            cursor = self.cursor()
        except ValueError:
            result['reason'] = 'anchor or cursor unavailable at completion'
            return result
        result['cursor'] = list(cursor)
        if info['row'] != original['row'] or info['col'] != original['col']:
            result['reason'] = 'the anchor relocated during input'
            return result
        if info['after'][:len(text)] != text or info['after'][len(text):].strip(' '):
            result['reason'] = 'the row changed between observation and completion'
            return result
        if cursor != (info['row'], start_col + len(text)):
            result['reason'] = 'cursor is not at the end of the text'
            return result
        result['ok'] = True
        return result

    def _recovery_gate(self, anchor, occurrence, original, start_col, prefix):
        """Re-read every recovery prerequisite at the moment of the resend.

        A ring that was empty when the burst was observed does not prove that
        device or application input has stopped arriving. A settle step and a
        bounded automation-queue wait pass first, then the ring, the automation
        queue, the anchor location, the row and the cursor are read again; the
        resend is allowed only if all of them still agree with the verified
        prefix at its original location.
        """
        self.client.step(self.settle_step_ms)
        self.wait_queue(self.drain_timeout_ms)
        guard = self.readiness()
        gate = {'queue': guard['queue'], 'automation': guard['automation'],
                'cursor': None, 'reason': None, 'ok': False,
                'pending': guard['pending'], 'limited': guard['limited']}
        if not guard['ok']:
            gate['reason'] = guard['reason']
            return False, gate
        if guard['limited']:
            gate['reason'] = 'pending input cannot be excluded; not resending'
            return False, gate
        try:
            info = self.row_info(anchor, occurrence)
            cursor = self.cursor()
        except ValueError:
            gate['reason'] = 'anchor or cursor unavailable; not resending'
            return False, gate
        gate['cursor'] = list(cursor)
        if info['row'] != original['row'] or info['col'] != original['col']:
            gate['reason'] = 'the anchor moved; not resending at a different location'
            return False, gate
        if info['after'][:len(prefix)] != prefix or info['after'][len(prefix):].strip(' '):
            gate['reason'] = 'the row no longer shows exactly the verified prefix'
            return False, gate
        if cursor != (info['row'], start_col + len(prefix)):
            gate['reason'] = 'insertion point is not at the end of the prefix'
            return False, gate
        gate['ok'] = True
        return True, gate

    def await_quiet(self, quiet_ms=250, budget_ms=3000):
        """Step until the observable stops changing for `quiet_ms`.

        A stable screen corroborates that the guest stopped producing output. That
        is weaker than knowing a command finished: a busy application that is not
        redrawing satisfies it too.
        """
        if (type(quiet_ms) is not int or quiet_ms < 0
                or type(budget_ms) is not int or budget_ms < 0):
            raise ValueError('invalid quiet budget')
        spent, quiet, previous = 0, 0, self.snapshot()['digest']
        while spent < budget_ms:
            self.client.step(50)
            spent += 50
            digest = self.snapshot()['digest']
            if digest == previous:
                quiet += 50
                if quiet >= quiet_ms:
                    return True
            else:
                quiet, previous = 0, digest
        return False

    def _observe(self, anchor, occurrence, start_col):
        """Return the text the cursor says was typed, plus the cursor.

        The guest BIOS cursor is the authority for how much of the row belongs to
        this input: everything from the anchor to the cursor is typed text, and a
        typed space counts exactly like any other character. Cells beyond the
        cursor must be blank, otherwise a longer previous line is leaving stale
        characters where new input should be, and the observation is refused.
        Two agreeing samples keep a half-drawn screen from being mistaken for a
        settled one.
        """
        spent, previous, quiet = 0, None, 0
        while True:
            try:
                info = self.row_info(anchor, occurrence)
                cursor = self.cursor()
            except ValueError:
                return None, None
            if cursor[0] != info['row'] or not start_col <= cursor[1] <= len(info['after']) + start_col:
                return None, cursor
            typed_len = cursor[1] - start_col
            tail = info['after'][typed_len:]
            if tail.strip(' '):
                return None, cursor
            typed = info['after'][:typed_len]
            if typed == previous:
                quiet += 1
                # An empty screen is never "settled": a delayed echo is
                # indistinguishable from a lost keystroke until time passes.
                if typed and quiet * 50 >= self.observe_quiet_ms:
                    return typed, cursor
            else:
                quiet, previous = 0, typed
            if spent >= self.verify_timeout_ms:
                return typed, cursor
            self.client.step(50)
            spent += 50
