"""Authorized native qualification of the corrected verified input facility.

Runs against one disposable clone on a visible, exclusively owned window. Every
stage records the socket reply, the guest BIOS ring, the cursor, the text row
that was compared and a PNG digest. Nothing here retries a stage whose result is
unclear: it records the classification and stops.

Usage:
    python tools/experimental/input_delivery_qualification.py \
        --machine C:/DeskMateLab/private-evidence/input-delivery-20261126/guest-02 \
        --port 8765 --out C:/DeskMateLab/private-evidence/input-delivery-20261126/run-04
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BOX_SPEC = importlib.util.spec_from_file_location('box_client', ROOT / 'tools/86box_client.py')
box = importlib.util.module_from_spec(BOX_SPEC)
BOX_SPEC.loader.exec_module(box)
DISK_SPEC = importlib.util.spec_from_file_location(
    'draw_disk', ROOT / 'tools/experimental/draw_disk.py')
draw_disk = importlib.util.module_from_spec(DISK_SPEC)
DISK_SPEC.loader.exec_module(draw_disk)

sys.path.insert(0, str(ROOT / 'src'))
from deskmate_formats.automation import input as inp          # noqa: E402
from deskmate_formats.automation import profiles              # noqa: E402

PROMPT_ROW = re.compile(r'^[A-Z]:\\?>')
ENTER = 0x1C
ESC = 0x01
DOWN = 0x150
F10 = 0x44

NOTE_LINES = ['FF INPUT 01', 'ALPHA BRAVO CHARLIE']


class Session:
    def __init__(self, client, out):
        self.client = client
        self.out = out
        self.input = inp.VerifiedInput(client)
        self.stages = []

    def capture(self, name, png=None):
        png = png if png is not None else self.input.frame()[0]
        path = self.out / f'{name}.png'
        path.write_bytes(png)
        return {'png': path.name, 'sha256': hashlib.sha256(png).hexdigest()}

    def record(self, name, **fields):
        status = self.client.status()
        entry = {'stage': name, 'ms': status['ms'], 'frames': status['frames'],
                 'bios_mode': status['bios_mode'], 'held': status['held'], **fields}
        self.stages.append(entry)
        print(json.dumps(entry))
        return entry

    def screen(self):
        if self.client.status()['bios_mode'] not in inp.TEXT_MODES:
            return ''
        return '\n'.join(self.client.text()['lines'])

    def prompt(self):
        for line in reversed(self.screen().split('\n')):
            match = PROMPT_ROW.match(line.strip())
            if match:
                return match.group(0)
        return None

    def step_until(self, predicate, budget_ms=120000, slice_ms=200):
        spent = 0
        while spent < budget_ms:
            if predicate():
                return True
            self.client.step(slice_ms)
            spent += slice_ms
        return predicate()

    def boot_to_dos(self):
        spent = 0
        while spent < 180000:
            if self.prompt():
                return True
            self.client.step(50)
            spent += 50
        return False


def pointer_regions(before, after, threshold=30):
    """Return connected changed regions between two framebuffer PNGs.

    A deterministic way to find the pointer without OCR: move it, diff, and take
    the small region that appeared away from the one that disappeared.
    """
    from PIL import Image
    first = Image.open(io.BytesIO(before)).convert('RGB')
    second = Image.open(io.BytesIO(after)).convert('RGB')
    if first.size != second.size:
        return []
    width, height = first.size
    a, b = first.load(), second.load()
    changed = set()
    for y in range(height):
        for x in range(width):
            pa, pb = a[x, y], b[x, y]
            if abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2]) > threshold:
                changed.add((x, y))
    regions = []
    while changed:
        seed = changed.pop()
        stack, points = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbour in changed:
                    changed.remove(neighbour)
                    stack.append(neighbour)
                    points.append(neighbour)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        regions.append({'count': len(points), 'x0': min(xs), 'y0': min(ys),
                        'x1': max(xs), 'y1': max(ys),
                        'cx': sum(xs) // len(xs), 'cy': sum(ys) // len(ys)})
    return sorted(regions, key=lambda region: region['cx'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--machine', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    client = box.Client(args.machine / 'automation.token', port=args.port, timeout=30)
    try:
        session = Session(client, args.out)
        info = client.info()
        header = {'machine': info['machine'], 'build': info['version'],
                  'disk_sha256_before': hashlib.sha256(
                      (args.machine / 'rsx-dos5-working.img').read_bytes()).hexdigest()}

        if not session.boot_to_dos():
            session.record('boot-to-dos', reached=False)
            return 1
        prompt = session.prompt()
        session.record('dos-prompt', prompt=prompt,
                       ring=session.input.bios_keyboard_queue(),
                       cursor=session.input.cursor(),
                       capture=session.capture('01-dos-prompt'))
        dos = profiles.DosPrompt(session.input, prompt, occurrence='last')

        # --- entry versus execution, with trailing spaces ---
        plain = dos.submit('VER', expect_output='MS-DOS Version')
        session.record('submit-ver', result=plain.as_dict(),
                       capture=session.capture('02-ver'))
        spaced = dos.submit('VER   ', expect_output='MS-DOS Version')
        session.record('submit-ver-spaces', result=spaced.as_dict(),
                       capture=session.capture('03-ver-spaces'))

        # --- pacing comparison on the same command ---
        timings = []
        for mode in ('unverified', 'paced', 'bursts', 'verified'):
            started = client.status()['ms']
            if mode == 'unverified':
                client.type_ascii('VER')
                client.tap(ENTER)
                matched = client.wait_text('MS-DOS Version', 60000)['matched']
                outcome = 'matched' if matched else 'unmatched'
                dos.await_empty_prompt()
            elif mode == 'paced':
                client.type_ascii('VER', pace_ms=25)
                client.tap(ENTER)
                matched = client.wait_text('MS-DOS Version', 60000)['matched']
                outcome = 'matched' if matched else 'unmatched'
                dos.await_empty_prompt()
            elif mode == 'bursts':
                report = session.input.type_text('VER', anchor=prompt, occurrence='last')
                client.tap(ENTER)
                matched = client.wait_text('MS-DOS Version', 60000)['matched']
                outcome = {'status': report.status, 'bursts': report.bursts,
                           'matched': matched}
                dos.await_empty_prompt()
            else:
                result = dos.submit('VER', expect_output='MS-DOS Version')
                outcome = {'entered': result.entered, 'prompt': result.prompt_returned,
                           'output': result.output_matched}
            timings.append({'mode': mode, 'emulated_ms': client.status()['ms'] - started,
                            'outcome': outcome})
        session.record('pacing-comparison', timings=timings,
                       capture=session.capture('04-pacing'))

        # --- ring occupancy while the guest is not reading input ---
        session.input.type_text('TYPE C:\\DOS\\COMMAND.COM', anchor=prompt, occurrence='last')
        client.tap(ENTER)
        client.type_ascii('XYZ')          # type-ahead, no waiting between keys
        ring = session.input.bios_keyboard_queue()
        occupied = session.input.wait_drained(timeout_ms=0)
        session.record('ring-typeahead', ring=ring, immediately_after=occupied,
                       tail_leads=(ring['tail'] - ring['head']) % (ring['size'] or 2)
                       if ring['valid'] else None,
                       capture=session.capture('05-ring-typeahead'))
        # The queued keystrokes reach the DOS line editor only when the guest is
        # done writing, and they sit there until something submits them.
        arrived = session.step_until(
            lambda: last_prompt_text(session) == 'XYZ', 180000, slice_ms=500)
        echoed = sum(line.count('XYZ') for line in session.screen().split('\n'))
        session.record('ring-delivered', arrived=arrived, echoed_lines=echoed,
                       ring=session.input.bios_keyboard_queue(),
                       capture=session.capture('06-ring-after'))
        client.tap(ENTER)
        dos.await_empty_prompt()

        # --- graphics: menus, note persistence, pointer ---
        if not dos.at_empty_prompt():
            session.record('stray-input', row=last_prompt_text(session))
            client.tap(ENTER)
            dos.await_empty_prompt()
        session.input.type_text('MOUSE', anchor=prompt, occurrence='last')
        client.tap(ENTER)
        dos.await_empty_prompt()
        session.input.type_text('DESK', anchor=prompt, occurrence='last')
        client.tap(ENTER)
        session.step_until(lambda: client.status()['bios_mode'] not in inp.TEXT_MODES, 120000)
        for _ in range(3):
            session.input.await_render(6000, slice_ms=200)
        screens = profiles.ScreenStates(session.input)
        desktop = screens.capture('desktop')
        session.record('deskmate-desktop', digest=desktop['digest'],
                       capture=session.capture('07-deskmate-desktop'))

        opened = session.input.press(F10, expect='changed')
        screens.capture('menu')
        session.record('menu-open', report=opened.as_dict(),
                       capture=session.capture('08-menu-open'))
        restored = session.input.press(ESC, expect='state', reference=desktop)
        session.record('menu-restore', report=restored.as_dict(),
                       capture=session.capture('09-menu-restored'))

        # Corkboard: F10, five Downs, Enter (documented RSX sequence).
        session.input.press(F10)
        session.input.press(*([DOWN] * 5))
        session.input.press(ENTER)
        for _ in range(2):
            session.input.await_render(4000, slice_ms=200)
        screens.capture('corkboard')
        session.record('corkboard-open', digest=screens.states['corkboard']['digest'],
                       capture=session.capture('10-corkboard'))
        for index, line in enumerate(NOTE_LINES):
            client.type_ascii(line)
            if index < len(NOTE_LINES) - 1:
                client.tap(ENTER)
            client.step(120)
        screens.capture('corkboard-typed')
        typed_png = session.input.frame()[0]
        session.record('corkboard-typed', digest=screens.states['corkboard-typed']['digest'],
                       capture=session.capture('11-corkboard-typed', typed_png))

        # Escape closes this revision's note; the desktop should come back.
        client.tap(ESC)
        client.step(400)
        returned = session.step_until(
            lambda: session.input.snapshot()['digest'] == desktop['digest'], 30000, 200)
        session.record('note-closed', desktop_returned=returned,
                       digest=session.input.snapshot()['digest'],
                       capture=session.capture('12-after-note'))

        # Reopen the same accessory: the note should render again as it was saved.
        session.input.press(F10)
        session.input.press(*([DOWN] * 5))
        session.input.press(ENTER)
        for _ in range(2):
            session.input.await_render(4000, slice_ms=200)
        reopened_png = session.input.frame()[0]
        session.record('corkboard-reopened',
                       diff=pixel_diff(typed_png, reopened_png),
                       capture=session.capture('13-corkboard-reopened', reopened_png))
        client.tap(ESC)
        client.step(400)

        # --- pointer calibration and one deliberate click ---
        before = session.input.frame()[0]
        client.mouse(-4000, -4000, 0)
        client.step(200)
        home = session.input.frame()[0]
        client.mouse(200, 0, 0)
        client.step(200)
        moved = session.input.frame()[0]
        regions = pointer_regions(home, moved)
        session.record('pointer-calibration', regions=regions[:4],
                       capture=moved if not regions else None)
        (args.out / 'pointer-home.png').write_bytes(home)
        (args.out / 'pointer-moved.png').write_bytes(moved)
        del before

        session.record('closeout', stages=len(session.stages))
        (args.out / 'run.json').write_text(json.dumps(
            {'session': header, 'stages': session.stages}, indent=2) + '\n')
        return 0
    finally:
        try:
            client.quit()
        finally:
            client.close()


def pixel_diff(before, after, threshold=30):
    """Deterministically compare two frames: how many pixels differ, and where."""
    from PIL import Image
    first = Image.open(io.BytesIO(before)).convert('RGB')
    second = Image.open(io.BytesIO(after)).convert('RGB')
    if first.size != second.size:
        return {'comparable': False}
    width, height = first.size
    a, b = first.load(), second.load()
    points = []
    for y in range(height):
        for x in range(width):
            pa, pb = a[x, y], b[x, y]
            if abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2]) > threshold:
                points.append((x, y))
    if not points:
        return {'comparable': True, 'count': 0, 'total': width * height}
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {'comparable': True, 'count': len(points), 'total': width * height,
            'bbox': [min(xs), min(ys), max(xs), max(ys)]}


def last_prompt_text(session):
    """Return what follows the bottom-most prompt, or None outside text mode."""
    try:
        return session.input.row_after(session.prompt() or 'C:\\>', 'last').strip(' ')
    except ValueError:
        return None


def _letters(text):
    """Map upper-case letters and spaces to set-1 make codes (shifted as needed)."""
    plain = '1234567890-=qwertyuiop[]asdfghjkl;\'`\\zxcvbnm,./'
    scans = list(range(2, 14)) + list(range(16, 28)) + list(range(30, 42)) + [43]
    scans += list(range(44, 54))
    table = {char: scan for char, scan in zip(plain, scans)}
    codes = []
    for char in text:
        if char == ' ':
            codes.append(57)
        elif char.isupper():
            codes.extend([0x2A, table[char.lower()], 0xAA])
        else:
            codes.append(table[char])
    return codes


if __name__ == '__main__':
    sys.exit(main())
