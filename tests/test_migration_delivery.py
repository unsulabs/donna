import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest import mock
from support import ROOT, Case
from donna_runtime.common import DonnaError
from donna_migrate_team import convert
from scaffold_vault import scaffold
import config_guard
import apply_source_overlay as delivery

class MigrationTests(Case):
    def test_legacy_readiness_not_inherited(self):
        result,warnings=convert({'members':[{'id':'builder','profile':'builder','role':'Builder','status':'active','doctrine_paths':['local:SOUL']}]})
        self.assertEqual(result['members'][0]['status'],'configured')
        self.assertEqual(result['members'][0]['checks'],{})
        self.assertTrue(warnings)

    def test_legacy_duplicate_rejected(self):
        item={'id':'b','profile':'b','role':'Builder'}
        with self.assertRaises(DonnaError):convert({'members':[item,item]})

    def test_coordinator_not_specialist(self):
        result,_=convert({'orchestrator':'donna','members':[{'id':'donna','role':'Coordinator'}]})
        self.assertEqual(result['members'],[])

    def test_scaffold_rejects_existing_vault(self):
        with self.assertRaises(DonnaError):scaffold(self.vault,self.vault,apply=True)

    def test_new_scaffold_dryrun_then_apply(self):
        starter=self.root/'starter';starter.mkdir();(starter/'Home.md').write_text('hello')
        out=self.root/'new-vault'
        self.assertFalse(scaffold(out,starter)['applied']);self.assertFalse(out.exists())
        self.assertTrue(scaffold(out,starter,apply=True)['applied'])
        self.assertEqual((out/'Home.md').read_text(),'hello')

    def test_scaffold_rejects_symlink_source(self):
        starter=self.root/'starter';starter.mkdir();(starter/'evil').symlink_to(self.config_path)
        with self.assertRaises(DonnaError):scaffold(self.root/'new-vault',starter,apply=True)

    def test_model_guard_cannot_rewrite(self):
        fake=mock.Mock(returncode=0,stdout='different')
        with mock.patch('config_guard.subprocess.run',return_value=fake) as runner:
            self.assertEqual(config_guard.main(['--profile','donna','--expect','model.default=expected']),3)
            self.assertIn('get',runner.call_args[0][0])
            self.assertNotIn('set',runner.call_args[0][0])

class DeliveryTests(Case):
    def setUp(self):
        super().setUp()
        self.repo=self.root/'git';self.repo.mkdir()
        self.bundle=self.root/'bundle';(self.bundle/'overlay').mkdir(parents=True)
        self.run_git('init','-b','feature/test')
        self.run_git('config','user.email','test@example.invalid');self.run_git('config','user.name','Fixture')
        (self.repo/'old.txt').write_text('old\n');self.run_git('add','.');self.run_git('commit','-m','fixture')
        base=self.run_git('rev-parse','HEAD').strip()
        (self.bundle/'overlay/old.txt').write_text('new\n');(self.bundle/'overlay/new.txt').write_text('added\n')
        self.manifest={'schema_version':1,'base_commit':base,'files':[
            {'path':'old.txt','base_blob':delivery.blob_hash(b'old\n'),'sha256':delivery.sha256(b'new\n')},
            {'path':'new.txt','base_blob':None,'sha256':delivery.sha256(b'added\n')}]}
        self.write_manifest()
    def run_git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],capture_output=True,text=True,check=True).stdout
    def write_manifest(self):
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
    def test_dry_run_preserves_repo(self):
        self.assertFalse(delivery.apply_bundle(self.bundle,self.repo)['applied'])
        self.assertEqual((self.repo/'old.txt').read_text(),'old\n')
    def test_clean_feature_apply(self):
        self.assertTrue(delivery.apply_bundle(self.bundle,self.repo,apply=True)['applied'])
        self.assertEqual((self.repo/'new.txt').read_text(),'added\n')
    def test_dirty_repo_refused(self):
        (self.repo/'old.txt').write_text('my edits')
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo,apply=True)
        self.assertEqual((self.repo/'old.txt').read_text(),'my edits')
    def test_wrong_head_refused(self):
        self.manifest['base_commit']='0'*40;self.write_manifest()
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo)
    def test_corrupt_payload_refused(self):
        (self.bundle/'overlay/new.txt').write_text('corrupt')
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo,apply=True)
    def test_main_branch_refused(self):
        self.run_git('branch','-m','main')
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo,apply=True)
    def test_unmanifested_payload_refused(self):
        (self.bundle/'overlay/unexpected.txt').write_text('x')
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo)
    def test_path_escape_refused(self):
        self.manifest['files'][0]['path']='../outside';self.write_manifest()
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo)
    def test_blob_preimage_required(self):
        self.manifest['files'][0]['base_blob']='0'*40;self.write_manifest()
        with self.assertRaises(delivery.ApplyError):delivery.apply_bundle(self.bundle,self.repo)
    def test_rollback_on_write_failure(self):
        real=delivery.replace;calls=[]
        def fail_once(path,data,mode):
            calls.append(path.name)
            if len(calls)==2:raise OSError('fixture disk failure')
            return real(path,data,mode)
        with mock.patch.object(delivery,'replace',side_effect=fail_once), self.assertRaises(delivery.ApplyError):
            delivery.apply_bundle(self.bundle,self.repo,apply=True)
        self.assertEqual((self.repo/'old.txt').read_text(),'old\n')
        self.assertFalse((self.repo/'new.txt').exists())
