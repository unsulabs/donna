"""Bounded proactive reviews: persist intent, lease a turn, acknowledge AFTER work.

A lost wake or failed LLM turn is retried after lease expiry, not marked handled.
The scheduler remains Hermes cron; this module never starts a background daemon.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .common import Conflict, DonnaError, digest, instant, stamp, text, utcnow
from .engine import Engine
from .projection import Projection


class Review:
    def __init__(self, engine: Engine):
        self.e = engine
        self.db = engine.db

    def inspect(self, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or utcnow()
        local_day = now.astimezone(ZoneInfo(self.e.cfg.timezone)).date()
        items: list[dict[str, Any]] = []
        projects = {p["id"]: p for p in self.db.all("project")}
        for p in projects.values():
            if p["state"] != "active":
                continue
            if p["next_review"] is None or instant(p["next_review"]) <= now:
                items.append({"id": "project-review:" + p["id"], "kind": "project_review", "project": p["id"],
                              "due": p["next_review"], "priority": p["priority"]})
            if p["deadline"] and (datetime.fromisoformat(p["deadline"]["date"]).date() - local_day).days <= 7:
                items.append({"id": "deadline:" + p["id"], "kind": "deadline", "project": p["id"], "date": p["deadline"]["date"], "as_of_day": str(local_day)})
        for t in self.db.all("task"):
            p = projects[t["project_id"]]
            d = self.db.dispatch(t["id"], t["generation"])
            if d and d["error"]:
                items.append({"id": "transport:" + t["id"], "kind": "native_error", "task": t["id"], "detail": d["error"], "attempts": d["attempts"]})
            if self.db.meta("invalidated:" + t["id"]):
                items.append({"id": "invalidated:" + t["id"], "kind": "accepted_result_changed", "task": t["id"]})
            if p["state"] not in {"active", "paused"}:
                continue
            if t["state"] in {"awaiting_review", "waiting", "needs_changes"}:
                items.append({"id": f"task:{t['id']}:{t['generation']}", "kind": t["state"], "task": t["id"], "project": t["project_id"]})
            elif p["state"] == "active" and t["state"] in {"planned", "dispatching"}:
                deps_ready = all(self.db.get("task", dep)["state"] == "verified" for dep in t["dependencies"])
                time_ready = not t["not_before"] or instant(t["not_before"]) <= now
                if deps_ready and time_ready:
                    owner = t["owner"]["kind"]
                    kind = "human_action" if owner in {"user", "human"} else ("donna_action" if owner == "donna" else "ready_to_coordinate")
                    items.append({"id": f"task:{t['id']}:{t['generation']}", "kind": kind, "task": t["id"], "owner": t["owner"],
                                  "blocker": self.e.blocker(t, now) if kind == "ready_to_coordinate" else None})
            if p["state"] == "active" and t["deadline"] and t["state"] != "verified" and (datetime.fromisoformat(t["deadline"]["date"]).date() - local_day).days <= 7:
                items.append({"id": "task-deadline:" + t["id"], "kind": "deadline", "task": t["id"], "date": t["deadline"]["date"], "as_of_day": str(local_day)})
        for gap in self.db.all("gap"):
            if gap["state"] == "open":
                items.append({"id": gap["id"], "kind": "capability_gap", "project": gap["project_id"], "capability": gap["capability"]})
        for row in self.db.conn.execute("SELECT id,path FROM conflicts WHERE status='open' ORDER BY id"):
            items.append({"id": row["id"], "kind": "obsidian_conflict", "path": row["path"]})
        health = self.db.meta("sync_health")
        if health and not health["ok"]:
            items.append({"id": "native-health", "kind": "native_health", "ok": False})
        allocation = sum(p["allocation_hours_week"] for p in projects.values() if p["state"] == "active")
        capacity = self.e.cfg.human_capacity_hours
        if capacity is not None and allocation > capacity:
            items.append({"id": "human-overload", "kind": "capacity", "allocated": allocation, "available": capacity})
        items.sort(key=lambda i: i["id"])
        return {"digest": digest(items), "items": items, "total": len(items), "as_of": stamp(now),
                "human_capacity": {"available": capacity, "allocated": allocation},
                "meaning": "Action queue for Donna; not a list that transfers coordination back to the user."}

    def pulse(self, *, now: datetime | None = None, synchronize: bool = True) -> dict[str, Any]:
        now = now or utcnow()
        lease = self.db.meta("review_lease")
        if lease and instant(lease["until"]) > now:
            return {"wakeAgent": False, "reason": "A review is already leased"}
        if synchronize:
            synced = self.e.sync(now=now)
            if synced["errors"]:
                # Nonzero preflight prevents a false quiet tick, and Hermes records failure.
                raise DonnaError("Native reconciliation failed; pending work retained. Run sync/doctor locally.")
        Projection(self.e).render()
        current = self.inspect(now=now)
        with self.db.transaction():
            lease = self.db.meta("review_lease")
            if lease and instant(lease["until"]) > now:
                return {"wakeAgent": False, "reason": "Another process acquired the review lease"}
            if not current["items"]:
                return {"wakeAgent": False, "reason": "No actionable or due work"}
            ack = self.db.meta("review_ack")
            if ack and ack["digest"] == current["digest"] and instant(ack["next_at"]) > now:
                return {"wakeAgent": False, "reason": "Already reviewed; waiting for recorded follow-up"}
            failures = self.db.meta("wake_budget", {"digest": None, "count": 0})
            attempts = failures["count"] + 1 if failures["digest"] == current["digest"] else 1
            if attempts > self.e.cfg.max_wakes:
                # Persisted previous count remains exhausted; an explicit reset is needed.
                raise DonnaError("Review wake budget exhausted without a successful acknowledgement; inspect and use review-reset with a reason")
            token = str(uuid.uuid4())
            lease = {"token": token, "until": stamp(now + timedelta(seconds=self.e.cfg.lease_seconds)),
                     "digest": current["digest"], "item_ids": [i["id"] for i in current["items"]]}
            self.db.setmeta("review_lease", lease)
            self.db.setmeta("wake_budget", {"digest": current["digest"], "count": attempts})
            self.db.event("review_leased", self.e.cfg.profile, {"token": token, "count": current["total"], "attempt": attempts})
        return {"wakeAgent": True, "context": {"review_token": token, "digest": current["digest"], "total": current["total"],
                "items": current["items"][:40], "more": current["total"] > 40,
                "instruction": "Load donna-operational-review. Run review for the complete queue. Act, verify, then review-finish. Do not acknowledge merely because a wake was emitted."}}

    def finish(self, token: str, expected_digest: str, report: Any, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or utcnow()
        if not isinstance(report, dict) or set(report) != {"summary", "next_at", "items"}:
            raise DonnaError("Review report needs summary, next_at and items")
        text(report["summary"], "review summary")
        next_at = instant(report["next_at"])
        if not now < next_at <= now + timedelta(days=7):
            raise DonnaError("Review next_at must be future and no more than 7 days away")
        if not isinstance(report["items"], list):
            raise DonnaError("Review dispositions must be a list")
        ids: set[str] = set()
        for item in report["items"]:
            if not isinstance(item, dict) or set(item) - {"id", "disposition", "source", "next_at"}:
                raise DonnaError("Invalid review disposition")
            identifier = text(item.get("id"), "review item id")
            if identifier in ids:
                raise DonnaError("Duplicate review disposition")
            ids.add(identifier)
            if item.get("disposition") not in {"resolved", "deferred", "escalated"}:
                raise DonnaError("Disposition must be resolved, deferred or escalated")
            text(item.get("source"), "action evidence/source")
            if item["disposition"] != "resolved":
                follow_up = instant(item.get("next_at"))
                if follow_up <= now or next_at > follow_up:
                    raise DonnaError("Deferred/escalated work requires a follow-up no earlier than the next review")
        with self.db.transaction():
            lease = self.db.meta("review_lease")
            if not lease or lease["token"] != token or instant(lease["until"]) <= now:
                raise Conflict("Review lease is absent, different or expired")
            current = self.inspect(now=now)
            if current["digest"] != expected_digest:
                raise Conflict("Queue changed; inspect again rather than acknowledging unseen work")
            required = set(lease["item_ids"]) | {i["id"] for i in current["items"]}
            if ids != required:
                raise DonnaError("Report must account for every original and current review item")
            still_present = {i["id"] for i in current["items"]}
            if any(i["id"] in still_present and i["disposition"] == "resolved" for i in report["items"]):
                raise DonnaError("An item still present cannot be declared resolved; perform the operation or defer/escalate it")
            self.db.setmeta("review_ack", {"digest": current["digest"], "next_at": stamp(next_at), "at": stamp(now)})
            self.db.setmeta("review_lease", None)
            self.db.setmeta("wake_budget", {"digest": None, "count": 0})
            self.db.event("review_finished", self.e.cfg.profile, report)
        return {"acknowledged": True, "next_at": stamp(next_at)}

    def reset(self, reason: str) -> dict[str, Any]:
        reason = text(reason, "reset reason")
        with self.db.transaction():
            self.db.setmeta("review_lease", None)
            self.db.setmeta("wake_budget", {"digest": None, "count": 0})
            self.db.event("review_reset", self.e.cfg.profile, {"reason": reason})
        return {"reset": True, "reason": reason}
