"""Process-level contract tests against an EXPLICIT TEST DOUBLE, never live Hermes."""
import json
from contextlib import closing
import os
import sqlite3
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from support import Case, ROOT, NOW, evidence, plan, team
from donna_runtime.common import NativeError, pretty
from donna_runtime.config import Config
from donna_runtime.engine import Engine
from donna_runtime.hermes import Hermes

class NativeCLI(Case):
    def setUp(self):
        super().setUp()
        self.raw_config['hermes_command'] = [sys.executable, str(ROOT / 'tests/fake_hermes.py')]
        self.raw_config['limits']['native_timeout'] = 1
        self.config_path.write_text(pretty(self.raw_config))
        self.cfg = Config.load(self.config_path)
        self.env = {'FAKE_HERMES_DB': str(self.root / 'native.sqlite'), 'FAKE_EXPECT_HOME': str(self.home)}
        p = patch.dict(os.environ, self.env)
        p.start(); self.addCleanup(p.stop)
        self.h = Hermes(self.cfg)
        self.e = Engine(self.cfg, self.db, self.h)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/donna_ops.py'), '--config', str(self.config_path), *args],
                              capture_output=True, text=True, timeout=15)

    def test_profile_resolution(self):
        self.assertEqual(self.h.profiles(), {'donna', 'builder'})

    def test_doctor_does_not_claim_live_fixture_dispatcher(self):
        report = self.h.doctor()
        self.assertTrue(report['ok'])
        self.assertTrue(report['diagnostics']['fixture_only'])
        self.assertFalse(report['diagnostics']['dispatcher_running'])

    def test_native_create_show(self):
        self.active()
        card = self.e.dispatch_one('build', now=NOW)['card_id']
        self.assertEqual(card, 't_1')
        self.assertEqual(self.h.show(card)['status'], 'ready')

    def test_idempotency_survives_lost_response(self):
        self.active()
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'lost-response'}):
            with self.assertRaises(NativeError):
                self.e.dispatch_one('build', now=NOW)
            self.assertEqual(self.e.dispatch_one('build', now=NOW + timedelta(minutes=2))['card_id'], 't_1')
        with closing(sqlite3.connect(self.env['FAKE_HERMES_DB'])) as db:
            self.assertEqual(db.execute('select count(*) from cards').fetchone()[0], 1)

    def test_no_shell_interpretation(self):
        p = plan(); p['tasks'][0]['title'] = '$(touch ' + str(self.root/'injected') + ')'
        self.active(p)
        self.e.dispatch_one('build', now=NOW)
        self.assertFalse((self.root/'injected').exists())

    def test_invalid_json_fails_closed(self):
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'malformed'}), self.assertRaises(NativeError):
            self.h.profiles()

    def test_bounded_output(self):
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'oversized'}), self.assertRaises(NativeError):
            self.h.profiles()

    def test_timeout(self):
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'sleep'}), self.assertRaises(NativeError):
            self.h.profiles()

    def test_raw_error_secrets_not_exposed(self):
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'secret-error'}):
            with self.assertRaises(NativeError) as err:
                self.h.profiles()
            self.assertNotIn('TEST_SECRET', str(err.exception))

    def test_unknown_native_status(self):
        self.active(); card = self.e.dispatch_one('build', now=NOW)['card_id']
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'unknown-status'}), self.assertRaises(NativeError):
            self.h.show(card)

    def test_wrong_native_id(self):
        self.active(); card = self.e.dispatch_one('build', now=NOW)['card_id']
        with patch.dict(os.environ, {'FAKE_HERMES_MODE': 'wrong-id'}), self.assertRaises(NativeError):
            self.h.show(card)

    def test_worker_cannot_masquerade_as_coordinator(self):
        self.active()
        payload = self.e.prepare('build', now=NOW)['payload']
        with patch.dict(os.environ, {'HERMES_KANBAN_TASK': 't_worker'}), self.assertRaises(NativeError):
            self.h.create(payload)

    def test_identifier_conflicts(self):
        with self.assertRaises(NativeError):
            self.h.identifier({'id':'t_1', 'task_id':'t_2'})

    def test_separate_process_roundtrip_and_restart(self):
        pfile = self.root/'plan.json'; pfile.write_text(pretty(plan()))
        tfile = self.root/'team.json'; tfile.write_text(pretty(team()))
        for args in [('plan-import', str(pfile)), ('team-import', str(tfile)),
                     ('activate','life-project','--authorization','fixture:mandate'), ('dispatch','build')]:
            result = self.cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
        # Simulate specialist completion in TEST DOUBLE only.
        with closing(sqlite3.connect(self.env['FAKE_HERMES_DB'])) as db:
            raw = json.loads(db.execute('SELECT data FROM cards WHERE id=?', ('t_1',)).fetchone()[0])
            raw.update(status='done', updated_at='fixture-final', result='fixture artifact')
            db.execute('UPDATE cards SET data=? WHERE id=?', (json.dumps(raw), 't_1'))
            db.commit()
        self.assertEqual(self.cli('sync').returncode, 0)
        state = json.loads(self.cli('show','task','build').stdout)
        self.assertEqual(state['state'], 'awaiting_review')
        ev = self.root/'evidence.json'; ev.write_text(pretty(evidence()))
        self.assertEqual(self.cli('accept-task','build','--evidence',str(ev)).returncode, 0)
        self.assertEqual(self.cli('render').returncode, 0)
        self.assertTrue((self.vault/'Operations/Donna/Board.md').is_file())
        final = self.cli('dispatch', 'build')
        self.assertEqual(final.returncode, 0, final.stderr)
        self.assertFalse(json.loads(final.stdout)['created'])

    def test_cli_invalid_evidence_returns_error(self):
        self.active(); f=self.root/'bad.json'; f.write_text('{}')
        result=self.cli('accept-task','build','--evidence',str(f))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)

    def test_cli_help_without_configuration(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/donna_ops.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('transport-reset', result.stdout)
