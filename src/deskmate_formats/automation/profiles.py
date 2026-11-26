"""Application-shaped verification profiles for the verified input facility.

The generic layer owns delivery, pacing, bounded recovery and evidence. These
profiles own what a *successful* interaction looks like in one kind of
application, and they never upgrade a weak observation into a strong claim:

* `DosPrompt` separates entry (the command line is on screen, the cursor is at
  its end) from execution (Enter was sent and the prompt came back), and never
  replays a command whose execution is uncertain.
* `ScreenStates` recognises named graphics states by snapshot digest, which is
  deterministic for one guest and build but says nothing about *why* the pixels
  differ. A state that was never captured cannot be recognised.
"""
from dataclasses import dataclass, field

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
    steps: list = field(default_factory=list)

    @property
    def succeeded(self):
        return (self.entered == OBSERVED and self.submitted
                and self.prompt_returned is True and self.output_matched is not False)

    def as_dict(self):
        return {'command': self.command, 'entered': self.entered,
                'submitted': self.submitted, 'prompt_returned': self.prompt_returned,
                'output_matched': self.output_matched, 'detail': self.detail,
                'succeeded': self.succeeded, 'steps': list(self.steps),
                'entry': self.entry.as_dict() if isinstance(self.entry, Report) else self.entry}


class DosPrompt:
    """Text-mode DOS command entry and execution at a known prompt anchor."""

    def __init__(self, facility, anchor, occurrence='last', prompt_timeout_ms=30000):
        if facility.basis() != 'text':
            raise ProfileError('DosPrompt requires a text-mode guest')
        self.input = facility
        self.anchor = anchor
        self.occurrence = occurrence
        self.prompt_timeout_ms = prompt_timeout_ms

    def prompt_text(self):
        """Return what follows the prompt, read without stripping spaces."""
        return self.input.row_after(self.anchor, self.occurrence)

    def at_empty_prompt(self):
        return self.prompt_text().strip(' ') == ''

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

    def submit(self, command, *, expect_output=None, timeout_ms=60000):
        """Type `command`, press Enter, and report entry and execution separately.

        Nothing is retried. If the command line is not exactly on screen and the
        cursor not at its end, Enter is not sent at all; if it is sent and the
        prompt does not return, the execution state is reported as unknown rather
        than the command being replayed.
        """
        result = CommandResult(command, 'not attempted')
        entry = self.input.type_text(command, anchor=self.anchor,
                                     occurrence=self.occurrence)
        result.entry = entry
        result.entered = entry.status
        result.steps.append({'stage': 'entry', 'status': entry.status,
                             'bursts': entry.bursts, 'recoveries': entry.recoveries})
        if entry.status != OBSERVED:
            result.detail = 'command line not verified; Enter withheld'
            return result
        self.input.press(0x1C)
        result.submitted = True
        result.steps.append({'stage': 'submit', 'ms': self.input.client.status()['ms']})
        if expect_output is not None:
            reply = self.input.client.wait_text(expect_output, timeout_ms)
            result.output = reply
            result.output_matched = reply['matched'] is True
            result.steps.append({'stage': 'output', 'needle': expect_output,
                                 'matched': result.output_matched, 'ms': reply['ms']})
        result.prompt_returned = self.await_empty_prompt()
        result.steps.append({'stage': 'prompt', 'returned': result.prompt_returned,
                             'ms': self.input.client.status()['ms']})
        if result.prompt_returned is False:
            result.detail = 'prompt did not return; execution state unknown'
        elif result.output_matched is False:
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
        """Send keys and check the screen moved from `before` to `after`.

        A change that lands on neither named state is reported as ambiguous: it
        is neither the expected transition nor a no-op.
        """
        started = self.matches(before)
        report = self.input.press(*codes, pace_ms=pace_ms)
        reached = self.matches(after)
        report.status = OBSERVED if (started and reached) else 'ambiguous'
        report.evidence.observed = started and reached
        report.detail = {'started_from': before, 'started': started,
                         'expected': after, 'reached': reached}
        return report
