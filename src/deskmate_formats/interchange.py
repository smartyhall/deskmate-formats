"""Version 1 semantic JSON contract; native snapshots remain the preservation unit.

No timezone, recurrence, Unicode conversion or synchronization identity is inferred.
Storage IDs describe one native snapshot and may change after application edits.
"""
from dataclasses import asdict, dataclass
from datetime import date
import re

from .addressbook.personal import Contact
from .calendar.writer import Appointment, _validate

FORMAT = 'deskmate-interchange'
VERSION = 1


class InterchangeError(ValueError):
    def __init__(self, code, path, message):
        self.code, self.path = code, path
        super().__init__(f'{code} at {path}: {message}')


@dataclass(frozen=True)
class CalendarItem:
    appointment: Appointment
    storage_record_id: int | None = None


@dataclass(frozen=True)
class ContactItem:
    contact: Contact
    storage_record_id: int | None = None


@dataclass(frozen=True)
class ConversionIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ExportResult:
    document: dict
    issues: tuple[ConversionIssue, ...]


def _check(condition, code, path, message):
    if not condition:
        raise InterchangeError(code, path, message)


def load_document(document):
    """Validate a decoded JSON object and return typed values with snapshot IDs.

    Unknown properties fail. This validates semantics; native writer capacity and
    insertion policies still apply. Storage IDs never direct new-file allocation.
    """
    _check(type(document) is dict, 'invalid_document', '$', 'expected object')
    required = {'format', 'version', 'kind', 'items'}
    _check(required <= document.keys() and document.keys() <= required | {'source_sha256'},
           'unsupported_property', '$', 'expected format/version/kind/items and optional source_sha256')
    _check(document['format'] == FORMAT and type(document['version']) is int
           and document['version'] == VERSION, 'unsupported_version', '$.version', 'expected version 1')
    kind = document['kind']
    _check(kind in ('calendar', 'addressbook'), 'unsupported_kind', '$.kind', 'unknown kind')
    if 'source_sha256' in document:
        digest = document['source_sha256']
        _check(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest) is not None,
               'invalid_value', '$.source_sha256', 'expected lowercase SHA-256')
    values = document['items']
    _check(type(values) is list and len(values) <= 100, 'invalid_value', '$.items', 'expected 0..100 objects')
    result, ids = [], set()
    for n, item in enumerate(values):
        path = f'$.items[{n}]'
        fields = ({'date', 'start_minutes', 'end_minutes', 'description', 'alarm_enabled'}
                  if kind == 'calendar' else {'first_name', 'last_name', 'city', 'work_phone'})
        _check(type(item) is dict and fields <= item.keys() and item.keys() <= fields | {'storage_record_id'},
               'unsupported_property', path, 'missing required field or unknown property')
        ident = item.get('storage_record_id')
        if 'storage_record_id' in item:
            _check(type(ident) is int and 16 <= ident < 128 and ident not in ids,
                   'invalid_storage_id', path + '.storage_record_id', 'expected unique low snapshot ID')
            ids.add(ident)
        try:
            if kind == 'calendar':
                _check(type(item['date']) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['date']) is not None,
                       'invalid_value', path + '.date', 'expected ISO YYYY-MM-DD')
                _check(type(item['alarm_enabled']) is bool, 'invalid_value', path + '.alarm_enabled', 'expected boolean')
                event = Appointment(date.fromisoformat(item['date']), item['start_minutes'], item['end_minutes'],
                                    item['description'], protected_raw=b'q' if item['alarm_enabled'] else b'1')
                _validate(event, profile='sdk')
                result.append(CalendarItem(event, ident))
            else:
                result.append(ContactItem(Contact(**{k: item[k] for k in fields}), ident))
        except InterchangeError:
            raise
        except (ValueError, TypeError) as exc:
            raise InterchangeError('invalid_value', path, str(exc)) from exc
    if kind == 'calendar':
        keys = [(v.appointment.day, v.appointment.start_minutes) for v in result]
        _check(len(set(keys)) == len(keys), 'unsupported_tie', '$.items', 'simultaneous starts are unverified')
    return tuple(result)


def calendar_document(items, *, source_sha256=None):
    values = []
    for item in items:
        event = item.appointment
        value = {'date': event.day.isoformat(), 'start_minutes': event.start_minutes,
                 'end_minutes': event.end_minutes, 'description': event.description,
                 'alarm_enabled': {b'1': False, b'q': True}.get(event.protected_raw)}
        # Do not silently discard nonempty Duration/unknown Protected from Python callers.
        _validate(event, profile='sdk')
        if item.storage_record_id is not None:
            value['storage_record_id'] = item.storage_record_id
        values.append(value)
    document = {'format': FORMAT, 'version': VERSION, 'kind': 'calendar', 'items': values}
    if source_sha256 is not None:
        document['source_sha256'] = source_sha256
    load_document(document)
    return document


def addressbook_document(items, *, source_sha256=None):
    values = []
    for item in items:
        value = asdict(item.contact)
        if item.storage_record_id is not None:
            value['storage_record_id'] = item.storage_record_id
        values.append(value)
    document = {'format': FORMAT, 'version': VERSION, 'kind': 'addressbook', 'items': values}
    if source_sha256 is not None:
        document['source_sha256'] = source_sha256
    load_document(document)
    return document


def _minutes(value):
    hour, minute = value.split(':')
    return int(hour) * 60 + int(minute)


def export_calendar(database, *, lossy=False):
    """Export ordinary events. Explicit lossy mode skips unrepresentable rows."""
    _check(type(lossy) is bool, 'invalid_option', '$.options.lossy', 'expected explicit boolean')
    _check(len(getattr(database, 'calendars', ())) <= 1,
           'unsupported_calendars', '$.native.calendars',
           'version 1 has no calendar ownership field; multicalendar export is unsupported')
    items, issues = [], []
    for n, row in enumerate(database.appointments):
        path = f'$.native.appointments[{n}]'
        try:
            _check(None not in (row.date, row.start_time, row.end_time, row.description, row.alarm_enabled)
                   and row.raw_fields['Duration'] == '', 'unsupported_record', path,
                   'date/time/text/alarm or Duration outside ordinary profile')
            event = Appointment(date.fromisoformat(row.date), _minutes(row.start_time), _minutes(row.end_time),
                                row.description, protected_raw=b'q' if row.alarm_enabled else b'1')
            _validate(event, profile='sdk')
            items.append(CalendarItem(event, row.record_id))
        except (ValueError, TypeError) as exc:
            if not lossy:
                raise InterchangeError('unsupported_record', path, str(exc)) from exc
            issues.append(ConversionIssue('skipped_record', path, str(exc)))
    return ExportResult(calendar_document(items, source_sha256=database.sha256), tuple(issues))


DEFAULT_OPAQUE_CONTACT = {'Title': b'', 'Address': b'', 'State': b'', 'Zip': b'',
                          'CompanyName': b'', 'HomePhone': b'', 'DateOne': b'',
                          'NoteOne': b'Birthday', 'DateTwo': b'', 'NoteTwo': b'Anniversary',
                          'Notes': b'', 'Christmas': b'n'}


def export_addressbook(book, *, lossy=False):
    """Export verified fields; populated opaque fields require explicit loss."""
    _check(type(lossy) is bool, 'invalid_option', '$.options.lossy', 'expected explicit boolean')
    items, issues = [], []
    for n, row in enumerate(book.contacts):
        path = f'$.native.contacts[{n}]'
        opaque = row.opaque_fields != DEFAULT_OPAQUE_CONTACT
        _check(lossy or not opaque, 'unsupported_fields', path, 'nondefault opaque contact fields would be omitted')
        try:
            contact = Contact(**row.known_fields)
        except (ValueError, TypeError) as exc:
            if not lossy:
                raise InterchangeError('unsupported_record', path, str(exc)) from exc
            issues.append(ConversionIssue('skipped_record', path, str(exc)))
            continue
        if opaque:
            issues.append(ConversionIssue('omitted_opaque_fields', path, 'exported verified fields only'))
        items.append(ContactItem(contact, row.record_id))
    return ExportResult(addressbook_document(items, source_sha256=book.storage.sha256), tuple(issues))
