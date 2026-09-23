"""Documented CLI. JSON output makes agent calls explicit and inspectable."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from . import __version__
from .common import DonnaError, pretty, read_json, digest
from .config import Config, initialize
from .engine import Engine
from .projection import Projection
from .review import Review
from .store import Store


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="donna_ops.py", description="Donna coordination toolkit — no implicit installation or background service")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--config", help="Absolute path to the private donna-ops.json; otherwise DONNA_OPS_CONFIG/HERMES_HOME")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Plan configuration, or create it with --apply; never scaffold the vault")
    init.add_argument("--profile", required=True)
    init.add_argument("--profile-home", required=True)
    init.add_argument("--vault", required=True)
    init.add_argument("--area", required=True, help="Approved relative folder inside the existing vault")
    init.add_argument("--board", required=True)
    init.add_argument("--timezone", required=True)
    init.add_argument("--human-capacity", type=float)
    init.add_argument("--apply", action="store_true")
    imp = sub.add_parser("plan-import")
    imp.add_argument("file")
    add = sub.add_parser("task-add")
    add.add_argument("project")
    add.add_argument("file")
    add.add_argument("--authorization", required=True)
    act = sub.add_parser("activate")
    act.add_argument("project")
    act.add_argument("--authorization", required=True)
    act.add_argument("--acknowledge-unknown-capacity", action="store_true")
    for cmd in ("pause", "reopen"):
        s = sub.add_parser(cmd)
        s.add_argument("project")
        s.add_argument("--reason", required=True)
    am = sub.add_parser("project-amend")
    am.add_argument("project")
    am.add_argument("file", help="JSON object of editable fields")
    am.add_argument("--revision", type=int, required=True)
    ti = sub.add_parser("team-import")
    ti.add_argument("file")
    sub.add_parser("team-list")
    gap = sub.add_parser("gap")
    gap.add_argument("project")
    gap.add_argument("capability")
    gap.add_argument("--reason", required=True)
    res = sub.add_parser("gap-resolve")
    res.add_argument("gap")
    res.add_argument("member")
    for cmd in ("prepare", "dispatch", "forecast"):
        s = sub.add_parser(cmd)
        s.add_argument("id")
    sub.add_parser("dispatch-ready")
    rev = sub.add_parser("task-revise")
    rev.add_argument("task"); rev.add_argument("file")
    rev.add_argument("--revision", type=int, required=True)
    rev.add_argument("--authorization", required=True)
    recovery = sub.add_parser("transport-reset")
    recovery.add_argument("task"); recovery.add_argument("--reason", required=True)
    allocate = sub.add_parser("allocate")
    allocate.add_argument("project"); allocate.add_argument("--hours", type=float, required=True)
    allocate.add_argument("--authorization", required=True)
    auth = sub.add_parser("authorize-task")
    auth.add_argument("task")
    auth.add_argument("--reference", required=True)
    for cmd in ("accept-task", "close-project"):
        s = sub.add_parser(cmd)
        s.add_argument("id")
        s.add_argument("--evidence", required=True, help="JSON criterion-level verification and human receipt when applicable")
    rw = sub.add_parser("rework")
    rw.add_argument("task")
    rw.add_argument("--reason", required=True)
    for cmd in ("sync", "render", "conflicts", "review", "pulse", "status"):
        sub.add_parser(cmd)
    show = sub.add_parser("show")
    show.add_argument("kind", choices=["project", "task", "member", "gap"])
    show.add_argument("id")
    rs = sub.add_parser("resolve")
    rs.add_argument("id")
    rs.add_argument("--hash", required=True)
    rs.add_argument("--action", choices=["import-project", "keep-state"], required=True)
    rs.add_argument("--reason", required=True)
    fin = sub.add_parser("review-finish")
    fin.add_argument("--token", required=True)
    fin.add_argument("--digest", required=True)
    fin.add_argument("--report", required=True)
    reset = sub.add_parser("review-reset")
    reset.add_argument("--reason", required=True)
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--native", action="store_true", help="Invoke native help/diagnostics, never a model")
    backup = sub.add_parser("backup")
    backup.add_argument("destination")
    events = sub.add_parser("events")
    events.add_argument("--after", type=int, default=0)
    events.add_argument("--limit", type=int, default=100)
    return p


def dispatch(args, cfg: Config, db: Store):
    e = Engine(cfg, db)
    cmd = args.command
    load = lambda filename: read_json(Path(filename).expanduser().absolute())
    if cmd == "plan-import":
        return e.import_plan(load(args.file))
    if cmd == "task-add":
        return e.add_tasks(args.project, load(args.file), args.authorization)
    if cmd == "activate":
        return e.activate(args.project, args.authorization, accept_unknown_capacity=args.acknowledge_unknown_capacity)
    if cmd == "pause":
        return e.pause(args.project, args.reason)
    if cmd == "reopen":
        return e.reopen(args.project, args.reason)
    if cmd == "project-amend":
        return e.amend_project(args.project, load(args.file), args.revision)
    if cmd == "team-import":
        raw = load(args.file)
        result = e.import_team(raw)
        # Keep the human-owned roster authoritative: block dispatch if edited later.
        with db.transaction():
            db.setmeta("team_source", {"path": str(Path(args.file).expanduser().absolute()), "digest": digest(raw)})
        return result
    if cmd == "team-list":
        return {"members": db.all("member")}
    if cmd == "gap":
        return e.capability_gap(args.project, args.capability, args.reason)
    if cmd == "gap-resolve":
        return e.resolve_gap(args.gap, args.member)
    if cmd in {"prepare", "dispatch", "dispatch-ready"}:
        # Discover user edits before dispatch; do not execute on stale projected intent.
        Projection(e).render()
        source = db.meta("team_source")
        if source and digest(read_json(Path(source["path"]))) != source["digest"]:
            raise DonnaError("Authoritative .team changed; review and reimport it before dispatch")
        if cmd == "prepare":
            return e.prepare(args.id)
        if cmd == "dispatch":
            return e.dispatch_one(args.id)
        return e.dispatch_ready()
    if cmd == "task-revise":
        return e.revise_task(args.task, load(args.file), args.revision, args.authorization)
    if cmd == "transport-reset":
        return e.reset_transport(args.task, args.reason)
    if cmd == "allocate":
        return e.allocate(args.project, args.hours, args.authorization)
    if cmd == "authorize-task":
        return e.authorize_task(args.task, args.reference)
    if cmd == "accept-task":
        return e.accept_task(args.id, load(args.evidence))
    if cmd == "close-project":
        return e.close_project(args.id, load(args.evidence))
    if cmd == "rework":
        return e.request_rework(args.task, args.reason)
    if cmd == "sync":
        return e.sync()
    if cmd == "render":
        return Projection(e).render()
    if cmd == "conflicts":
        return Projection(e).conflicts()
    if cmd == "resolve":
        return Projection(e).resolve(args.id, expected_hash=args.hash, action=args.action, reason=args.reason)
    if cmd == "review":
        return Review(e).inspect()
    if cmd == "pulse":
        return Review(e).pulse()
    if cmd == "review-finish":
        return Review(e).finish(args.token, args.digest, load(args.report))
    if cmd == "review-reset":
        return Review(e).reset(args.reason)
    if cmd == "forecast":
        return e.forecast(args.id)
    if cmd == "show":
        return db.get(args.kind, args.id)
    if cmd == "status":
        return {"version": __version__, "projects": db.all("project"), "tasks": db.all("task"),
                "gaps": db.all("gap"), "review": Review(e).inspect(), "sync_health": db.meta("sync_health")}
    if cmd == "doctor":
        result = {"ok": True, "version": __version__, "profile": cfg.profile, "board": cfg.board,
                  "configuration": "validated", "journal": db.conn.execute("PRAGMA quick_check").fetchone()[0],
                  "limits": {"max_dispatch_per_run": cfg.max_dispatch_per_run, "max_rework": cfg.max_rework},
                  "native_tested": False, "notice": "No secrets, model pins or .obsidian settings inspected."}
        if args.native:
            result["native"] = e.native.doctor()
            result["native_tested"] = True
            result["ok"] = result["native"]["ok"]
        return result
    if cmd == "backup":
        dest = Path(args.destination).expanduser().absolute()
        db.backup(dest)
        return {"backup": str(dest), "note": "Consistent SQLite backup; also preserve configuration, roster and authorized vault files."}
    if cmd == "events":
        if args.after < 0 or not 1 <= args.limit <= 1000:
            raise DonnaError("Invalid event window")
        rows = db.conn.execute("SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT ?", (args.after, args.limit)).fetchall()
        return {"events": [{**dict(r), "payload": json.loads(r["payload"])} for r in rows], "next_after": rows[-1]["seq"] if rows else args.after}
    raise DonnaError("Unknown command")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    db = None
    try:
        if args.command == "init":
            if not args.config:
                raise DonnaError("init requires explicit --config destination")
            result = initialize(Path(args.config).expanduser().absolute(), profile=args.profile,
                                profile_home=Path(args.profile_home).expanduser().absolute(),
                                vault=Path(args.vault).expanduser().absolute(), area=args.area,
                                board=args.board, zone=args.timezone, capacity=args.human_capacity, apply=args.apply)
        else:
            cfg = Config.load(args.config)
            db = Store(cfg.state_dir)
            result = dispatch(args, cfg, db)
        if args.command == "pulse":
            # Hermes reads wakeAgent only from the FINAL stdout line.
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        else:
            print(pretty(result), end="")
        if isinstance(result, dict) and (result.get("ok") is False or result.get("errors") or (args.command == "render" and result.get("conflicts"))):
            return 3
        return 0
    except DonnaError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error, UnicodeError) as exc:
        # Paths and raw errors may contain sensitive details: no stack trace by default.
        print(json.dumps({"ok": False, "error_code": "io_error", "error": type(exc).__name__ + ": inspect permissions, paths and the journal locally"}), file=sys.stderr)
        return 2
    finally:
        if db:
            db.close()
