"""Authenticated protocol-1 client for an explicitly selected local 86Box.

No automatic retries: a lost reply to a mutation means uncertain delivery.
Logs and captures belong outside the repository; they can contain guest data.
"""
import argparse
import base64
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import socket
import struct
import sys
import threading
import time
import uuid
import zlib


class ProtocolError(RuntimeError):
    """Transport failure, malformed reply or inconsistent observation."""


class CommandError(RuntimeError):
    """The emulator rejected a command; transport remains synchronized."""


class Client:
    """One serialized connection; finite timeouts and bounded JSON replies."""

    def __init__(self, token_file, port=8765, host='127.0.0.1', timeout=15,
                 journal=None, max_reply=16 * 1024 * 1024, *, expected_token_sha256=None):
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError('only loopback endpoints are allowed')
        if not 1 <= port <= 65535 or timeout <= 0 or max_reply < 128:
            raise ValueError('invalid transport limits')
        with Path(token_file).open('rb') as stream:
            raw_token = stream.read(129)
        token = raw_token.decode('ascii').strip()
        if len(raw_token) > 128 or not re.fullmatch(r'[0-9a-fA-F]{64}', token):
            raise ValueError('token file must contain 32 hex-encoded bytes')
        if (expected_token_sha256 is not None
                and hashlib.sha256(bytes.fromhex(token)).hexdigest() != expected_token_sha256):
            raise ProtocolError('unexpected token identity')
        self.journal = Path(journal) if journal else None
        self.max_reply = max_reply
        self.timeout = timeout
        self.sequence = 0
        self.connection_id = uuid.uuid4().hex
        self.lock = threading.RLock()
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.pending = bytearray()
        try:
            self.sock.sendall(('auth ' + token + '\n').encode('ascii'))
            reply = self._read()
            if reply.get('ok') is not True or reply.get('auth') is not True:
                raise ProtocolError('authentication rejected')
        except Exception:
            self.close()
            raise
        finally:
            del token

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def _read(self):
        deadline = time.monotonic() + self.timeout
        while b'\n' not in self.pending:
            if len(self.pending) > self.max_reply:
                raise ProtocolError('oversized JSON reply')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProtocolError('total JSON reply deadline exceeded')
            self.sock.settimeout(remaining)
            block = self.sock.recv(min(65536, self.max_reply + 1 - len(self.pending)))
            if not block:
                raise ProtocolError('EOF before complete JSON reply; delivery uncertain')
            self.pending.extend(block)
        self.sock.settimeout(self.timeout)
        line, _, rest = self.pending.partition(b'\n')
        self.pending = bytearray(rest)
        if len(line) > self.max_reply:
            raise ProtocolError('oversized JSON reply')
        try:
            reply = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ProtocolError('invalid JSON reply') from exc
        if not isinstance(reply, dict) or type(reply.get('ok')) is not bool:
            raise ProtocolError('missing boolean ok field')
        if reply.get('fatal'):
            raise ProtocolError('unsolicited fatal emulator reply')
        return reply

    def _log(self, event):
        if self.journal:
            event = dict(event, connection_id=self.connection_id,
                         sequence=self.sequence, wall_time_ns=time.time_ns())
            with self.journal.open('a', encoding='utf-8') as out:
                out.write(json.dumps(event, sort_keys=True) + '\n')

    def _call(self, command):
        if any(c in command for c in '\r\n\0'):
            raise ValueError('protocol line injection rejected')
        wire = (command + '\n').encode('utf-8')
        with self.lock:
            if self.sock is None:
                raise ProtocolError('connection closed; reauthenticate explicitly')
            self.sequence += 1
            self._log({'event': 'request', 'command': command})
            try:
                self.sock.sendall(wire)
                reply = self._read()
                safe = dict(reply)
                if 'png' in safe:
                    safe['png'] = '<base64 omitted; capture stored separately>'
                self._log({'event': 'reply', 'response': safe})
            except (OSError, ProtocolError) as exc:
                self.close()
                self._log({'event': 'transport_failure', 'delivery': 'uncertain',
                           'error_type': type(exc).__name__})
                raise ProtocolError('transport failed; do not replay mutations') from exc
            if not reply['ok']:
                raise CommandError(str(reply.get('error', 'unspecified emulator error')))
            return reply

    def status(self):
        result = self._call('status')
        if result.get('protocol') != 1:
            self.close()
            raise ProtocolError('unsupported protocol version')
        return result

    def info(self):
        return self._call('info')

    def hold(self):
        return self._call('hold')

    def registers(self):
        return self._call('regs')

    def memory(self, address, length, view='normal'):
        if (type(address) is not int or type(length) is not int or address < 0
                or not 1 <= length <= 65536 or address + length > 2**32
                or view not in ('normal', 'bus', 'cpu', 'linear')):
            raise ValueError('invalid memory span or view')
        result = self._call(f'memr {address} {length} {view} 1')
        try:
            data = bytes.fromhex(result['data'])
        except (KeyError, TypeError, ValueError) as exc:
            self.close()
            raise ProtocolError('invalid memory hex') from exc
        if len(data) != length or result.get('addr') != address:
            self.close()
            raise ProtocolError('truncated memory read')
        return data

    def text(self):
        result = self._call('text')
        try:
            rows = [bytes.fromhex(row).decode('cp437') for row in result['chars']]
            if len(rows) != result['rows'] or any(len(r) != result['cols'] for r in rows):
                raise ValueError('wrong text dimensions')
        except (KeyError, TypeError, ValueError) as exc:
            self.close()
            raise ProtocolError('invalid CP437 text response') from exc
        return dict(result, lines=rows)

    def framebuffer(self):
        result = self._call('screenshot')
        try:
            png = base64.b64decode(result['png'], validate=True)
            if (len(png) < 33 or png[:8] != b'\x89PNG\r\n\x1a\n'
                    or png[12:16] != b'IHDR'):
                raise ValueError('missing PNG header')
            width, height = struct.unpack('>II', png[16:24])
            if (width, height) != (result['w'], result['h']) or not (0 < width <= 8192 and 0 < height <= 8192):
                raise ValueError('invalid PNG dimensions')
            offset = 8
            ended = False
            while offset < len(png):
                length = int.from_bytes(png[offset:offset + 4], 'big')
                end = offset + 12 + length
                if end > len(png):
                    raise ValueError('truncated PNG chunk')
                chunk = png[offset + 4:offset + 8 + length]
                crc = int.from_bytes(png[offset + 8 + length:end], 'big')
                if zlib.crc32(chunk) != crc:
                    raise ValueError('PNG checksum mismatch')
                if chunk[:4] == b'IEND':
                    if length or end != len(png):
                        raise ValueError('invalid PNG end')
                    ended = True
                offset = end
            if not ended:
                raise ValueError('PNG missing end')
        except (KeyError, TypeError, ValueError) as exc:
            self.close()
            raise ProtocolError('invalid framebuffer payload') from exc
        return png, {k: v for k, v in result.items() if k != 'png'}

    def step(self, milliseconds):
        if type(milliseconds) is not int or not 1 <= milliseconds <= 1000:
            raise ValueError('step must be 1..1000 milliseconds')
        with self.lock:
            before = self.status()
            quantum = before.get('quantum_ms')
            if (before.get('held') is not True or before.get('paused') is not False
                    or quantum not in (1, 10) or milliseconds % quantum):
                raise ValueError('step requires held, unpaused, quantum-aligned machine')
            result = self._call(f'step {milliseconds}')
            after = self.status()
            delta = after['ms'] - before['ms']
            if delta != milliseconds or after.get('held') is not True:
                raise ProtocolError(f'step interrupted: requested {milliseconds}, actual {delta}')
            return dict(result, actual_delta_ms=delta)

    def key(self, action, *codes):
        if (action not in ('down', 'up') or not 1 <= len(codes) <= 8
                or any(type(c) is not int or not 1 <= c <= 0x1ff for c in codes)):
            raise ValueError('invalid key action/scancode')
        return self._call('key ' + action + ' ' + ' '.join(hex(c) for c in codes))

    def tap(self, code):
        with self.lock:
            self.key('down', code)
            return self.key('up', code)

    def type_ascii(self, text):
        # US set-1 keyboard. Validate the entire string before sending any input.
        plain = '1234567890-=qwertyuiop[]asdfghjkl;\'`\\zxcvbnm,./'
        scans = list(range(2, 14)) + list(range(16, 28)) + list(range(30, 42)) + [43] + list(range(44, 54))
        mapping = dict(zip(plain, scans))
        mapping.update({' ': 57, '\n': 28, '\t': 15, '\b': 14, '\x1b': 1})
        shifted = dict(zip('!@#$%^&*()_+{}:"~|<>?', '1234567890-=[];\'`\\,./'))
        events = []
        for char in text:
            shift = char.isascii() and char.isupper() or char in shifted
            base = shifted.get(char, char.lower() if shift else char)
            if base not in mapping:
                raise ValueError('unsupported character in keyboard input')
            events.append((shift, mapping[base]))
        with self.lock:
            for shift, code in events:
                if shift:
                    self.key('down', 42)
                self.tap(code)
                if shift:
                    self.key('up', 42)

    def floppy(self, drive, path=None):
        if type(drive) is not int or drive not in (0, 1):
            raise ValueError('floppy drive must be 0 or 1')
        if path is None:
            return self._call(f'fdd eject {drive}')
        target = Path(path).resolve(strict=True)
        if not target.is_file():
            raise ValueError('floppy path must be a file')
        return self._call(f'fdd load {drive} {target}')

    def reset(self, kind='hard'):
        if kind not in ('hard', 'cad'):
            raise ValueError('reset must be hard or cad')
        return self._call('reset ' + kind)

    def quit(self):
        return self._call('quit')

    def observe(self, spans=(), framebuffer=False):
        """Held group; framebuffer is the latest rendered frame, not an instruction snapshot.

        Caller must approve memory ranges (mapped device reads may have side effects).
        No application semantics or breakpoint precision is implied.
        """
        with self.lock:
            self.hold()
            before, identity = self.status(), self.info()
            registers = self.registers()
            memory = [{'address': a, 'data': self.memory(a, n).hex()} for a, n in spans]
            text = self.text() if before.get('bios_mode') in (0, 1, 2, 3, 7) else None
            png, frame = self.framebuffer() if framebuffer else (None, None)
            after, end_identity = self.status(), self.info()
            fields = ('ms', 'frames', 'held', 'paused', 'bios_mode', 'w', 'h', 'version')
            ids = ('version', 'machine', 'hard_resets', 'soft_resets', 'last_reset_ms')
            if (before.get('held') is not True or before.get('paused') is not False
                    or any(type(before.get(k)) is not int for k in ('ms', 'frames'))
                    or any(type(identity.get(k)) is not int for k in ('hard_resets', 'soft_resets', 'last_reset_ms'))
                    or not identity.get('machine') or not identity.get('version')
                    or any(before.get(k) != after.get(k) for k in fields)
                    or any(identity.get(k) != end_identity.get(k) for k in ids)
                    or frame and any(frame.get(k) != before.get(k) for k in ('ms', 'frames'))):
                raise ProtocolError('inconsistent observation group; discard results')
            return {'status': before, 'info': identity, 'registers': registers,
                    'memory': memory, 'text': text, 'frame': frame}, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--machine', required=True, type=Path)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--journal', type=Path)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('status', 'info', 'hold', 'registers', 'text', 'quit'):
        sub.add_parser(action)
    step = sub.add_parser('step')
    step.add_argument('milliseconds', type=int)
    key = sub.add_parser('tap')
    key.add_argument('code', type=lambda s: int(s, 0))
    typing = sub.add_parser('type')
    typing.add_argument('text')
    mem = sub.add_parser('memory')
    mem.add_argument('address', type=lambda s: int(s, 0))
    mem.add_argument('length', type=lambda s: int(s, 0))
    floppy = sub.add_parser('floppy')
    floppy.add_argument('drive', type=int)
    floppy.add_argument('path', nargs='?')
    reset = sub.add_parser('reset')
    reset.add_argument('kind', choices=('hard', 'cad'))
    capture = sub.add_parser('capture')
    capture.add_argument('prefix', type=Path)
    args = parser.parse_args()
    with Client(args.machine / 'automation.token', args.port, journal=args.journal) as client:
        if args.action == 'capture':
            result, png = client.observe(framebuffer=True)
            # Exclusive publication prevents accidental evidence replacement.
            with args.prefix.with_suffix('.png').open('xb') as out:
                out.write(png)
            result['png_sha256'] = hashlib.sha256(png).hexdigest()
            with args.prefix.with_suffix('.json').open('x', encoding='utf-8') as out:
                json.dump(result, out, indent=2)
            print('\n'.join(result['text']['lines']) if result['text'] else 'graphics mode')
        elif args.action == 'memory':
            print(client.memory(args.address, args.length).hex())
        elif args.action == 'type':
            client.type_ascii(args.text)
        else:
            values = {'step': ('milliseconds',), 'tap': ('code',),
                      'floppy': ('drive', 'path'), 'reset': ('kind',)}
            result = getattr(client, args.action)(*(getattr(args, k) for k in values.get(args.action, ())))
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, ProtocolError, CommandError) as exc:
        print(f'86Box client: {exc}', file=sys.stderr)
        raise SystemExit(2)
