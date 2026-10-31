"""Observed DeskMate 3.05 Calendar subset; no shared-engine claim."""
from .personal import CalendarParseError, parse_bytes, parse_file

__all__ = ["CalendarParseError", "parse_bytes", "parse_file"]
