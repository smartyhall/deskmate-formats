"""Controlled native probe of Corkboard's persisted header and live buffer.

The previous campaigns typed a note with the cursor at the end, so a header word
equal to the text length and one equal to the insertion position were
indistinguishable. This probe separates the two: the text is typed once, then
the cursor is moved without editing, and the document is extracted after every
save. Nothing here assumes an address, and nothing is retried.

Each step is one cold boot: open DeskMate, open Corkboard, apply the moves or
text, close with Escape (the save path), quit the emulator, then extract
``DESKMATE/DMCORKBD`` from the stopped image. The driver relaunches between
steps so every save is flushed and every reopen is genuinely from disk.

Phases:

``step``
    One named step from ``PLAN``.

``burst``
    The same environment, but the note is typed as one request per line instead
    of one keystroke at a time, with the automation counters around it. This is
    the failing condition the earlier campaign saw, recorded on the instrumented
    build so the layer where characters disappear can be named.

``extract``
    Offline: re-derive the documents from saved images.

Usage:
    python tools/experimental/corkboard_header_probe.py --phase step \
        --step s2-home --machine .../guest-idq-03 --port 8765 \
        --out .../corkboard-header-01
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
BOX_SPEC = importlib.util.spec_from_file_location('box_client', ROOT / 'tools/86box_client.py')
box = importlib.util.module_from_spec(BOX_SPEC)
BOX_SPEC.loader.exec_module(box)
DISK_SPEC = importlib.util.spec_from_file_location(
    'draw_disk', ROOT / 'tools/experimental/draw_disk.py')
draw_disk = importlib.util.module_from_spec(DISK_SPEC)
DISK_SPEC.loader.exec_module(draw_disk)
QUAL_SPEC = importlib.util.spec_from_file_location(
    'qualification', ROOT / 'tools/experimental/input_delivery_qualification.py')
qual = importlib.util.module_from_spec(QUAL_SPEC)
QUAL_SPEC.loader.exec_module(qual)

sys.path.insert(0, str(ROOT / 'src'))
from deskmate_formats.automation import input as inp          # noqa: E402
from deskmate_formats.automation import profiles              # noqa: E402

F10, DOWN, ENTER, ESC = 0x44, 0x150, 0x1C, 0x01
HOME, END, LEFT, RIGHT = 0x147, 0x14F, 0x14B, 0x14D
NOTE = 'ABCDEFGHIJ'
IMAGE = 'rsx-dos5-working.img'

# name -> (cursor moves before editing, text typed afterwards)
PLAN = {
    's0-empty': ((), ''),
    's1-ten-at-end': ((), NOTE),
    's2-home': ((HOME,), ''),
    's3-end': ((END,), ''),
    's4-right-four': ((HOME, RIGHT, RIGHT, RIGHT, RIGHT), ''),
    's5-left-three': ((END, LEFT, LEFT, LEFT), ''),
    's6-insert-mid': ((HOME, RIGHT, RIGHT, RIGHT, RIGHT, RIGHT), 'XY'),
    's7-backspace': ((HOME, RIGHT, RIGHT, RIGHT, RIGHT), '\b'),
    's8-newline': ((END,), '\rZZ'),
    's9-no-change': ((), ''),
    's10-position-probe': ((), 'Q'),
    # More lines than fit on screen: the only state so far that could make a
    # second header word track a scroll offset.
    's11-scroll': ((END,) + (ENTER,) * 22, 'ZZ'),
}


def open_corkboard(session):
    session.input.press(F10)
    session.input.press(*([DOWN] * 5))
    session.input.press(ENTER)
    for _ in range(2):
        session.input.await_render(4000, slice_ms=200)


def type_graphics(session, text, pause_ms=40):
    """Type in graphics mode, one request per character, and record the evidence."""
    before = session.input.snapshot()['digest']
    session.client.type_ascii(text)
    session.client.step(pause_ms)
    return {'text': text, 'frame_changed': session.input.snapshot()['digest'] != before,
            'input': session.client.input_state(),
            'ring': session.input.bios_keyboard_queue()}


def document(image_bytes):
    """Extract DMCORKBD and describe its header and text without guessing."""
    try:
        raw = draw_disk.extract(image_bytes, ['DMCORKBD'])['DMCORKBD']
    except Exception as exc:                      # noqa: BLE001 - recorded, not hidden
        return {'error': f'{type(exc).__name__}: {exc}'}
    text = raw[4:].split(b'\0', 1)[0]
    return {'sha256': hashlib.sha256(raw).hexdigest(),
            'size': len(raw),
            'header_hex': raw[:8].hex(),
            'word0': int.from_bytes(raw[0:2], 'little'),
            'word1': int.from_bytes(raw[2:4], 'little'),
            'text_cp437': text.decode('cp437', 'replace'),
            'text_length_with_cr': len(text)}


def snapshot(out, image_path, name):
    """Copy the stopped image, extract the note, and keep only the document."""
    temporary = out / f'{name}.img'
    shutil.copyfile(image_path, temporary)
    data = temporary.read_bytes()
    temporary.unlink()
    record = document(data)
    record['disk_sha256'] = hashlib.sha256(data).hexdigest()
    return record


def save_probe(out, entry):
    path = out / 'probe.json'
    existing = json.loads(path.read_text()) if path.is_file() else {'steps': []}
    existing['steps'] = [step for step in existing['steps']
                         if step['step'] != entry['step']] + [entry]
    path.write_text(json.dumps(existing, indent=2) + '\n')


def enter_deskmate(session, client):
    prompt = session.prompt()
    dos = profiles.DosPrompt(session.input, prompt, occurrence='last')
    dos.submit('MOUSE')
    session.input.type_text('DESK', anchor=prompt, occurrence='last')
    client.tap(ENTER)
    session.step_until(lambda: client.status()['bios_mode'] not in inp.TEXT_MODES, 120000)
    for _ in range(3):
        session.input.await_render(6000, slice_ms=200)


def phase_step(args):
    if args.step not in PLAN:
        raise SystemExit(f'unknown step: {args.step}')
    moves, text = PLAN[args.step]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    image_path = args.machine / IMAGE
    client = box.Client(args.machine / 'automation.token', port=args.port, timeout=30)
    entry = {'step': args.step, 'moves': [hex(code) for code in moves],
             'text_input': text.replace('\r', '<CR>').replace('\b', '<BS>'),
             'caps': client.capabilities(), 'exe_sha256': args.exe_sha256}
    try:
        session = qual.Session(client, out)
        entry['input_at_boot'] = client.input_state()
        if not session.boot_to_dos():
            entry['error'] = 'dos prompt not reached'
            save_probe(out, entry)
            return 1
        enter_deskmate(session, client)
        entry['desktop'] = session.capture(f'{args.step}-desktop')
        open_corkboard(session)
        entry['opened'] = session.capture(f'{args.step}-open')
        for code in moves:
            session.input.press(code)
            client.step(60)
        if moves:
            entry['moved'] = session.capture(f'{args.step}-moved')
        if text:
            entry['typed'] = type_graphics(session, text)
            entry['typed_frame'] = session.capture(f'{args.step}-typed')
        entry['input_before_save'] = client.input_state()
        entry['ring_before_save'] = session.input.bios_keyboard_queue()
        client.tap(ESC)
        client.step(900)
        entry['closed'] = session.capture(f'{args.step}-closed')
        entry['input_after_save'] = client.input_state()
        client.quit()
    finally:
        client.close()
    entry['document'] = snapshot(out, image_path, args.step)
    save_probe(out, entry)
    print(json.dumps({'step': args.step, 'document': entry['document']}))
    return 0


def phase_burst(args):
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    image_path = args.machine / IMAGE
    lines = ['FF INPUT 01', 'ALPHA BRAVO CHARLIE']
    record = {'phase': 'burst', 'machine': str(args.machine),
              'exe_sha256': args.exe_sha256}
    client = box.Client(args.machine / 'automation.token', port=args.port, timeout=30)
    try:
        session = qual.Session(client, out)
        if not session.boot_to_dos():
            return 1
        enter_deskmate(session, client)
        open_corkboard(session)
        record['corkboard'] = session.capture('burst-corkboard')
        record['input_before'] = client.input_state()
        record['ring_before'] = session.input.bios_keyboard_queue()
        for index, line in enumerate(lines):
            before = client.input_state()
            client.type_ascii(line)              # one request, no pacing
            # Let the guest consume what the interface forwarded before the next
            # request; the request size stays the variable under test.
            drained = session.input.wait_drained(4000)
            client.step(250)
            after = client.input_state()
            delta = (lambda key: None if not before or not after
                     else after[key] - before[key])
            record[f'line{index}'] = {
                'text': line,
                'accepted_delta': delta('accepted'),
                'forwarded_delta': delta('forwarded'),
                'dropped_delta': delta('dropped'),
                'queue': None if not after else after['queue'],
                'ring_after_drain': drained,
                'ring': session.input.bios_keyboard_queue(),
                'wait_queue': client.wait_queue(5000),
                'frame': session.capture(f'burst-line{index}')}
            if index < len(lines) - 1:
                client.tap(ENTER)
                client.step(120)
        record['typed'] = session.capture('burst-typed')
        record['input_after'] = client.input_state()
        record['ring_before_close'] = session.input.wait_drained(4000)
        client.step(600)
        client.tap(ESC)
        client.step(900)
        record['closed'] = session.capture('burst-closed')
        client.quit()
    finally:
        client.close()
    record['document'] = snapshot(out, image_path, 'burst')
    (out / 'burst.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record['document']))
    return 0


def phase_extract(args):
    """Re-derive documents from saved images without an emulator."""
    out = args.out
    results = {}
    for path in sorted(args.image):
        results[path.name] = document(path.read_bytes())
    (out / 'extract.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('step', 'burst', 'extract'), required=True)
    parser.add_argument('--step', choices=sorted(PLAN))
    parser.add_argument('--machine', type=Path)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--image', type=Path, nargs='*', default=[])
    parser.add_argument('--exe-sha256', default='')
    args = parser.parse_args()
    if args.phase == 'step':
        if not args.step:
            raise SystemExit('--step is required for the step phase')
        return phase_step(args)
    if args.phase == 'burst':
        return phase_burst(args)
    return phase_extract(args)


if __name__ == '__main__':
    sys.exit(main())
