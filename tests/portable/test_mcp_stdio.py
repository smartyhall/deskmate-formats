"""Exercise the installed official SDK client and server over subprocess stdio."""
import asyncio
import base64
from importlib.util import find_spec
import json
import os
import subprocess
import sys
import unittest
from urllib.request import urlopen

from mcp_fixture import NativePeer, png


@unittest.skipUnless(find_spec('mcp'), 'install the mcp extra for SDK integration tests')
class StdioTests(unittest.TestCase):
    def setUp(self):
        self.peer = NativePeer()
        self.addCleanup(self.peer.close)
        self.config_path = self.peer.root / 'private-config.json'
        self.config_path.write_text(json.dumps(self.peer.config()), encoding='utf-8')
        self.args = ['-m', 'deskmate_formats.automation.mcp_server', '--config', str(self.config_path)]

    async def exercise(self, calls, *, observer=False):
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        stderr_path = self.peer.root / 'stderr.txt'
        params = StdioServerParameters(command=sys.executable, args=self.args, env=dict(os.environ))
        with stderr_path.open('w', encoding='utf-8') as stderr:
            async with stdio_client(params, errlog=stderr) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=15) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.server_info.name, 'deskmate-86box-readonly')
                    self.assertIsNotNone(initialized.capabilities.tools)
                    if observer:
                        url = stderr_path.read_text(encoding='utf-8').splitlines()[0].removeprefix(
                            '86Box observatory: ')
                        await calls(session, url)
                    else:
                        await calls(session)
        if not observer:
            self.assertEqual(stderr_path.read_bytes(), b'')

    def test_stdio_owner_publishes_to_its_embedded_listener(self):
        from hashlib import sha256
        from deskmate_formats.observer.journal import publish_event
        from observatory_fixture import event

        config = self.peer.config()
        config['observer'] = {'port': 0}
        item = config['instances']['fixture']
        item['display_approval'] = dict(item['ram_checkpoint'],
                                       screen_sha256=sha256('┌'.encode()).hexdigest())
        self.config_path.write_text(json.dumps(config), encoding='utf-8')
        spool = self.peer.root.parent / 'event-journal'
        publish_event(spool, event(machine_ids=['fixture']))
        self.args.extend(('--journal', str(spool), '--agent-page-limit', '3'))
        address = None

        async def calls(session, url):
            nonlocal address
            address = url
            self.assertRegex(url, r'^http://127\.0\.0\.1:[0-9]+/$')

            def read(route):
                with urlopen(url + route, timeout=2) as response:
                    return response.read()

            self.assertIsNone(json.loads(read('api/status'))['observation'])
            agent_feed = json.loads(read('api/v1/agents'))
            self.assertEqual(agent_feed['limit'], 3)
            self.assertTrue(agent_feed['agents'][0]['historical'])
            self.assertEqual(agent_feed['agents'][0]['machine_ids'], ['fixture'])
            self.assertEqual(self.peer.authentications, 0)
            result = await session.call_tool('observe_machine', {'instance_id': 'fixture'})
            self.assertFalse(result.is_error)
            commands = self.peer.commands.copy()
            for _ in range(3):
                view = json.loads(read('api/status'))['observation']
                self.assertEqual(view['screen'], '┌')
                self.assertEqual(view['observed_at_ms'], result.structured_content['metadata']['observed_at_ms'])
                self.assertEqual(view['emulated_ms'], 1000)
                self.assertIn(b'APPROVED SCREEN TEXT\r\n+\r\n', read('status.txt'))
            self.assertEqual(self.peer.commands, commands)
            self.assertEqual(self.peer.authentications, 1)

        asyncio.run(self.exercise(calls, observer=True))
        self.assertTrue(self.peer.disconnected.wait(2))
        from urllib.error import URLError
        with self.assertRaises(URLError):
            urlopen(address + 'healthz', timeout=1)

    def test_discovery_invocation_and_native_disconnect(self):
        from mcp.types import ImageContent

        async def calls(session):
            tools = (await session.list_tools()).tools
            self.assertEqual({tool.name for tool in tools}, {
                'list_instances', 'get_instance_status', 'get_cpu_registers', 'get_screen_text',
                'get_framebuffer', 'read_memory', 'observe_machine',
            })
            for tool in tools:
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.destructive_hint)
                self.assertFalse(tool.input_schema['additionalProperties'])

            async def call(name, args=None, error=None):
                result = await session.call_tool(name, args)
                self.assertEqual(bool(result.is_error), bool(error))
                data = result.structured_content
                self.assertEqual(json.loads(result.content[0].text), data)
                serialized = json.dumps(data)
                for secret in ('DO_NOT_DISCLOSE', self.peer.token):
                    self.assertNotIn(secret, serialized)
                if error:
                    self.assertEqual(data['error']['code'], error)
                return data, result.content[1:]

            instances, _ = await call('list_instances')
            self.assertEqual(instances['instances'][0]['instance_id'], 'fixture')
            self.assertEqual(instances['instances'][0]['ram_regions'], {'canary': 64})
            await call('get_instance_status', {'instance_id':'unknown'}, 'UNKNOWN_INSTANCE')
            await call('get_instance_status', {'instance_id':'fixture','port':1234}, 'BAD_ARGUMENTS')
            self.assertEqual(self.peer.authentications, 0)
            target = {'instance_id':'fixture'}
            status, _ = await call('get_instance_status', target)
            meta = status['metadata']
            approval = dict(expected_session=meta['server_session'], expected_generation=meta['generation'])
            span = dict(region_id='canary', offset=4, length=4)
            ram, _ = await call('read_memory', dict(target, **approval, **span))
            self.assertEqual(ram['memory'][0]['hex'], bytes(n % 251 for n in range(0x504, 0x508)).hex())
            await call('read_memory', dict(target, **approval, **dict(span, offset=63)), 'MEMORY_DENIED')
            regs, _ = await call('get_cpu_registers', target)
            self.assertEqual(regs['registers']['eax'], 0x13579bdf)
            screen, _ = await call('get_screen_text', target)
            self.assertEqual(screen['screen']['lines'], ['┌'])
            frame, images = await call('get_framebuffer', target)
            self.assertEqual(frame['framebuffer']['ms'], 1000)
            self.assertEqual(len(images), 1)
            self.assertIsInstance(images[0], ImageContent)
            self.assertEqual(images[0].mime_type, 'image/png')
            self.assertEqual(base64.b64decode(images[0].data, validate=True), png())
            group, images = await call('observe_machine', dict(target, **approval,
                memory=[span], include_framebuffer=True))
            self.assertEqual(group['memory'], ram['memory'])
            self.assertEqual(group['screen'], screen['screen'])
            self.assertTrue(group['metadata']['coherent_held_group'])
            self.assertEqual(len(images), 1)
            self.assertEqual(self.peer.authentications, 1)
            self.assertEqual(self.peer.ms, 1000)
            self.peer.held = False
            await call('get_cpu_registers', target, 'ALREADY_HELD_REQUIRED')
            self.peer.held = True
            await call('read_memory', dict(target, **approval, **span), 'MEMORY_APPROVAL_STALE')

        asyncio.run(self.exercise(calls))
        self.assertTrue(self.peer.disconnected.wait(2), 'stdio shutdown did not close the native socket')
        self.assertTrue(all(c.split()[0] in {'status','info','regs','text','memr','screenshot'}
                            for c in self.peer.commands))

    def test_authentication_error_is_structured_and_safe(self):
        self.peer.failure = 'auth'

        async def calls(session):
            result = await session.call_tool('get_instance_status', {'instance_id':'fixture'})
            self.assertTrue(result.is_error)
            self.assertEqual(result.structured_content['error']['code'], 'NATIVE_UNAVAILABLE_OR_INVALID')
            for secret in ('DO_NOT_DISCLOSE', self.peer.token):
                self.assertNotIn(secret, result.content[0].text)

        asyncio.run(self.exercise(calls))
        self.assertEqual(self.peer.authentications, 1)
        self.assertEqual(self.peer.commands, [])

    def test_startup_failure_uses_stderr_and_eof_exits_cleanly(self):
        def run():
            return subprocess.run([sys.executable, *self.args], input=b'', capture_output=True, timeout=15)

        normal = run()
        self.assertEqual((normal.returncode, normal.stdout, normal.stderr), (0, b'', b''))
        self.config_path.write_text('{INVALID DO_NOT_DISCLOSE}', encoding='utf-8')
        failed = run()
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, b'')
        self.assertIn(b'STARTUP_OR_SERVER_FAILED', failed.stderr)
        self.assertNotIn(b'DO_NOT_DISCLOSE', failed.stderr)
        self.assertNotIn(self.peer.token.encode(), failed.stderr)
        self.assertEqual(self.peer.authentications, 0)
