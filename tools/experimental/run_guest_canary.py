"""One bounded native-socket canary experiment on an already launched clone.

No automatic reconnect/replay after failure. Deliberate reconnect and hard reset
occur only after successful checkpoints. Raw captures/journals remain private.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
Client = importlib.import_module('86box_client').Client
fixture = importlib.import_module('guest_canary')


def save(path, data):
    with path.open('x', encoding='utf-8') as out:
        json.dump(data, out, indent=2, ensure_ascii=False)
        out.write('\n')


def advance(client, milliseconds):
    while milliseconds:
        part = min(milliseconds, 1000)
        client.step(part)
        milliseconds -= part


def capture(client, evidence, name, checkpoint=False):
    client.hold()
    where = fixture.locations(client.registers()) if checkpoint else None
    spans = [(where['code'], 98), (where['data'], 32)] if where else ()
    observation, png = client.observe(spans, framebuffer=True)
    save(evidence/(name+'.json'), observation)
    with (evidence/(name+'.png')).open('xb') as out:
        out.write(png)
    result = fixture.validate(observation) if checkpoint else observation
    if checkpoint:
        result['framebuffer_sha256'] = hashlib.sha256(png).hexdigest()
    return result


def wait_for_exit(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:  # PID already exited.
            return
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if kernel.WaitForSingleObject(handle, 10000) != 0:
            raise RuntimeError('quit replied but process did not exit; do not copy a live disk')
    finally:
        kernel.CloseHandle(handle)


def run(machine, evidence, receipt_path):
    machine, evidence = Path(machine).resolve(), Path(evidence).resolve()
    if evidence.is_relative_to(fixture.ROOT):
        raise ValueError('evidence must remain outside the repository')
    launch = json.loads(Path(receipt_path).read_text(encoding='utf-8'))
    if launch.get('state') != 'ready' or launch['status']['ms'] != 0:
        raise ValueError('require a ready held launch receipt at 0 ms')
    image = machine/'media/canary-data.img'
    if image.read_bytes() != fixture.floppy(fixture.program()):
        raise ValueError('experimental floppy does not match original generated source')
    evidence.mkdir(parents=True, exist_ok=False)
    port = int(launch['command'][launch['command'].index('--automation')+1].rsplit(':',1)[1])
    options = dict(port=port, journal=evidence/'commands.jsonl')
    token = machine/'automation.token'
    with Client(token, **options) as first:
        initial = first.status()
        if initial['ms'] != 0 or initial['held'] is not True:
            raise ValueError('guest has already advanced; use a fresh launch')
        advance(first, 12000)
        boot = capture(first, evidence, '01-boot')
        if 'C:\\>' not in '\n'.join(boot['text']['lines']):
            raise ValueError('expected independent DOS hard-disk boot')
        first.floppy(0, image)
        first.type_ascii('a:\\canary\n')
        advance(first, 3000)
        checkpoint = capture(first, evidence, '02-checkpoint', True)
        connection = first.connection_id
        before_disconnect = first.status()
    # Intentional disconnect with no outstanding request. No mutation is replayed.
    with Client(token, **options) as second:
        after_connect = second.status()
        if any(before_disconnect[k] != after_connect[k] for k in ('ms','frames','held','paused')):
            raise ValueError('state changed across deliberate held reconnect')
        if second.connection_id == connection:
            raise ValueError('expected fresh authenticated client connection')
        reconnected = capture(second, evidence, '03-reconnected', True)
        if checkpoint != reconnected:
            raise ValueError('checkpoint differs after reconnect')
        second.step(1000)
        advanced = capture(second, evidence, '04-advanced', True)
        second.floppy(0)  # Data floppy is NOT bootable; eject before reset.
        reset_before = second.info()
        second.reset('hard')
        advance(second, 12000)
        reboot = capture(second, evidence, '05-reset-boot')
        reset_after = reboot['info']
        if reset_after['hard_resets'] <= reset_before['hard_resets']:
            raise ValueError('hard reset generation did not increase')
        if 'C:\\>' not in '\n'.join(reboot['text']['lines']):
            raise ValueError('reset failed to return to DOS')
        second.type_ascii('ver\n')
        second.step(500)
        version = capture(second, evidence, '06-reset-ver')
        if 'MS-DOS Version 5.00' not in '\n'.join(version['text']['lines']):
            raise ValueError('DOS version after reset not observed')
        summary = {'checkpoint':checkpoint, 'reconnected':reconnected, 'advanced':advanced,
            'reconnect':{'fresh_authenticated_connection':True,'no_replayed_mutation':True,
                         'ms_before':before_disconnect['ms'],'ms_after':after_connect['ms']},
            'reset':{'before':{k:reset_before[k] for k in ('hard_resets','soft_resets','last_reset_ms')},
                     'after':{k:reset_after[k] for k in ('hard_resets','soft_resets','last_reset_ms')},
                     'boot_ms':reboot['status']['ms'],'version_ms':version['status']['ms'],
                     'dos_version':'5.00','old_address_mapping_retired':True},
            'launch':{'pid':launch['pid'],'mode':launch['mode'],
                      'executable_sha256':launch['executable_sha256']}}
        save(evidence/'validated-summary.json', summary)
        second.quit()
    wait_for_exit(launch['pid'])
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--machine', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    run(args.machine, args.evidence, args.receipt)
