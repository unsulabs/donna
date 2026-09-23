import json
from datetime import timedelta
from pathlib import Path

from support import Case, NOW, evidence, plan, task
from donna_runtime.common import Conflict, DonnaError, digest, stamp
from donna_runtime.projection import Projection, BEGIN, END, split_document
from donna_runtime.review import Review


class ProjectionTests(Case):
    def setUp(self):
        super().setUp()
        self.active()
        self.p = Projection(self.e)

    def test_existing_vault_preserved(self):
        sentinel = self.vault / "My existing note.md"; sentinel.write_text("Keep me")
        settings = self.vault / ".obsidian"; settings.mkdir()
        (settings / "app.json").write_text('{"old":true}')
        self.p.render()
        self.assertEqual(sentinel.read_text(), "Keep me")
        self.assertEqual((settings / "app.json").read_text(), '{"old":true}')

    def test_repeated_render_is_idempotent(self):
        self.p.render(); second = self.p.render()
        self.assertTrue(all(x["status"] == "unchanged" for x in second["files"]))

    def test_user_notes_outside_managed_block_survive(self):
        self.p.render()
        path = self.cfg.projection_root / "Tasks/build.md"
        path.write_text(path.read_text() + "\nMy important personal note\n")
        self.delivered(); self.p.render()
        self.assertIn("My important personal note", path.read_text())
        self.assertIn("awaiting_review", path.read_text())

    def test_existing_unmanaged_target_is_not_overwritten(self):
        path = self.cfg.projection_root / "Projects/life-project.md"
        path.parent.mkdir(parents=True); path.write_text("An incumbent note")
        result = self.p.render()
        self.assertGreater(result["conflicts"], 0)
        self.assertEqual(path.read_text(), "An incumbent note")

    def test_human_project_edit_is_proposed_then_imported(self):
        self.p.render()
        path = self.cfg.projection_root / "Projects/life-project.md"
        path.write_text(path.read_text().replace('"title": "A whole-life project"', '"title": "My corrected title"'))
        self.p.render(); conflict = self.p.conflicts()[0]
        self.assertEqual(self.db.get("project", "life-project")["title"], "A whole-life project")
        result = self.p.resolve(conflict["id"], expected_hash=conflict["actual_hash"], action="import-project", reason="User corrected title")
        self.assertTrue(Path(result["backup"]).exists())
        self.assertEqual(self.db.get("project", "life-project")["title"], "My corrected title")
        self.assertIn("My corrected title", path.read_text())

    def test_two_sided_edit_requires_explicit_reconciliation(self):
        self.p.render()
        path = self.cfg.projection_root / "Projects/life-project.md"
        path.write_text(path.read_text().replace('"title": "A whole-life project"', '"title": "User change"'))
        p = self.db.get("project", "life-project")
        self.e.amend_project("life-project", {"title": "Agent change"}, p["_revision"])
        self.p.render(); c = self.p.conflicts()[0]
        with self.assertRaises(Conflict): self.p.resolve(c["id"], expected_hash=c["actual_hash"], action="import-project", reason="Attempt")
        self.assertIn("User change", path.read_text())

    def test_moving_board_card_does_not_mark_task_verified(self):
        self.p.render(); path = self.cfg.projection_root / "Board.md"
        path.write_text(path.read_text().replace("- [ ]", "- [x]"))
        result = self.p.render()
        self.assertEqual(result["conflicts"], 1)
        self.assertEqual(self.db.get("task", "build")["state"], "planned")

    def test_keep_state_preserves_original_board_edit_in_backup(self):
        self.p.render(); path = self.cfg.projection_root / "Board.md"
        path.write_text(path.read_text().replace("- [ ]", "- [x]"))
        self.p.render(); c = self.p.conflicts()[0]
        result = self.p.resolve(c["id"], expected_hash=c["actual_hash"], action="keep-state", reason="Checkbox requested review, not completion")
        self.assertIn("- [x]", Path(result["backup"]).read_text())
        self.assertIn("- [ ]", path.read_text())

    def test_delete_of_managed_note_is_a_conflict(self):
        self.p.render(); path = self.cfg.projection_root / "Tasks/build.md"; path.unlink()
        result = self.p.render()
        self.assertGreater(result["conflicts"], 0)
        self.assertFalse(path.exists())

    def test_changed_again_conflict_cannot_be_resolved_from_stale_hash(self):
        self.p.render(); path = self.cfg.projection_root / "Board.md"
        path.write_text(path.read_text().replace("- [ ]", "- [x]")); self.p.render(); c = self.p.conflicts()[0]
        path.write_text(path.read_text() + "new annotation")
        with self.assertRaises(Conflict): self.p.resolve(c["id"], expected_hash=c["actual_hash"], action="keep-state", reason="stale")

    def test_invalid_markers_preserve_user_content(self):
        self.p.render(); path = self.cfg.projection_root / "Tasks/build.md"
        path.write_text(path.read_text().replace(END, "USER REPLACED MARKER"))
        self.p.render(); c = self.p.conflicts()[0]
        self.p.resolve(c["id"], expected_hash=c["actual_hash"], action="keep-state", reason="Restore markers and retain user text")
        self.assertIn("USER REPLACED MARKER", path.read_text())
        self.assertEqual(path.read_text().count(BEGIN), 1)

    def test_markup_inside_data_cannot_escape_generated_block(self):
        p = self.db.get("project", "life-project")
        self.e.amend_project("life-project", {"outcome": 'Hello ```\n' + END + '\n[[evil|link]]'}, p["_revision"])
        self.p.render(); path = self.cfg.projection_root / "Projects/life-project.md"
        self.assertEqual(path.read_text().count(END), 1)
        split_document(path.read_text())

    def test_symlink_projection_path_is_rejected(self):
        self.cfg.projection_root.parent.mkdir(parents=True)
        self.cfg.projection_root.symlink_to(self.root)
        with self.assertRaises(DonnaError): Projection(self.e)


class ReviewTests(Case):
    def setUp(self):
        super().setUp(); self.active(); self.r = Review(self.e)

    def report(self, pulse, current, when):
        lease = self.db.meta("review_lease")
        current_ids = {i["id"] for i in current["items"]}
        ids = set(lease["item_ids"]) | current_ids
        return {"summary": "Fixture review with explicit dispositions", "next_at": stamp(when),
                "items": [{"id": i, "disposition": "deferred" if i in current_ids else "resolved", "source": "fixture:review-action",
                           **({"next_at": stamp(when)} if i in current_ids else {})} for i in sorted(ids)]}

    def test_wake_is_not_acknowledgement(self):
        pulse = self.r.pulse(now=NOW, synchronize=False)
        self.assertTrue(pulse["wakeAgent"])
        self.assertIsNone(self.db.meta("review_ack"))

    def test_active_lease_prevents_parallel_review(self):
        self.r.pulse(now=NOW, synchronize=False)
        self.assertFalse(self.r.pulse(now=NOW + timedelta(seconds=1), synchronize=False)["wakeAgent"])

    def test_lost_wake_is_retried_after_expiry(self):
        first = self.r.pulse(now=NOW, synchronize=False)
        second = self.r.pulse(now=NOW + timedelta(seconds=31), synchronize=False)
        self.assertTrue(second["wakeAgent"])
        self.assertNotEqual(first["context"]["review_token"], second["context"]["review_token"])

    def test_repeated_unacknowledged_wakes_hit_budget(self):
        for sec in (0, 31, 62): self.r.pulse(now=NOW + timedelta(seconds=sec), synchronize=False)
        with self.assertRaises(DonnaError): self.r.pulse(now=NOW + timedelta(seconds=93), synchronize=False)
        self.r.reset("Operator repaired a fixture worker")
        self.assertTrue(self.r.pulse(now=NOW + timedelta(seconds=94), synchronize=False)["wakeAgent"])

    def test_successful_review_suppresses_same_queue_until_followup(self):
        pulse = self.r.pulse(now=NOW, synchronize=False)
        current = self.r.inspect(now=NOW)
        when = NOW + timedelta(hours=1)
        self.r.finish(pulse["context"]["review_token"], current["digest"], self.report(pulse, current, when), now=NOW + timedelta(seconds=1))
        self.assertFalse(self.r.pulse(now=NOW + timedelta(minutes=10), synchronize=False)["wakeAgent"])
        self.assertTrue(self.r.pulse(now=when, synchronize=False)["wakeAgent"])

    def test_cannot_acknowledge_unseen_queue(self):
        pulse = self.r.pulse(now=NOW, synchronize=False)
        before = self.r.inspect(now=NOW)
        report = self.report(pulse, before, NOW + timedelta(hours=1))
        self.e.capability_gap("life-project", "social", "New requirement")
        with self.assertRaises(Conflict): self.r.finish(pulse["context"]["review_token"], before["digest"], report, now=NOW + timedelta(seconds=1))

    def test_cannot_claim_unresolved_items_resolved(self):
        pulse = self.r.pulse(now=NOW, synchronize=False); current = self.r.inspect(now=NOW)
        report = self.report(pulse, current, NOW + timedelta(hours=1))
        report["items"][0]["disposition"] = "resolved"
        with self.assertRaises(DonnaError): self.r.finish(pulse["context"]["review_token"], current["digest"], report, now=NOW + timedelta(seconds=1))

    def test_all_original_and_current_items_need_dispositions(self):
        pulse = self.r.pulse(now=NOW, synchronize=False); current = self.r.inspect(now=NOW)
        report = self.report(pulse, current, NOW + timedelta(hours=1)); report["items"] = []
        with self.assertRaises(DonnaError): self.r.finish(pulse["context"]["review_token"], current["digest"], report, now=NOW + timedelta(seconds=1))

    def test_expired_lease_cannot_acknowledge(self):
        pulse = self.r.pulse(now=NOW, synchronize=False); current = self.r.inspect(now=NOW)
        report = self.report(pulse, current, NOW + timedelta(hours=1))
        with self.assertRaises(Conflict): self.r.finish(pulse["context"]["review_token"], current["digest"], report, now=NOW + timedelta(seconds=40))

    def test_native_reconciliation_failure_is_not_silent(self):
        self.delivered(); self.native.fail_show = True
        with self.assertRaises(DonnaError): self.r.pulse(now=NOW)
        self.assertIsNone(self.db.meta("review_ack"))

    def test_deadline_uses_user_timezone(self):
        p = plan("dated", tasks=[task("dated-task")]); p["project"]["deadline"] = {"date": "2026-09-22", "source": "fixture:confirmed"}
        self.e.import_plan(p); self.e.activate("dated", "fixture:mandate")
        result = self.r.inspect(now=NOW)
        self.assertTrue(any(i["kind"] == "deadline" and i.get("date") == "2026-09-22" for i in result["items"]))

    def test_changed_result_wakes_even_after_previous_ack(self):
        pulse = self.r.pulse(now=NOW, synchronize=False); current = self.r.inspect(now=NOW)
        self.r.finish(pulse["context"]["review_token"], current["digest"], self.report(pulse, current, NOW + timedelta(hours=1)), now=NOW + timedelta(seconds=1))
        self.delivered()
        self.assertTrue(self.r.pulse(now=NOW + timedelta(minutes=2), synchronize=False)["wakeAgent"])
