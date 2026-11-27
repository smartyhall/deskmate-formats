"""Campaign registry, canonical leases and reconciliation without blind takeover."""

from datetime import timedelta
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from deskmate_formats.supervisor import campaigns


def tree(owner="alive", descendants="stopped"):
    return lambda claim: {"owner": owner, "descendants": descendants, "live": None}


def probe(statuses):
    return lambda pid, identity: statuses.get(pid, "not-found")


class CampaignRegistryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.directory = self.root / "registry"
        self.pid = os.getpid()

    def registry(self, *, create=False):
        return campaigns.open_registry(self.directory, create=create)

    def register(self, registry, identifier, provider="codex", worktree=None):
        registry.register(identifier, owner="Synthetic Owner", provider=provider,
                          branch=f"codex/{identifier}",
                          worktree=str(worktree or (self.root / identifier)),
                          purpose="Synthetic coordination test")

    def test_registration_status_and_handoff(self):
        with self.registry(create=True) as registry:
            record = registry.register(
                "audit-20261126", owner="Freebuff", provider="freebuff",
                branch="freebuff/audit", worktree=str(self.root / "wt"),
                purpose="Audit supervisor state", base_commit="a" * 40)
            self.assertEqual((record.status, record.provider, record.base_commit),
                             ("active", "freebuff", "a" * 40))
            with self.assertRaises(campaigns.RegistryError):
                registry.register("audit-20261126", owner="X", provider="codex",
                                  branch="codex/x", worktree=str(self.root), purpose="duplicate")
            for bad in ({"provider": "other"}, {"branch": "bad branch"},
                        {"worktree": "relative/path"}, {"base_commit": "abc"}):
                arguments = {"owner": "X", "provider": "codex", "branch": "codex/y",
                             "worktree": str(self.root), "purpose": "p"} | bad
                with self.subTest(bad=bad), self.assertRaises(campaigns.RegistryError):
                    registry.register("another", **arguments)
            self.assertEqual(registry.set_status("audit-20261126", "blocked",
                                                 reason="awaiting review").status, "blocked")
            self.assertEqual(registry.handoff("audit-20261126", owner="ChatGPT").owner, "ChatGPT")
            with self.assertRaises(campaigns.RegistryError):
                registry.set_status("unknown", "active")

    def test_two_campaigns_naming_one_worktree_cannot_both_hold_it(self):
        now = campaigns.utcnow()
        shared = self.root / "shared-checkout"
        with self.registry(create=True) as registry:
            self.register(registry, "alpha", worktree=shared)
            self.register(registry, "beta", worktree=shared)
            registry.acquire("worktree:alpha", "alpha", pid=self.pid,
                             process_identity="alpha", ttl_seconds=600, now=now)
            # The label differs but the canonical resource does not.
            with self.assertRaisesRegex(campaigns.LeaseConflict, "leased"):
                registry.acquire("worktree:beta", "beta", pid=self.pid,
                                 process_identity="beta", ttl_seconds=600, now=now)
            # Both labels now address one canonical lease, held by alpha.
            self.assertEqual(registry.lease("worktree:beta", now=now).campaign, "alpha")

    def test_path_leases_require_a_registered_campaign(self):
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            with self.assertRaisesRegex(campaigns.RegistryError, "registered campaign"):
                registry.acquire("worktree:unknown-owner", "alpha", pid=self.pid,
                                 process_identity="alpha", ttl_seconds=60)

    def test_conflicting_reservations_leave_the_registry_unchanged(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("worktree:alpha", "alpha", pid=self.pid,
                             process_identity="synthetic-alpha", ttl_seconds=600, now=now)
            with self.assertRaises(campaigns.LeaseConflict):
                registry.acquire("worktree:alpha", "beta", pid=self.pid,
                                 process_identity="synthetic-beta", ttl_seconds=600, now=now)
            with self.assertRaises(campaigns.LeaseConflict):
                registry.reserve(["worktree:beta", "worktree:alpha"], "beta", pid=self.pid,
                                 process_identity="synthetic-beta", ttl_seconds=600, now=now)
            self.assertIsNone(registry.lease("worktree:beta", now=now))
            self.assertEqual(registry.lease("worktree:alpha", now=now).campaign, "alpha")

    def test_failed_reservation_preserves_a_preexisting_lease(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            first = registry.acquire("worktree:alpha", "alpha", pid=self.pid,
                                     process_identity="alpha", ttl_seconds=600, now=now)
            registry.acquire("worktree:beta", "beta", pid=self.pid,
                             process_identity="beta", ttl_seconds=600, now=now)
            later = now + timedelta(seconds=30)
            with self.assertRaises(campaigns.LeaseConflict):
                registry.reserve(["worktree:alpha", "worktree:beta"], "alpha", pid=self.pid,
                                 process_identity="alpha", ttl_seconds=600, now=later)
            kept = registry.lease("worktree:alpha", now=later)
            self.assertIsNotNone(kept)
            self.assertEqual((kept.campaign, kept.acquired_at), ("alpha", first.acquired_at))
            self.assertEqual(registry.lease("worktree:beta", now=later).campaign, "beta")

    def test_expired_lease_blocks_implicit_takeover(self):
        now = campaigns.utcnow()
        later = now + timedelta(seconds=7200)
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("emulator:rsx-02", "alpha", pid=self.pid,
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            lease = registry.lease("emulator:rsx-02", now=later)
            self.assertTrue(lease.stale)
            self.assertEqual(lease.campaign, "alpha")
            with self.assertRaises(campaigns.LeaseConflict):
                registry.acquire("emulator:rsx-02", "beta", pid=self.pid,
                                 process_identity="synthetic-beta", ttl_seconds=60, now=later)
            with self.assertRaisesRegex(campaigns.RegistryError, "has not expired"):
                registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                 process_identity="beta-owner", ttl_seconds=600,
                                 operator_reason="Operator reassignment", now=now,
                                 probe=probe({self.pid: "alive"}),
                                 tree=tree(owner="stopped"))

    def test_reclaim_requires_a_positively_stopped_owner(self):
        now = campaigns.utcnow()
        later = now + timedelta(seconds=7200)
        alive = probe({self.pid: "alive"})
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("emulator:rsx-02", "alpha", pid=4242,
                             process_identity="previous-owner", ttl_seconds=60, now=now)
            for observed in ("alive", "unknown"):
                with self.subTest(observed=observed):
                    with self.assertRaisesRegex(campaigns.RegistryError,
                                                "not positively stopped"):
                        registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                         process_identity="beta-owner", ttl_seconds=600,
                                         operator_reason="Operator reassignment", now=later,
                                         probe=alive, tree=tree(owner=observed))
            with self.assertRaises(campaigns.RegistryError):
                registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                 process_identity="beta-owner", ttl_seconds=600,
                                 operator_reason="   ", now=later, probe=alive,
                                 tree=tree(owner="stopped"))
            reclaimed = registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                         process_identity="beta-owner", ttl_seconds=600,
                                         operator_reason="Operator reassignment", now=later,
                                         probe=alive, tree=tree(owner="stopped"))
            self.assertEqual(reclaimed.campaign, "beta")
            takeover = registry.takeovers()[0]
            self.assertEqual((takeover["previous_campaign"], takeover["new_campaign"]),
                             ("alpha", "beta"))
            self.assertEqual(takeover["reason"], "Operator reassignment")
            self.assertEqual(takeover["previous_descendants"], "stopped")

    def test_reclaim_accepts_a_replaced_owner_number(self):
        """The recorded owner is gone when its number carries another stamp.

        That is evidence about the owner only: the tree must still be proven
        empty, so no confirmation is set and none is required.
        """
        now = campaigns.utcnow()
        later = now + timedelta(seconds=7200)
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("emulator:rsx-02", "alpha", pid=4242,
                             process_identity="previous-owner", ttl_seconds=60, now=now)
            lease = registry.reclaim(
                "emulator:rsx-02", "beta", pid=self.pid, process_identity="beta-owner",
                ttl_seconds=600, now=later, operator_reason="Owner instance replaced",
                probe=probe({self.pid: "alive"}), tree=tree(owner="identity-mismatch"))
            self.assertEqual(lease.campaign, "beta")
            takeover = registry.takeovers()[0]
            self.assertEqual(takeover["previous_owner"], "identity-mismatch")
            self.assertEqual(takeover["previous_descendants"], "stopped")
            self.assertFalse(takeover["descendants_confirmed"])

    def test_reclaim_requires_a_genuine_new_owner_and_no_surviving_descendant(self):
        now = campaigns.utcnow()
        later = now + timedelta(seconds=7200)
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("emulator:rsx-02", "alpha", pid=4242,
                             process_identity="previous-owner", ttl_seconds=60, now=now)
            with self.assertRaisesRegex(campaigns.RegistryError, "live local process"):
                registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                 process_identity="beta-owner", ttl_seconds=600,
                                 operator_reason="Operator reassignment", now=later,
                                 probe=probe({}), tree=tree(owner="stopped"))
            with self.assertRaisesRegex(campaigns.RegistryError, "descendant"):
                registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                 process_identity="beta-owner", ttl_seconds=600,
                                 operator_reason="Operator reassignment", now=later,
                                 probe=probe({self.pid: "alive"}),
                                 tree=tree(owner="stopped", descendants="alive"))
            with self.assertRaisesRegex(campaigns.RegistryError, "cannot be proven"):
                registry.reclaim("emulator:rsx-02", "beta", pid=self.pid,
                                 process_identity="beta-owner", ttl_seconds=600,
                                 operator_reason="Operator reassignment", now=later,
                                 probe=probe({self.pid: "alive"}),
                                 tree=tree(owner="stopped", descendants="unknown"))
            takeover_lease = registry.reclaim(
                "emulator:rsx-02", "beta", pid=self.pid, process_identity="beta-owner",
                ttl_seconds=600, operator_reason="Operator reassignment",
                confirm_descendants_stopped=True, now=later,
                probe=probe({self.pid: "alive"}),
                tree=tree(owner="stopped", descendants="unknown"))
            self.assertEqual(takeover_lease.campaign, "beta")
            self.assertTrue(registry.takeovers()[0]["descendants_confirmed"])

    def test_renewal_and_release_require_the_recorded_identity(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            self.register(registry, "beta")
            registry.acquire("socket:86box-01", "alpha", pid=self.pid,
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            renewed = registry.renew("socket:86box-01", "alpha", pid=self.pid,
                                     process_identity="synthetic-alpha",
                                     ttl_seconds=600, now=now)
            self.assertFalse(renewed.stale)
            with self.assertRaises(campaigns.RegistryError):
                registry.renew("socket:86box-01", "beta", pid=self.pid,
                               process_identity="synthetic-beta", ttl_seconds=600, now=now)
            with self.assertRaises(campaigns.RegistryError):
                registry.renew("socket:86box-01", "alpha", pid=self.pid + 1,
                               process_identity="synthetic-alpha", ttl_seconds=600, now=now)
            with self.assertRaises(campaigns.RegistryError):
                registry.release("socket:86box-01", "beta", pid=self.pid,
                                 process_identity="synthetic-beta")
            with self.assertRaises(campaigns.RegistryError):
                registry.release("socket:86box-01", "alpha", pid=self.pid,
                                 process_identity="wrong-identity")
            self.assertTrue(registry.release("socket:86box-01", "alpha", pid=self.pid,
                                             process_identity="synthetic-alpha"))
            self.assertIsNone(registry.lease("socket:86box-01", now=now))

    def test_public_summary_omits_private_locators_and_process_identity(self):
        now = campaigns.utcnow()
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            registry.acquire("worktree:alpha", "alpha", pid=self.pid,
                             process_identity="synthetic-alpha", ttl_seconds=60, now=now)
            summary = campaigns.summarize(registry, now=now, tree=tree(owner="alive"))
        dumped = json.dumps(summary)
        self.assertEqual(summary["lease_count"], 1)
        self.assertNotIn(str(self.root), dumped)
        self.assertNotIn("synthetic-alpha", dumped)
        self.assertNotIn('"pid"', dumped)
        self.assertEqual(summary["campaigns"][0]["resources"][0]["name"], "worktree:alpha")

    def test_export_writes_the_public_summary(self):
        output = self.root / "view.json"
        with self.registry(create=True) as registry:
            self.register(registry, "alpha")
            campaigns.export(registry, output)
        self.assertEqual(json.loads(output.read_text())["lease_count"], 0)

    def test_registry_schema_one_is_refused_with_a_clear_message(self):
        options = self.directory.parent / "old"
        with campaigns.open_registry(options, create=True):
            pass
        (options / campaigns.FILE).write_text(json.dumps(
            {"schema_version": 1, "campaigns": {}, "leases": {}, "takeovers": []}),
            encoding="utf-8")
        with self.assertRaisesRegex(campaigns.RegistryError, "schema 1"):
            with campaigns.open_registry(options):
                pass


if __name__ == "__main__":
    unittest.main()
