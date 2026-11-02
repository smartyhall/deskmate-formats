"""Experimental, independently authored protocol model; NEVER connects to 86Box.

Only an intentionally small, stricter subset is simulated. Fixture bytes,
registers and images are synthetic. Passing these tests does not validate an
emulator build, transport, debugger or MCP registration.
"""
import base64
import json


class Model:
    """Line/JSON fixture with explicit failure injection; no ROMs or sockets."""

    def __init__(self):
        self.ms = 0
        self.frames = 1
        self.held = True
        self.resets = 0
        self.connected = True
        self.fail_after_apply = False
        self.keys = set()
        self.memory = bytes((i % 251 for i in range(65536)))
        self.version = 'MOCK-ONLY'

    def line(self, request):
        if not self.connected:
            raise ConnectionError('model disconnected')
        if '\n' in request or '\r' in request:
            raise ValueError('one line required')
        parts = request.split()
        if not parts:
            raise ValueError('empty line')
        verb = parts[0]
        reply = {'ok': True}
        if parts == ['status']:
            reply.update(protocol=1, version=self.version, ms=self.ms,
                         frames=self.frames, held=self.held, paused=False,
                         ff=False, w=1, h=1, quantum_ms=1)
        elif parts == ['info']:
            reply.update(version=self.version, machine='SYNTHETIC',
                         hard_resets=self.resets, soft_resets=0)
        elif parts == ['hold']:
            self.held = True
            reply.update(ms=self.ms, frames=self.frames, held=True)
        elif len(parts) == 2 and verb == 'step':
            amount = int(parts[1], 0)
            if not 1 <= amount <= 1000:
                raise ValueError('model step bound')
            self.ms += amount
            reply.update(ms=self.ms, frames=self.frames, held=self.held)
        elif len(parts) == 3 and verb == 'key' and parts[1] in ('down', 'up'):
            scan = int(parts[2], 0)
            if not 0 <= scan <= 0x1ff:
                raise ValueError('model scancode bound')
            if parts[1] == 'down':
                self.keys.add(scan)
            else:
                self.keys.discard(scan)
            self.ms += 2
            reply.update(ms=self.ms, frames=self.frames, held=self.held)
        elif parts == ['regs']:
            reply.update(eax=0x0206, ebx=0x100, ecx=0, edx=0x80,
                         esi=0, edi=0, ebp=0, esp=0x800,
                         eip=0x100, eflags=0x202, cs=0, ds=0, es=0,
                         ss=0, cs_base=0, cr0=0)
        elif len(parts) == 5 and verb == 'memr' and parts[3:] == ['normal', '1']:
            start, length = int(parts[1], 0), int(parts[2], 0)
            if not (0 <= start < len(self.memory) and 1 <= length <= 4096
                    and start + length <= len(self.memory)):
                raise ValueError('model memory bound')
            reply.update(addr=start, data=self.memory[start:start + length].hex())
        elif parts == ['screenshot']:
            # Synthetic marker, deliberately not a usable emulator screenshot.
            reply.update(w=1, h=1, ms=self.ms, frames=self.frames,
                         png=base64.b64encode(b'SYNTHETIC-IMAGE').decode())
        else:
            reply = {'ok': False, 'error': 'outside model subset'}
        if self.fail_after_apply:
            self.fail_after_apply = False
            self.connected = False
            raise ConnectionError('model lost reply after applying request')
        return json.dumps(reply)


class ObservationHarness:
    """Proposed epoch/bracketing policy exercised against a synthetic model.

    No socket implementation or production MCP adapter is provided. A live
    adapter additionally needs an out-of-band per-run identity and RAM map.
    """

    def __init__(self, exchange, expected_version='MOCK-ONLY'):
        self.exchange = exchange
        self.expected_version = expected_version
        self.epoch = 0
        self.ready = False

    def call(self, request):
        try:
            reply = json.loads(self.exchange(request))
            if not isinstance(reply, dict) or reply.get('ok') is not True:
                raise ValueError('failed or malformed reply')
            return reply
        except (OSError, ValueError, TypeError):
            self.ready = False
            self.epoch += 1
            raise

    def attach(self):
        self.ready = False
        self.epoch += 1
        status, info = self.call('status'), self.call('info')
        if (status.get('protocol') != 1 or status.get('version') != self.expected_version
                or info.get('version') != self.expected_version
                or info.get('machine') != 'SYNTHETIC'):
            raise ValueError('wrong model target')
        self.call('hold')
        self.reset_pair = self.resets(self.call('info'))
        self.ready = True
        return self.epoch

    @staticmethod
    def resets(info):
        pair = (info.get('hard_resets'), info.get('soft_resets'))
        if any(type(n) is not int or n < 0 for n in pair):
            raise ValueError('missing reset counters')
        return pair

    def observe(self, epoch, address, length, framebuffer=False):
        if not self.ready or epoch != self.epoch:
            raise ValueError('stale observation epoch')
        if (type(address) is not int or type(length) is not int or address < 0
                or not 1 <= length <= 4096 or address + length > 65536):
            raise ValueError('outside synthetic RAM window')
        try:
            before = self.call('status')
            start_resets = self.resets(self.call('info'))
            regs = self.call('regs')
            mem = self.call(f'memr {address} {length} normal 1')
            frame = self.call('screenshot') if framebuffer else None
            after = self.call('status')
            end_resets = self.resets(self.call('info'))
            if (before.get('held') is not True or after.get('held') is not True
                    or before.get('paused') is not False or after.get('paused') is not False
                    or any(before.get(k) != after.get(k) for k in ('ms', 'frames', 'version'))
                    or before.get('version') != self.expected_version
                    or start_resets != end_resets or start_resets != self.reset_pair):
                raise ValueError('inconsistent observation')
            raw = bytes.fromhex(mem['data'])
            if mem.get('addr') != address or len(raw) != length:
                raise ValueError('wrong memory span')
            if frame and (frame.get('ms') != before['ms']
                          or frame.get('frames') != before['frames']):
                raise ValueError('frame timing changed')
            return dict(mock_only=True, epoch=epoch, ms=before['ms'],
                        regs=regs, data=raw.hex(), frame=frame)
        except (KeyError, OSError, ValueError, TypeError):
            self.ready = False
            self.epoch += 1
            raise
