"""Enter an Award setup menu on a dedicated held machine via native keyboard."""
import argparse
import importlib
import json
from pathlib import Path

box = importlib.import_module('86box_client')
TEXT_MODES = {0, 1, 2, 3, 7}
DELETE = 0x153


def award_main(rows):
    screen = '\n'.join(line.upper() for line, _ in rows)
    return ('CMOS SETUP UTILITY' in screen and 'STANDARD CMOS SETUP' in screen
            and 'BIOS FEATURES SETUP' in screen)


def enter_setup(client, machine_id, max_ms=15000):
    identity = client.info()
    status = client.status()
    start = status['ms']
    if (identity['machine'] != machine_id or not status['held'] or status['paused']
            or not 0 <= start - identity['last_reset_ms'] <= 300):
        raise ValueError('expected the named, held machine at the beginning of POST')
    while status['ms'] - start < max_ms:
        if status['bios_mode'] in TEXT_MODES and status['w']:
            rows = client.text_attributes()
            if award_main(rows):
                return status, rows
            screen = '\n'.join(line.upper() for line, _ in rows)
            if 'STARTING WINDOWS' in screen or 'MICROSOFT WINDOWS 98 STARTUP MENU' in screen:
                raise RuntimeError('guest boot began before the Award menu appeared')
        client.tap(DELETE)
        status = client.advance(200)['status']
    raise TimeoutError('Award main menu did not appear in the specified emulated interval')


def open_highlighted(client, label, attribute):
    status = client.status()
    if not status['held'] or status['paused']:
        raise ValueError('expected a held, unpaused Award menu')
    before = client.text_attributes()
    if not award_main(before):
        raise ValueError('Award main menu is absent')
    label = label.upper()
    matches = []
    for line, attributes in before:
        column = line.upper().find(label)
        if column >= 0:
            matches.append(attributes[column:column + len(label)])
    if len(matches) != 1 or matches[0] != bytes([attribute]) * len(label):
        raise ValueError('specified menu item is not uniquely highlighted')
    client.tap(0x1c)
    status = client.advance(250)['status']
    after = client.text_attributes()
    if award_main(after) or not any(label in row.upper() for row, _ in after):
        raise RuntimeError('the specified submenu was not observed')
    return status, after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--machine', type=Path, required=True)
    parser.add_argument('--machine-id', required=True)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('output', type=Path, help='new private receipt')
    parser.add_argument('--highlighted', nargs=2, metavar=('LABEL', 'ATTRIBUTE'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output receipt already exists')
    with box.Client(args.machine / 'automation.token', args.port, timeout=30) as client:
        if args.highlighted:
            if client.info()['machine'] != args.machine_id:
                raise ValueError('unexpected machine identity')
            label, attribute = args.highlighted
            status, rows = open_highlighted(client, label, int(attribute, 0))
        else:
            status, rows = enter_setup(client, args.machine_id)
    result = {'status': status, 'rows': [{'text': line, 'attrs': attrs.hex()} for line, attrs in rows]}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'machine': args.machine_id, 'port': args.port, 'ms': status['ms']}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        raise SystemExit(f'Award setup: {exc}')
