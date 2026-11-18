"""Archival and standard-format projections for Calendar and Address Book."""
from .. import interchange
from ..addressbook.personal import Contact
from .model import Conversion, Diagnostic
from .render import html_page, html_table, html_text, json_bytes


def _escape_text(value, *, structured=False):
    escaped = (value.replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n')
               .replace('\n', '\\n').replace(',', '\\,'))
    return escaped.replace(';', '\\;') if structured else escaped


def _fold_lines(lines):
    """Use UTF-8, CRLF and at most 75 octets per physical line."""
    output = bytearray()
    for line in lines:
        width = 0
        for character in line:
            encoded = character.encode('utf-8')
            if width + len(encoded) > 75:
                output.extend(b'\r\n ')
                width = 1
            output.extend(encoded)
            width += len(encoded)
        output.extend(b'\r\n')
    return bytes(output)


def _interchange(conversion, export, snapshot):
    try:
        result = export(snapshot)
    except interchange.InterchangeError as exc:
        conversion.diagnostics.append(Diagnostic(
            'interchange_' + exc.code, 'omission',
            f'Strict version 1 interchange unavailable. {exc}', exc.path))
    else:
        conversion.artifacts['interchange-v1.json'] = json_bytes(result.document)
        conversion.diagnostics.extend(
            Diagnostic('interchange_' + issue.code, 'omission', issue.message, issue.path)
            for issue in result.issues
        )


def _icalendar(name, number, appointments, digest):
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//DeskMate Preservation Workbench//Phase I//EN',
        'CALSCALE:GREGORIAN', 'X-WR-CALNAME:' + _escape_text(name, structured=True),
        'X-DESKMATE-DTSTAMP-POLICY:FIXED-EXPORT-PLACEHOLDER',
    ]
    for row in appointments:
        day = row.date.replace('-', '')
        start, end = (value.replace(':', '') for value in (row.start_time, row.end_time))
        description = _escape_text(row.description, structured=True)
        alarm = 'TRUE' if row.alarm_enabled else 'FALSE'
        lines.extend([
            'BEGIN:VEVENT',
            f'UID:{digest}-{number}-{row.record_id}@deskmate-preservation.invalid',
            'DTSTAMP:19800101T000000Z',
            f'DTSTART:{day}T{start}00', f'DTEND:{day}T{end}00',
            'SUMMARY:' + description, 'DESCRIPTION:' + description,
            f'X-DESKMATE-ALARM-ENABLED:{alarm}', 'END:VEVENT',
        ])
    return _fold_lines([*lines, 'END:VCALENDAR'])


def _ordinary_event(row):
    return (None not in (row.date, row.start_time, row.end_time, row.description, row.alarm_enabled)
            and row.raw_fields['Duration'] == '')


def _appointment_row(row):
    return tuple(value if value is not None else 'Undecoded' for value in
                 (row.date, row.start_time, row.end_time, row.description,
                  {True: 'On', False: 'Off'}.get(row.alarm_enabled)))


def convert_calendar(snapshot, filename):
    content = snapshot.to_dict()
    content['standard_exports'] = []
    conversion = Conversion(content, [
        Diagnostic('calendar_sdk_codec_scope', 'notice', 'Date and time decoding uses the bounded SDK profile. '
                   'Only controlled combinations have native verification.'),
        Diagnostic('calendar_control_records_omitted', 'omission',
                   'Native internal/control records are retained in content.json and excluded from appointment exports.'),
        Diagnostic('calendar_opaque_fields', 'opaque',
                   'Raw Protected and Duration values, record locators and storage metadata are retained in JSON.'),
    ])
    if snapshot.metadata['retired_rows']:
        conversion.diagnostics.append(Diagnostic(
            'calendar_retired_rows_omitted', 'omission', 'Retired native rows are retained in content.json only.'))
    _interchange(conversion, interchange.export_calendar, snapshot)
    body = []
    for number, named in enumerate(snapshot.calendars, 1):
        appointments = []
        for row in named.appointments:
            if _ordinary_event(row):
                appointments.append(row)
            else:
                conversion.diagnostics.append(Diagnostic(
                    'calendar_ical_record_omitted', 'omission',
                    'The record is outside the supported ordinary appointment profile. '
                    'Decoded fields, raw bytes and reader warnings are retained in content.json.',
                    f'{named.name}, file offset {row.offset}'))
        section = f'<section><h2>{html_text(named.name)}</h2>'
        if appointments:
            path = f'calendar-{number:02}.ics'
            conversion.artifacts[path] = _icalendar(named.name, number, appointments, snapshot.sha256)
            content['standard_exports'].append({
                'calendar': named.name, 'path': path, 'event_count': len(appointments),
            })
            section += f'<p><a href="{path}">Download iCalendar</a></p>'
        else:
            conversion.diagnostics.append(Diagnostic(
                'calendar_ical_no_events', 'notice',
                'No supported ordinary appointments for iCalendar in this calendar.', named.name))
        if named.appointments:
            section += html_table(('Date', 'Start', 'End', 'Description', 'Alarm'),
                                  map(_appointment_row, named.appointments), 'Indexed appointment rows')
        else:
            section += '<p>No indexed appointment rows.</p>'
        body.append(section + '</section>')
    if content['standard_exports']:
        conversion.diagnostics.extend([
            Diagnostic('calendar_ical_floating_time', 'notice',
                       'iCalendar uses floating local times and snapshot-scoped event IDs. '
                       'Required export timestamps use a fixed placeholder.'),
            Diagnostic('calendar_ical_alarm_delivery_omitted', 'omission',
                       'The measured alarm state is stored in a custom iCalendar property. '
                       'Alarm triggers and recurrence rules are outside the recovered profile.'),
        ])
    conversion.artifacts['preview.html'] = html_page(
        filename, 'DeskMate Calendar · indexed appointments', ''.join(body), diagnostics=conversion.diagnostics)
    return conversion


def _vcard(contact):
    surname, given, city = (_escape_text(value, structured=True) for value in
                            (contact.last_name, contact.first_name, contact.city))
    name = _escape_text(f'{contact.first_name} {contact.last_name}')
    lines = ['BEGIN:VCARD', 'VERSION:4.0', f'FN:{name}', f'N:{surname};{given};;;']
    if city:
        lines.append(f'ADR:;;;{city};;;')
    if contact.work_phone:
        lines.append('TEL;TYPE=work;VALUE=text:' + _escape_text(contact.work_phone))
    return [*lines, 'END:VCARD']


def convert_addressbook(snapshot, filename):
    content = snapshot.to_dict()
    conversion = Conversion(content, [
        Diagnostic('addressbook_measured_fields', 'notice',
                   'First name, last name, city and work phone are the measured contact fields.'),
        Diagnostic('addressbook_opaque_fields', 'opaque',
                   'Other field bytes are in content.json. Their meanings, including date fields, remain opaque. '
                   'NAMES and CONFIG tables are in the original file.'),
    ])
    if len(snapshot.contacts) > 1:
        conversion.diagnostics.append(Diagnostic(
            'addressbook_native_order_scope', 'notice',
            'Contacts are in native index order. General native collation remains unverified.'))
    _interchange(conversion, interchange.export_addressbook, snapshot)
    cards, records = [], []
    for row in snapshot.contacts:
        known = row.known_fields
        records.append([value if value is not None else 'Undecoded' for value in
                        (known['first_name'], known['last_name'], known['city'], known['work_phone'])])
        location = f'Contact at file offset {row.row.offset}'
        try:
            contact = Contact(**known)
        except ValueError as exc:
            conversion.diagnostics.append(Diagnostic(
                'addressbook_vcard_record_omitted', 'omission', f'vCard skipped this contact. {exc}', location))
            continue
        if row.opaque_fields != interchange.DEFAULT_OPAQUE_CONTACT:
            conversion.diagnostics.append(Diagnostic(
                'addressbook_vcard_opaque_fields_omitted', 'omission',
                'Nondefault opaque fields are retained in content.json and omitted from this vCard.', location))
        cards.extend(_vcard(contact))
    body = ''
    if cards:
        conversion.artifacts['contacts.vcf'] = _fold_lines(cards)
        body = '<p><a href="contacts.vcf">Download vCards</a></p>'
    if records:
        body += html_table(('First name', 'Last name', 'City', 'Work phone'), records, 'Indexed contacts')
    else:
        body += '<p>No indexed contacts.</p>'
    conversion.artifacts['preview.html'] = html_page(
        filename, 'DeskMate Address Book · indexed contacts', body, diagnostics=conversion.diagnostics)
    return conversion
