"""CLI command integration in-process with a test-only native adapter."""
import contextlib
import io
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from support import Case, plan, task, team, evidence, NOW
from donna_runtime.cli import main
from donna_runtime.common import pretty, stamp, utcnow

class CommandIntegration(Case):
    def setUp(self):
        super().setUp()
        self.counter=0
        patcher=patch('donna_runtime.engine.Hermes',return_value=self.native)
        patcher.start();self.addCleanup(patcher.stop)
    def file(self,value):
        self.counter+=1;p=self.root/f'data{self.counter}.json';p.write_text(pretty(value));return str(p)
    def call(self,*args,code=0):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            status=main(['--config',str(self.config_path),*map(str,args)])
        self.assertEqual(status,code,err.getvalue()+out.getvalue())
        return json.loads(out.getvalue() or err.getvalue())
    def seed(self,p=None):
        self.call('plan-import',self.file(p or plan()))
        self.call('team-import',self.file(team()))
        self.call('activate','life-project','--authorization','fixture:mandate')
    def test_read_commands_and_backup(self):
        self.seed()
        for cmd in ('status','review','doctor','team-list','render'):
            self.assertIsInstance(self.call(cmd),dict)
        self.assertEqual(self.call('show','task','build')['id'],'build')
        self.assertIn('critical_path_days',self.call('forecast','life-project'))
        self.assertTrue(self.call('events')['events'])
        self.call('events','--limit',0,code=2)
        self.call('backup',self.root/'copy.sqlite')
        self.assertTrue((self.root/'copy.sqlite').is_file())
    def test_full_lifecycle_commands(self):
        self.seed()
        self.call('prepare','build');card=self.call('dispatch','build')['card_id']
        self.native.finish(card);self.call('sync')
        self.call('rework','build','--reason','fixture:criterion repair')
        card=self.call('dispatch-ready')['results'][0]['card_id']
        self.native.finish(card);self.call('sync')
        self.call('accept-task','build','--evidence',self.file(evidence()))
        self.call('close-project','life-project','--evidence',self.file(evidence('outcome',human=True)))
        self.call('reopen','life-project','--reason','fixture:new authorized work')
        self.call('activate','life-project','--authorization','fixture:resume')
        self.call('pause','life-project','--reason','fixture:pause')
    def test_edit_commands(self):
        self.seed()
        p=self.call('show','project','life-project')
        self.call('project-amend','life-project',self.file({'title':'Reviewed title'}),'--revision',p['_revision'])
        self.call('allocate','life-project','--hours',4,'--authorization','fixture:allocation')
        t=self.call('show','task','build');new=task();new['brief']='Correct clarified brief'
        self.call('task-revise','build',self.file(new),'--revision',t['_revision'],'--authorization','fixture:clarification')
        self.call('task-add','life-project',self.file([task('second',deps=['build'])]),'--authorization','fixture:scope')
        self.assertEqual(len(self.call('status')['tasks']),2)
    def test_gap_and_authorization(self):
        p=plan();p['tasks'][0]['action_class']='publish';self.seed(p)
        gap=self.call('gap','life-project','build','--reason','fixture:check capability')
        self.call('gap-resolve',gap['id'],'builder')
        self.call('dispatch','build',code=2)
        self.call('authorize-task','build','--reference','fixture:specific-publication')
        self.call('dispatch','build')
    def test_transport_command_recovery(self):
        self.seed();self.native.fail_after_once=True
        self.call('dispatch','build',code=2)
        self.call('transport-reset','build','--reason','fixture:native key verified')
        self.assertEqual(self.call('dispatch','build')['card_id'],'t_1')
    def test_pulse_and_finish_commands(self):
        self.seed()
        pulse=self.call('pulse');self.assertTrue(pulse['wakeAgent'])
        current=self.call('review');at=stamp(utcnow()+timedelta(hours=1))
        report={'summary':'fixture:all pending consciously deferred','next_at':at,
                'items':[{'id':item['id'],'disposition':'deferred','source':'fixture:pending','next_at':at} for item in current['items']]}
        self.call('review-finish','--token',pulse['context']['review_token'],'--digest',current['digest'],'--report',self.file(report))
        self.assertFalse(self.call('pulse')['wakeAgent'])
        self.call('review-reset','--reason','fixture:operator recovery')
    def test_init_apply_is_explicit(self):
        out=io.StringIO()
        args=['--config',str(self.home/'new.json'),'init','--profile','donna','--profile-home',str(self.home),
              '--vault',str(self.vault),'--area','Another','--board','donna-ops','--timezone','America/Mexico_City']
        with contextlib.redirect_stdout(out):self.assertEqual(main(args),0)
        self.assertFalse((self.home/'new.json').exists())
        with contextlib.redirect_stdout(out):self.assertEqual(main(args+['--apply']),0)
        self.assertTrue((self.home/'new.json').is_file())
    def test_roster_edit_blocks_cli(self):
        self.call('plan-import',self.file(plan()));source=Path(self.file(team()))
        self.call('team-import',source);self.call('activate','life-project','--authorization','fixture')
        source.write_text('{"schema_version":2,"members":[]}')
        self.call('dispatch','build',code=2)
        self.assertFalse(self.native.calls)
    def test_projection_resolve_command(self):
        self.seed();self.call('render')
        path=self.vault/'Operations/Donna/Projects/life-project.md'
        path.write_text(path.read_text().replace('A whole-life project','Title edited in Obsidian'))
        self.call('render',code=3)
        rows=self.call('conflicts')
        item=rows[0]
        self.call('resolve',item['id'],'--hash',item['actual_hash'],'--action','import-project','--reason','fixture:intent reviewed')
        self.assertEqual(self.call('show','project','life-project')['title'],'Title edited in Obsidian')
    def test_missing_config_is_structured_error(self):
        self.config_path.unlink()
        error=self.call('status',code=2)
        self.assertFalse(error['ok'])
