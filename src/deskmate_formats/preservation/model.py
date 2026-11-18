"""Minimal shared types for the application-specific projections."""
from dataclasses import dataclass, field


class PreservationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def error_report(exc):
    if isinstance(exc, PreservationError):
        return {'error': exc.code, 'message': str(exc)}
    if isinstance(exc, FileExistsError):
        return {'error': 'output_exists', 'message': 'The output path already exists.'}
    return {'error': 'io_error', 'message': exc.strerror or 'The operating system reported an I/O error.'}


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
