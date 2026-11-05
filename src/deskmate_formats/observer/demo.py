"""Deterministic fictional scenes for testing the observer without an emulator."""

import argparse
from io import BytesIO
from threading import Event, Thread

from .frames import Frame
from .http import ObserverServer
from .publication import Action, Machine, Observation, ObservationRegistry, decode_cp437, host_time_ms

MACHINES = (
    Machine("synthetic-rsx", "Synthetic RSX"),
    Machine("synthetic-at", "Synthetic AT"),
    Machine("synthetic-486", "Synthetic 486"),
)
_SCENES = (
    (Action.BOOT, "Firmware self-check", 0, False, (
        "STATION FIRMWARE 0.4", "", "Conventional memory ... 640 KiB",
        "Display adapter ....... ready", "Boot volume ........... ready", "", "Loading system...",
    )),
    (Action.OBSERVE, "DOS prompt ready", 1200, True, (
        "LAB DOS COMMAND INTERPRETER", "", r"C:\>VER", "Lab DOS 5.0 (synthetic)", "", "C:\\>_",
    )),
    (Action.KEY_SEQUENCE, "Diagnostics running", 4250, False, (
        r"C:\>LABCHECK", "", "MEDIA CHECK   [######....] 60%",
        "VIDEO CHECK   PASS", "CLOCK CHECK   PASS", "", "Checking sector 18 of 30...",
    )),
    (Action.STEP, "Diagnostic checkpoint held", 7330, True, (
        "LABCHECK / STATION REPORT", "", "╔════════════════════════════╗",
        "║       DIAGNOSTIC PASS      ║", "╠════════════════════════════╣",
        "║  Memory ............. OK   ║", "║  Display ............ OK   ║",
        "║  Clock .............. OK   ║", "╚════════════════════════════╝", "", "Checkpoint complete",
    )),
)
_BOX_STROKES = {
    "═": "lr", "║": "ud", "╔": "rd", "╗": "ld", "╚": "ru", "╝": "lu", "╠": "urd", "╣": "uld",
}
_PALETTES = {
    "synthetic-rsx": ("#87f7cc", "#091923"),
    "synthetic-at": ("#ffcc7e", "#22190d"),
    "synthetic-486": ("#c0ddff", "#10162c"),
}


def _scene_png(machine, lines):
    from PIL import Image, ImageDraw, ImageFont

    ink, background = _PALETTES[machine.instance_id]
    image = Image.new("RGB", (320, 175), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=10)
    draw.text((12, 8), machine.label.upper() + " / FICTIONAL FIXTURE", fill=ink, font=font)
    draw.line((12, 24, 308, 24), fill=ink)
    for row, line in enumerate(lines):
        for col, char in enumerate(line):
            x, y = 12 + 8 * col, 33 + 12 * row
            if char in _BOX_STROKES:
                ends = {"l": (x, y + 5), "r": (x + 8, y + 5), "u": (x + 4, y - 1), "d": (x + 4, y + 11)}
                for direction in _BOX_STROKES[char]:
                    draw.line((x + 4, y + 5, *ends[direction]), fill=ink)
            elif char != " ":
                draw.text((x, y), char, fill=ink, font=font)
    output = BytesIO()
    image.resize((640, 350), Image.Resampling.NEAREST).save(output, "PNG")
    return output.getvalue()


def publish_scene(stream, index, observed_at_ms, *, with_frames=True):
    """Publish the next scene, including a simulated disconnect every fifth update."""
    generation, scene = divmod(index, 5)
    if scene == len(_SCENES):
        stream.mark_unavailable(sequence=index, observed_at_ms=observed_at_ms)
        return
    action, milestone, emulated_ms, held, lines = _SCENES[scene]
    frame = None
    if with_frames:
        frame = Frame(
            _scene_png(stream.machine, lines), generation=scene, captured_at_ms=observed_at_ms,
            rendered_emulated_ms=emulated_ms - (40 if scene == 3 else 0),
        )
    stream.publish(Observation(
        instance_id=stream.machine.instance_id, sequence=index, generation=generation,
        observed_at_ms=observed_at_ms, emulated_ms=emulated_ms, held=held, paused=False,
        action=action, milestone=milestone, dropped_updates=generation + int(scene == 3),
        screen=decode_cp437(line.encode("cp437") for line in lines), frame=frame,
    ))


def _cycle(stream, stop, interval, with_frames):
    index = 1
    while not stop.wait(interval):
        publish_scene(stream, index, host_time_ms(), with_frames=with_frames)
        index += 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Serve fictional 86Box observations over localhost.")
    parser.add_argument("--port", type=int, default=8086, help="loopback port (default 8086, 0 for ephemeral)")
    parser.add_argument("--instances", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--interval", type=float, default=2.0, help="seconds per fictional scene (default 2)")
    parser.add_argument("--text-only", action="store_true", help="run without the optional Pillow dependency")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535 or not 0.25 <= args.interval <= 60:
        parser.error("port must be 0..65535 and interval must be 0.25..60 seconds")
    if not args.text_only:
        try:
            import PIL  # noqa: F401
        except ImportError:
            parser.error("install deskmate-formats[observer] or use --text-only")
    registry = ObservationRegistry(MACHINES[:args.instances], stale_after=max(10, args.interval * 3))
    stop = Event()
    workers = []
    try:
        with ObserverServer(registry, port=args.port) as server:
            for machine in registry.machines:
                stream = registry.stream(machine.instance_id)
                publish_scene(stream, 0, host_time_ms(), with_frames=not args.text_only)
                worker = Thread(target=_cycle, args=(stream, stop, args.interval, not args.text_only))
                worker.start()
                workers.append(worker)
            print(f"Synthetic observer at http://127.0.0.1:{server.port}/ (Ctrl+C to stop)", flush=True)
            server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    except OSError:
        parser.exit(1, "could not start the observer on the selected loopback port\n")
    finally:
        stop.set()
        for worker in workers:
            worker.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
