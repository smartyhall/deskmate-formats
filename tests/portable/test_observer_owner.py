"""Exercise the real HTTP and authenticated native transports together."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from importlib.util import find_spec
import json
import socket
from threading import Event, Thread
from time import monotonic
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from deskmate_formats.automation.observer_bridge import prepare_frame
from deskmate_formats.automation.readonly import Adapter, Refusal
from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.observer.http import ObserverServer
from deskmate_formats.observer.journal import publish_event
from mcp_fixture import NativePeer, png
from observatory_fixture import event


def approve(config, *, screen='┌', framebuffer=False):
    item = config['instances']['fixture']
    item['display_approval'] = dict(item['ram_checkpoint'])
    if screen is not None:
        item['display_approval']['screen_sha256'] = sha256(screen.encode()).hexdigest()
    if framebuffer:
        item['display_approval']['framebuffer_sha256'] = sha256(png()).hexdigest()


class OwnerObserverTests(unittest.TestCase):
    def setUp(self):
        self.peer = self.make_peer()
        self.config = self.peer.config()
        self.config['observer'] = {'port': 0}

    def make_peer(self):
        peer = NativePeer()
        self.addCleanup(peer.close)
        return peer

    def start(self, *, agent_publication=None):
        self.adapter = Adapter(self.config)
        self.addCleanup(self.adapter.close)
        self.server = ObserverServer(self.adapter.registry, port=0, agent_publication=agent_publication)
        listener = Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01})
        listener.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(listener.join, 3)
        self.addCleanup(self.server.shutdown)
        self.url = f'http://127.0.0.1:{self.server.port}'

    def call(self, tool='get_instance_status', *, name='fixture', **kwargs):
        return self.adapter.call(tool, {'instance_id': name, **kwargs})

    def get(self, path='/api/status'):
        with urlopen(self.url + path, timeout=3) as reply:
            return reply.read()

    def status(self, name='fixture'):
        return json.loads(self.get(f'/i/{name}/api/status'))

    def http_error(self, path, code):
        with self.assertRaises(HTTPError) as error:
            self.get(path)
        self.assertEqual(error.exception.code, code)
        error.exception.close()

    def test_default_status_only_and_refresh_has_zero_native_activity(self):
        self.start()
        self.assertIsNone(self.status()['observation'])
        self.http_error('/frame.png', 404)
        self.assertEqual(self.peer.authentications, 0)
        meta = self.call()[0]['metadata']
        result, frame = self.call('observe_machine', include_framebuffer=True,
            memory=[{'region_id': 'canary', 'offset': 0, 'length': 8}],
            expected_session=meta['server_session'], expected_generation=meta['generation'])
        self.assertEqual(frame, png())
        self.assertEqual(result['screen']['lines'], ['┌'])
        before = list(self.peer.commands)
        for _ in range(3):
            body = self.get()
            view = json.loads(body)
            obs = view['observation']
            self.assertTrue(obs['held'])
            self.assertEqual(obs['emulated_ms'], 1000)
            self.assertEqual(obs['observed_at_ms'], result['metadata']['observed_at_ms'])
            self.assertIsNone(obs['screen'])
            self.assertIsNone(obs['frame'])
            for private in (self.peer.token, str(self.peer.root), 'registers', 'memory',
                            result['memory'][0]['hex'], '13579bdf', 'SYNTHETIC'):
                self.assertNotIn(private, body.decode())
            self.get('/legacy/')
            self.get('/status.txt')
            self.http_error('/frame.gif', 404)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url + '/api/status', method='POST'), timeout=3)
        self.assertEqual(error.exception.code, 405)
        error.exception.close()
        self.assertEqual(self.peer.commands, before)
        self.assertEqual((self.peer.authentications, self.peer.ms), (1, 1000))

    def test_agent_and_machine_browser_reads_do_not_touch_native_peer(self):
        spool = self.peer.root.parent / 'agent-journal'
        publish_event(spool, event(machine_ids=['fixture']))
        feed = self.enterContext(AgentJournalFeed(spool, interval=0.05))
        approve(self.config)
        self.start(agent_publication=feed.publication)
        self.assertEqual(json.loads(self.get('/api/v1/events'))['events'][0]['machine_ids'], ['fixture'])
        self.assertEqual(self.peer.authentications, 0)
        self.call('get_screen_text')
        baseline = (self.peer.authentications, self.peer.ms, self.peer.frames, self.peer.resets, self.peer.commands[:])
        connect = socket.socket.connect
        connect_ex = socket.socket.connect_ex
        attempts = []

        def guard(operation):
            def checked(peer, address):
                if address != self.server.server_address:
                    attempts.append(address)
                    raise AssertionError('unexpected outbound connection during browser polling')
                return operation(peer, address)
            return checked

        routes = ('/', '/legacy/', '/api/status', '/status.txt', '/i/fixture/api/status', '/healthz',
                  '/api/v1/agents', '/api/v1/events?after=0')
        for disconnected in (False, True):
            if disconnected:
                self.adapter.close()
                self.assertTrue(self.peer.disconnected.wait(2))
            view = self.adapter.registry.stream('fixture').view()
            with patch.object(socket.socket, 'connect', guard(connect)), \
                    patch.object(socket.socket, 'connect_ex', guard(connect_ex)), ThreadPoolExecutor(6) as pool:
                self.assertTrue(all(pool.map(self.get, routes * 20)))
            self.assertEqual(self.adapter.registry.stream('fixture').view(), view)
            self.assertEqual(view.observation.emulated_ms, 1000)
        self.assertEqual(attempts, [])
        self.assertEqual((self.peer.authentications, self.peer.ms, self.peer.frames,
                          self.peer.resets, self.peer.commands), baseline)

    def test_text_approval_canonicalizes_cp437_and_checks_exact_content(self):
        self.peer.text_chars = '01'  # Native MCP decodes as a CP437 low byte.
        approve(self.config, screen='☺')
        self.start()
        self.call('get_screen_text')
        self.assertEqual(self.status()['observation']['screen'], '☺')
        self.call('get_framebuffer')
        self.assertEqual(self.status()['observation']['screen'], '☺')
        self.http_error('/frame.png', 404)
        self.peer.text_chars = '41'
        self.assertEqual(self.call('get_screen_text')[0]['screen']['lines'], ['A'])
        self.assertIsNone(self.status()['observation']['screen'])

    def test_release_or_reset_permanently_retires_display_approval(self):
        approve(self.config)
        self.start()
        self.call('get_screen_text')
        original = self.status()['observation']
        self.peer.held = False
        with self.assertRaisesRegex(Refusal, 'ALREADY_HELD_REQUIRED'):
            self.call('get_screen_text')
        running = self.status()['observation']
        self.assertFalse(running['held'])
        self.assertIsNone(running['screen'])
        self.peer.held = True
        self.call('get_screen_text')
        self.assertIsNone(self.status()['observation']['screen'])
        self.peer.resets += 1
        self.peer.ms = 2
        result, _ = self.call('get_screen_text')
        reset = self.status()['observation']
        self.assertGreater(reset['sequence'], running['sequence'])
        self.assertGreater(reset['generation'], original['generation'])
        self.assertEqual(reset['generation'], result['metadata']['generation'])
        self.assertEqual(reset['emulated_ms'], 2)
        self.assertIsNone(reset['screen'])
        self.assertEqual(self.peer.authentications, 1)
        self.assertTrue(set(self.peer.commands) <= {'status', 'info', 'text'})

    def test_mid_group_reset_drops_display_and_marks_unknown(self):
        approve(self.config)
        self.start()
        self.call('get_screen_text')
        def reset(command):
            if command == 'text':
                self.peer.resets += 1
                self.peer.ms = 0
        self.peer.after_command = reset
        with self.assertRaisesRegex(Refusal, 'INCONSISTENT_OBSERVATION'):
            self.call('get_screen_text')
        view = self.status()
        self.assertTrue(view['stale'])
        for key in ('held', 'paused', 'emulated_ms', 'screen', 'frame'):
            self.assertIsNone(view['observation'][key])

    def test_disconnect_is_stale_and_only_explicit_owner_call_reconnects(self):
        approve(self.config)
        self.start()
        self.call('get_screen_text')
        original = self.status()['observation']
        self.peer.failure = 'eof'
        with self.assertRaisesRegex(Refusal, 'NATIVE_UNAVAILABLE_OR_INVALID'):
            self.call()
        before = list(self.peer.commands)
        self.peer.failure = None
        for _ in range(2):
            view = self.status()
            self.assertTrue(view['stale'])
            stale = view['observation']
            self.assertEqual(stale['connection'], 'error')
            self.assertIsNone(stale['held'])
            self.assertEqual(stale['emulated_ms'], original['emulated_ms'])
            self.assertEqual(stale['screen'], original['screen'])
            self.assertEqual(stale['generation'], original['generation'])
        self.assertEqual(self.peer.commands, before)
        self.assertEqual(self.peer.authentications, 1)
        data, _ = self.call('get_screen_text')
        self.assertEqual(data['metadata']['connection_generation'], 2)
        new = self.status()['observation']
        self.assertGreater(new['sequence'], stale['sequence'])
        self.assertGreater(new['generation'], stale['generation'])
        self.assertIsNone(new['screen'])
        self.assertEqual(self.peer.authentications, 2)

    def test_wrong_launch_credential_cannot_publish(self):
        approve(self.config)
        item = self.config['instances']['fixture']
        item['ram_regions'] = {}
        del item['ram_checkpoint']
        item['display_approval']['token_sha256'] = '0' * 64
        self.start()
        with self.assertRaisesRegex(Refusal, 'NATIVE_UNAVAILABLE_OR_INVALID'):
            self.call('get_screen_text')
        view = self.status()
        self.assertTrue(view['stale'])
        self.assertIsNone(view['observation']['screen'])
        self.assertEqual(self.peer.authentications, 0)

    def test_unreviewed_png_never_reaches_image_preparation(self):
        approve(self.config, framebuffer=True)
        self.config['instances']['fixture']['display_approval']['framebuffer_sha256'] = '0' * 64
        self.start()
        with patch('deskmate_formats.automation.readonly.prepare_frame') as encode:
            _, native = self.call('observe_machine', include_framebuffer=True)
        self.assertEqual(native, png())
        encode.assert_not_called()
        self.assertEqual(self.status()['observation']['screen'], '┌')
        self.http_error('/frame.png', 404)

    def test_configuration_rejects_duplicate_targets_and_unscoped_approval(self):
        item = self.config['instances']['fixture']
        self.config['instances']['other'] = dict(item)
        with self.assertRaisesRegex(ValueError, 'distinct instance'):
            Adapter(self.config)
        del self.config['instances']['other']
        approve(self.config)
        del self.config['observer']
        with self.assertRaisesRegex(ValueError, 'display approval requires'):
            Adapter(self.config)

    def test_slow_http_and_native_instance_do_not_block_another_instance(self):
        other = self.make_peer()
        other.ms = 2000
        self.config['instances']['other'] = other.config()['instances']['fixture']
        approve(self.config)
        self.start()
        entered, release = Event(), Event()
        def delay(command):
            if command == 'status':
                entered.set()
                release.wait(4)
        self.peer.after_command = delay
        with (socket.create_connection(('127.0.0.1', self.server.port), timeout=3) as slow,
              ThreadPoolExecutor(max_workers=2) as workers):
            slow.sendall(b'GET /api/status HTTP/1.0\r\nX-Incomplete: ')
            first = workers.submit(self.call, 'get_screen_text')
            try:
                self.assertTrue(entered.wait(2))
                second = workers.submit(self.call, name='other').result(timeout=2)[0]['metadata']
                self.assertFalse(first.done())
                self.assertIsNone(self.status()['observation'])
                self.assertEqual(self.status('other')['observation']['emulated_ms'], 2000)
            finally:
                release.set()
            result, _ = first.result(timeout=3)
        self.assertNotEqual(result['metadata']['server_session'], second['server_session'])
        with self.assertRaisesRegex(Refusal, 'MEMORY_APPROVAL_STALE'):
            self.call('read_memory', name='other', region_id='canary', offset=0, length=1,
                      expected_session=result['metadata']['server_session'],
                      expected_generation=result['metadata']['generation'])
        self.assertNotEqual(self.status()['publication_session'], self.status('other')['publication_session'])
        self.assertEqual(self.status()['observation']['screen'], '┌')
        self.assertIsNone(self.status('other')['observation']['screen'])
        self.assertEqual((self.peer.authentications, other.authentications), (1, 1))

    @unittest.skipUnless(find_spec('PIL'), 'install observer image extra')
    def test_frame_links_latest_render_and_expired_capture(self):
        from io import BytesIO
        from PIL import Image

        approve(self.config, framebuffer=True)
        self.start()
        data, _ = self.call('observe_machine', include_framebuffer=True)
        view = self.status()
        frame = view['observation']['frame']
        self.assertEqual(frame['captured_at_ms'], data['framebuffer']['captured_at_ms'])
        self.assertTrue(frame['latest_rendered'])
        self.assertEqual(frame['age_basis'], 'capture')
        self.assertIsNone(frame['rendered_at_ms'])
        self.assertIsNone(frame['rendered_emulated_ms'])
        commands = self.peer.commands.copy()
        for extension in ('png', 'gif'):
            with Image.open(BytesIO(self.get(f'/frame.{extension}?frame={frame["key"]}'))) as image:
                self.assertEqual(image.convert('RGB').getpixel((0, 0)), (17, 34, 51))
        self.assertIn(b'latest render at capture', self.get('/status.txt'))
        self.assertEqual(self.peer.commands, commands)
        self.assertEqual((self.peer.authentications, self.peer.ms), (1, 1000))
        self.call()
        retained = self.status()['observation']['frame']
        self.assertEqual(retained, dict(frame, age_ms=retained['age_ms']))
        self.call('get_framebuffer')
        self.http_error(f'/frame.png?frame={frame["key"]}', 404)
        with patch('deskmate_formats.observer.publication.monotonic', return_value=monotonic() + 60):
            self.assertTrue(self.status()['stale'])
            self.assertIsNotNone(self.status()['observation']['frame'])
        self.peer.resets += 1
        self.call()
        self.http_error('/frame.png', 404)

    @unittest.skipUnless(find_spec('PIL'), 'install observer image extra')
    def test_bounded_encoding_runs_off_lock_and_cannot_publish_out_of_order(self):
        approve(self.config, framebuffer=True)
        self.start()
        entered, release = Event(), Event()
        def delay(*args):
            entered.set()
            if not release.wait(4):
                raise AssertionError('timed out waiting to release the encoder')
            return prepare_frame(*args)
        with (patch('deskmate_formats.automation.readonly.prepare_frame', side_effect=delay) as encode,
              ThreadPoolExecutor(max_workers=2) as workers):
            first = workers.submit(self.call, 'observe_machine', include_framebuffer=True)
            try:
                self.assertTrue(entered.wait(2))
                workers.submit(self.call, 'get_framebuffer').result(timeout=2)
                self.assertEqual(encode.call_count, 1)
                self.peer.resets += 1
                latest = workers.submit(self.call).result(timeout=2)[0]['metadata']
                before = self.status()['observation']
                self.assertEqual(before['generation'], latest['generation'])
                self.assertEqual(before['dropped_updates'], 2)
            finally:
                release.set()
            first.result(timeout=3)
        self.assertEqual(self.status()['observation'], before)
        self.http_error('/frame.png', 404)
        self.assertEqual(self.peer.authentications, 1)

    def test_delayed_publication_expires_from_the_sample_time(self):
        self.start()
        with patch('deskmate_formats.automation.readonly.sample_times',
                   return_value=(1, monotonic() - 60)):
            self.call()
        view = self.status()
        self.assertTrue(view['stale'])
        self.assertEqual(view['observation']['observed_at_ms'], 1)
