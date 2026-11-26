"""Native qualification for the instrumented automation build.

This runs against the separately built experimental executable, never the shared
production one. It exercises the instrumentation the review asked for and then
uses it to find out where Corkboard text entry loses characters.

Phases, each in its own process so the guest image can be inspected between them:

``type``
    Boot DOS, verify capability negotiation and input-event accounting, type a
    DOS command, then open Corkboard and type a marker note one keystroke at a
    time, recording for each keystroke: the automation queue state, the BIOS ring,
    the event counters and whether the frame changed. A differential memory search
    locates candidate copies of the marker without assuming an address. The note
    is closed with Escape (the documented save path) and the emulator quit.

``reopen``
    Cold relaunch on the same disposable clone, reopen Corkboard and compare the
    frame with the one captured after typing.

``verify``
    Offline. Extract ``DESKMATE/DMCORKBD`` through the FAT16 reader and compare
    the text it holds with what was typed: the independent document check.

Usage:
    python tools/experimental/instrumented_qualification.py --phase type \\
        --machine C:/DeskMateLab/private-evidence/.../guest-idq-01 --port 8765 \\
        --out C:/DeskMateLab/private-evidence/.../idq-run-01
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
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
NOTE_LINES = ['FF INPUT 01', 'ALPHA BRAVO CHARLIE']
NOTE_TEXT = '\r'.join(NOTE_LINES)
REQUIRED_CAPS = {'input_queue', 'event_seq', 'wait_queue', 'video_meta',
                 'mouse_state', 'keyboard_held'}


def memory_search(client, needle, limit=0xA0000, block=0x10000):
    """Return physical offsets where `needle` occurs in conventional memory."""
    hits = []
    for base in range(0, limit, block):
        data = client.memory(base, block)
        start = 0
        while True:
            found = data.find(needle, start)
            if found < 0:
                break
            hits.append(base + found)
            start = found + 1
    return hits


def type_with_evidence(session, text, pause_ms=40):
    """Type one character per request, recording the evidence for each one."""
    client = session.client
    log = []
    for index, char in enumerate(text):
        before = session.input.snapshot()['digest']
        session.client.type_ascii(char)
        client.step(pause_ms)
        log.append({'index': index, 'char': char,
                    'frame_changed': session.input.snapshot()['digest'] != before,
                    'input': client.input_state(),
                    'ring': session.input.bios_keyboard_queue()})
    return log


def phase_type(args):
    args.out.mkdir(parents=True, exist_ok=True)
    client = box.Client(args.machine / 'automation.token', port=args.port, timeout=30)
    header = {'phase': 'type', 'exe_sha256': args.exe_sha256,
              'version': client.info()['version'],
              'disk_sha256_before': hashlib.sha256(
                  (args.machine / 'rsx-dos5-working.img').read_bytes()).hexdigest()}
    stages = []
    try:
        session = qual.Session(client, args.out)
        caps = client.capabilities()
        start = client.input_state()
        session.record('capabilities', caps=caps, missing=sorted(REQUIRED_CAPS - set(caps)),
                       input=start, video=client.video(), mouse=client.mouse_state())
        stages.extend(session.stages)
        if not session.boot_to_dos():
            return 1
        prompt = session.prompt()
        dos = profiles.DosPrompt(session.input, prompt, occurrence='last')
        video = client.video()
        session.record('dos-prompt', prompt=prompt, video=video,
                       ring=session.input.bios_keyboard_queue(),
                       input=client.input_state(),
                       capture=session.capture('01-dos-prompt'))

        # A DOS command, with the counters that describe its delivery.
        before = client.input_state()
        submitted = dos.submit('VER', expect_output='MS-DOS Version')
        after = client.input_state()
        awaited = client.wait_queue(5000)
        session.record('submit-ver', result=submitted.as_dict(),
                       before=before, after=after, wait_queue=awaited,
                       ring=session.input.bios_keyboard_queue(),
                       capture=session.capture('02-ver'))
        stages.extend(session.stages[-1:])

        # DeskMate, then Corkboard through the documented F10 sequence.
        for command in ('MOUSE', 'DESK'):
            session.input.type_text(command, anchor=prompt, occurrence='last')
            client.tap(ENTER)
            if command == 'MOUSE':
                # DESK switches the guest to graphics mode: no prompt follows it.
                dos.await_empty_prompt()
        session.step_until(lambda: client.status()['bios_mode'] not in inp.TEXT_MODES,
                           120000)
        for _ in range(3):
            session.input.await_render(6000, slice_ms=200)
        screens = profiles.ScreenStates(session.input)
        screens.capture('desktop')
        session.record('deskmate-desktop', digest=screens.states['desktop']['digest'],
                       video=client.video(), input=client.input_state(),
                       capture=session.capture('03-desktop'))
        session.input.press(F10, expect='changed')
        screens.capture('menu')
        session.record('menu-open', digest=screens.states['menu']['digest'],
                       capture=session.capture('04-menu'))
        session.input.press(*([DOWN] * 5))
        session.input.press(ENTER)
        for _ in range(2):
            session.input.await_render(4000, slice_ms=200)
        screens.capture('corkboard')
        session.record('corkboard-open', digest=screens.states['corkboard']['digest'],
                       capture=session.capture('05-corkboard'))

        # Where the marker was absent before typing.
        absent = {'marker': memory_search(client, b'FF INPUT 01'),
                  'line2': memory_search(client, b'ALPHA BRAVO')}
        session.record('buffer-search-before', hits=absent)

        log = []
        for index, line in enumerate(NOTE_LINES):
            log.append({'line': index, 'characters': type_with_evidence(session, line)})
            if index < len(NOTE_LINES) - 1:
                session.client.tap(ENTER)
                client.step(60)
        screens.capture('typed')
        typed_png = session.input.frame()[0]
        (args.out / 'typed.png').write_bytes(typed_png)
        session.record('corkboard-typed', digest=screens.states['typed']['digest'],
                       keystrokes=log,
                       capture={'png': 'typed.png',
                                'sha256': hashlib.sha256(typed_png).hexdigest()})

        # A candidate buffer is only a candidate: record where the marker is now,
        # then confirm it against the saved file in the verify phase.
        present = {'marker': memory_search(client, b'FF INPUT 01'),
                   'line2': memory_search(client, b'ALPHA BRAVO'),
                   'full': memory_search(client, NOTE_TEXT.encode('ascii')),
                   'first_char_lost': memory_search(client, b'F INPUT 01'),
                   'line2_truncated': memory_search(client, b'ALPHA BRA')}
        stable = memory_search(client, b'FF INPUT 01')
        session.record('buffer-search-after', hits=present, repeated=stable,
                       stable=sorted(set(present['marker']) & set(stable)) == sorted(present['marker']),
                       input=client.input_state())

        # Escape is the documented close-and-retain path.
        client.tap(ESC)
        client.step(400)
        session.record('note-closed', video=client.video(), input=client.input_state(),
                       capture=session.capture('06-after-note'))
        (args.out / 'session.json').write_text(json.dumps(
            {'header': header, 'stages': session.stages}, indent=2) + '\n')
        return 0
    finally:
        try:
            client.quit()
        finally:
            client.close()


def phase_reopen(args):
    args.out.mkdir(parents=True, exist_ok=True)
    client = box.Client(args.machine / 'automation.token', port=args.port, timeout=30)
    try:
        session = qual.Session(client, args.out)
        record = {'phase': 'reopen', 'version': client.info()['version'],
                  'input': client.input_state()}
        if not session.boot_to_dos():
            return 1
        profiles.DosPrompt(session.input, session.prompt(), occurrence='last').submit('MOUSE')
        session.input.type_text('DESK', anchor=session.prompt(), occurrence='last')
        client.tap(ENTER)
        session.step_until(lambda: client.status()['bios_mode'] not in inp.TEXT_MODES,
                           120000)
        for _ in range(3):
            session.input.await_render(6000, slice_ms=200)
        session.input.press(F10)
        session.input.press(*([DOWN] * 5))
        session.input.press(ENTER)
        for _ in range(2):
            session.input.await_render(4000, slice_ms=200)
        reopened = session.input.frame()[0]
        typed = (args.out / 'typed.png').read_bytes() if (args.out / 'typed.png').is_file() else None
        record.update({'diff': qual.pixel_diff(typed, reopened) if typed else None,
                       'digest': session.input.snapshot()['digest'],
                       'capture': session.capture('07-reopened', reopened),
                       'input': client.input_state()})
        (args.out / 'reopen.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record))
        return 0
    finally:
        try:
            client.quit()
        finally:
            client.close()


def phase_verify(args):
    image = (args.machine / 'rsx-dos5-working.img').read_bytes()
    document = draw_disk.extract(image, ['DMCORKBD'])['DMCORKBD']
    body = document[4:]
    expectation = NOTE_TEXT.encode('ascii')
    found = body.find(expectation)
    partial = {name: body.find(needle.encode('ascii'))
               for name, needle in (('F INPUT 01', 'F INPUT 01'),
                                    ('ALPHA BRA', 'ALPHA BRA'),
                                    ('ALPHA BRAVO CHARLIE', 'ALPHA BRAVO CHARLIE'))}
    report = {'phase': 'verify',
              'disk_sha256': hashlib.sha256(image).hexdigest(),
              'document_sha256': hashlib.sha256(document).hexdigest(),
              'document_size': len(document),
              'header_hex': document[:8].hex(),
              'text_offset_of_full_note': found,
              'full_note_present': found >= 0,
              'partial_offsets': partial,
              'text_cp437': body.rstrip(b'\0').decode('cp437', 'replace')[:200],
              'expected': NOTE_TEXT}
    (args.out / 'document.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if found >= 0 else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('type', 'reopen', 'verify'), required=True)
    parser.add_argument('--machine', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--exe-sha256', default='')
    args = parser.parse_args()
    if args.phase == 'type':
        return phase_type(args)
    if args.phase == 'reopen':
        return phase_reopen(args)
    return phase_verify(args)


if __name__ == '__main__':
    sys.exit(main())
