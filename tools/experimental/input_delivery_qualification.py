"""Authorized native qualification of the verified input facility.

Runs against one disposable clone on a visible, exclusively owned window. Every
stage records the socket reply, the guest BIOS keyboard buffer, the text row that
was compared, and a PNG digest of the observed screen. Nothing here retries a
failed stage: an unclear result is recorded and the run stops.

Usage:
    python tools/experimental/input_delivery_qualification.py \
        --machine C:/DeskMateLab/private-evidence/input-delivery-20261126/guest-01 \
        --port 8765 --out C:/DeskMateLab/private-evidence/input-delivery-20261126/run-01
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('box_client', ROOT / 'tools/86box_client.py')
box = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(box)
SPEC_INPUT = importlib.util.spec_from_file_location(
    'automation_input', ROOT / 'src/deskmate_formats/automation/input.py')
inp = importlib.util.module_from_spec(SPEC_INPUT)
SPEC_INPUT.loader.exec_module(inp)

PROMPT_ROW = re.compile(r'^[A-Z]:\\?>')
ENTER = 0x1C
ESC = 0x01
F5 = 0x3F
F10 = 0x44


class Session:
    def __init__(self, client, out):
        self.client = client
        self.out = out
        self.input = inp.VerifiedInput(client)
        self.stages = []
        self.frames = 0

    def capture(self, name, png=None):
        png = png if png is not None else self.input.frame()[0]
        path = self.out / f'{name}.png'
        path.write_bytes(png)
        self.frames += 1
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

    def step_until(self, predicate, budget_ms=120000, slice_ms=200):
        spent = 0
        while spent < budget_ms:
            if predicate():
                return True
            self.client.step(slice_ms)
            spent += slice_ms
        return predicate()

    def prompt(self):
        """Return the bottom-most DOS prompt on screen, or None.

        The guest decides its own prompt (``C>`` without AUTOEXEC, ``C:\\>``
        with it), so it is read rather than assumed.
        """
        for line in reversed(self.screen().split('\n')):
            match = PROMPT_ROW.match(line.strip())
            if match:
                return match.group(0)
        return None

    def await_prompt(self, prompt, budget_ms=30000):
        """Step until the bottom prompt row is empty again (a new input line)."""
        spent = 0
        while spent < budget_ms:
            try:
                if self.input.row_after(prompt, 'last') == '':
                    return True
            except ValueError:
                pass
            self.client.step(100)
            spent += 100
        return False

    def boot_to_dos(self):
        """Hold-start the clone and skip AUTOEXEC so the guest stays in DOS."""
        skipped, spent = False, 0
        while spent < 180000:
            screen = self.screen()
            if not skipped and 'Starting MS-DOS' in screen:
                self.client.tap(F5)
                skipped = True
                self.record('boot-skip-autoexec', skipped=True)
            if self.prompt():
                return True
            self.client.step(50)
            spent += 50
        return False


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
        record = {'machine': info['machine'], 'build': info['version'],
                  'clone_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(args.machine.glob('*.img'))}}

        if not session.boot_to_dos():
            session.record('boot-to-dos', reached=False)
            return 1
        prompt = session.prompt()
        session.record('dos-prompt', reached=True, prompt=prompt,
                       queue=session.input.bios_keyboard_queue(),
                       capture=session.capture('01-dos-prompt'))

        # --- text entry: delivery, guest acceptance, application consumption ---
        autobat = session.input.type_text('TYPE AUTOEXEC.BAT', anchor=prompt)
        session.record('type-autoexec', report=autobat.as_dict(),
                       capture=session.capture('02-autoexec-typed'))
        session.input.press(ENTER)
        shown = client.wait_text('AUTOEXEC', 60000)
        session.await_prompt(prompt)
        session.record('autoexec-consumed', matched=shown['matched'], ms=shown['ms'],
                       capture=session.capture('03-autoexec-output'))

        entry = session.input.type_text('VER', anchor=prompt, occurrence='last')
        session.record('type-ver', report=entry.as_dict(),
                       capture=session.capture('04-ver-typed'))
        session.input.press(ENTER)
        matched = client.wait_text('MS-DOS Version', 60000)
        session.await_prompt(prompt)
        session.record('ver-consumed', matched=matched['matched'],
                       ms=matched['ms'], capture=session.capture('05-ver-output'))

        # A keystroke the guest accepts but no application acts on: F10 in DOS.
        control = session.input.press(F10, expect='change')
        session.record('negative-control', report=control.as_dict(),
                       capture=session.capture('06-negative-control'))

        listing = session.input.type_text('DIR', anchor=prompt, occurrence='last')
        session.record('type-dir', report=listing.as_dict(),
                       capture=session.capture('07-dir-typed'))
        session.input.press(ENTER)
        consumed = client.wait_text('Directory of', 60000)
        session.await_prompt(prompt)
        session.record('dir-consumed', matched=consumed['matched'], ms=consumed['ms'],
                       capture=session.capture('08-dir-output'))

        # --- text to graphics, menu transition and pointer ---
        mouse = session.input.type_text('MOUSE', anchor=prompt, occurrence='last')
        session.input.press(ENTER)
        session.await_prompt(prompt)
        session.record('mouse-driver', report=mouse.as_dict(),
                       capture=session.capture('09-mouse-driver'))

        session.input.type_text('DESK', anchor=prompt, occurrence='last')
        session.input.press(ENTER)
        session.step_until(lambda: client.status()['bios_mode'] not in inp.TEXT_MODES, 120000)
        # A settled frame is not a drawn application: DeskMate clears to a stable
        # black screen before it paints the desktop, so require real redraws.
        redraws = [session.input.await_render(6000, slice_ms=200) for _ in range(3)]
        desktop = session.input.snapshot()
        session.record('deskmate-desktop', digest=desktop['digest'], basis=desktop['basis'],
                       redraws=redraws,
                       capture=session.capture('10-deskmate-desktop'))

        menu = session.input.press(F10, expect='change')
        session.record('menu-open', report=menu.as_dict(),
                       capture=session.capture('11-menu-open'))
        closed = session.input.press(ESC, expect='restore', reference=desktop)
        session.record('menu-restore', report=closed.as_dict(),
                       capture=session.capture('12-menu-closed'))

        moved = session.input.pointer(40, 0, 0)
        session.record('pointer-move', report=moved.as_dict(),
                       capture=session.capture('13-pointer-moved'))
        clicked = session.input.pointer(0, 0, 1)
        session.record('pointer-down', report=clicked.as_dict(),
                       capture=session.capture('14-pointer-down'))
        session.input.pointer(0, 0, 0)

        session.record('closeout', remaining=len(session.stages))
        (args.out / 'run.json').write_text(json.dumps(
            {'session': record, 'stages': session.stages}, indent=2) + '\n')
        return 0
    finally:
        try:
            client.quit()
        finally:
            client.close()


if __name__ == '__main__':
    sys.exit(main())
