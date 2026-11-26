"""Synthetic-only S3 end-to-end and permanent-fence failure regression coverage."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from deskmate_formats.observer.agent_feed import AgentJournalFeed
from deskmate_formats.supervisor import editing, workspace
from deskmate_formats.supervisor.bridge import grant as text_grant
from deskmate_formats.supervisor.driver import DriverError, load_plan, read_record
from deskmate_formats.supervisor.task_manifest import TaskError, validate_manifest
from deskmate_formats.supervisor.task_queue import open_queue
from task_fixture import TaskRepo, TASK_PATH, manifest

LICENSE = b'SPDX-FileCopyrightText: 2026 DeskMate Formats contributors\nSPDX-License-Identifier: GPL-3.0-or-later\n'


def make_repository(path):
    repo = TaskRepo(path)
    files = {
        'src/sample.py': b'def answer():\n    return 1\n',
        'tests/portable/test_s3_sample.py': b'import unittest\nfrom src.sample import answer\nclass Sample(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(), 1)\n',
        'tests/fixtures/application-generated/manifest.json': b'{"fixtures":[]}',
    }
    for name, raw in list(files.items()):
        repo.stage(name, raw)
        repo.stage(name + '.license', LICENSE)
    repo.stage('LICENSES/GPL-3.0-or-later.txt', (Path(__file__).resolve().parents[2] / 'LICENSES/GPL-3.0-or-later.txt').read_bytes())
    source = repo.commit()
    dev = {'source_revision': source, 'modify': ['src/sample.py', 'tests/portable/test_s3_sample.py'],
           'create': [], 'acceptance': ['answer returns 2 and the corresponding real regression test passes'],
           'test_profiles': ['synthetic-unit'], 'deliverables': ['final-response', 'local-checkpoint']}
    commit = repo.commit(manifest(schema_version=2, title='Synthetic bounded edit', description='Change answer from 1 to 2 and its test.',
                                  resources=['source-read', 'source-edit', 'portable-tests'], development=dev))
    return repo, source, commit


class EditingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.repo, self.source, self.commit = make_repository(self.root / 'git')
        self.queue = self.root / 'queue'
        self.state = self.root / 'state'
        with open_queue(self.queue, source=self.repo.source()) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)

    def accept(self):
        with open_queue(self.queue) as queue:
            queue.decide(self.commit, TASK_PATH, self.candidate.review_token, 'accepted', 'Offline synthetic operator review')

    def prepare(self, mode='success'):
        return editing.grant(self.queue, self.state, 'sample', 1, self.candidate.review_token,
                             task_class='source-edit-v1', authorize_checkpoint=True, mode=mode, timeout=2, deadline=4)

    def send(self, grant):
        return editing.dispatch(self.queue, self.state, grant['claim'], grant['plan_sha256'],
                                checkpoint_authorization=grant['plan_sha256'])

    def test_complete_flow_expected_commit_and_observatory(self):
        self.accept()
        g = self.prepare()
        with self.assertRaises(DriverError):
            editing.dispatch(self.queue, self.state, g['claim'], g['plan_sha256'], checkpoint_authorization='0'*64)
        outcome = self.send(g)
        self.assertEqual(outcome['state'], 'completed', outcome)
        w = Path(g['workspace'])
        self.assertEqual(workspace.git(w, 'rev-parse', 'HEAD^').decode().strip(), self.source)
        self.assertEqual(workspace.git(w, 'show', 'HEAD:src/sample.py'), b'def answer():\n    return 2\n')
        names = workspace.git(w, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().splitlines()
        self.assertEqual(names, ['src/sample.py', 'tests/portable/test_s3_sample.py'])
        self.assertTrue(all(step['exit_status'] == 0 for step in outcome['validation']))
        self.assertEqual(self.repo.head(), self.commit)
        run_root = self.state / g['claim']
        with AgentJournalFeed(run_root / 'spool') as feed:
            self.assertIn('local checkpoint completed', str(feed.publication.view()))
        before = (run_root / 'checkpoint-outcome.json').read_bytes()
        with self.assertRaises(DriverError): self.send(g)
        with self.assertRaises(DriverError): self.prepare()
        self.assertEqual(before, (run_root / 'checkpoint-outcome.json').read_bytes())
        plan, token = load_plan(run_root)
        with self.assertRaises(DriverError):
            workspace.checkpoint(run_root, plan['edit_workspace'], token, token, {'state':'completed'})

    def test_unaccepted_and_text_bridge_refuse(self):
        with self.assertRaises(DriverError): self.prepare()
        self.accept()
        with self.assertRaises(DriverError):
            text_grant(self.queue, self.state, 'sample', 1, self.candidate.review_token)
        with self.assertRaises(DriverError):
            editing.grant(self.queue, self.state, 'sample', 1, self.candidate.review_token,
                          task_class='text-analysis-v1', authorize_checkpoint=True)

    def test_dirty_workspace_and_stale_source(self):
        self.accept()
        g = self.prepare()
        (Path(g['workspace']) / 'src/sample.py').write_text('changed')
        with self.assertRaises(DriverError): self.send(g)
        self.assertFalse((self.state / g['claim'] / 'attempt.json').exists())
        # Git task movement independently invalidates the frozen source receipt.
        self.repo.commit()
        with self.assertRaises((DriverError, TaskError)): self.send(g)

    def test_failure_scenarios_retain_and_never_replay(self):
        self.accept()
        for scenario in ('s3-unauthorized', 's3-test-fail', 's3-audit-fail', 'web-tool', 'normal', 'driver-approval', 'lost-ack', 'eof', 'readonly-implicit'):
            with self.subTest(scenario=scenario):
                self.state = self.root / scenario
                g = self.prepare(scenario)
                result = self.send(g)
                self.assertEqual(result['state'], 'blocked', result)
                self.assertEqual(len(result['validation']), 3)
                self.assertTrue(Path(g['workspace']).is_dir())
                self.assertEqual(workspace.git(g['workspace'], 'rev-parse', 'HEAD').decode().strip(), self.source)
                with self.assertRaises(DriverError): self.send(g)
                if scenario == 'readonly-implicit':
                    worker = read_record(self.state / g['claim'] / 'outcome.json')
                    self.assertEqual([op['method'] for op in worker['operations']], ['thread/start'])
                    self.assertEqual(read_record(self.state / g['claim'] / 'evidence/peer.json')['turns'], [])
                if scenario == 's3-test-fail':
                    self.assertNotEqual(result['validation'][0]['exit_status'], 0)
                if scenario == 's3-audit-fail':
                    self.assertNotEqual(next(x for x in result['validation'] if x['step']=='publication-audit')['exit_status'], 0)

    def test_git_metadata_mutation_and_ignored_new_file(self):
        self.accept()
        g = self.prepare()
        w = Path(g['workspace'])
        (w / '.git/config').write_text('[core]\nrepositoryformatversion=0\n')
        with self.assertRaises(DriverError): self.send(g)

    def test_incomplete_checkpoint_and_interrupted_owner_are_fenced(self):
        self.accept()
        g = self.prepare()
        real_git = workspace.git
        def interrupted(w, *args, **kwargs):
            if args[0] == 'update-ref':
                raise KeyboardInterrupt()
            return real_git(w, *args, **kwargs)
        with patch.object(workspace, 'git', side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
            self.send(g)
        root = self.state / g['claim']
        self.assertTrue((root / 'checkpoint-object.json').exists())
        self.assertEqual(read_record(root / 'checkpoint-outcome.json')['state'], 'blocked')
        with self.assertRaises(DriverError): self.send(g)

    def test_interrupted_worker_has_durable_owner_outcome_and_no_checkpoint(self):
        from deskmate_formats.supervisor.protocol import AppServer
        self.accept()
        g = self.prepare()
        request = AppServer.request
        def interrupt(client, method, params, **kwargs):
            result = request(client, method, params, **kwargs)
            if method == 'turn/start':
                raise KeyboardInterrupt()
            return result
        with patch.object(AppServer, 'request', interrupt), self.assertRaises(KeyboardInterrupt):
            self.send(g)
        root = self.state / g['claim']
        self.assertEqual(read_record(root / 'outcome.json')['reason'], 'owner-interrupted')
        self.assertFalse((root / 'checkpoint-intent.json').exists())
        with self.assertRaises(DriverError): self.send(g)

    def test_live_profile_and_all_grants_using_only_synthetic_image(self):
        import subprocess
        import sys
        from deskmate_formats.supervisor import driver
        package = Path(driver.__file__).parent.parent
        for relative in driver.implementation_hashes():
            self.repo.stage("src/deskmate_formats/" + relative, (package / relative).read_bytes())
        self.repo.stage("src/deskmate_formats/supervisor/codex-0.166.0.json",
                        (package / "supervisor/codex-0.166.0.json").read_bytes())
        self.commit = self.repo.commit(self.candidate.manifest)
        with open_queue(self.queue) as queue:
            self.candidate = queue.discover(self.commit, TASK_PATH)
        self.accept()
        auth = self.root / "synthetic-auth.json"
        auth.write_bytes(b'{"OPENAI_API_KEY":"synthetic-not-a-key"}')
        popen = subprocess.Popen
        launches = []
        def image(argv, **kwargs):
            if argv[1:] == ["app-server", "--listen", "stdio://"]:
                launches.append(argv)
                return popen([sys.executable, "-I", "-m", "deskmate_formats.supervisor.synthetic_peer",
                              str(run_root / "evidence/peer.json"), "success", "--live-policy"], **kwargs)
            return popen(argv, **kwargs)
        with patch.object(driver, "verify_native", return_value=str(Path(sys.executable).resolve())), patch("subprocess.Popen", image):
            g = editing.grant(self.queue, self.state, "sample", 1, self.candidate.review_token,
                              task_class="source-edit-v1", authorize_checkpoint=True,
                              executable=sys.executable, profile="experimental-lab", auth_file=auth,
                              model="synthetic-selected-model", effort="low", windows_sandbox="unelevated",
                              # The synthetic peer answers in milliseconds of CPU, but this
                              # test asserts the grant matrix, not latency. A tight window
                              # turns a saturated host into a false "worker incomplete".
                              timeout=10, deadline=30)
            run_root = self.state / g['claim']
            token = g['plan_sha256']
            for dispatch, checkpoint, model, risk in [(None,token,token,token),(token,None,token,token),
                                                    (token,token,None,token),(token,token,token,None)]:
                with self.assertRaises(DriverError):
                    editing.dispatch(self.queue,self.state,g['claim'],dispatch,checkpoint_authorization=checkpoint,
                                     live=True,model_authorization=model,lab_risk_ack=risk)
            self.assertEqual(launches, [])
            result = editing.dispatch(self.queue,self.state,g['claim'],token,checkpoint_authorization=token,
                                      live=True,model_authorization=token,lab_risk_ack=token)
            self.assertEqual(result['state'], 'completed', result)
            self.assertEqual(len(launches),1)
            config = (run_root / 'codex-home/config.toml').read_text()
            self.assertIn('shell_tool = false',config)
            self.assertIn('sandbox_mode = "workspace-write"',config)

    def test_original_claim_attempt_marker_permanently_refuses_without_launch(self):
        # Reproduce the consumed identity only in this test's temporary synthetic queue.
        # Never read, edit or dispatch the real private claim.
        from deskmate_formats.supervisor import driver
        claim = '883aa0e5db4fbc586a788caff894273fae0deb24ce144163ed8de290bc8bade5'
        self.accept()
        with patch.object(editing, '_claim', return_value=claim):
            g = self.prepare()
        marker = self.state / claim / 'attempt.json'
        marker.write_text('{"plan_sha256":"a6efdbe7e569014cc2c486723eb9aadc7b239b31e017fc7925352a139c9f9fd6"}')
        before = marker.read_bytes()
        with patch.object(driver, 'AppServer', side_effect=AssertionError('no launch')), \
                self.assertRaisesRegex(DriverError, 'permanent attempt fence'):
            self.send(g)
        self.assertEqual(marker.read_bytes(), before)
        self.assertFalse((self.state / claim / 'checkpoint-intent.json').exists())

    def test_missing_backend_refused_before_reserving_workspace(self):
        import sys
        self.accept()
        with self.assertRaisesRegex(DriverError, "explicit Windows sandbox"):
            editing.grant(self.queue, self.state, "sample", 1, self.candidate.review_token,
                          task_class="source-edit-v1", authorize_checkpoint=True,
                          executable=sys.executable, profile="experimental-lab")
        self.assertFalse(self.state.exists())

    def test_manifest_scope_and_capability_rejections(self):
        value = self.candidate.manifest
        for update in ({'commands': ['anything']}, {'resources': ['source-read']},
                       {'development': value['development'] | {'modify':['.git/config']}},
                       {'development': value['development'] | {'test_profiles':['arbitrary-shell']}}):
            with self.subTest(update=update), self.assertRaises(TaskError):
                validate_manifest(json.dumps(value | update).encode())

    def test_packaged_audit_is_existing_project_audit(self):
        from deskmate_formats.supervisor import repository_audit
        self.assertEqual(Path(repository_audit.__file__).read_bytes(),
                         (Path(__file__).resolve().parents[2] / 'tools/audit_repository.py').read_bytes())


if __name__ == '__main__':
    unittest.main()
