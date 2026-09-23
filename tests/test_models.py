import copy
import json
import math
import os
import sqlite3
from datetime import timedelta
from pathlib import Path

from support import Case, NOW, evidence, plan, task, team
from donna_runtime import models
from donna_runtime.common import DonnaError, Conflict, instant, digest, atomic_write, stamp
from donna_runtime.config import Config, initialize
from donna_runtime.store import Store


class ValidationTests(Case):
    def test_unknown_plan_fields_rejected(self):
        p = plan(); p["execute_immediately"] = True
        with self.assertRaises(DonnaError): self.e.import_plan(p)
        self.assertEqual(self.db.all("project"), [])

    def test_duplicate_task_id(self):
        with self.assertRaises(DonnaError): self.e.import_plan(plan(tasks=[task(), task()]))

    def test_dependency_cycle(self):
        with self.assertRaises(DonnaError): self.e.import_plan(plan(tasks=[task("a", deps=["b"]), task("b", deps=["a"])]))

    def test_unknown_dependency(self):
        with self.assertRaises(DonnaError): self.e.import_plan(plan(tasks=[task(deps=["missing"])]))

    def test_path_traversal_id(self):
        p = plan(); p["project"]["id"] = "../escape"
        with self.assertRaises(DonnaError): self.e.import_plan(p)

    def test_nonfinite_estimate(self):
        for value in (float("nan"), float("inf"), -1, True):
            with self.subTest(value=value):
                p = plan(); p["tasks"][0]["human_hours"]["high"] = value
                with self.assertRaises(DonnaError): models.plan(p)

    def test_reversed_estimate(self):
        p = plan(); p["tasks"][0]["duration_days"] = {"low": 5, "high": 1}
        with self.assertRaises(DonnaError): models.plan(p)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(DonnaError): instant("2026-09-22T12:00:00")

    def test_external_deadline_requires_source(self):
        p = plan(); p["project"]["deadline"] = {"date": "2026-10-01"}
        with self.assertRaises(DonnaError): models.plan(p)

    def test_failing_acceptance_is_rejected(self):
        e = evidence(); e["checks"][0]["passed"] = False
        with self.assertRaises(DonnaError): models.evidence(e, [{"id": "usable", "description": "test"}])

    def test_evidence_must_cover_every_criterion(self):
        with self.assertRaises(DonnaError): models.evidence(evidence(), [{"id": "different", "description": "test"}])

    def test_human_receipt_required(self):
        with self.assertRaises(DonnaError): models.evidence(evidence(), [{"id": "usable", "description": "test"}], human=True)

    def test_state_dir_cannot_be_in_vault(self):
        self.raw_config["state_dir"] = str(self.vault / "state")
        self.config_path.write_text(json.dumps(self.raw_config))
        with self.assertRaises(DonnaError): Config.load(self.config_path)

    def test_unknown_config_key_is_not_ignored(self):
        self.raw_config["auto_accept_everything"] = True
        self.config_path.write_text(json.dumps(self.raw_config))
        with self.assertRaises(DonnaError): Config.load(self.config_path)

    def test_symlink_managed_path_rejected(self):
        link = self.home / "link"
        link.symlink_to(self.root)
        self.raw_config["state_dir"] = str(link / "escape")
        self.config_path.write_text(json.dumps(self.raw_config))
        with self.assertRaises(DonnaError): Config.load(self.config_path)

    def test_obsidian_settings_cannot_be_projection_root(self):
        self.raw_config["area"] = ".obsidian"
        self.config_path.write_text(json.dumps(self.raw_config))
        with self.assertRaises(DonnaError): Config.load(self.config_path)

    def test_config_init_is_dry_run_by_default(self):
        target = self.home / "new-config.json"
        result = initialize(target, profile="donna", profile_home=self.home, vault=self.vault,
                            area="Donna", board="donna", zone="America/Mexico_City", capacity=None)
        self.assertFalse(result["applied"])
        self.assertFalse(target.exists())
        self.assertEqual(list(self.vault.iterdir()), [])

    def test_atomic_write_compare_and_swap(self):
        path = self.root / "note"
        atomic_write(path, "original", create_only=True)
        with self.assertRaises(Conflict): atomic_write(path, "bad", expected=digest("different"))
        self.assertEqual(path.read_text(), "original")
        atomic_write(path, "updated", expected=digest("original"))
        self.assertEqual(path.read_text(), "updated")

    def test_atomic_create_never_overwrites(self):
        path = self.root / "note"; path.write_text("mine")
        with self.assertRaises(Conflict): atomic_write(path, "new", create_only=True)
        self.assertEqual(path.read_text(), "mine")

    def test_future_journal_schema_refused(self):
        path = self.home / "future"; path.mkdir()
        c = sqlite3.connect(path / "coordination.sqlite3"); c.execute("PRAGMA user_version=999"); c.close()
        with self.assertRaises(DonnaError): Store(path)

    def test_journal_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with self.db.transaction():
                self.db.put("gap", {"id": "rollback", "project_id": "none"})
                raise RuntimeError("fixture rollback")
        self.assertFalse(self.db.exists("gap", "rollback"))

    def test_journal_backup(self):
        self.e.import_plan(plan())
        dest = self.root / "backup" / "journal.sqlite3"
        self.db.backup(dest)
        c = sqlite3.connect(dest)
        self.assertEqual(c.execute("SELECT count(*) FROM objects WHERE kind='project'").fetchone()[0], 1)
        c.close()

    def test_verified_member_requires_all_readiness_checks(self):
        m = team()["members"][0]; del m["checks"]["handoff"]
        with self.assertRaises(DonnaError): models.member(m)
