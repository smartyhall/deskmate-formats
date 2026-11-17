"""Offline Windows S3 selection and policy regression tests; no native launches."""

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from unittest.mock import patch

from deskmate_formats.observer.events import encode_json
from deskmate_formats.supervisor import driver


class WindowsBackendTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.auth = self.root / 'auth.json'
        self.auth.write_text('{"OPENAI_API_KEY":"synthetic-not-a-key"}')
        self.enterContext(patch.object(driver, 'verify_native', return_value=str(Path(sys.executable).resolve())))
        self.enterContext(patch.object(driver, 'task_prompt', return_value='offline synthetic context'))
        self.enterContext(patch.object(driver, 'AppServer', side_effect=AssertionError('native launch forbidden')))

    def prepare(self, **kw):
        root = self.root / 'run'
        driver.prepare(root, executable=sys.executable, model='synthetic-selected', effort='low',
                       profile='experimental-lab', auth_file=self.auth, binding={},
                       task_context={'class':'source-edit-v1'}, edit_workspace={'path':str(self.root)}, **kw)
        return root, driver.load_plan(root)

    def test_disabled_or_unsupported_backend_refused_without_staging(self):
        for backend in (None, 'disabled', 'elevated', 'mxc'):
            with self.subTest(backend=backend), self.assertRaisesRegex(driver.DriverError, 'explicit Windows sandbox'):
                self.prepare(windows_sandbox=backend)
            self.assertFalse((self.root / 'run').exists())

    def test_explicit_backend_is_frozen_without_tool_expansion(self):
        root, (plan, token) = self.prepare(windows_sandbox='unelevated')
        config_path = root / 'codex-home/config.toml'
        config = tomllib.loads(config_path.read_text())
        self.assertEqual(config['windows'], {'sandbox':'unelevated'})
        self.assertTrue(driver._windows_editing_matches(root, plan))
        self.assertEqual(plan['windows_sandbox'], 'unelevated')
        self.assertEqual(token, sha256(encode_json(plan)).hexdigest())
        self.assertNotEqual(token, sha256(encode_json(plan | {'windows_sandbox':'disabled'})).hexdigest())
        self.assertEqual(config['approval_policy'], 'never')
        self.assertEqual(config['web_search'], 'disabled')
        self.assertEqual(config['mcp_servers'], {})
        self.assertEqual(config['features'], dict.fromkeys(
            ('shell_tool','js_repl','code_mode','multi_agent','multi_agent_v2','codex_git_commit'), False))
        self.assertEqual(config['sandbox_workspace_write'],
                         {'network_access':False,'exclude_tmpdir_env_var':True,'exclude_slash_tmp':True})
        self.assertEqual(plan['config_sha256'], sha256(config_path.read_bytes()).hexdigest())
        self.assertFalse(driver._windows_editing_matches(root, plan | {'windows_sandbox':'disabled'}))
        with self.assertRaisesRegex(driver.DriverError, 'exact plan digest'):
            driver._validate_plan(root, plan, token, '0'*64, None)
        config_path.write_text(config_path.read_text().replace('unelevated', 'disabled'))
        self.assertFalse(driver._windows_editing_matches(root, plan))
        with patch.object(driver, '_task_plan_matches', return_value=True), self.assertRaisesRegex(driver.DriverError, 'configuration changed'):
            driver._validate_plan(root, plan, token, token, None, token)

    def test_native_fallback_and_policy_expansion_rejected(self):
        root, (plan, _) = self.prepare(windows_sandbox='unelevated')
        policy = {'cwd':str(self.root),'approvalPolicy':'never','approvalsReviewer':'user',
                  'model':plan['model'],'modelProvider':'openai','reasoningEffort':'low',
                  'thread':{'ephemeral':False,'turns':[]},
                  'sandbox':{'type':'workspaceWrite','writableRoots':[], 'networkAccess':False,
                             'excludeTmpdirEnvVar':True,'excludeSlashTmp':True}}
        driver._effective_policy(policy, plan, self.root)
        for change in ({'sandbox':{'type':'readOnly','networkAccess':False}},
                       {'approvalPolicy':'on-request'}, {'approvalsReviewer':'auto_review'},
                       {'sandbox':policy['sandbox'] | {'networkAccess':True}},
                       {'sandbox':policy['sandbox'] | {'writableRoots':[str(root)]}}):
            with self.subTest(change=change), self.assertRaises(driver.DriverError):
                driver._effective_policy(deepcopy(policy) | change, plan, self.root)

    def test_s0_and_s2_keep_readonly_config_and_reject_backend_selection(self):
        for context in (None, {'class':'text-analysis-v1'}):
            root=self.root / ('s0' if context is None else 's2')
            args=dict(executable=sys.executable, model='synthetic-selected', effort='low',
                      profile='experimental-lab', auth_file=self.auth, task_context=context,
                      binding=None if context is None else {})
            with self.assertRaisesRegex(driver.DriverError, 'only supported for live S3'):
                driver.prepare(root, **args, windows_sandbox='unelevated')
            driver.prepare(root, **args)
            config=tomllib.loads((root/'codex-home/config.toml').read_text())
            self.assertEqual(config['sandbox_mode'],'read-only')
            self.assertNotIn('windows',config)
            self.assertNotIn('windows_sandbox',driver.load_plan(root)[0])
