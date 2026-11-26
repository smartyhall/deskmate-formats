"""Bounded, verified guest input with explicit evidence levels.

The native automation protocol has four distinct levels between "a request was
sent" and "the application did what was intended". This module names them and
keeps them apart:

``ACKNOWLEDGED``
    The emulator replied to the socket request. Nothing about the guest follows.

``DELIVERED``
    The build's ``key`` command is a timed command: it forwards the first event,
    then emits the rest two emulated milliseconds apart and only replies after
    the last event has had its gap. The reply therefore means the emulated
    keyboard device was handed every event. It still says nothing about the BIOS
    keyboard buffer, the operating system, or an application.

``ACCEPTED``
    The guest's BIOS keyboard buffer drained (head equals tail). That is read
    from guest memory, so it shows the guest consumed the scan codes. It cannot
    show that any application acted on them.

``OBSERVED``
    An expectation the caller supplied is now visible in guest state: a string
    after an anchor on a text-mode row, or a framebuffer change (with an optional
    restoration check).

Recovery is deliberately narrow. The only automatic resend is a suffix the
caller's own observation proved was never delivered, and only when the observed
state is a strict prefix of the intended text. An unchanged or unclassifiable
state stops the operation with evidence instead of replaying input, because a
delivered keystroke and an ignored keystroke look identical from the socket.
"""
from dataclasses import dataclass, field
import hashlib

ACKNOWLEDGED = 'acknowledged'
DELIVERED = 'delivered'
ACCEPTED = 'accepted'
OBSERVED = 'observed'

TEXT_MODES = (0, 1, 2, 3, 7)
BIOS_KEY_HEAD = 0x41A
BIOS_KEY_TAIL = 0x41C
BIOS_KEY_START = 0x480
BIOS_KEY_END = 0x482


@dataclass
class Report:
    """One bounded input operation and what the evidence actually supports."""

    operation: str
    status: str            # observed | unchanged | ambiguous
    level: str
    sent: str
    observed: str | None = None
    missing: str | None = None
    attempts: int = 0
    steps: list = field(default_factory=list)

    def as_dict(self):
        return {'operation': self.operation, 'status': self.status, 'level': self.level,
                'sent': self.sent, 'observed': self.observed, 'missing': self.missing,
                'attempts': self.attempts, 'steps': list(self.steps)}


class VerifiedInput:
    """Drive one held machine with bounded bursts, verification and evidence."""

    def __init__(self, client, *, chunk=8, settle_step_ms=40, settle_quiet=2,
                 drain_timeout_ms=1000, verify_timeout_ms=1500, max_attempts=3):
        if type(chunk) is not int or not 1 <= chunk <= 64:
            raise ValueError('chunk must be 1..64 characters')
        if type(settle_step_ms) is not int or not 1 <= settle_step_ms <= 1000:
            raise ValueError('invalid settle step')
        if type(settle_quiet) is not int or settle_quiet < 1:
            raise ValueError('invalid settle quiet count')
        if type(max_attempts) is not int or not 1 <= max_attempts <= 8:
            raise ValueError('max_attempts must be 1..8')
        self.client = client
        self.chunk = chunk
        self.settle_step_ms = settle_step_ms
        self.settle_quiet = settle_quiet
        self.drain_timeout_ms = drain_timeout_ms
        self.verify_timeout_ms = verify_timeout_ms
        self.max_attempts = max_attempts
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

    def snapshot(self):
        """Hash the current observable state using the guest's own basis."""
        if self.basis() == 'text':
            rows = '\n'.join(self.text_lines())
            return {'basis': 'text', 'digest': hashlib.sha256(rows.encode('utf-8')).hexdigest()}
        digest, _ = self.settle_frame()
        return {'basis': 'frame', 'digest': digest}

    def settle_frame(self, max_ms=2000):
        """Advance until the framebuffer stops changing, and return its digest.

        Each sample is a hash of a freshly rendered frame on a held machine. A
        quiet run means the guest stopped redrawing; it does not prove the
        application finished working, only that the screen is stable enough to
        compare.
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
        not started drawing yet satisfies that trivially, and an all-black frame
        is a perfectly stable picture. This proves at least one redraw happened
        while the caller was watching, which is a precondition for treating any
        later frame as that application's state.
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

    def text_lines(self):
        return self.client.text()['lines']

    def bios_keyboard_queue(self):
        """Read the guest BIOS keyboard ring: start, end, head, tail and depth."""
        bda = self.client.memory(BIOS_KEY_START, 4)
        head = int.from_bytes(self.client.memory(BIOS_KEY_HEAD, 2), 'little')
        tail = int.from_bytes(self.client.memory(BIOS_KEY_TAIL, 2), 'little')
        start = int.from_bytes(bda[0:2], 'little')
        end = int.from_bytes(bda[2:4], 'little')
        # The BIOS extents are start..end with the pointers wrapping at `end`, so
        # the usable ring is end - start bytes holding one word per keystroke.
        size = end - start
        if 2 < size <= 64 and size % 2 == 0:
            depth = ((head - tail) % size) // 2
        else:
            size, depth = None, None
        return {'start': start, 'end': end, 'head': head, 'tail': tail,
                'size': size, 'depth': depth}

    def wait_drained(self, timeout_ms=None):
        """Advance until the BIOS keyboard buffer is empty, or the budget ends."""
        budget = self.drain_timeout_ms if timeout_ms is None else timeout_ms
        spent, state = 0, self.bios_keyboard_queue()
        while state['depth'] not in (0, None) and spent < budget:
            slice_ms = min(50, max(1, budget - spent))
            self.client.step(slice_ms)
            spent += slice_ms
            state = self.bios_keyboard_queue()
        return state

    def row_after(self, anchor, occurrence='only'):
        """Return the characters after `anchor` on the row that holds it.

        `occurrence` is ``'only'`` (the strict default: exactly one row may
        match), ``'last'`` (a scrolling terminal, where the bottom-most match is
        the live input line) or ``'first'``. No match is always an error.
        """
        if not isinstance(anchor, str) or not anchor:
            raise ValueError('anchor must be a non-empty string')
        if occurrence not in ('only', 'last', 'first'):
            raise ValueError('occurrence must be only, last or first')
        matches = []
        for line in self.text_lines():
            index = line.find(anchor)
            if index >= 0:
                matches.append(line[index + len(anchor):].rstrip())
        if not matches:
            raise ValueError(f'anchor {anchor!r} matched no row')
        if len(matches) > 1 and occurrence == 'only':
            raise ValueError(f'anchor {anchor!r} matched {len(matches)} rows')
        return matches[-1] if occurrence == 'last' else matches[0]

    # ---- operations ----

    def type_text(self, text, *, anchor, occurrence='only', pace_ms=None):
        """Type `text` after a text-mode anchor, verifying and recovering suffixes.

        Success requires the row after `anchor` to read exactly `text`. A short
        observation is retried only when it is a strict prefix of `text`, so a
        partially delivered burst resumes at the proven boundary. Anything else
        stops without replaying input.
        """
        if not isinstance(text, str) or not text:
            raise ValueError('text must be a non-empty string')
        status = self.client.status()
        if status.get('bios_mode') not in TEXT_MODES:
            raise ValueError('anchor verification requires a text-mode guest')
        before = self.row_after(anchor, occurrence)
        if before:
            raise ValueError(f'anchor is not at an empty input position: {before!r}')
        report = Report('type_text', 'unchanged', ACKNOWLEDGED, text)
        pending = text
        while pending:
            if report.attempts >= self.max_attempts:
                report.status, report.missing = 'ambiguous', pending
                return report
            report.attempts += 1
            burst = pending[:self.chunk]
            self.client.type_ascii(burst, pace_ms=pace_ms)
            report.level = DELIVERED
            queue = self.wait_drained()
            report.level = ACCEPTED if queue['depth'] == 0 else DELIVERED
            observed = self._observe_text(anchor, occurrence)
            report.observed = observed
            report.steps.append({'attempt': report.attempts, 'burst': burst,
                                 'observed': observed,
                                 'queue_depth': queue['depth'],
                                 'ms': self.client.status()['ms']})
            if observed == text:
                report.status, report.level, report.missing = 'observed', OBSERVED, None
                return report
            if observed and text.startswith(observed):
                pending = text[len(observed):]
                continue
            if observed:
                # The screen diverged inside the intended text, so the missing
                # portion is not a suffix we may simply resend.
                divergence = next((i for i in range(min(len(observed), len(text)))
                                   if observed[i] != text[i]), min(len(observed), len(text)))
                report.status, report.missing = 'ambiguous', text[divergence:]
            else:
                report.status, report.missing = 'unchanged', text
            return report
        return report

    def press(self, *codes, expect=None, reference=None, pace_ms=None):
        """Send key make/break events and report what the screen did.

        `expect` is ``'change'`` (the frame must differ from the settled starting
        frame) or ``'restore'`` (it must equal `reference`, a digest the caller
        kept from an earlier state). A graphics-mode screen has no text
        comparison here, so only a framebuffer observation is claimed.
        """
        if not codes:
            raise ValueError('at least one scancode is required')
        if expect not in (None, 'change', 'restore'):
            raise ValueError('expect must be change, restore or None')
        before = self.snapshot()
        if expect == 'restore':
            if not isinstance(reference, dict) or reference.get('basis') != before['basis']:
                raise ValueError('restore needs a snapshot of the same basis')
        report = Report('press', 'unchanged', ACKNOWLEDGED,
                        ' '.join(hex(code) for code in codes))
        for code in codes:
            self.client.tap(code)
            report.level = DELIVERED
            if pace_ms is not None:
                self.client.step(pace_ms)
        after = self.snapshot()
        report.observed = after['digest']
        report.steps.append({'basis': before['basis'], 'before': before['digest'],
                             'after': after['digest'], 'ms': self.client.status()['ms']})
        changed = after['digest'] != before['digest']
        if expect is None:
            report.status = 'changed' if changed else 'unchanged'
            return report
        satisfied = changed if expect == 'change' else after['digest'] == reference['digest']
        report.status = 'observed' if satisfied else ('unchanged' if not changed else 'ambiguous')
        if satisfied:
            report.level = OBSERVED
        return report

    def pointer(self, dx, dy, buttons=0, *, expect=None, settle_ms=None):
        """Move the configured mouse and optionally press buttons; observe the frame."""
        before, _ = self.settle_frame()
        report = Report('pointer', 'unchanged', ACKNOWLEDGED, f'{dx},{dy},{buttons}')
        self.client.mouse(dx, dy, buttons)
        report.level = DELIVERED
        if settle_ms is not None:
            self.client.step(settle_ms)
        after, meta = self.settle_frame()
        report.observed = after
        report.steps.append({'before': before, 'after': after, 'ms': meta['ms']})
        changed = after != before
        if expect is None:
            report.status = 'changed' if changed else 'unchanged'
            return report
        satisfied = changed if expect == 'change' else not changed
        report.status = 'observed' if satisfied else 'unchanged'
        if satisfied:
            report.level = OBSERVED
        return report

    def _observe_text(self, anchor, occurrence='only'):
        """Poll the anchored row until it stops changing or the budget runs out."""
        spent, previous = 0, None
        while True:
            try:
                current = self.row_after(anchor, occurrence)
            except ValueError:
                return None
            if current == previous:
                return current
            previous = current
            if spent >= self.verify_timeout_ms:
                return current
            self.client.step(50)
            spent += 50
