"""Select a native reader by signature, then let it validate the profile."""
from dataclasses import dataclass

from .. import draw, filer, music, sound, text, worksheet
from ..addressbook import personal as addressbook
from ..calendar import personal as calendar
from .model import PreservationError


MAX_SOURCE_BYTES = text.MAX_BYTES
MAX_TEXT_CONTROLS = 32_768
EXTENSIONS = {'worksheet': 'wks', 'text': 'doc', 'draw': 'fig', 'filer': 'fil',
              'calendar': 'cln', 'addressbook': 'adr', 'sound': 'snd', 'music': 'sng'}
APPLICATIONS = tuple(EXTENSIONS)
PROFILES = {
    'worksheet': (worksheet.parse_bytes, 'worksheet-3.05-packed-lists', {}),
    'text': (text.parse_bytes, 'text-3.05-formatted-doc',
             {'include_controls': True, 'control_limit': MAX_TEXT_CONTROLS}),
    'draw': (draw.parse_bytes, 'draw-3.05-14-fig', {}),
    'filer': (filer.parse_bytes, 'filer-3.05-bounded-dmdb', {}),
    'calendar': (calendar.parse_bytes, 'calendar-3.05-sdk', {'profile': 'sdk'}),
    'addressbook': (addressbook.parse_bytes, 'addressbook-3.05-ten-page', {}),
    'sound': (sound.parse_bytes, None, {}),
    'music': (music.parse_bytes, 'music-0c-sng-four-stream', {}),
}
SIGNATURES = {b'\x0eWKS': 'worksheet', b'\rDOC': 'text', b'\x14FIG': 'draw',
              b'\x03\0\0\0': 'addressbook', music.SIGNATURE: 'music'}


@dataclass(frozen=True)
class NativeDocument:
    application: str
    profile: str
    parser: str
    value: object


def _parse(data, application):
    parser, profile, options = PROFILES[application]
    try:
        value = parser(data, **options)
    except ValueError as exc:
        raise PreservationError('invalid_native_profile', f'{application} reader rejected the source: {exc}') from exc
    if application == 'text' and not value.header:
        profile = 'text-3.05-headerless-dos-stream'
    if application == 'sound':
        profile = value.profile
    return NativeDocument(application, profile, f'{parser.__module__}.{parser.__name__}', value)


def open_native(data, application=None):
    if application is not None:
        if application not in APPLICATIONS:
            raise PreservationError('unknown_application', f'Unknown application {application!r}.')
        return _parse(data, application)
    signature = data[:4]
    if signature in SIGNATURES:
        return _parse(data, SIGNATURES[signature])
    if signature == b'\x03FIL':
        # The Filer and Calendar readers validate mutually exclusive table sets.
        failures = []
        for candidate in ('filer', 'calendar'):
            try:
                return _parse(data, candidate)
            except PreservationError as exc:
                failures.append(str(exc))
        raise PreservationError('unsupported_dmdb_profile', ' | '.join(failures))
    if signature == b'\x10FIG':
        raise PreservationError('unsupported_draw_profile', 'The measured Draw reader supports the 14 FIG profile.')
    if data[:1] == b'\x1a' or data[44:46] == sound.LATER_SIGNATURE:
        return _parse(data, 'sound')
    detail = ' If this is a headerless DeskMate Text file, select --application text.'
    raise PreservationError('unsupported_signature', 'No supported DeskMate signature found.' + detail)
