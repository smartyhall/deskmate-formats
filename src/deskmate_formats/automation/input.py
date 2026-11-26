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
    polls the controller bypasses it entirely. An empty ring is a negative
    observation, not proof that a particular keystroke was consumed.

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

TEXT_MODES = (0, 1, 2, 3, 7)
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


@dataclass
class Evidence:
    """What each layer actually established, kept separate per layer."""

    acknowledged: bool = False
    delivered: bool = False
    accepted: object = None      # True, False or None (unknown / not applicable)
    observed: object = None      # True, False or None (no expectation given)

    def as_dict(self):
        return {'acknowledged': self.acknowledged, 'delivered': self.delivered,
                'accepted': self.accepted, 'observed': self.observed}


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
    detail: object = None
    steps: list = field(default_factory=list)

    def as_dict(self):
        return {'operation': self.operation, 'status': self.status, 'sent': self.sent,
                'evidence': self.evidence.as_dict(), 'observed': self.observed,
                'missing': self.missing, 'bursts': self.bursts,
                'recoveries': self.recoveries, 'cursor': self.cursor,
                'queue': self.queue, 'detail': self.detail, 'steps': list(self.steps)}


class VerifiedInput:
    """Drive one held machine with bounded bursts, verification and evidence."""

    def __init__(self, client, *, chunk=8, settle_step_ms=40, settle_quiet=2,
                 observe_quiet_ms=150, drain_timeout_ms=1000, verify_timeout_ms=1500,
                 max_bursts=4096, max_recoveries=2):
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
        self.client = client
        self.chunk = chunk
        self.settle_step_ms = settle_step_ms
        self.settle_quiet = settle_quiet
        self.drain_timeout_ms = drain_timeout_ms
        self.verify_timeout_ms = verify_timeout_ms
        self.observe_quiet_ms = observe_quiet_ms
        self.max_bursts = max_bursts
        self.max_recoveries = max_recoveries
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
        elif not (start <= head <= end and start <= tail <= end):
            result['reason'] = 'pointer outside extents'
        elif (head - start) % 2 or (tail - start) % 2:
            result['reason'] = 'unaligned pointer'
        else:
            result.update(size=size, valid=True, depth=((tail - head) % size) // 2)
        return result

    def wait_drained(self, timeout_ms=None):
        """Advance until the BIOS ring reports empty, or the budget ends.

        Empty is a negative observation: it excludes queued translated keystrokes
        at this instant, and the ring can refill immediately afterwards.
        """
        budget = self.drain_timeout_ms if timeout_ms is None else timeout_ms
        spent, state = 0, self.bios_keyboard_queue()
        while state['depth'] not in (0, None) and spent < budget:
            slice_ms = min(50, max(1, budget - spent))
            self.client.step(slice_ms)
            spent += slice_ms
            state = self.bios_keyboard_queue()
        return state

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
        before = self.row_info(anchor, occurrence)
        if before['after'].strip(' '):
            raise ValueError(f'anchor is not at an empty input position: {before["after"]!r}')
        report = Report('type_text', UNCHANGED, text)
        pending = text
        confirmed = ''          # what has been observed and accepted as progress
        start_col = before['col'] + len(anchor)
        while pending:
            if report.bursts >= self.max_bursts:
                report.status, report.detail = AMBIGUOUS, 'burst budget exhausted'
                return report
            queue = self.bios_keyboard_queue()
            report.queue = queue
            if queue['depth'] not in (0, None):
                report.status = PENDING
                report.evidence.accepted = False
                report.detail = 'keystrokes still queued before this burst'
                return report
            burst = pending[:self.chunk]
            self.client.type_ascii(burst, pace_ms=pace_ms)
            report.evidence.acknowledged = True
            report.evidence.delivered = True
            report.bursts += 1
            queue = self.wait_drained()
            report.queue = queue
            if queue['valid']:
                report.evidence.accepted = queue['depth'] == 0
            observed, cursor = self._observe(anchor, occurrence, start_col)
            report.observed, report.cursor = observed, cursor
            report.steps.append({'burst': report.bursts, 'sent': burst,
                                 'observed': observed, 'cursor': cursor,
                                 'queue': queue, 'ms': self.client.status()['ms']})
            if observed == text and (cursor is None or not require_cursor
                                     or cursor == (before['row'], start_col + len(text))):
                report.status = OBSERVED
                report.evidence.observed = True
                return report
            if observed == text:
                report.status = AMBIGUOUS
                report.evidence.observed = False
                report.detail = 'text matches but the cursor is not at its end'
                return report
            # Input that is still queued can still arrive. Nothing new is sent
            # while the guest owes us characters, and a quiet prefix proves
            # nothing until the queue is empty.
            if queue['depth']:
                report.status = PENDING
                report.evidence.observed = False
                report.detail = 'input still queued; not resending'
                return report
            if observed and text.startswith(observed):
                if len(observed) > len(confirmed):
                    # Normal progress through the text, not a recovery.
                    confirmed = observed
                    pending = text[len(observed):]
                    continue
                # No new characters: this is now a proven-missing suffix, and it
                # may be resent only from a verified insertion point.
                if queue['depth'] is None:
                    report.status = AMBIGUOUS
                    report.detail = 'cannot read the keyboard ring; not resending'
                    return report
                if cursor != (before['row'], start_col + len(observed)):
                    report.status = AMBIGUOUS
                    report.detail = 'insertion point is not at the end of the prefix'
                    return report
                if report.recoveries >= self.max_recoveries:
                    report.status, report.detail = AMBIGUOUS, 'recovery budget exhausted'
                    return report
                report.recoveries += 1
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

        `expect` is ``'change'`` (the screen must differ from the snapshot taken
        before the press) or ``'restore'`` (it must equal `reference`, a snapshot
        the caller kept earlier). Without an expectation, a difference is reported
        as a change, never as success.
        """
        if not codes:
            raise ValueError('at least one scancode is required')
        if expect not in (None, 'change', 'restore'):
            raise ValueError('expect must be change, restore or None')
        before = self.snapshot()
        if expect == 'restore':
            if not isinstance(reference, dict) or reference.get('basis') != before['basis']:
                raise ValueError('restore needs a snapshot of the same basis')
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
        if expect is None:
            report.status = 'changed' if changed else UNCHANGED
            return report
        satisfied = changed if expect == 'change' else after['digest'] == reference['digest']
        report.status = OBSERVED if satisfied else (UNCHANGED if not changed else AMBIGUOUS)
        report.evidence.observed = satisfied
        return report

    def pointer(self, dx, dy, buttons=0, *, expect=None, reference=None, settle_ms=None):
        """Move the configured mouse and optionally press buttons; observe the frame.

        A changed frame proves the pointer was redrawn, not that a control was hit.
        A click's effect must be established by a state expectation of its own.
        """
        before = self.snapshot()
        if expect == 'restore':
            if not isinstance(reference, dict) or reference.get('basis') != before['basis']:
                raise ValueError('restore needs a snapshot of the same basis')
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
        if expect is None:
            report.status = 'changed' if changed else UNCHANGED
            return report
        satisfied = changed if expect == 'change' else after['digest'] == reference['digest']
        report.status = OBSERVED if satisfied else (UNCHANGED if not changed else AMBIGUOUS)
        report.evidence.observed = satisfied
        return report

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
