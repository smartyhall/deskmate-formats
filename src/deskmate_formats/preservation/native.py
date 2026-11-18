"""Select a native reader by signature, then let it validate the profile."""
from dataclasses import dataclass

from .. import worksheet
from .model import PreservationError


MAX_SOURCE_BYTES = 1024 * 1024
APPLICATIONS = ('worksheet',)
EXTENSIONS = {'worksheet': 'wks'}


@dataclass(frozen=True)
class NativeDocument:
    application: str
    profile: str
    parser: str
    value: object


def open_native(data, application=None):
    if application is not None and application not in APPLICATIONS:
        raise PreservationError('unknown_application', f'Unknown application {application!r}.')
    if application is None:
        if data.startswith(b'\x0eWKS'):
            application = 'worksheet'
        else:
            raise PreservationError('unsupported_signature', 'No supported DeskMate signature found.')
    try:
        value = worksheet.parse_bytes(data)
    except worksheet.WorksheetFormatError as exc:
        raise PreservationError('invalid_native_profile', f'Worksheet reader rejected the source: {exc}') from exc
    return NativeDocument(application, 'worksheet-3.05-packed-lists', 'deskmate_formats.worksheet.parse_bytes', value)
