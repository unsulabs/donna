import copy
from datetime import timedelta
from support import Case, NOW, evidence, plan, task, team
from donna_runtime.common import Conflict, DonnaError, NativeError, stamp


class PlanningTests(Case):
    def test_repeated_import_is_idempotent(self):
        self.e.import_plan(plan()); result = self.e.import_plan(plan())
        self.assertFalse(result["created"])
        self.assertEqual(len(self.db.all("task")), 1)

    def test_same_id_different_plan_conflicts(self):
        self.e.import_plan(plan()); other = plan(); other["project"]["outcome"] = "Different"
        with self.assertRaises(Conflict): self.e.import_plan(other)

    def test_aspiration_is_not_automatically_active(self):
        p = plan(kind="aspiration", tasks=[]); self.e.import_plan(p)
        self.assertEqual(self.db.get("project", "life-project")["state"], "incubating")
        self.assertFalse(self.e.dispatch_ready(now=NOW)["results"])

    def test_activation_requires_a_complete_contract(self):
        p = plan(); p["project"]["assumptions"] = []; self.e.import_plan(p)
        with self.assertRaises(DonnaError): self.e.activate("life-project", "fixture:mandate")

    def test_human_capacity_conflict_blocks_activation(self):
        self.active()
        p = plan("another", tasks=[task("other")]); p["project"]["allocation_hours_week"] = 9
        self.e.import_plan(p)
        with self.assertRaises(DonnaError): self.e.activate("another", "fixture:mandate")

    def test_pause_prevents_new_dispatch(self):
        self.active(); self.e.pause("life-project", "User changed priorities")
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)
        self.assertEqual(self.native.cards, {})

    def test_rejected_framing_does_not_remove_inventory(self):
        self.active(); p = self.db.get("project", "life-project")
        self.e.amend_project("life-project", {"title": "A better framing"}, p["_revision"])
        self.assertTrue(self.db.exists("task", "build"))

    def test_optimistic_revision_protects_amendment(self):
        self.active(); p = self.db.get("project", "life-project")
        self.e.amend_project("life-project", {"title": "First"}, p["_revision"])
        with self.assertRaises(Conflict): self.e.amend_project("life-project", {"title": "Second"}, p["_revision"])

    def test_add_task_requires_existing_dependencies(self):
        self.active()
        with self.assertRaises(DonnaError): self.e.add_tasks("life-project", [task("extra", deps=["not-here"])], "fixture:scope")

    def test_add_task_preserves_existing_inventory(self):
        self.active(); self.e.add_tasks("life-project", [task("extra", deps=["build"])], "fixture:scope")
        self.assertEqual(len(self.db.all("task")), 2)

    def test_forecast_separates_estimate_from_deadline(self):
        self.active(); result = self.e.forecast("life-project")
        self.assertEqual(result["critical_path_days"], {"low": 1.0, "high": 2.0})
        self.assertIsNone(result["deadline"])
        self.assertAlmostEqual(result["elapsed_days_lower_bound"]["high"], 14 / 3)

    def test_human_task_never_becomes_native_profile(self):
        self.active(plan(tasks=[task("decide", kind="user", owner="user")]))
        with self.assertRaises(DonnaError): self.e.dispatch_one("decide", now=NOW)
        self.assertEqual(self.native.cards, {})

    def test_human_dependency_blocks_only_its_branch(self):
        self.active(plan(tasks=[task("decide", kind="user", owner="user"), task("dependent", deps=["decide"]), task("independent")]))
        result = self.e.dispatch_ready(now=NOW)
        self.assertEqual([x["task"] for x in result["results"]], ["independent"])
        self.e.accept_task("decide", evidence(human=True), now=NOW)
        self.assertIsNone(self.e.blocker(self.db.get("task", "dependent"), NOW))

    def test_no_specialist_invention(self):
        self.active(); self.native.available = set()
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)
        self.assertFalse(self.native.cards)

    def test_capability_gap_is_idempotent(self):
        self.active()
        a = self.e.capability_gap("life-project", "social", "Missing social access")
        b = self.e.capability_gap("life-project", "social", "Missing social access")
        self.assertEqual(a["id"], b["id"])
        with self.assertRaises(DonnaError): self.e.resolve_gap(a["id"], "builder", now=NOW)

    def test_stale_readiness_blocks_dispatch(self):
        self.active(); self.e.import_team(team(NOW - timedelta(days=100)))
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)

    def test_future_readiness_is_not_trusted(self):
        self.active(); self.e.import_team(team(NOW + timedelta(days=4)))
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)

    def test_sensitive_action_requires_per_attempt_approval(self):
        p = plan(); p["tasks"][0]["action_class"] = "publish"; self.active(p)
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)
        self.e.authorize_task("build", "fixture:user-approved-this-exact-publication")
        self.assertIn("card_id", self.e.dispatch_one("build", now=NOW))

    def test_not_before_is_respected(self):
        p = plan(); p["tasks"][0]["not_before"] = stamp(NOW + timedelta(days=1)); self.active(p)
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)


class ExecutionTests(Case):
    def test_create_is_idempotent(self):
        self.active(); a = self.e.dispatch_one("build", now=NOW); b = self.e.dispatch_one("build", now=NOW)
        self.assertEqual(a["card_id"], b["card_id"])
        self.assertEqual(len(self.native.cards), 1)

    def test_response_lost_after_commit_recovers_same_card(self):
        self.active(); self.native.fail_after_once = True
        with self.assertRaises(NativeError): self.e.dispatch_one("build", now=NOW)
        self.assertEqual(len(self.native.cards), 1)
        recovered = self.e.dispatch_one("build", now=NOW + timedelta(minutes=2))
        self.assertEqual(recovered["card_id"], "t_1")
        self.assertEqual(len(self.native.cards), 1)

    def test_backoff_prevents_immediate_retry(self):
        self.active(); self.native.fail_before = True
        with self.assertRaises(NativeError): self.e.dispatch_one("build", now=NOW)
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW)
        self.assertEqual(len(self.native.calls), 1)

    def test_transport_retry_budget_is_bounded(self):
        self.active(); self.native.fail_before = True
        for minute in (0, 10, 20):
            with self.assertRaises(NativeError): self.e.dispatch_one("build", now=NOW + timedelta(minutes=minute))
        with self.assertRaises(DonnaError): self.e.dispatch_one("build", now=NOW + timedelta(hours=1))
        self.assertEqual(len(self.native.calls), 3)

    def test_native_done_is_not_verified(self):
        self.active(); self.delivered()
        self.assertEqual(self.db.get("task", "build")["state"], "awaiting_review")
        with self.assertRaises(DonnaError): self.e.close_project("life-project", evidence("outcome", human=True))

    def test_blocked_native_card_is_not_accepted(self):
        self.active(); result = self.e.dispatch_one("build", now=NOW)
        self.native.cards[result["card_id"]]["status"] = "blocked"
        self.e.sync(now=NOW)
        with self.assertRaises(DonnaError): self.e.accept_task("build", evidence(), now=NOW)

    def test_repeated_observation_does_not_duplicate_event(self):
        self.active(); self.delivered()
        before = self.db.conn.execute("SELECT count(*) FROM events WHERE kind='native_observed'").fetchone()[0]
        self.e.sync(now=NOW)
        after = self.db.conn.execute("SELECT count(*) FROM events WHERE kind='native_observed'").fetchone()[0]
        self.assertEqual(before, after)

    def test_delivery_defect_rework_and_acceptance(self):
        self.active(); first = self.delivered()
        self.e.request_rework("build", "Required field missing")
        second = self.e.dispatch_one("build", now=NOW)
        self.assertNotEqual(first, second["card_id"])
        self.assertIn(first, self.native.calls[-1]["parents"])
        self.native.finish(second["card_id"]); self.e.sync(now=NOW)
        self.e.accept_task("build", evidence(), now=NOW)
        self.assertEqual(self.db.get("task", "build")["state"], "verified")
        self.e.close_project("life-project", evidence("outcome", human=True))
        self.assertEqual(self.db.get("project", "life-project")["state"], "closed")

    def test_repeated_rework_request_does_not_double_generation(self):
        self.active(); self.delivered()
        self.e.request_rework("build", "Missing field")
        self.e.request_rework("build", "Missing field")
        self.assertEqual(self.db.get("task", "build")["generation"], 2)

    def test_remediation_budget(self):
        self.active()
        for index in range(3):
            self.delivered()
            if index < 2:
                self.e.request_rework("build", f"Correction {index}")
            else:
                with self.assertRaises(DonnaError): self.e.request_rework("build", "Too many")

    def test_verified_dependency_is_required_not_native_done(self):
        self.active(plan(tasks=[task("first"), task("second", deps=["first"])]))
        self.delivered("first")
        with self.assertRaises(DonnaError): self.e.dispatch_one("second", now=NOW)
        self.e.accept_task("first", evidence(), now=NOW)
        result = self.e.dispatch_one("second", now=NOW)
        self.assertIn("card_id", result)

    def test_native_read_failure_does_not_erase_state(self):
        self.active(); self.delivered(); self.native.fail_show = True
        result = self.e.sync(now=NOW)
        self.assertTrue(result["errors"])
        self.assertEqual(self.db.get("task", "build")["state"], "awaiting_review")

    def test_native_reopen_invalidates_acceptance_and_closed_project(self):
        self.active(); card = self.delivered()
        self.e.accept_task("build", evidence(), now=NOW)
        self.e.close_project("life-project", evidence("outcome", human=True))
        self.native.cards[card]["status"] = "ready"
        self.e.sync(now=NOW)
        self.assertEqual(self.db.get("task", "build")["state"], "dispatched")
        self.assertEqual(self.db.get("project", "life-project")["state"], "paused")

    def test_human_acceptance_required_to_close_project(self):
        self.active(); self.delivered(); self.e.accept_task("build", evidence(), now=NOW)
        with self.assertRaises(DonnaError): self.e.close_project("life-project", evidence("outcome"))

    def test_responsibility_is_not_finite_project(self):
        self.active(plan(kind="responsibility")); self.delivered(); self.e.accept_task("build", evidence(), now=NOW)
        with self.assertRaises(DonnaError): self.e.close_project("life-project", evidence("outcome", human=True))

    def test_donna_can_research_without_delegating_her_own_work(self):
        self.active(plan(tasks=[task("research", kind="donna", owner="donna")]))
        self.e.accept_task("research", evidence(), now=NOW)
        self.assertFalse(self.native.cards)
        self.assertEqual(self.db.get("task", "research")["state"], "verified")
