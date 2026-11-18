"""Minimal shared types for the application-specific projections."""
from dataclasses import dataclass, field


class PreservationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    effect: str
    message: str
    location: str | None = None


@dataclass
class Conversion:
    content: dict
    diagnostics: list[Diagnostic] = field(default_factory=list)
    artifacts: dict[str, bytes] = field(default_factory=dict)
