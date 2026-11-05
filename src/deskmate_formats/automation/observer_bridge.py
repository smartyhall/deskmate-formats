"""Allowlisted publication from an existing, serialized native owner."""

from dataclasses import replace
from hashlib import sha256
from time import monotonic

from ..observer.frames import Frame, MAX_COUNTER
from ..observer.publication import (
    Action, Connection, ErrorCode, Observation, decode_cp437, host_time_ms,
)

RESET_FIELDS = ('hard_resets', 'soft_resets', 'last_reset_ms')
CHECKPOINT_FIELDS = ('ms', 'frames', *RESET_FIELDS)


def matches_checkpoint(approval, sample):
    reset, (ms, frames, held, paused, *_) = sample
    return (held and not paused
            and (ms, frames, *reset) == tuple(approval[key] for key in CHECKPOINT_FIELDS))


class OwnerPublication:
    """Per-instance publisher. Only frame preparation runs outside the owner lock."""

    def __init__(self, stream, approval):
        self.stream = stream
        self.approval = approval
        self.sequence = 0
        self.dropped = 0
        self.pending = None

    def track(self, sample):
        if self.approval and not matches_checkpoint(self.approval, sample):
            self.approval = None

    def begin(self):
        self.sequence += 1
        if self.pending == self.sequence - 1:
            # The encoder retains its one slot until it returns. Newer samples
            # can publish immediately and supersede that result.
            self.dropped += 1
        return self.stream.view().observation

    def unavailable(self, generation, *, error=None, retain=False):
        previous = self.begin()
        retain = retain and previous is not None and previous.generation == generation
        self.stream.publish(Observation(
            self.stream.machine.instance_id, self.sequence, generation, host_time_ms(),
            previous.emulated_ms if retain else None, None, None,
            action=Action.CONNECTION, dropped_updates=self.dropped,
            connection=Connection.ERROR if error is not None else Connection.DISCONNECTED,
            error=error, screen=previous.screen if retain and self.approval else None,
            frame=previous.frame if retain and self.approval else None,
        ))

    def record(self, generation, sample, observed_at, sampled_at, *, lines=None,
               png=None, captured_at=None):
        ms, _, held, paused, *_ = sample[1]
        if ms > MAX_COUNTER:
            self.unavailable(generation, error=ErrorCode.OBSERVATION_FAILED)
            return None
        previous = self.begin()
        screen = frame = None
        approved_png = None
        if self.approval:
            if (previous is not None and previous.generation == generation
                    and previous.connection is Connection.CONNECTED):
                screen, frame = previous.screen, previous.frame
                if frame is not None and frame.captured_at_ms > observed_at:
                    frame = None
            if lines is not None:
                screen = None
                if 'screen_sha256' in self.approval:
                    try:
                        candidate = decode_cp437(line.encode('cp437') for line in lines)
                    except ValueError:
                        pass  # A wider native text mode has no browser representation.
                    else:
                        if sha256(candidate.encode('utf-8')).hexdigest() == self.approval['screen_sha256']:
                            screen = candidate
            if png is not None:
                if sha256(png).hexdigest() == self.approval.get('framebuffer_sha256'):
                    approved_png = png
                else:
                    frame = None

        if approved_png is not None and self.pending is not None:
            self.dropped += 1
            approved_png = None
        observation = Observation(
            self.stream.machine.instance_id, self.sequence, generation, observed_at,
            ms, held, paused, dropped_updates=self.dropped, screen=screen, frame=frame,
        )
        if approved_png is None:
            self.stream.publish(observation, sampled_at=sampled_at)
            return None
        self.pending = observation.sequence
        return observation, sampled_at, approved_png, captured_at

    def finish(self, observation, sampled_at, frame):
        self.pending = None
        if observation.sequence == self.sequence:
            if frame is None:
                self.dropped += 1
            self.stream.publish(replace(
                observation, frame=frame, dropped_updates=self.dropped,
            ), sampled_at=sampled_at)


def prepare_frame(observation, png, captured_at):
    """Bounded by native and observer limits. Render timestamps are unknown."""
    try:
        return Frame(png, generation=observation.sequence, captured_at_ms=captured_at,
                     latest_rendered=True)
    except (ValueError, RuntimeError, OSError):
        return None  # Native MCP result remains usable if browser conversion fails.


def sample_times():
    return host_time_ms(), monotonic()
