"""Application-shaped verification profiles for the verified input facility.

The generic layer owns delivery, pacing, bounded recovery and evidence. These
profiles own what a *successful* interaction looks like in one kind of
application, and they never upgrade a weak observation into a strong claim:

* `DosPrompt` separates entry (the command line is on screen, the cursor at its
  end) from execution (Enter sent, an empty prompt returned below the command),
  matches expected output only in rows that could not have been on screen before
  the command was submitted, and reports ambiguity when it cannot tell.
* `ScreenStates` recognises named graphics states by snapshot digest and withholds
  input when the expected starting state is not the current one.
"""
from dataclasses import dataclass, field
import hashlib

from .input import OBSERVED, Report, UNCHANGED


class ProfileError(ValueError):
    """A profile was used outside the guest state or mode it supports."""


@dataclass
class CommandResult:
    """Outcome of one command line, with each stage kept separate."""

    command: str
    entered: str
    submitted: bool = False
    prompt_returned: object = None
    output_matched: object = None
    detail: object = None
    entry: object = None
    output: object = None
    fresh_rows: object = None
    pre_enter: object = None
    settled: object = None
    steps: list = field(default_factory=list)

    @property
    def left_text(self):
        """True when the guest left text mode after Enter, as an application does."""
        return self.prompt_returned is None and self.submitted

    @property
    def succeeded(self):
        return (self.entered == OBSERVED and self.submitted
                and self.prompt_returned is True and self.output_matched is not False)

    def as_dict(self):
        return {'command': self.command, 'entered': self.entered,
                'submitted': self.submitted, 'prompt_returned': self.prompt_returned,
                'output_matched': self.output_matched, 'detail': self.detail,
                'succeeded': self.succeeded, 'fresh_rows': self.fresh_rows,
                'pre_enter': self.pre_enter, 'settled': self.settled,
                'left_text': self.left_text, 'steps': list(self.steps),
                'entry': self.entry.as_dict() if isinstance(self.entry, Report) else self.entry}


def _scroll_alignment(before_rows, after_rows):
    """Return ``(shift, fresh_rows)`` under a vertical-scroll model.

    A DOS screen scrolls: old rows move up and disappear rather than staying in
    place. For each candidate shift, every row of the new screen is compared with
    the row it would have come from; rows that still differ, and rows revealed
    below the old screen, are the only ones that can carry new output. The
    smallest shift that leaves the fewest unexplained rows wins, so a large
    apparent shift is never invented to freshen old text.
    """
    best = None
    for shift in range(0, len(before_rows) + 1):
        fresh = []
        for index, row in enumerate(after_rows):
            source = index + shift
            if source >= len(before_rows):
                if row.strip(' '):
                    fresh.append(row)
            elif row != before_rows[source]:
                fresh.append(row)
        key = (len(fresh), shift)
        if best is None or key < best[0]:
            best = (key, shift, fresh)
        if not fresh:
            break
    if best is None:
        return 0, list(after_rows)
    return best[1], best[2]


def fresh_region(before_rows, after_rows):
    """Return the rows that are new since `before_rows`, with the scroll shift.

    Comparing the joined screen as one string is not enough: a scroll moves old
    text up, where a common-prefix comparison reads it as new. Only rows that
    cannot be explained by a vertical shift count as fresh.
    """
    if not isinstance(before_rows, (list, tuple)) or not isinstance(after_rows, (list, tuple)):
        raise TypeError('row lists are required')
    shift, rows = _scroll_alignment(list(before_rows), list(after_rows))
    return {'shift': shift, 'rows': rows, 'text': '\n'.join(rows),
            'changed': bool(rows)}


def fresh_text(before_rows, after_rows):
    """Return the screen text that changed, ignoring text preserved word for word."""
    return fresh_region(before_rows, after_rows)['text']


class DosPrompt:
    """Text-mode DOS command entry and execution at a known prompt anchor."""

    def __init__(self, facility, anchor, occurrence='last', prompt_timeout_ms=30000,
                 quiet_ms=250):
        if facility.basis() != 'text':
            raise ProfileError('DosPrompt requires a text-mode guest')
        self.input = facility
        self.anchor = anchor
        self.occurrence = occurrence
        self.prompt_timeout_ms = prompt_timeout_ms
        self.quiet_ms = quiet_ms

    def prompt_text(self):
        """Return what follows the prompt, read without stripping spaces."""
        return self.input.row_after(self.anchor, self.occurrence)

    def at_empty_prompt(self):
        return self.prompt_text().strip(' ') == ''

    def new_text(self, before_rows):
        return fresh_text(before_rows, self.input.text_lines())

    def await_empty_prompt(self, timeout_ms=None):
        """Step until the prompt row is empty again, or the budget ends."""
        budget = self.prompt_timeout_ms if timeout_ms is None else timeout_ms
        spent = 0
        while spent < budget:
            try:
                if self.at_empty_prompt():
                    return True
            except ValueError:
                pass
            self.input.client.step(100)
            spent += 100
        try:
            return self.at_empty_prompt()
        except ValueError:
            return False

    def await_new_prompt(self, before_rows, timeout_ms=None):
        """Wait for an empty prompt at the bottom of a screen that has changed.

        The prompt must be the bottom-most non-blank row, it must be empty after
        the anchor, and the BIOS cursor must sit at its end. The screen must also
        differ from `before_rows`, so a prompt that was already on screen cannot
        be mistaken for the result of this command.

        Returns ``True`` for a new prompt, ``False`` for a timeout, and ``None``
        when the guest left text mode: an application that takes over the screen
        has produced neither a prompt nor a proven failure.
        """
        budget = self.prompt_timeout_ms if timeout_ms is None else timeout_ms
        spent = 0
        while spent <= budget:
            if self.input.basis() != 'text':
                return None
            lines = self.input.text_lines()
            try:
                cursor = self.input.cursor()
            except ValueError:
                cursor = None
            if lines != before_rows:
                for index in range(len(lines) - 1, -1, -1):
                    row = lines[index]
                    if not row.strip(' '):
                        continue
                    column = row.find(self.anchor)
                    if (column >= 0 and not row[column + len(self.anchor):].strip(' ')
                            and cursor == (index, column + len(self.anchor))):
                        return True
                    break
            self.input.client.step(100)
            spent += 100
        return False

    def _await_output(self, needle, before_rows, timeout_ms):
        spent = 0
        region = fresh_region(before_rows, self.input.text_lines())
        while True:
            if needle in region['text']:
                return True, region
            if spent >= timeout_ms:
                return False, region
            self.input.client.step(50)
            spent += 50
            region = fresh_region(before_rows, self.input.text_lines())

    def submit(self, command, *, expect_output=None, timeout_ms=60000):
        """Type `command`, press Enter, and report entry and execution separately.

        Nothing is retried. If the command line is not exactly on screen and the
        cursor not at its end, Enter is not sent at all; if it is sent and a new
        prompt does not appear, the execution state is reported as unknown rather
        than the command being replayed.

        The reference for "new" output is captured after entry has been verified
        and immediately before Enter, so the command's own echo - which is on
        screen before submission - can never be credited as execution output.
        """
        result = CommandResult(command, 'not attempted')
        entry = self.input.type_text(command, anchor=self.anchor,
                                     occurrence=self.occurrence)
        result.entry = entry
        result.entered = entry.status
        result.steps.append({'stage': 'entry', 'status': entry.status,
                             'bursts': entry.bursts, 'recoveries': entry.recoveries,
                             'limitations': list(entry.evidence.limitations)})
        if entry.status != OBSERVED:
            result.detail = 'command line not verified; Enter withheld'
            return result
        ready = self.input.readiness()
        result.steps.append({'stage': 'pre-enter', 'ok': ready['ok'],
                             'pending': ready['pending'], 'limited': ready['limited'],
                             'queue': ready['queue'], 'automation': ready['automation']})
        if not ready['ok']:
            result.detail = 'input still pending; Enter withheld'
            return result
        before_rows = self.input.text_lines()
        try:
            before_cursor = self.input.cursor()
        except ValueError:
            before_cursor = None
        result.pre_enter = {
            'digest': hashlib.sha256('\n'.join(before_rows).encode('utf-8')).hexdigest(),
            'cursor': before_cursor, 'rows': len(before_rows)}
        self.input.press(0x1C)
        result.submitted = True
        result.steps.append({'stage': 'submit', 'ms': self.input.client.status()['ms']})
        if expect_output is not None:
            matched, region = self._await_output(expect_output, before_rows, timeout_ms)
            result.output = {'matched': matched, 'fresh': region['text'][-400:],
                             'shift': region['shift']}
            result.output_matched = matched
            result.fresh_rows = region['text'][-400:]
            result.steps.append({'stage': 'output', 'needle': expect_output,
                                 'matched': matched, 'shift': region['shift'],
                                 'ms': self.input.client.status()['ms']})
        result.prompt_returned = self.await_new_prompt(before_rows)
        result.steps.append({'stage': 'prompt', 'returned': result.prompt_returned,
                             'ms': self.input.client.status()['ms']})
        if result.prompt_returned is None:
            result.detail = 'guest left the text screen; execution state unknown'
            return result
        if result.prompt_returned is False:
            result.detail = 'no new prompt appeared; execution state unknown'
            return result
        # A prompt that stops changing corroborates completion; a screen that is
        # still scrolling or rewriting means output may still be arriving.
        result.settled = self.input.await_quiet(quiet_ms=self.quiet_ms, budget_ms=2000)
        result.steps.append({'stage': 'settle', 'quiet': result.settled,
                             'ms': self.input.client.status()['ms']})
        if result.output_matched is False:
            result.detail = 'command ran but the expected output did not appear'
        return result


class ScreenStates:
    """Named reference states for a graphics-mode application.

    Captures are taken by the caller during an authorized session; digests are
    specific to that guest, build and configuration, so they belong in private
    recipes rather than in this module.
    """

    def __init__(self, facility, states=None):
        if facility.basis() != 'frame':
            raise ProfileError('ScreenStates requires a graphics-mode guest')
        self.input = facility
        self.states = dict(states or {})

    def capture(self, name):
        """Record the current frame under `name` and return its snapshot."""
        snapshot = self.input.snapshot()
        self.states[name] = snapshot
        return snapshot

    def matches(self, name):
        """Return True only if `name` was captured and the screen equals it."""
        if name not in self.states:
            raise ProfileError(f'unknown screen state: {name}')
        return self.input.snapshot()['digest'] == self.states[name]['digest']

    def expect(self, name):
        """Return a report with an explicit observation result for `name`."""
        if name not in self.states:
            raise ProfileError(f'unknown screen state: {name}')
        observed = self.input.snapshot()
        matched = observed['digest'] == self.states[name]['digest']
        return Report('screen_state', OBSERVED if matched else UNCHANGED,
                      name, observed=observed['digest'],
                      detail={'expected': self.states[name]['digest'],
                              'basis': observed['basis']})

    def transition(self, *codes, before, after, pace_ms=None):
        """Send keys only if the screen is in `before`, then require `after`.

        Withholding the action on a failed precondition matters: sending
        navigation keys into an unexpected state is how a menu walk turns into a
        destructive click somewhere else.
        """
        if before not in self.states or after not in self.states:
            raise ProfileError(f'unknown screen state: {before!r} or {after!r}')
        report = Report('screen_state', UNCHANGED, ' '.join(hex(code) for code in codes))
        if not self.matches(before):
            report.detail = {'started_from': before, 'started': False,
                             'expected': after, 'reached': False,
                             'action': 'withheld'}
            return report
        sent = self.input.press(*codes, pace_ms=pace_ms)
        reached = self.matches(after)
        report.status = OBSERVED if reached else 'ambiguous'
        report.evidence = sent.evidence
        report.evidence.observed = reached
        report.observed = sent.observed
        report.steps = sent.steps
        report.detail = {'started_from': before, 'started': True,
                         'expected': after, 'reached': reached, 'action': 'sent'}
        return report
