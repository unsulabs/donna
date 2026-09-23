"""Validated planning and acceptance contracts, not model-generated status guesses."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .common import DonnaError, day, enum, instant, number, slug, strings, text

KINDS = {"aspiration", "responsibility", "routine", "project", "commitment"}
OWNER_KINDS = {"user", "human", "donna", "agent"}
ACTIONS = {"internal", "publish", "payment", "destructive", "account_change"}
NATIVE_STATES = {"triage", "todo", "ready", "running", "blocked", "review", "done", "archived"}
EDITABLE_PROJECT = {"title", "outcome", "priority", "next_review", "assumptions", "context_refs", "target_date"}


def obj(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DonnaError(f"{name} must be an object")
    return value


def only(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unexpected = set(value) - allowed
    if unexpected:
        raise DonnaError(f"Unexpected {name} fields: {', '.join(sorted(unexpected))}")


def bounds(value: Any, name: str) -> dict[str, float]:
    value = obj(value, name)
    only(value, {"low", "high"}, name)
    if set(value) != {"low", "high"}:
        raise DonnaError(f"{name} requires low and high estimates")
    low, high = number(value["low"], name), number(value["high"], name)
    if high < low:
        raise DonnaError(f"{name}: high must not be less than low")
    return {"low": low, "high": high}


def criteria(value: Any, name: str = "criteria") -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 100:
        raise DonnaError(f"{name} must be a list, at most 100 criteria")
    out, seen = [], set()
    for item in value:
        item = obj(item, name)
        only(item, {"id", "description"}, name)
        identifier = slug(item.get("id"), "criterion id")
        if identifier in seen:
            raise DonnaError("Duplicate criterion id")
        seen.add(identifier)
        out.append({"id": identifier, "description": text(item.get("description"), name, maximum=4000)})
    return out


def deadline(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    value = obj(value, "deadline")
    only(value, {"date", "source"}, "deadline")
    return {"date": day(value.get("date")).isoformat(), "source": text(value.get("source"), "deadline source")}


def project(value: Any) -> dict[str, Any]:
    p = deepcopy(obj(value, "project"))
    only(p, {"id", "title", "kind", "outcome", "criteria", "priority", "next_review", "allocation_hours_week",
             "assumptions", "deadline", "target_date", "context_refs", "acceptance_owner"}, "project")
    p["id"] = slug(p.get("id"), "project id")
    p["title"] = text(p.get("title"), "project title", maximum=300)
    p["kind"] = enum(p.get("kind"), KINDS, "project kind")
    p["outcome"] = text(p.get("outcome"), "project outcome")
    p["criteria"] = criteria(p.get("criteria", []))
    if type(p.get("priority", 3)) is not int:
        raise DonnaError("priority must be an integer")
    p["priority"] = int(number(p.get("priority", 3), "priority", 1, 5))
    p["next_review"] = instant(p["next_review"]).isoformat() if p.get("next_review") else None
    p["allocation_hours_week"] = number(p.get("allocation_hours_week", 0), "allocation_hours_week", 0, 168)
    p["assumptions"] = strings(p.get("assumptions", []), "assumptions")
    p["context_refs"] = strings(p.get("context_refs", []), "context_refs")
    p["deadline"] = deadline(p.get("deadline"))
    p["target_date"] = day(p["target_date"]).isoformat() if p.get("target_date") else None
    p["acceptance_owner"] = enum(p.get("acceptance_owner", "user"), {"user", "donna"}, "acceptance_owner")
    return p


def task(value: Any, project_id: str) -> dict[str, Any]:
    t = deepcopy(obj(value, "task"))
    only(t, {"id", "title", "owner", "outcome", "brief", "criteria", "dependencies", "capabilities", "duration_days",
             "human_hours", "action_class", "source_refs", "skills", "not_before", "deadline", "workspace"}, "task")
    t["id"] = slug(t.get("id"), "task id")
    t["project_id"] = project_id
    t["title"] = text(t.get("title"), "task title", maximum=300)
    own = obj(t.get("owner"), "owner")
    only(own, {"kind", "id"}, "owner")
    t["owner"] = {"kind": enum(own.get("kind"), OWNER_KINDS, "owner kind"), "id": slug(own.get("id"), "owner id")}
    t["outcome"] = text(t.get("outcome"), "task outcome")
    t["brief"] = text(t.get("brief"), "brief")
    t["criteria"] = criteria(t.get("criteria", []))
    t["dependencies"] = strings(t.get("dependencies", []), "dependencies")
    for dep in t["dependencies"]:
        slug(dep, "dependency id")
    if len(t["dependencies"]) != len(set(t["dependencies"])):
        raise DonnaError("Duplicate dependency")
    t["capabilities"] = strings(t.get("capabilities", []), "capabilities")
    for cap in t["capabilities"]:
        slug(cap, "capability")
    t["estimate_known"] = "duration_days" in t
    t["human_effort_known"] = "human_hours" in t
    t["workspace"] = t.get("workspace")
    if t["workspace"] is not None:
        from .common import absolute
        t["workspace"] = str(absolute(t["workspace"], "workspace", exists=True))
    t["duration_days"] = bounds(t.get("duration_days", {"low": 0, "high": 0}), "duration_days")
    t["human_hours"] = bounds(t.get("human_hours", {"low": 0, "high": 0}), "human_hours")
    t["action_class"] = enum(t.get("action_class", "internal"), ACTIONS, "action_class")
    t["source_refs"] = strings(t.get("source_refs", []), "source_refs")
    t["skills"] = strings(t.get("skills", []), "skills")
    for skill in t["skills"]:
        slug(skill, "skill")
    t["not_before"] = instant(t["not_before"]).isoformat() if t.get("not_before") else None
    t["deadline"] = deadline(t.get("deadline"))
    return t


def graph(tasks: list[dict[str, Any]]) -> list[str]:
    by_id = {t["id"]: t for t in tasks}
    if len(by_id) != len(tasks):
        raise DonnaError("Duplicate task id")
    visiting: set[str] = set()
    done: set[str] = set()
    ordered: list[str] = []

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise DonnaError("Dependency cycle")
        if identifier in done:
            return
        if identifier not in by_id:
            raise DonnaError(f"Unknown dependency: {identifier}")
        visiting.add(identifier)
        for dep in by_id[identifier]["dependencies"]:
            visit(dep)
        visiting.remove(identifier)
        done.add(identifier)
        ordered.append(identifier)

    for identifier in by_id:
        visit(identifier)
    return ordered


def plan(value: Any) -> dict[str, Any]:
    value = obj(value, "plan")
    only(value, {"schema_version", "project", "tasks"}, "plan")
    if value.get("schema_version") != 1:
        raise DonnaError("Unsupported plan schema")
    p = project(value.get("project"))
    raw_tasks = value.get("tasks", [])
    if not isinstance(raw_tasks, list) or len(raw_tasks) > 500:
        raise DonnaError("tasks must be a list of at most 500 entries")
    tasks = [task(t, p["id"]) for t in raw_tasks]
    graph(tasks)
    return {"schema_version": 1, "project": p, "tasks": tasks}


def evidence(value: Any, wanted: list[dict[str, str]], *, human: bool = False) -> dict[str, Any]:
    """Validate an attestation structure; semantic truth is reviewed, not inferred."""
    value = deepcopy(obj(value, "evidence"))
    only(value, {"reviewer", "source", "summary", "checks", "receipt"}, "evidence")
    value["reviewer"] = text(value.get("reviewer"), "reviewer", maximum=200)
    value["source"] = text(value.get("source"), "evidence source")
    value["summary"] = text(value.get("summary"), "evidence summary")
    if human:
        value["receipt"] = text(value.get("receipt"), "actual human decision/completion receipt")
    elif value.get("receipt") is not None:
        value["receipt"] = text(value["receipt"], "receipt")
    checks = value.get("checks")
    if not isinstance(checks, list) or not checks:
        raise DonnaError("Acceptance requires criterion-level evidence")
    seen = set()
    for check in checks:
        obj(check, "check")
        only(check, {"criterion", "passed", "source", "observation", "artifact"}, "check")
        cid = slug(check.get("criterion"), "criterion")
        if cid in seen:
            raise DonnaError("Duplicate criterion evidence")
        seen.add(cid)
        if check.get("passed") is not True:
            raise DonnaError("Cannot accept failing or unverified evidence")
        text(check.get("source"), "check source")
        text(check.get("observation"), "check observation")
        if check.get("artifact") is not None:
            artifact = obj(check["artifact"], "artifact")
            only(artifact, {"path", "sha256"}, "artifact")
            from .common import absolute
            absolute(artifact.get("path"), "artifact path")
            import re
            if not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
                raise DonnaError("Artifact evidence needs a lowercase SHA-256 digest")
    if seen != {c["id"] for c in wanted}:
        raise DonnaError("Evidence must cover exactly every acceptance criterion")
    return value


def member(value: Any) -> dict[str, Any]:
    value = deepcopy(obj(value, "member"))
    only(value, {"id", "profile", "role", "capabilities", "skills", "doctrine_paths", "status", "verified_at", "checks"}, "member")
    value["id"] = slug(value.get("id"), "member id")
    value["profile"] = slug(value.get("profile"), "member profile")
    value["role"] = text(value.get("role"), "member role")
    for field in ("capabilities", "skills", "doctrine_paths"):
        value[field] = strings(value.get(field, []), field)
    for field in ("capabilities", "skills"):
        for entry in value[field]:
            slug(entry, field)
    value["status"] = enum(value.get("status", "proposed"), {"proposed", "configured", "verified", "disabled"}, "member status")
    value["verified_at"] = instant(value["verified_at"]).isoformat() if value.get("verified_at") else None
    value["checks"] = value.get("checks", {})
    obj(value["checks"], "member checks")
    if value["status"] == "verified":
        if not value["verified_at"] or not value["capabilities"] or not value["doctrine_paths"]:
            raise DonnaError("Verified member requires timestamp, capabilities and doctrine paths")
        for name in ("model", "tools", "handoff"):
            check = obj(value["checks"].get(name), f"member check {name}")
            if check.get("passed") is not True:
                raise DonnaError(f"Missing successful member check: {name}")
            text(check.get("source"), f"member check {name} source")
    return value
