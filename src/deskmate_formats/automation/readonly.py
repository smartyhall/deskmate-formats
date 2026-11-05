"""Strict single-instance observation policy; no MCP dependency and no mutation.

The adapter intentionally does NOT call Client.observe(), which establishes hold.
Only status/info/regs/text/memr/screenshot are reachable through this interface.
"""
import json
from pathlib import Path
import re
import threading
import uuid

from .client import Client

TOOLS = ('list_instances', 'get_instance_status', 'get_cpu_registers',
         'get_screen_text', 'get_framebuffer', 'read_memory', 'observe_machine')
MAX_READ = 512
MAX_TOTAL = 1024
MAX_FRAME = 1024 * 1024
IDENTIFIER = re.compile(r'[A-Za-z0-9_-]{1,64}\Z')
RESET_FIELDS = ('hard_resets', 'soft_resets', 'last_reset_ms')
STATUS_FIELDS = ('ms', 'frames', 'held', 'paused', 'bios_mode', 'w', 'h')


class Refusal(Exception):
    """Safe machine-readable error; native exception strings are never exposed."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('invalid integer')
    return value


def configuration(path):
    """Owner-only config, no native token contents or credentials in configuration."""
    try:
        with Path(path).open('rb') as stream:
            data = stream.read(65537)
        if len(data) > 65536:
            raise ValueError()
        return validate_config(json.loads(data.decode('utf-8')))
    except Exception:
        raise Refusal('INVALID_CONFIGURATION') from None


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {'instances'}:
        raise ValueError('one explicit instances mapping required')
    instances = config['instances']
    if not isinstance(instances, dict) or len(instances) != 1:
        raise ValueError('Phase I supports exactly one configured instance')
    for name, item in instances.items():
        if not IDENTIFIER.fullmatch(name) or not isinstance(item, dict):
            raise ValueError('invalid instance')
        required = {'machine_directory', 'port', 'expected_machine', 'expected_version', 'ram_regions'}
        if not required <= set(item) <= required | {'ram_checkpoint'}:
            raise ValueError('invalid instance fields')
        if not Path(item['machine_directory']).is_absolute():
            raise ValueError('machine directory must be absolute')
        integer(item['port'], 1, 65535)
        for key, pattern in (('expected_machine', r'[A-Za-z0-9_.-]{1,64}'),
                             ('expected_version', r'[A-Za-z0-9_. \[\]()-]{1,64}')):
            if not isinstance(item[key], str) or not re.fullmatch(pattern, item[key]):
                raise ValueError('invalid expected identity')
        regions = item['ram_regions']
        if not isinstance(regions, dict) or len(regions) > 16:
            raise ValueError('invalid regions')
        for region, span in regions.items():
            if not IDENTIFIER.fullmatch(region) or not isinstance(span, dict) or set(span) != {'start','length'}:
                raise ValueError('invalid region')
            start = integer(span['start'], 0x500, 0x9ffff)
            length = integer(span['length'], 1, 4096)
            if start + length > 0xa0000:
                raise ValueError('only conventional ordinary RAM is supported')
        checkpoint = item.get('ram_checkpoint')
        if regions:
            counts = ('ms', 'frames', *RESET_FIELDS)
            if not isinstance(checkpoint, dict) or set(checkpoint) != {'token_sha256', *counts}:
                raise ValueError('RAM requires an owner-verified checkpoint')
            for key in counts:
                integer(checkpoint[key], 0, 2**64-1)
            if not isinstance(checkpoint['token_sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', checkpoint['token_sha256']):
                raise ValueError('invalid checkpoint token fingerprint')
        elif checkpoint is not None:
            raise ValueError('RAM checkpoint requires configured regions')
    return config


class Adapter:
    """One serialized lazy connection, explicit generations, no implicit retries."""

    def __init__(self, config, client_factory=Client):
        self.config = validate_config(config)
        self.instance_id, self.item = next(iter(config['instances'].items()))
        self.factory = client_factory
        self.client = None
        self.lock = threading.RLock()
        self.server_session = uuid.uuid4().hex  # Local identity, NOT a process UUID.
        self.generation = 0
        self.connection_generation = 0
        self.mapping_valid = bool(self.item['ram_regions'])
        self.last = None
        self.last_error = None

    def close(self):
        with self.lock:
            if self.client is not None:
                self.client.close()  # Never quit/release/hold the emulator.
                self.client = None

    def drop(self):
        self.close()
        self.generation += 1
        self.mapping_valid = False

    def invalidate_mapping(self):
        if self.mapping_valid:
            self.generation += 1
            self.mapping_valid = False

    def connect(self):
        if self.client is None:
            checkpoint = self.item.get('ram_checkpoint') or {}
            self.client = self.factory(Path(self.item['machine_directory']) / 'automation.token',
                port=self.item['port'], host='127.0.0.1', timeout=5, max_reply=2*1024*1024,
                expected_token_sha256=checkpoint.get('token_sha256'))
            self.connection_generation += 1
            self.generation += 1
            if self.connection_generation > 1:
                self.mapping_valid = False
            self.last = None
        return self.client

    def track(self, status, info):
        for k in ('ms','frames','w','h','bios_mode'):
            integer(status[k], 0, 2**64-1)
        if type(status['held']) is not bool or type(status['paused']) is not bool:
            raise ValueError('invalid hold status')
        if (info['machine'] != self.item['expected_machine']
                or info['version'] != self.item['expected_version']
                or status['version'] != info['version']):
            raise Refusal('TARGET_MISMATCH')
        reset = tuple(integer(info[k], 0, 2**64-1) for k in RESET_FIELDS)
        sample = reset, tuple(status[k] for k in STATUS_FIELDS)
        checkpoint = self.item.get('ram_checkpoint')
        if self.last and (reset != self.last[0] or status['ms'] < self.last[1][0]):
            self.generation += 1
            self.mapping_valid = False
        if self.mapping_valid and (
                not status['held'] or status['paused']
                or any(status[k] != checkpoint[k] for k in ('ms', 'frames'))
                or reset != tuple(checkpoint[k] for k in RESET_FIELDS)
                or self.last is not None and sample != self.last):
            self.invalidate_mapping()
        self.last = sample
        return sample

    def memory_spans(self, requests):
        if not isinstance(requests, list) or len(requests) > 4:
            raise Refusal('REQUEST_LIMIT')
        spans = []
        total = 0
        for request in requests:
            if not isinstance(request, dict) or set(request) != {'region_id','offset','length'}:
                raise Refusal('BAD_ARGUMENTS')
            try:
                region = self.item['ram_regions'][request['region_id']]
                offset = integer(request['offset'], 0, 4095)
                length = integer(request['length'], 1, MAX_READ)
            except Exception:
                raise Refusal('MEMORY_DENIED') from None
            if offset + length > region['length']:
                raise Refusal('MEMORY_DENIED')
            total += length
            spans.append((request['region_id'], region['start']+offset, length))
        if total > MAX_TOTAL:
            raise Refusal('REQUEST_LIMIT')
        return spans

    def call(self, tool, arguments):
        """Return (safe JSON object, optional PNG); Refusal carries only a fixed code."""
        with self.lock:
            try:
                return self._call(tool, arguments)
            except Refusal as exc:
                self.last_error = exc.code
                if exc.code == 'TARGET_MISMATCH':
                    self.drop()
                elif exc.code == 'INCONSISTENT_OBSERVATION':
                    self.invalidate_mapping()
                raise
            except Exception:
                self.drop()
                self.last_error = 'NATIVE_UNAVAILABLE_OR_INVALID'
                raise Refusal(self.last_error) from None

    def _call(self, tool, args):
        if tool not in TOOLS:
            raise Refusal('UNKNOWN_TOOL')
        if not isinstance(args, dict):
            raise Refusal('BAD_ARGUMENTS')
        if tool == 'list_instances':
            if args:
                raise Refusal('BAD_ARGUMENTS')
            return {'instances':[{'instance_id':self.instance_id,
                'availability':'connected' if self.client else 'not_connected',
                'last_error':self.last_error,
                'ram_regions':{name: span['length'] for name, span in self.item['ram_regions'].items()}}]}, None
        allowed = {'instance_id'}
        if tool == 'read_memory':
            allowed |= {'region_id','offset','length','expected_generation','expected_session'}
        if tool == 'observe_machine':
            allowed |= {'memory','include_text','include_framebuffer','expected_generation','expected_session'}
        if set(args) - allowed or args.get('instance_id') != self.instance_id:
            raise Refusal('UNKNOWN_INSTANCE' if args.get('instance_id') != self.instance_id else 'BAD_ARGUMENTS')
        for key in ('include_text','include_framebuffer'):
            if key in args and type(args[key]) is not bool:
                raise Refusal('BAD_ARGUMENTS')
        requests = args.get('memory', [])
        if tool == 'read_memory':
            if not {'region_id','offset','length','expected_generation','expected_session'} <= set(args):
                raise Refusal('BAD_ARGUMENTS')
            requests = [{k:args[k] for k in ('region_id','offset','length')}]
        spans = self.memory_spans(requests)
        c = self.connect()
        before, identity = c.status(), c.info()
        sample = self.track(before, identity)
        held = before['held'] and not before['paused']
        if tool != 'get_instance_status' and not held:
            raise Refusal('ALREADY_HELD_REQUIRED')
        if spans and (not self.mapping_valid or args.get('expected_generation') != self.generation
                      or type(args.get('expected_generation')) is not int
                      or args.get('expected_session') != self.server_session):
            raise Refusal('MEMORY_APPROVAL_STALE')
        result = {}
        if tool in ('get_cpu_registers','observe_machine'):
            registers = c.registers()
            if not registers or len(registers) > 128 or any(
                    not re.fullmatch(r'[a-z0-9_]{1,32}', k) or type(v) not in (int, bool)
                    or isinstance(v, int) and not 0 <= v < 2**64 for k,v in registers.items()):
                raise ValueError('malformed registers')
            result['registers'] = registers
        if tool == 'get_screen_text' or tool == 'observe_machine' and args.get('include_text', True):
            if before['bios_mode'] not in (0,1,2,3,7):
                raise Refusal('TEXT_MODE_REQUIRED')
            screen = c.text()
            if not (type(screen['cols']) is int and type(screen['rows']) is int
                    and 1 <= screen['cols'] <= 160 and 1 <= screen['rows'] <= 60
                    and type(screen['mode']) is int and screen['mode'] == before['bios_mode']
                    and isinstance(screen['cursor'], list) and len(screen['cursor']) == 2
                    and all(type(v) is int and 0 <= v < 160 for v in screen['cursor'])
                    and isinstance(screen['lines'], list) and len(screen['lines']) == screen['rows']
                    and all(isinstance(v,str) and len(v) == screen['cols'] for v in screen['lines'])):
                raise ValueError('text dimensions')
            result['screen'] = {k:screen[k] for k in ('mode','cols','rows','cursor','lines')}
        png = None
        if tool == 'get_framebuffer' or tool == 'observe_machine' and args.get('include_framebuffer', False):
            png, frame = c.framebuffer()
            if len(png) > MAX_FRAME or frame['w']*frame['h'] > 2048*1536:
                raise Refusal('FRAMEBUFFER_LIMIT')
            if any(frame[k] != before[k] for k in ('ms','frames','w','h')):
                raise Refusal('INCONSISTENT_OBSERVATION')
            result['framebuffer'] = {k:frame[k] for k in ('ms','frames','w','h')}
            result['framebuffer']['semantics'] = 'last rendered frame; not instruction precise'
        if spans:
            result['memory'] = []
            for index, (name, address, length) in enumerate(spans):
                # Recheck after other reads before sending the next memory request.
                if (index or tool == 'observe_machine') and self.track(c.status(), c.info()) != sample:
                    raise Refusal('INCONSISTENT_OBSERVATION')
                data = c.memory(address, length)
                result['memory'].append({'region_id':name,'address':address,'length':length,
                    'view':'normal','width':1,'hex':data.hex()})
        after, end = c.status(), c.info()
        final_sample = self.track(after, end)
        if tool != 'get_instance_status' and final_sample != sample:
            raise Refusal('INCONSISTENT_OBSERVATION')
        result['metadata'] = {'instance_id':self.instance_id, 'server_session':self.server_session,
            'generation':self.generation,'connection_generation':self.connection_generation,
            'memory_mapping_valid':self.mapping_valid,'coherent_held_group':tool != 'get_instance_status',
            'process_identity':'not provided by native protocol; no cross-restart guarantee',
            'status':{k:after[k] for k in ('ms','frames','held','paused','w','h','bios_mode')},
            'identity':{k:end[k] for k in ('machine','version','hard_resets','soft_resets','last_reset_ms')}}
        self.last_error = None
        return result, png
