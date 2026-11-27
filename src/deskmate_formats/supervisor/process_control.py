"""Termination authority, kept separate from process observation.

:mod:`process_tree` answers "what can be seen". This module answers a different
question: "what may be signalled". They are not the same, because a process
identifier is a number that can be recycled between the observation that found
it and the signal that would end it, and because a scope that can *describe* a
process does not necessarily *own* it.

The contracts:

identity-bound member
    A :class:`Member` is ``(pid, identity, group)``. The identity is the
    creation stamp sampled when the member was authorised, so a member names a
    process instance rather than a number. ``group`` says the instance leads its
    own process group, which is the only case where a group signal can be
    confined to a tree this attempt created.

authorised owner
    The recorded owner is authorised only while its identity still matches the
    claim. ``identity-mismatch`` means the number belongs to something else now:
    it is evidence that the owner is gone and never authority over the new
    holder.

authorised descendants
    Only a scope whose membership the kernel holds grants it. A POSIX session is
    keyed by the leader's ``struct pid``, which stays referenced while any member
    survives, so the identifier cannot be recycled while the scope still contains
    something: membership cannot be forged by a stale field. A Windows parent
    chain is a static field, so a reused number anywhere in the chain can attach
    an unrelated process to this tree. A parent chain, on either platform,
    therefore grants no descendant authority.

signal
    Every signal re-checks the identity first, and prefers an identity-bound
    operating-system handle: a Linux ``pidfd`` (the descriptor pins one instance,
    so the signal cannot reach a later holder of the number), or a Windows
    process handle (the creation stamp is read from the handle and
    ``TerminateProcess`` acts on that handle). Where neither exists the identity
    is sampled immediately before the signal, which narrows the window without
    closing it, and the mechanism is recorded with the result.

refusal
    ``identity-mismatch``, ``gone``, ``unknown``, ``refused`` and ``failed`` are
    reported as such. None of them is reported as a successful termination, and
    a member whose identity cannot be established is never signalled.

This module sends signals and nothing else: it never starts, waits for or
enumerates a process.
"""

from collections import namedtuple
from time import monotonic
import os
import signal as _signal
import sys

from deskmate_formats.observer.process_health import (process_health_identity,
                                                      start_stamp, verify_process)

from . import process_tree

#: Scopes that grant descendant authority. The set coincides with the durable
#: scopes because both properties come from the same fact: the kernel, not a
#: static record field, decides who is a member.
IDENTITY_SCOPES = process_tree.DURABLE_SCOPES

#: Results that must never be read as "the tree was cleaned up".
REFUSED_RESULTS = frozenset(("identity-mismatch", "unknown", "refused", "failed"))

#: ``pid`` and ``identity`` name one process instance; ``group`` says a group
#: signal is confined to a group this attempt created.
Member = namedtuple("Member", "pid identity group")

#: ``owner``/``members`` are what may be signalled; ``scope`` and ``enumeration``
#: say how strong that permission is; ``reason`` names the outcome for a record.
Authorization = namedtuple("Authorization", "owner members scope enumeration reason")

NO_AUTHORITY = Authorization(None, (), "none", "unavailable", "no-tree-handle")


def _report(pid, result, mechanism, matched, *, group=False):
    return {"pid": pid, "result": result, "mechanism": mechanism,
            "identity_matched": matched, "group": group}


def group_leader(pid):
    """Whether ``pid`` leads its own process group.

    A group signal to anything else would reach the process group this attempt
    was itself started from.
    """
    if os.name == "nt":
        return False
    try:
        return os.getpgid(pid) == pid
    except (OSError, AttributeError):
        return False


def authorize(claim, *, deadline_seconds=process_tree.SCAN_DEADLINE_SECONDS):
    """Bind each observed member to its identity, and say what may be signalled.

    Acceptance is not the same as permission: a member whose liveness or creation
    stamp cannot be sampled is dropped and the enumeration is downgraded, so an
    unidentifiable process can neither be signalled by this attempt nor be read
    as absent by it.
    """
    if type(claim) is not dict or claim.get("scope") == "unclaimed":
        return NO_AUTHORITY
    pid = claim.get("pid")
    if type(pid) is not int or not 1 <= pid < 2 ** 31:
        return NO_AUTHORITY
    deadline = monotonic() + deadline_seconds
    scan = process_tree.live_pids(claim, deadline_seconds=max(0.0, deadline_seconds))
    identity = claim.get("identity")
    owner = (Member(pid, identity, group_leader(pid))
             if type(identity) is str and verify_process(pid, identity) == "alive" else None)
    if scan.scope not in IDENTITY_SCOPES:
        # ``scan.pids`` may contain a positively observed process, but no scope
        # here can prove it is not an unrelated process attached by a reused
        # identifier, so none of them is authorised.
        return Authorization(owner, (), scan.scope, scan.enumeration,
                             "scope-not-identity-bound")
    owner_stamp = start_stamp(identity)
    members, unverified = [], 0
    for candidate in scan.pids:
        if monotonic() >= deadline:
            return Authorization(owner, tuple(members), scan.scope, "timed-out",
                                 "authorisation-deadline")
        observed = process_health_identity(candidate)
        stamp = start_stamp(observed)
        if observed is None or stamp is None:
            unverified += 1
            continue
        if owner_stamp is not None and stamp < owner_stamp:
            continue  # created before the owner: this number was reused
        members.append(Member(candidate, observed, group_leader(candidate)))
    if unverified:
        # Findings stay authorised (they were identified); the enumeration cannot
        # be called complete, so nothing may conclude the tree is empty.
        return Authorization(owner, tuple(members), scan.scope, "degraded",
                             "unverified-member-identities")
    return Authorization(owner, tuple(members), scan.scope, scan.enumeration,
                         "identity-bound-members")


def signal(member, *, group=False):
    """Signal one authorised member, or refuse it.

    ``group`` asks for the member's whole process group, and is honoured only for
    a member authorised as its own group leader.
    """
    if type(member) is not Member or type(member.pid) is not int or not 1 <= member.pid < 2 ** 31:
        return _report(None, "refused", "invalid-member", None)
    if type(member.identity) is not str:
        return _report(member.pid, "refused", "unrecorded-identity", None)
    if group:
        return _signal_group(member)
    if os.name == "nt":
        return _signal_handle(member)
    return _signal_pidfd(member)


def _signal_group(member):
    if os.name == "nt" or not member.group:
        # Windows has no group signal, and any other caller has not shown that
        # the member leads a group this attempt created.
        return _report(member.pid, "refused", "group-not-owned", False, group=True)
    status = verify_process(member.pid, member.identity)
    if status == "identity-mismatch":
        return _report(member.pid, "identity-mismatch", "group", False, group=True)
    matched = True if status == "alive" else None
    try:
        # The group identifier is the leader's ``struct pid``. The kernel keeps
        # that number reserved while any member survives, so a group signal
        # cannot be redirected to a later holder of the same number.
        os.killpg(member.pid, _signal.SIGKILL)
    except ProcessLookupError:
        return _report(member.pid, "gone", "group", matched, group=True)
    except OSError:
        return _report(member.pid, "failed", "group", matched, group=True)
    return _report(member.pid, "signalled", "group", matched, group=True)


def _signal_pidfd(member):
    open_fd = getattr(os, "pidfd_open", None)
    send = getattr(os, "pidfd_send_signal", None)
    if open_fd is None or send is None:
        return _signal_by_pid(member)
    try:
        descriptor = open_fd(member.pid, 0)
    except ProcessLookupError:
        return _report(member.pid, "gone", "pidfd", None)
    except OSError:
        return _signal_by_pid(member)
    try:
        # The descriptor pins one instance. The identity is checked *after* it
        # is opened, so a number recycled before the open is refused instead of
        # signalled, and a number recycled afterwards can no longer be reached.
        status = verify_process(member.pid, member.identity)
        if status == "identity-mismatch":
            return _report(member.pid, "identity-mismatch", "pidfd", False)
        if status in ("stopped", "not-found"):
            return _report(member.pid, "gone", "pidfd", True)
        send(descriptor, _signal.SIGKILL)
        return _report(member.pid, "signalled", "pidfd", True)
    except ProcessLookupError:
        return _report(member.pid, "gone", "pidfd", True)
    except OSError:
        return _report(member.pid, "failed", "pidfd", True)
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def _signal_by_pid(member):
    """Fallback: sample the identity immediately before the signal.

    The gap between the check and the signal is not zero, so the mechanism is
    recorded as ``pid``. A host with neither ``pidfd`` nor a process handle
    cannot close it, and this module does not pretend otherwise.
    """
    status = verify_process(member.pid, member.identity)
    if status == "identity-mismatch":
        return _report(member.pid, "identity-mismatch", "pid", False)
    if status in ("stopped", "not-found"):
        return _report(member.pid, "gone", "pid", True)
    try:
        os.kill(member.pid, _signal.SIGKILL)
    except ProcessLookupError:
        return _report(member.pid, "gone", "pid", True)
    except OSError:
        return _report(member.pid, "failed", "pid", True)
    return _report(member.pid, "signalled", "pid", True)


if sys.platform == "win32":
    import ctypes as ct
    from ctypes import wintypes as wt

    _kernel = ct.WinDLL("kernel32", use_last_error=True)
    _kernel.OpenProcess.argtypes = (wt.DWORD, wt.BOOL, wt.DWORD)
    _kernel.OpenProcess.restype = wt.HANDLE
    _kernel.GetProcessTimes.argtypes = (wt.HANDLE, *(ct.POINTER(wt.FILETIME),) * 4)
    _kernel.GetProcessTimes.restype = wt.BOOL
    _kernel.TerminateProcess.argtypes = (wt.HANDLE, wt.UINT)
    _kernel.TerminateProcess.restype = wt.BOOL
    _kernel.CloseHandle.argtypes = (wt.HANDLE,)
    _kernel.CloseHandle.restype = wt.BOOL

    _ACCESS = 0x0001 | 0x1000 | 0x00100000  # TERMINATE | QUERY_LIMITED | SYNCHRONIZE
    _ERROR_ACCESS_DENIED = 5
    _ERROR_INVALID_PARAMETER = 87

    def _signal_handle(member):
        """Terminate the instance the handle names, never a number.

        ``taskkill /PID`` re-resolves the number after the check; opening the
        process once and acting on that handle removes the window between them.
        """
        handle = _kernel.OpenProcess(_ACCESS, False, member.pid)
        if not handle:
            error = ct.get_last_error()
            if error == _ERROR_INVALID_PARAMETER:
                return _report(member.pid, "gone", "process-handle", None)
            return _report(member.pid,
                           "unknown" if error == _ERROR_ACCESS_DENIED else "failed",
                           "process-handle", None)
        try:
            created, exited, kernel, user = (wt.FILETIME() for _ in range(4))
            if not _kernel.GetProcessTimes(handle, *(ct.byref(item) for item in
                                                    (created, exited, kernel, user))):
                return _report(member.pid, "unknown", "process-handle", None)
            expected = start_stamp(member.identity)
            stamp = created.dwHighDateTime << 32 | created.dwLowDateTime
            if expected is None or stamp != expected:
                # The handle is open on the instance the number now names, and
                # that instance is not the one that was observed.
                return _report(member.pid, "identity-mismatch", "process-handle", False)
            if not _kernel.TerminateProcess(handle, 1):
                return _report(member.pid, "failed", "process-handle", True)
            return _report(member.pid, "signalled", "process-handle", True)
        finally:
            _kernel.CloseHandle(handle)
else:
    def _signal_handle(member):  # pragma: no cover - unreachable off Windows
        return _report(member.pid, "refused", "process-handle", None)
