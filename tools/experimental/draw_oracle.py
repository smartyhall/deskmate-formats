"""Capture an already launched, held Draw research clone over its native socket."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

from run_guest_canary import Client, advance, save, wait_for_exit


def action(client, operation, evidence):
    kind, _, value = operation.partition(':')
    if kind == 'step':
        duration = int(value)
        if not 1 <= duration <= 12_000:
            raise ValueError('step outside the allowed interval')
        advance(client, duration)
    elif kind == 'tap':
        client.tap(int(value, 0))
    elif kind == 'mod':
        modifier, key = (int(code, 0) for code in value.split('+'))
        client.key('down', modifier)
        client.tap(key)
        client.key('up', modifier)
    elif kind in ('type', 'text'):
        if not 0 < len(value) <= 128:
            raise ValueError('expected a short ASCII command')
        value = value.replace('|', '\n')
        if kind == 'type':
            client.type_ascii(value)
        else:
            for char in value:
                client.type_ascii(char)
                advance(client, 55)
    elif kind == 'mouse':
        dx, dy, buttons = map(int, value.split(','))
        if abs(dx) > 1000 or abs(dy) > 1000 or not 0 <= buttons <= 7:
            raise ValueError('mouse action outside the allowed interval')
        if not client._call(f'mouse {dx} {dy} {buttons}')['ok']:
            raise RuntimeError('mouse command failed')
    elif kind == 'floppy':
        if not re.fullmatch(r'[a-z0-9-]+\.img', value):
            raise ValueError('expected a disposable image filename in the evidence directory')
        media = (evidence / value).resolve(strict=True)
        if media.parent != evidence or media.stat().st_size != 1_474_560:
            raise ValueError('expected disposable 1.44 MB media')
        client.floppy(0, media)
    elif operation == 'eject':
        client.floppy(0)
    else:
        raise ValueError(f'unrecognized action: {kind}')


def held(client):
    state = client.status()
    if state['held'] is not True or state['paused'] is not False:
        raise RuntimeError('guest is outside the held stepping mode')
    return state


def run(machine, evidence, label, operations):
    if evidence.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError('framebuffer evidence must stay outside the repository')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', label) or len(operations) > 96:
        raise ValueError('invalid capture label or action count')
    launch_path, = machine.glob('launch-*/launch.json')
    launch = json.loads(launch_path.read_text(encoding='utf-8'))
    endpoint = launch['command'][launch['command'].index('--automation') + 1]
    match = re.fullmatch(r'tcp:127\.0\.0\.1:([0-9]{1,5})', endpoint)
    if launch['state'] != 'ready' or not match:
        raise ValueError('require a ready authenticated loopback launch')
    stem = evidence / label
    intent = stem.with_suffix('.intent.json')
    receipt = stem.with_suffix('.json')
    with Client(machine / 'automation.token', port=int(match[1]), timeout=15,
                journal=evidence / 'commands.jsonl') as client:
        start = held(client)
        if client.info()['machine'] != 'tandy1000rsx':
            raise RuntimeError('wrong oracle machine')
        save(intent, {'start': start, 'actions': operations})
        if operations == ['quit']:
            reply = client.quit()
            client.close()
            wait_for_exit(launch['pid'])
            save(receipt, {'status': start, 'quit': reply})
            return start
        transitions = []
        for operation in operations:
            action(client, operation, evidence)
            transitions.append(held(client))
        observation, png = client.observe(framebuffer=True)
        if observation['status'] != (transitions[-1] if transitions else start):
            raise RuntimeError('unexpected guest advance during capture')
        observation.update(
            actions=operations, transitions=transitions, start=start,
            png_sha256=sha256(png).hexdigest(), utc=datetime.now(timezone.utc).isoformat(),
        )
        with stem.with_suffix('.png').open('xb') as frame:
            frame.write(png)
        save(receipt, observation)
        return observation['status']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('machine', type=Path)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('label')
    parser.add_argument('operations', nargs='*')
    args = parser.parse_args()
    print(json.dumps(run(args.machine.resolve(), args.evidence.resolve(), args.label, args.operations)))
