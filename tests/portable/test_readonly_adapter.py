"""Real synthetic native TCP tests; no optional MCP dependency needed."""
import json
import unittest

from deskmate_formats.automation.client import Client
from deskmate_formats.automation.readonly import Adapter, Refusal, validate_config
from mcp_fixture import NativePeer, png


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.peer = NativePeer()
        self.addCleanup(self.peer.close)
        def factory(path, **options):
            options['timeout'] = 0.3
            return Client(path, **options)
        self.adapter = Adapter(self.peer.config(), client_factory=factory)
        self.addCleanup(self.adapter.close)

    def call(self, name, **args):
        return self.adapter.call(name,dict(instance_id='fixture',**args))

    def read_args(self):
        meta = self.call('get_instance_status')[0]['metadata']
        return dict(region_id='canary',offset=0,length=32,expected_generation=meta['generation'],
                    expected_session=meta['server_session'])

    def test_registry_routing_and_unknown_instance(self):
        data,_ = self.adapter.call('list_instances',{})
        self.assertEqual(data['instances'][0]['instance_id'],'fixture')
        self.assertEqual(self.peer.authentications,0)
        with self.assertRaisesRegex(Refusal,'UNKNOWN_INSTANCE'):
            self.adapter.call('get_instance_status',{'instance_id':'unknown'})
        self.assertEqual(self.peer.authentications,0)

    def test_safe_status_registers_text_frame_and_memory(self):
        args = self.read_args()
        result,_ = self.call('read_memory',**args)
        self.assertEqual(len(bytes.fromhex(result['memory'][0]['hex'])),32)
        self.assertEqual(self.call('get_cpu_registers')[0]['registers']['eax'],0x13579bdf)
        self.assertEqual(self.call('get_screen_text')[0]['screen']['lines'],['┌'])
        result, frame = self.call('get_framebuffer')
        self.assertEqual(frame,png())
        self.assertNotIn(str(self.peer.root),json.dumps(result))
        self.assertNotIn(self.peer.token,json.dumps(result))
        self.assertTrue(all(c.split()[0] in ('status','info','regs','text','screenshot','memr') for c in self.peer.commands))

    def test_memory_denied_before_native_access(self):
        for args in (dict(region_id='other',offset=0,length=1),
                     dict(region_id='canary',offset=50,length=32),
                     dict(region_id='canary',offset=0,length=65536),
                     dict(region_id='canary',offset=True,length=1)):
            with self.assertRaises(Refusal):
                self.call('read_memory',**args,expected_generation=1,expected_session='0'*32)
        self.assertEqual(self.peer.commands,[])

    def test_total_request_limit(self):
        reads = [dict(region_id='canary',offset=0,length=1)]*5
        with self.assertRaisesRegex(Refusal,'REQUEST_LIMIT'):
            self.call('observe_machine',memory=reads)

    def test_unheld_status_allowed_but_observation_never_holds(self):
        self.peer.held = False
        self.assertFalse(self.call('get_instance_status')[0]['metadata']['status']['held'])
        with self.assertRaisesRegex(Refusal,'ALREADY_HELD_REQUIRED'):
            self.call('get_cpu_registers')
        self.assertNotIn('hold',self.peer.commands)
        self.assertFalse(self.peer.held)

    def test_auth_transport_timeout_and_malformed_errors_are_safe(self):
        for failure in ('auth','eof','json','timeout'):
            with self.subTest(failure=failure):
                self.adapter.close()
                self.peer.failure = failure
                with self.assertRaises(Refusal) as error:
                    self.call('get_instance_status')
                self.assertNotIn(str(self.peer.root),str(error.exception))
                self.assertNotIn(self.peer.token,str(error.exception))
                self.assertIsNone(self.adapter.client)

    def test_reset_invalidates_memory_but_keeps_observation_available(self):
        args = self.read_args()
        previous = self.adapter.generation
        self.peer.resets += 1
        new = self.call('get_instance_status')[0]['metadata']
        self.assertGreater(new['generation'],previous)
        self.assertFalse(new['memory_mapping_valid'])
        with self.assertRaisesRegex(Refusal,'MEMORY_APPROVAL_STALE'):
            self.call('read_memory',**args)
        self.call('get_cpu_registers')

    def test_execution_before_first_connection_invalidates_owner_checkpoint(self):
        self.peer.ms += 1
        args = self.read_args()
        self.assert_no_memory_read(args)

    def test_execution_between_held_observations_invalidates_even_fresh_generation(self):
        args = self.read_args()
        self.peer.ms += 1
        self.assert_no_memory_read(args)
        self.assert_no_memory_read(self.read_args())

    def test_observed_release_invalidates_even_after_rehold_at_same_time(self):
        args = self.read_args()
        self.peer.held = False
        self.assertFalse(self.call('get_instance_status')[0]['metadata']['memory_mapping_valid'])
        self.peer.held = True
        self.assert_no_memory_read(args)

    def test_mid_group_execution_prevents_memory_dispatch(self):
        args = self.read_args()
        def advance(command):
            if command == 'regs':
                self.peer.ms += 1
        self.peer.after_command = advance
        with self.assertRaisesRegex(Refusal, 'INCONSISTENT_OBSERVATION'):
            self.call('observe_machine', include_text=False,
                      memory=[{k:args[k] for k in ('region_id','offset','length')}],
                      expected_generation=args['expected_generation'], expected_session=args['expected_session'])
        self.assertFalse(any(c.startswith('memr ') for c in self.peer.commands))
        self.assert_no_memory_read(self.read_args())

    def test_execution_during_memory_read_discards_result_and_stales_approval(self):
        args = self.read_args()
        def advance(command):
            if command.startswith('memr '):
                self.peer.ms += 1
        self.peer.after_command = advance
        with self.assertRaisesRegex(Refusal, 'INCONSISTENT_OBSERVATION'):
            self.call('read_memory', **args)
        self.assertEqual(sum(c.startswith('memr ') for c in self.peer.commands), 1)
        self.assert_no_memory_read(self.read_args())

    def test_identity_mismatch_invalidates_memory_after_reconnect(self):
        args = self.read_args()
        self.peer.machine = 'OTHER'
        with self.assertRaisesRegex(Refusal, 'TARGET_MISMATCH'):
            self.call('read_memory', **args)
        self.peer.machine = 'SYNTHETIC'
        self.assert_no_memory_read(self.read_args())

    def test_different_token_refused_before_connecting(self):
        (self.peer.root / 'automation.token').write_text('cd' * 32, encoding='ascii')
        with self.assertRaisesRegex(Refusal, 'NATIVE_UNAVAILABLE_OR_INVALID'):
            self.call('get_instance_status')
        self.assertEqual(self.peer.authentications, 0)

    def test_wrong_session_or_generation_refuses_without_invalidating_checkpoint(self):
        args = self.read_args()
        self.assert_no_memory_read(dict(args, expected_session='0' * 32))
        self.assert_no_memory_read(dict(args, expected_generation=args['expected_generation'] + 1))
        self.call('read_memory', **args)

    def assert_no_memory_read(self, args):
        before = len(self.peer.commands)
        with self.assertRaisesRegex(Refusal, 'MEMORY_APPROVAL_STALE'):
            self.call('read_memory', **args)
        self.assertFalse(any(c.startswith('memr ') for c in self.peer.commands[before:]))

    def test_disconnect_no_automatic_retry_and_new_connection_generation(self):
        self.read_args()
        before = self.peer.authentications
        self.peer.failure = 'eof'
        with self.assertRaises(Refusal):
            self.call('get_instance_status')
        self.assertEqual(self.peer.authentications,before)
        self.peer.failure = None
        meta = self.call('get_instance_status')[0]['metadata']
        self.assertEqual(meta['connection_generation'],2)
        self.assertFalse(meta['memory_mapping_valid'])
        self.assert_no_memory_read(self.read_args())

    def test_invalid_framebuffer_is_rejected_and_connection_invalidated(self):
        self.peer.bad_png = True
        with self.assertRaises(Refusal):
            self.call('get_framebuffer')
        self.assertIsNone(self.adapter.client)

    def test_no_default_instance_or_rom_configuration(self):
        for mutate in ('empty','rom','missing_checkpoint'):
            config = self.peer.config()
            if mutate == 'empty': config['instances'] = {}
            if mutate == 'rom': config['instances']['fixture']['ram_regions']['canary']['start'] = 0xf0000
            if mutate == 'missing_checkpoint': del config['instances']['fixture']['ram_checkpoint']
            with self.assertRaises(ValueError):
                validate_config(config)


if __name__ == '__main__':
    unittest.main()
