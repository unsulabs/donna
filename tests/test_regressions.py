import hashlib
from datetime import timedelta
from support import Case, NOW, plan, task, team, evidence
from donna_runtime.common import DonnaError, Conflict, pretty
from donna_runtime.config import Config
from donna_runtime.engine import Engine

class RegressionTests(Case):
    def test_transitive_acceptance_invalidated_on_rework(self):
        self.active(plan(tasks=[task('a'),task('b',deps=['a']),task('c',deps=['b'])]))
        for ident in ('a','b','c'):
            self.delivered(ident); self.e.accept_task(ident,evidence(),now=NOW)
        self.e.request_rework('a','The input artifact was incomplete')
        for ident in ('b','c'):
            self.assertEqual(self.db.get('task',ident)['state'],'awaiting_review')
            self.assertIsNone(self.db.get('task',ident)['accepted'])
        with self.assertRaises(DonnaError):
            self.e.accept_task('b',evidence(),now=NOW)

    def test_artifact_hash_checked(self):
        self.active(plan(tasks=[task(kind='donna',owner='donna')]))
        path=self.vault/'result.md'; path.write_text('correct')
        ev=evidence(); ev['checks'][0]['artifact']={'path':str(path),'sha256':hashlib.sha256(b'correct').hexdigest()}
        self.e.accept_task('build',ev,now=NOW)
        path.write_text('tampered')
        with self.assertRaises(DonnaError): self.e.accept_task('build',ev,now=NOW)

    def test_artifact_outside_authorized_roots(self):
        self.active(plan(tasks=[task(kind='donna',owner='donna')]))
        path=self.root/'other.md'; path.write_text('x')
        ev=evidence(); ev['checks'][0]['artifact']={'path':str(path),'sha256':hashlib.sha256(b'x').hexdigest()}
        with self.assertRaises(DonnaError): self.e.accept_task('build',ev,now=NOW)

    def test_missing_estimate_not_zero_promise(self):
        p=plan(); del p['tasks'][0]['duration_days']; self.e.import_plan(p)
        forecast=self.e.forecast('life-project')
        self.assertTrue(forecast['unknown_estimates'])

    def test_removed_roster_member_disabled(self):
        self.active(); self.e.import_team({'schema_version':2,'members':[]})
        self.assertEqual(self.db.get('member','builder')['status'],'disabled')
        with self.assertRaises(DonnaError): self.e.dispatch_one('build',now=NOW)

    def test_task_contract_revision_before_dispatch(self):
        self.active(); t=task(); t['brief']='Clarified correct requirements'
        old=self.db.get('task','build')
        self.e.revise_task('build',t,old['_revision'],'fixture:scope')
        self.assertEqual(self.db.get('task','build')['brief'],t['brief'])
        with self.assertRaises(Conflict): self.e.revise_task('build',t,old['_revision'],'fixture:scope')

    def test_prepared_contract_cannot_mutate(self):
        self.active(); self.e.prepare('build',now=NOW)
        with self.assertRaises(DonnaError): self.e.revise_task('build',task(),self.db.get('task','build')['_revision'],'fixture:scope')

    def test_custom_workspace_rejected_by_default(self):
        p=plan(); p['tasks'][0]['workspace']=str(self.root)
        self.active(p)
        with self.assertRaises(DonnaError): self.e.prepare('build',now=NOW)

    def test_custom_workspace_explicitly_allowed(self):
        self.raw_config['workspace_roots']=[str(self.root)]
        self.config_path.write_text(pretty(self.raw_config))
        self.cfg=Config.load(self.config_path); self.e=Engine(self.cfg,self.db,self.native)
        p=plan(); p['tasks'][0]['workspace']=str(self.vault)
        self.active(p)
        self.assertEqual(self.e.prepare('build',now=NOW)['payload']['workspace'],'dir:'+str(self.vault))

    def test_transport_reset_preserves_idempotency(self):
        self.active(); self.native.fail_before=True
        with self.assertRaises(DonnaError): self.e.dispatch_one('build',now=NOW)
        old=self.db.dispatch('build',1)['request_key']
        self.e.reset_transport('build','fixture:operator inspected native state')
        self.assertEqual(self.db.dispatch('build',1)['request_key'],old)
        self.assertEqual(self.db.dispatch('build',1)['attempts'],0)

    def test_allocate_enforces_capacity(self):
        self.active()
        with self.assertRaises(DonnaError): self.e.allocate('life-project',11,'fixture:request')
        self.e.allocate('life-project',4,'fixture:request')
        self.assertEqual(self.db.get('project','life-project')['allocation_hours_week'],4)

    def test_live_rework_checks_not_stale_snapshot(self):
        self.active(); card=self.delivered()
        self.native.cards[card]['status']='running'
        with self.assertRaises(DonnaError): self.e.request_rework('build','fix')

    def test_close_checks_fresh_native_state(self):
        self.active(); card=self.delivered()
        self.e.accept_task('build',evidence(),now=NOW)
        self.native.cards[card]['status']='running'
        with self.assertRaises(DonnaError): self.e.close_project('life-project',evidence('outcome',human=True))

    def test_failed_dispatches_do_not_starve_other_tasks(self):
        self.raw_config['limits']['max_dispatch_per_run']=1
        self.config_path.write_text(pretty(self.raw_config))
        self.cfg=Config.load(self.config_path);self.e=Engine(self.cfg,self.db,self.native)
        self.active(plan(tasks=[task('a'),task('b')]))
        self.native.fail_before=True
        self.assertEqual(self.e.dispatch_ready(now=NOW)['results'][0]['task'],'a')
        self.native.fail_before=False
        self.assertEqual(self.e.dispatch_ready(now=NOW)['results'][0]['task'],'b')

    def test_donna_research_never_dispatched_to_self(self):
        self.active(plan(tasks=[task(kind='donna',owner='builder')]))
        with self.assertRaises(DonnaError):self.e.dispatch_one('build',now=NOW)
        self.assertFalse(self.native.calls)
        self.e.accept_task('build',evidence(),now=NOW)

    def test_missing_native_tenant_not_accepted(self):
        self.active();card=self.delivered();self.native.cards[card]['tenant']=None
        with self.assertRaises(DonnaError):self.e.accept_task('build',evidence(),now=NOW)

    def test_edited_project_blocks_new_dispatch(self):
        from donna_runtime.projection import Projection
        self.active();v=Projection(self.e);v.render()
        p=self.vault/'Operations/Donna/Projects/life-project.md'
        p.write_text(p.read_text().replace('A whole-life project','My important edit'))
        v.render()
        with self.assertRaises(DonnaError):self.e.dispatch_one('build',now=NOW)
