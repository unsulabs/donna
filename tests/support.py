"""Test-only fixtures. MemoryNative is NOT Hermes and never calls an LLM."""
import copy
import json
import sys
import tempfile
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from donna_runtime.common import NativeError, pretty, stamp, utcnow
from donna_runtime.config import Config
from donna_runtime.engine import Engine
from donna_runtime.store import Store

NOW = datetime(2026, 9, 22, 18, 0, tzinfo=timezone.utc)


def task(identifier="build", *, kind="agent", owner="builder", deps=None):
    return {"id": identifier, "title": "Build a bounded artifact", "owner": {"kind": kind, "id": owner},
            "outcome": "A useful checked artifact", "brief": "Build only the approved local test artifact.",
            "criteria": [{"id": "usable", "description": "The artifact has the agreed fields and passes its checks"}],
            "dependencies": deps or [], "capabilities": ["build"] if kind == "agent" else [], "skills": [],
            "duration_days": {"low": 1, "high": 2}, "human_hours": {"low": 1, "high": 2},
            "action_class": "internal", "source_refs": ["fixture:approved-brief"]}


def plan(identifier="life-project", tasks=None, kind="project"):
    return {"schema_version": 1,
            "project": {"id": identifier, "title": "A whole-life project", "kind": kind,
                        "outcome": "A verified useful outcome", "criteria": [{"id": "outcome", "description": "The user can use the result"}],
                        "priority": 2, "next_review": stamp(NOW - timedelta(hours=1)),
                        "allocation_hours_week": 3, "assumptions": ["Scope and available hours are declared, not guessed"],
                        "context_refs": ["fixture:source"], "acceptance_owner": "user"},
            "tasks": [task()] if tasks is None else tasks}


def team(now=NOW):
    return {"schema_version": 2, "members": [{"id": "builder", "profile": "builder", "role": "Fixture builder",
             "capabilities": ["build"], "skills": [], "doctrine_paths": ["fixture:builder/SOUL.md"],
             "status": "verified", "verified_at": stamp(now - timedelta(days=1)),
             "checks": {k: {"passed": True, "source": "fixture:" + k} for k in ("model", "tools", "handoff")}}]}


def evidence(criterion="usable", *, human=False):
    e = {"reviewer": "fixture-reviewer", "source": "fixture:independent-verification", "summary": "Checked fixture only",
         "checks": [{"criterion": criterion, "passed": True, "source": "fixture:observations", "observation": "All required fields are present"}]}
    if human:
        e["receipt"] = "fixture:user-confirmed-this-action"
    return e


class MemoryNative:
    def __init__(self):
        self.cards = {}
        self.keys = {}
        self.calls = []
        self.available = {"builder", "donna"}
        self.fail_before = False
        self.fail_after_once = False
        self.fail_show = False
        self.lock = threading.Lock()

    def profiles(self):
        return self.available

    def create(self, payload):
        with self.lock:
            self.calls.append(copy.deepcopy(payload))
            if self.fail_before:
                raise NativeError("Fixture transport unavailable")
            key = payload["idempotency_key"]
            if key not in self.keys:
                card = "t_" + str(len(self.keys) + 1)
                self.keys[key] = card
                self.cards[card] = {"id": card, "status": "ready", "tenant": payload["tenant"], "result": None,
                                    "updated_at": "fixture-v1", "assignee": payload["assignee"], "run_id": None, "last_failure_error": False}
            card = self.keys[key]
            if self.fail_after_once:
                self.fail_after_once = False
                raise NativeError("Fixture lost response after native commit")
            return card

    def show(self, identifier):
        if self.fail_show:
            raise NativeError("Fixture native read failed")
        return copy.deepcopy(self.cards[identifier])

    def finish(self, identifier, *, result="Delivered fixture"):
        self.cards[identifier].update(status="done", result=result, updated_at="fixture-done")


class Case(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "profile"
        self.vault = self.root / "existing-vault"
        self.home.mkdir()
        self.vault.mkdir()
        self.config_path = self.home / "donna-ops.json"
        self.raw_config = {"schema_version": 1, "instance_id": str(uuid.uuid4()), "profile": "donna", "profile_home": str(self.home),
                           "vault": str(self.vault), "state_dir": str(self.home / "donna-state"), "area": "Operations/Donna", "board": "donna-ops",
                           "timezone": "America/Mexico_City", "human_capacity_hours": 10,
                           "hermes_command": ["hermes"], "limits": {"lease_seconds": 30}}
        self.config_path.write_text(pretty(self.raw_config), encoding="utf-8")
        self.cfg = Config.load(self.config_path)
        self.db = Store(self.cfg.state_dir)
        self.addCleanup(self.db.close)
        self.native = MemoryNative()
        self.e = Engine(self.cfg, self.db, self.native)

    def active(self, p=None):
        p = p or plan()
        self.e.import_plan(p)
        self.e.import_team(team())
        self.e.activate(p["project"]["id"], "fixture:explicit-project-mandate")
        return p

    def delivered(self, identifier="build"):
        response = self.e.dispatch_one(identifier, now=NOW)
        self.native.finish(response["card_id"])
        self.e.sync(now=NOW)
        return response["card_id"]
