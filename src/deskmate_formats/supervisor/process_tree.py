"""Bounded read-only process-tree observation.

Killing an owner process does not kill what it started. On POSIX an orphan is
reparented to init, so the parent chain is useless after death; the runner puts
each attempt in its own session, so the session identifier is the durable
handle. On Windows ``ParentProcessId`` is a static field that survives the
parent, so the chain itself is the handle.

The contracts this module implements, and the limits of each, are:

owner identity
    A claim is ``(pid, identity)`` where the identity is a creation stamp
    (Linux start time bound to a boot id, Windows creation ``FILETIME``). A live
    number carrying a different stamp is ``identity-mismatch``: the recorded
    owner is gone and the number now belongs to something else. It is evidence
    the owner is gone, not evidence its descendants are.

owner liveness
    ``alive``, ``stopped`` (terminated, still sampled), ``not-found``,
    ``identity-mismatch`` or ``unknown``. A missing owner never establishes
    descendant termination.

descendant identity
    Descendants are never claimed individually. They are recognised only by
    membership of an observation scope: the recorded POSIX session, or the
    Windows parent chain. Membership is therefore only as strong as the scope.

descendant liveness
    ``alive`` (a positively observed live member), ``stopped`` (a complete scan
    of a scope that cannot lose members found none) or ``unknown``.

enumeration
    ``complete``, ``truncated`` (process-count limit), ``timed-out``,
    ``degraded`` (a record could not be read or parsed), ``unavailable`` (no
    enumeration at all) or ``incomplete`` (the scope itself is lossy).

    An unreadable or malformed record is never treated as an absent process.
    Absence is conclusive only under ``complete``.

observation scope
    ``session`` (POSIX session leader: membership survives reparenting, so an
    empty session is termination), ``parent-chain`` (Windows: a static chain
    finds members, but loses a grandchild when the parent between them exits,
    so it never proves absence), ``process`` (POSIX non-leader: a display of the
    chain only, never proof) and ``none``/``unclaimed`` (no handle was ever
    taken).

session continuity
    A session identifier is the leader's *number*, so membership may only be read
    from it once the number is shown to still name the recorded session
    (:func:`_session_continuity`). ``leader-current`` means the number is held by
    the recorded instance, which cannot be recycled while the session exists, so
    membership is exact. ``leader-reused`` means a different instance holds the
    number: that is proof the original session ended and this one is someone
    else's. ``leader-absent`` means the leader has exited; the session may well be
    the original one, since its identifier stays reserved while a member survives,
    but only the number says so, so it is an observation and never authority.

termination proof
    ``stopped(claim)`` is true only when the owner is positively gone *and* a
    complete enumeration of a non-lossy scope found no live member on the same
    boot as the claim. Nothing weaker is reported as termination. Absence does
    not depend on continuity: a session always contains its own leader, so an
    empty scan of a session number is sound whichever session last held it.

authority
    This module is read-only. A PID it reports is a finding, not permission to
    signal it: nothing here binds an observation to the instance that would be
    terminated. :mod:`deskmate_formats.supervisor.process_control` establishes
    that authority separately, and only for a scope whose membership the kernel
    holds.

This module opens no process handle for control, sends no signal and starts
nothing. Every scan is bounded by a process-count cap and a deadline, and so is
its traversal.
"""

from collections import defaultdict, namedtuple
import os
from pathlib import Path
import sys
from time import monotonic

from deskmate_formats.observer.process_health import (identity_boot,
                                                      process_health_identity,
                                                      process_status, start_stamp,
                                                      verify_process)

MAX_PROCESSES = 8192
SCAN_DEADLINE_SECONDS = 3.0

#: Owner verdicts that mean the recorded process instance is gone. Each is
#: positive evidence about the owner only; none of them is evidence about what
#: it started.
OWNER_GONE = ("stopped", "not-found", "identity-mismatch")

#: Scopes whose membership is durable: an empty scan is termination.
#:
#: Only a POSIX session qualifies. A Windows parent chain is *not* durable: an
#: intermediate parent that exits takes its identifier with it, so a grandchild
#: whose parent is gone is no longer reachable from the owner and an empty walk
#: proves nothing. A job object would qualify; a static chain does not.
DURABLE_SCOPES = ("session",)

#: ``pids`` are positively observed live processes in the recorded scope and
#: never include the owner; ``complete`` says whether their absence may be read as
#: termination. A PID here is not authorisation to signal it: see
#: :mod:`process_control`.
#:
#: ``continuity`` says whether those observations are *bound* to the claim:
#: ``leader-current`` (the scope identifier still names the recorded instance),
#: ``leader-reused``, ``leader-absent``, ``unknown``, or ``n/a`` for a scope with
#: no leader record. Anything but ``leader-current`` means the PIDs were observed
#: and not attributed, so they carry no authority and no absence.
Scan = namedtuple("Scan", "pids complete enumeration scope reason continuity",
                  defaults=("n/a",))


if sys.platform == "win32":
    import ctypes as ct
    from ctypes import wintypes as wt

    _TH32CS_SNAPPROCESS = 0x00000002
    _ERROR_NO_MORE_FILES = 18
    _INVALID_HANDLE = -1
    _kernel = ct.WinDLL("kernel32", use_last_error=True)

    class _Entry(ct.Structure):
        _fields_ = (("dwSize", wt.DWORD), ("cntUsage", wt.DWORD),
                    ("th32ProcessID", wt.DWORD), ("th32DefaultHeapID", ct.c_void_p),
                    ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ct.c_long),
                    ("dwFlags", wt.DWORD), ("szExeFile", wt.WCHAR * 260))

    _kernel.CreateToolhelp32Snapshot.argtypes = (wt.DWORD, wt.DWORD)
    _kernel.CreateToolhelp32Snapshot.restype = wt.HANDLE
    _kernel.Process32FirstW.argtypes = (wt.HANDLE, ct.POINTER(_Entry))
    _kernel.Process32NextW.argtypes = (wt.HANDLE, ct.POINTER(_Entry))
    _kernel.Process32FirstW.restype = wt.BOOL
    _kernel.Process32NextW.restype = wt.BOOL
    _kernel.CloseHandle.argtypes = (wt.HANDLE,)

    def _entries(deadline):
        """Return ``(entries, enumeration, reason)`` for one Toolhelp walk.

        The walk is bounded by a count cap and a deadline, and it ends for a
        stated reason: reaching ``ERROR_NO_MORE_FILES`` is the end of the list,
        anything else is an early stop that must not be read as a complete
        enumeration.
        """
        snapshot = _kernel.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if snapshot in (_INVALID_HANDLE, 2 ** (8 * ct.sizeof(wt.HANDLE)) - 1):
            return None, "unavailable", "snapshot-failed"
        try:
            entry = _Entry()
            entry.dwSize = ct.sizeof(_Entry)
            if not _kernel.Process32FirstW(snapshot, ct.byref(entry)):
                return None, "unavailable", "enumeration-failed"
            entries = []
            while True:
                if len(entries) >= MAX_PROCESSES:
                    return entries, "truncated", "process-count-limit"
                if monotonic() >= deadline:
                    return entries, "timed-out", "scan-deadline"
                entries.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID)))
                if not _kernel.Process32NextW(snapshot, ct.byref(entry)):
                    # Only ERROR_NO_MORE_FILES is the documented end of the
                    # list. Any other status, including a zero left in the
                    # thread's error slot, is an early stop and may never be
                    # reported as a complete enumeration.
                    if ct.get_last_error() != _ERROR_NO_MORE_FILES:
                        return entries, "degraded", "enumeration-ended-early"
                    return entries, "complete", "snapshot-complete"
        finally:
            _kernel.CloseHandle(snapshot)

    def _scan(claim, deadline):
        pid = claim["pid"]
        entries, enumeration, reason = _entries(deadline)
        if entries is None:
            return Scan((), False, enumeration, "parent-chain", reason)
        children = defaultdict(list)
        for child, parent in entries:
            if child != parent:
                children[parent].append(child)
        owner_stamp = start_stamp(claim.get("identity"))
        found, frontier, unverified = [], [pid], 0
        visited, timed_out = {pid}, False
        while frontier:
            if monotonic() >= deadline:
                timed_out = True
                break
            current = frontier.pop()
            for child in children.get(current, ()):
                if child in visited:
                    continue
                visited.add(child)
                stamp = start_stamp(process_health_identity(child))
                if owner_stamp is not None and stamp is not None and stamp < owner_stamp:
                    # Created before the owner: this number, not the tree, was
                    # reused, so the child is not a descendant of this instance.
                    continue
                if owner_stamp is not None and stamp is None:
                    unverified += 1  # reuse cannot be ruled out; keep, but say so
                found.append(child)
                frontier.append(child)
        if timed_out:
            # A traversal cut short by its deadline is not a finished walk.
            return Scan(tuple(found), False, "timed-out", "parent-chain",
                        "traversal-deadline")
        if enumeration == "complete" and unverified:
            return Scan(tuple(found), False, "degraded", "parent-chain",
                        "unverified-child-identities")
        if enumeration == "complete":
            # The walk itself finished, but a chain loses a grandchild as soon
            # as the parent between them exits. Findings stay findings; their
            # absence is not termination.
            return Scan(tuple(found), False, "incomplete", "parent-chain",
                        "scope-loses-orphans")
        return Scan(tuple(found), False, enumeration, "parent-chain", reason)

    def session_of(pid):
        """Windows has no session handle; the parent chain is the tree handle."""
        return None

    def member_identity(claim, pid):
        """A parent chain proves neither membership nor identity.

        Its association can be manufactured by a reused number, so there is no
        single record that would place ``pid`` in this tree. Returning ``None``
        keeps that scope from ever becoming authority to signal anything.
        """
        return None

else:
    def _boot_id():
        """Boot identity in the same form a process identity embeds."""
        try:
            return (Path("/proc/sys/kernel/random/boot_id")
                    .read_text(encoding="ascii").strip().replace("-", ""))
        except (OSError, ValueError):
            return None

    def _stat_fields(pid):
        """Return ``(state, ppid, session, starttime)`` or raise.

        ``FileNotFoundError`` means the process exited during enumeration, which
        is not a gap. Any other ``OSError`` means the record could not be
        observed, and a ``ValueError`` means it could not be parsed: neither is
        evidence that the process does not exist.
        """
        with open(f"/proc/{pid}/stat", "rb") as stream:
            data = stream.read(8192)
        fields = data.rpartition(b") ")[2].split()
        if len(fields) < 20:
            raise ValueError("truncated process record")
        if not (fields[1].isdigit() and fields[3].isdigit() and fields[19].isdigit()):
            raise ValueError("non-numeric process record")
        return fields[0], int(fields[1]), int(fields[3]), int(fields[19])

    def session_of(pid):
        """The session id of a live process, used as the durable tree handle."""
        try:
            return os.getsid(pid)
        except (OSError, AttributeError):
            return None

    def _session_continuity(claim):
        """Does the recorded session number still name the original session?

        A session identifier is the leader's number, so the leader's own record is
        the only observable binding. Three outcomes are distinguishable:

        ``leader-current``
            The number is held by the recorded instance. The kernel reserves a
            session's identifier while the session exists, so no reuse is
            possible and every process in the session is genuinely a member.
        ``leader-reused``
            A different instance holds the number. The original session had to be
            empty for that number to be issued again, so this is a stranger's
            session, not this attempt's.
        ``leader-absent``
            There is no leader record. The session may still be the original one
            and its identifier may still be reserved, but nothing observable binds
            it any more: the number matches and the owner does not.

        Returns ``(continuity, leader_stamp)``. ``boot-changed`` means the
        identifier is from another boot, so its start stamps are not comparable at
        all; ``unknown`` means the record could not be read or the claim carries
        no comparable stamp. Both are refused the same way an absent leader is.
        """
        session = claim.get("session")
        owner_stamp = start_stamp(claim.get("identity"))
        recorded_boot = claim.get("boot") or identity_boot(claim.get("identity"))
        if type(session) is not int or owner_stamp is None or recorded_boot is None:
            return "unknown", None
        if _boot_id() != recorded_boot:
            # A start stamp is a tick since *this* boot. Comparing one recorded on
            # another boot would silently accept an unrelated instance, so the
            # boot identity is part of the binding, not only of the identity string.
            return "boot-changed", None
        try:
            _, _, member_of, stamp = _stat_fields(session)
        except FileNotFoundError:
            return "leader-absent", None
        except (OSError, ValueError):
            return "unknown", None
        if member_of != session or stamp != owner_stamp:
            return "leader-reused", stamp
        return "leader-current", stamp

    def _session_scan(claim, deadline):
        session = claim["session"]
        # A recorded lease carries its boot binding inside the process identity
        # (``linux-<boot>-<start>``), so the guard applies without a new field.
        recorded_boot = claim.get("boot") or identity_boot(claim.get("identity"))
        if recorded_boot is not None:
            boot = _boot_id()
            if boot is None:
                return Scan((), False, "unavailable", "session",
                            "boot-identity-unavailable", "boot-changed")
            if boot != recorded_boot:
                # Process start times are relative to a boot. Comparing them
                # across a reboot would silently exclude the real tree.
                return Scan((), False, "unavailable", "session", "boot-changed",
                            "boot-changed")
        try:
            names = os.listdir("/proc")
        except OSError:
            return Scan((), False, "unavailable", "session", "proc-unavailable")
        # Read before the walk so a session number that already names another
        # instance cannot lend its members the claim's identity. It is read again
        # afterwards, which is the observation that actually decides the matter.
        continuity, before_stamp = _session_continuity(claim)
        owner_start = start_stamp(claim.get("identity"))
        found, scanned, unobservable, pre_owner = [], 0, 0, 0
        truncated = timed_out = False
        for name in names:
            if not name.isdigit():
                continue
            scanned += 1
            if scanned > MAX_PROCESSES:
                truncated = True
                break
            if monotonic() >= deadline:
                timed_out = True
                break
            pid = int(name)
            try:
                state, _, member_of, start = _stat_fields(pid)
            except FileNotFoundError:
                continue  # exited during enumeration: expected, not a gap
            except (OSError, ValueError):
                unobservable += 1
                continue
            if member_of != session or pid == claim["pid"]:
                continue
            if state in (b"Z", b"X", b"x"):
                continue  # terminated, awaiting reaping
            if owner_start is not None and start < owner_start:
                pre_owner += 1  # predates the owner: not its descendant
                continue
            found.append(pid)
        enumeration = ("truncated" if truncated else "timed-out" if timed_out
                       else "degraded" if unobservable else "complete")
        reason = {"truncated": "process-count-limit", "timed-out": "scan-deadline",
                  "degraded": "unobservable-process-records",
                  "complete": "session-scan-complete"}[enumeration]
        if enumeration == "complete" and pre_owner:
            # A member created before the owner contradicts the recorded lease,
            # so the walk is not a complete picture of this session.
            enumeration, reason = "degraded", "member-predates-owner"
        # The candidates were read while the leader record was in some state; the
        # state that decides whether they are bound is the one *after* the last
        # candidate read. A session that ended mid-walk can have had its number
        # reissued before the walk finished, and only the closing observation
        # rules that out.
        after, after_stamp = _session_continuity(claim)
        bound = (continuity == "leader-current" and after == "leader-current"
                 and before_stamp is not None and after_stamp == before_stamp)
        observed = continuity if after == "leader-current" else after
        if not bound:
            if found:
                # The number names *a* session, but nothing proves it is this
                # attempt's. The finding is kept as a finding; `continuity` says
                # it is not attributed to the claim.
                return Scan(tuple(found), False, "ambiguous", "session",
                            "session-leader-reused"
                            if "leader-reused" in (continuity, after)
                            else "session-continuity-unproven", observed)
            if enumeration != "complete":
                return Scan((), False, enumeration, "session", reason, observed)
        return Scan(tuple(found), enumeration == "complete", enumeration,
                    "session", reason, continuity)

    def _chain_scan(claim, deadline):
        """Best-effort parent walk for a process with no durable session.

        POSIX reparents orphans to init, so this walk loses members and a
        missing descendant is never proof that none exists. Positive findings
        are still real, so they are reported; completeness never is.
        """
        try:
            names = os.listdir("/proc")
        except OSError:
            return Scan((), False, "unavailable", "process", "proc-unavailable")
        owner = claim["pid"]
        parents, scanned, unobservable = {}, 0, 0
        truncated = timed_out = False
        for name in names:
            if not name.isdigit():
                continue
            scanned += 1
            if scanned > MAX_PROCESSES:
                truncated = True
                break
            if monotonic() >= deadline:
                timed_out = True
                break
            pid = int(name)
            try:
                state, ppid, _, start = _stat_fields(pid)
            except FileNotFoundError:
                continue
            except (OSError, ValueError):
                unobservable += 1
                continue
            parents[pid] = (ppid, state, start)
        owner_start = start_stamp(claim.get("identity"))
        found, frontier, visited = [], [owner], {owner}
        timed_out = False
        while frontier:
            if monotonic() >= deadline:
                timed_out = True
                break
            current = frontier.pop()
            for pid, (ppid, state, start) in parents.items():
                if ppid != current or pid in visited:
                    continue
                visited.add(pid)
                if state in (b"Z", b"X", b"x"):
                    continue
                if owner_start is not None and start < owner_start:
                    continue
                found.append(pid)
                frontier.append(pid)
        if timed_out:
            enumeration, reason = "timed-out", "traversal-deadline"
        elif truncated:
            enumeration, reason = "truncated", "process-count-limit"
        elif timed_out:
            enumeration, reason = "timed-out", "scan-deadline"
        elif unobservable:
            enumeration, reason = "degraded", "unobservable-process-records"
        else:
            enumeration, reason = "incomplete", "scope-not-durable"
        return Scan(tuple(found), False, enumeration, "process", reason)

    def _scan(claim, deadline):
        if claim.get("session") is None:
            return _chain_scan(claim, deadline)
        return _session_scan(claim, deadline)

    def member_identity(claim, pid):
        """Identity of ``pid`` when one record also places it in the claim's scope.

        Session membership and the creation stamp come from the same read, so a
        number reused between two reads cannot satisfy the scope check with an
        identity that belongs to a different process. ``None`` means the process
        cannot be bound to this tree, and is never authority to signal it.

        The leader is revalidated *after* the candidate record is read. Checking it
        first would leave a window: a session whose leader has exited can end and
        have its number reissued before the candidate is read, and the candidate
        would then carry a later stamp in a session this attempt never created.
        """
        if type(claim) is not dict or claim.get("scope") not in DURABLE_SCOPES:
            return None
        session = claim.get("session")
        boot = claim.get("boot") or identity_boot(claim.get("identity"))
        if type(session) is not int or boot is None or pid == claim.get("pid"):
            return None
        try:
            state, _, member_of, start = _stat_fields(pid)
        except (OSError, ValueError):
            return None
        if member_of != session or state in (b"Z", b"X", b"x"):
            return None
        continuity, _ = _session_continuity(claim)
        if continuity != "leader-current":
            # The closing observation is what binds the candidate: anything but the
            # recorded leader still holding the identifier makes the session
            # number, not the membership, the thing that matched.
            return None
        return f"linux-{boot}-{start}"


def _valid(claim):
    if type(claim) is not dict:
        return False
    pid = claim.get("pid")
    return type(pid) is int and 1 <= pid < 2 ** 31 and claim.get("scope") != "unclaimed"


def tree_claim(pid=None):
    """Claim an owner plus the durable handle for its future descendants.

    Returns ``None`` when the process is not alive. A caller that has just
    spawned a process should record the degraded claim from :func:`unclaimed`
    instead, so that "no handle was ever taken" stays visible.
    """
    pid = os.getpid() if pid is None else pid
    if type(pid) is not int or not 1 <= pid < 2 ** 31:
        raise ValueError("invalid PID")
    identity, status = process_health_identity(pid), process_status(pid)
    if identity is None or status != "alive":
        return None
    claim = {"pid": pid, "identity": identity, "platform": sys.platform}
    if sys.platform == "win32":
        # The chain is the only handle Windows offers without a job object. It
        # finds members and it survives the owner's exit, but it cannot prove
        # that none is left (see DURABLE_SCOPES).
        claim["scope"] = "parent-chain"
        return claim
    session = session_of(pid)
    if session is not None and session == pid:
        claim["session"] = session
        claim["scope"] = "session"
        boot = _boot_id()
        if boot is not None:
            claim["boot"] = boot
    else:
        # Recording the shared session of an ordinary process would make every
        # sibling look like a descendant, so only the display scope remains.
        claim["scope"] = "process"
    return claim


def unclaimed(pid):
    """A claim for a process that died before its tree handle could be taken."""
    if type(pid) is not int or not 1 <= pid < 2 ** 31:
        raise ValueError("invalid PID")
    return {"pid": pid, "identity": None, "platform": sys.platform,
            "scope": "unclaimed", "reason": "owner-exited-before-claim"}


def _live(pids, deadline):
    """Split observed members into positively live PIDs and unobservable ones.

    ``unknown`` liveness is neither evidence of life nor evidence of absence, so
    it is counted and reported instead of being guessed either way. A PID is
    only reported live when it was actually sampled alive.
    """
    alive, unobservable = [], 0
    for pid in pids:
        if monotonic() >= deadline:
            return tuple(alive), "liveness-deadline"
        status = process_status(pid)
        if status == "alive":
            alive.append(pid)
        elif status == "unknown":
            unobservable += 1
    return tuple(alive), ("unknown-member-liveness" if unobservable else None)


def live_pids(claim, *, deadline_seconds=SCAN_DEADLINE_SECONDS):
    """Positively observed live members of the recorded tree.

    Returns a :data:`Scan` of PIDs that were sampled alive. A PID is a finding,
    not a permission: this module does not carry the identity it observed, and
    nothing here establishes the authority to signal one (see
    :mod:`process_control`).

    A member whose liveness cannot be sampled is neither alive nor absent. It is
    left out of ``pids`` and the scan is marked ``degraded``, because its absence
    from that tuple must never be read as an empty tree.

    A PID may also be reported while the scope identifier is not provably the
    recorded one; ``continuity`` says so, and neither :mod:`process_control` nor
    :func:`tree_state` treats the finding as this tree's (see ``leader-reused``).
    """
    if not _valid(claim):
        return Scan((), False, "unavailable", "none", "invalid-claim")
    deadline = monotonic() + deadline_seconds
    scan = _scan(claim, deadline)
    alive, problem = _live(scan.pids, deadline)
    if problem is not None and scan.enumeration == "complete":
        scan = scan._replace(complete=False, enumeration="degraded", reason=problem)
    return scan._replace(pids=alive)


def tree_state(claim, *, deadline_seconds=SCAN_DEADLINE_SECONDS):
    """Report the owner separately from its descendants.

    ``descendants`` is ``stopped`` only for a complete scan of a durable scope
    on the same boot as the claim. ``unknown`` means the scan cannot be
    trusted, which must never be read as proof that nothing is still running.
    """
    if not _valid(claim):
        return {"owner": "unknown", "descendants": "unknown", "live": None,
                "scope": "unclaimed" if type(claim) is dict else "none",
                "enumeration": "unavailable", "reason": "no-tree-handle",
                "continuity": "n/a"}
    deadline = monotonic() + deadline_seconds
    owner = verify_process(claim["pid"], claim.get("identity"))
    scan = _scan(claim, deadline)
    alive, problem = _live(scan.pids, deadline)
    if problem is not None and scan.enumeration == "complete":
        scan = scan._replace(complete=False, enumeration="degraded", reason=problem)
    base = {"owner": owner, "scope": scan.scope, "enumeration": scan.enumeration,
            "continuity": scan.continuity}
    if owner == "identity-mismatch" and scan.scope == "parent-chain":
        # The number belongs to another process now, and a static parent chain
        # cannot separate the original children from the new process's.
        return dict(base, descendants="unknown", live=None, reason="owner-pid-reused")
    if alive:
        if scan.continuity == "leader-reused":
            # The session number was issued again, so these processes belong to
            # someone else's session: neither this tree's life nor its emptiness
            # may be inferred from them.
            return dict(base, descendants="unknown", live=None,
                        reason="session-leader-reused")
        return dict(base, descendants="alive", live=len(alive),
                    reason=("live-descendants" if scan.continuity in ("leader-current", "n/a")
                            else scan.reason))
    if scan.complete and scan.scope in DURABLE_SCOPES:
        return dict(base, descendants="stopped", live=0, reason=scan.reason)
    return dict(base, descendants="unknown", live=None, reason=scan.reason)


def stopped(claim, *, deadline_seconds=SCAN_DEADLINE_SECONDS):
    """True only when the owner and every descendant are positively gone."""
    state = tree_state(claim, deadline_seconds=deadline_seconds)
    return state["owner"] in OWNER_GONE and state["descendants"] == "stopped"


def worktree_root():
    """Diagnostic helper: the canonical location of this checkout, if any."""
    return Path(__file__).resolve().parents[3]
