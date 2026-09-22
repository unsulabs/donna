#!/usr/bin/env python3
"""Board-wide terminal-event notifier for a Hermes kanban board.

Why: per-card notify subscriptions only cover cards that auto-subscribed
from a chat. Cards created via CLI, cron, or --json can finish silently.
This watchdog covers the whole board without depending on how a card was born.

Designed for a no_agent cron (empty stdout = silent delivery):

  * nothing new              -> print nothing
  * terminal event           -> print a short block for cron delivery
  * card already subscribed  -> skip (avoid double notify)

State: cursor file (last seen task_events id). First run baselines without spam.

Honest limit: if delivery fails after the cursor advances, that ping is lost —
the board remains the source of truth (`hermes kanban list`).

Configuration (env, no secrets required beyond paths you already control):

  DONNA_KANBAN_BOARD          board slug (default: donna-ops)
  DONNA_KANBAN_BOARD_DB       absolute path to that board's kanban.db (required)
  DONNA_KANBAN_NOTIFY_CURSOR  optional path to cursor file
                              (default: next to this script, .kanban-board-notify.cursor)
  DONNA_KANBAN_NOTIFY_MAX     max lines to print (default: 40)
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

BOARD = os.environ.get("DONNA_KANBAN_BOARD", "donna-ops").strip() or "donna-ops"
BOARD_DB = Path(os.environ.get("DONNA_KANBAN_BOARD_DB", "")).expanduser()
STATE = Path(
    os.environ.get(
        "DONNA_KANBAN_NOTIFY_CURSOR",
        str(Path(__file__).resolve().parent / ".kanban-board-notify.cursor"),
    )
).expanduser()
TERMINAL = ("completed", "blocked", "gave_up", "crashed", "timed_out")
try:
    MAX_LINES = max(1, int(os.environ.get("DONNA_KANBAN_NOTIFY_MAX", "40")))
except ValueError:
    MAX_LINES = 40


def read_cursor() -> int | None:
    try:
        return int(STATE.read_text().strip())
    except Exception:
        return None


def write_cursor(value: int) -> bool:
    tmp = STATE.with_suffix(".tmp")
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(f"{value}\n")
        os.replace(tmp, STATE)
        return True
    except Exception:
        return False


def conn() -> sqlite3.Connection:
    # Read-only + WAL: dispatcher and workers write this DB.
    return sqlite3.connect(f"file:{BOARD_DB}?mode=ro", uri=True, timeout=10)


def main() -> int:
    if not BOARD_DB or not BOARD_DB.exists():
        return 0  # nothing to watch; silence

    try:
        db = conn()
        cur = db.cursor()
        cur.execute("select coalesce(max(id), 0) from task_events")
        top = int(cur.fetchone()[0] or 0)
    except Exception:
        return 0  # locked/unavailable: not the human's problem this tick

    cursor = read_cursor()
    if cursor is None:
        return 0 if write_cursor(top) else 1  # baseline, no alerts

    if top <= cursor:
        return 0

    try:
        cur.execute(
            "select id, task_id, kind, payload from task_events "
            "where id > ? order by id",
            (cursor,),
        )
        events = cur.fetchall()

        try:
            cur.execute("select task_id from kanban_notify_subs")
            subscribed = {r[0] for r in cur.fetchall()}
        except Exception:
            subscribed = set()

        lines: list[str] = []
        for _event_id, task_id, kind, payload in events:
            if kind not in TERMINAL or task_id in subscribed:
                continue
            cur.execute(
                "select title, assignee, status, tenant from tasks where id = ?",
                (task_id,),
            )
            row = cur.fetchone() or ("(untitled)", "?", "?", "")
            title, assignee, _status, tenant = row
            try:
                data = json.loads(payload) if payload else {}
            except Exception:
                data = {}
            detail = (
                data.get("summary")
                or data.get("reason")
                or data.get("error")
                or data.get("outcome")
                or ""
            )
            mark = "✔" if kind == "completed" else "⚠"
            head = f"{mark} [{BOARD}] @{assignee} {task_id} {kind} — {title}"
            if tenant:
                head += f"  ({tenant})"
            lines.append(head)
            if detail:
                lines.append("   " + " ".join(str(detail).split())[:400])
        db.close()
    except Exception:
        return 0

    if not write_cursor(top):
        print(
            "kanban board notify: could not write cursor "
            f"({STATE}); without it, alerts would duplicate",
            file=sys.stderr,
        )
        return 1

    if lines:
        print("\n".join(lines[:MAX_LINES]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
