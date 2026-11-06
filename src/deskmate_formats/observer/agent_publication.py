"""The immutable data boundary between the agent collector and the HTTP viewer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agents import AgentView, PublicEvent


@dataclass(frozen=True, slots=True)
class AgentSnapshot:
    collector: str = "disabled"
    agents: tuple[AgentView, ...] = ()
    events: tuple[PublicEvent, ...] = ()


class AgentPublication:
    def __init__(self):
        self._snapshot = AgentSnapshot()

    def view(self):
        """Read the current snapshot without performing I/O."""
        return self._snapshot
