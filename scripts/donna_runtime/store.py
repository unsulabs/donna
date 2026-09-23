"""Transactional Donna journal. Never opens a Hermes database."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .common import Conflict, DonnaError, canonical, private_dir, reject_symlink, stamp

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
 kind TEXT NOT NULL, id TEXT NOT NULL, project_id TEXT,
 data TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, updated TEXT NOT NULL,
 PRIMARY KEY(kind,id)
);
CREATE INDEX IF NOT EXISTS objects_project ON objects(project_id,kind);
CREATE TABLE IF NOT EXISTS dispatches (
 task_id TEXT NOT NULL, generation INTEGER NOT NULL, request_key TEXT NOT NULL UNIQUE,
 payload TEXT NOT NULL, payload_hash TEXT NOT NULL, card_id TEXT,
 state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
 error TEXT, snapshot TEXT, next_try TEXT, updated TEXT NOT NULL,
 PRIMARY KEY(task_id,generation)
);
CREATE TABLE IF NOT EXISTS events (
 seq INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE,
 kind TEXT NOT NULL, entity_id TEXT NOT NULL, payload TEXT NOT NULL, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projections (
 path TEXT PRIMARY KEY, kind TEXT NOT NULL, entity_id TEXT NOT NULL,
 block_hash TEXT NOT NULL, revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS conflicts (
 id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL, entity_id TEXT NOT NULL,
 actual_hash TEXT NOT NULL, proposed_hash TEXT NOT NULL, base_revision INTEGER NOT NULL,
 proposal TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, directory: Path):
        private_dir(directory)
        self.path = directory / "coordination.sqlite3"
        reject_symlink(self.path)
        self.conn = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=20000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.conn.close()
            raise DonnaError("Journal schema is newer/unknown; refusing to downgrade")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA user_version=1")
        if os.name == "posix":
            self.path.chmod(0o600)

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator["Store"]:
        if self.conn.in_transaction:
            raise DonnaError("Nested transaction: internal programming error")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def get(self, kind: str, identifier: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM objects WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row is None:
            raise DonnaError(f"Unknown {kind}: {identifier}")
        result = json.loads(row["data"])
        result["_revision"] = row["revision"]
        return result

    def exists(self, kind: str, identifier: str) -> bool:
        return self.conn.execute("SELECT 1 FROM objects WHERE kind=? AND id=?", (kind, identifier)).fetchone() is not None

    def all(self, kind: str, project: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT id FROM objects WHERE kind=?"
        args: list[Any] = [kind]
        if project is not None:
            query += " AND project_id=?"
            args.append(project)
        query += " ORDER BY id"
        return [self.get(kind, row[0]) for row in self.conn.execute(query, args).fetchall()]

    def put(self, kind: str, value: dict[str, Any], *, expected: int | None = None) -> None:
        if not self.conn.in_transaction:
            raise DonnaError("Write requires a transaction")
        data = dict(value)
        data.pop("_revision", None)
        identifier = data["id"]
        row = self.conn.execute("SELECT revision FROM objects WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row:
            if expected is None or row[0] != expected:
                raise Conflict(f"Revision changed for {kind} {identifier}")
            self.conn.execute("UPDATE objects SET data=?, revision=revision+1, updated=? WHERE kind=? AND id=?",
                              (canonical(data), stamp(), kind, identifier))
        elif expected is not None:
            raise Conflict(f"Missing {kind} while updating")
        else:
            self.conn.execute("INSERT INTO objects(kind,id,project_id,data,updated) VALUES(?,?,?,?,?)",
                              (kind, identifier, data.get("project_id"), canonical(data), stamp()))

    def event(self, kind: str, entity: str, payload: Any, *, key: str | None = None) -> None:
        self.conn.execute("INSERT OR IGNORE INTO events(event_key,kind,entity_id,payload,at) VALUES(?,?,?,?,?)",
                          (key, kind, entity, canonical(payload), stamp()))

    def meta(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def setmeta(self, key: str, value: Any) -> None:
        self.conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, canonical(value)))

    def dispatch(self, task: str, generation: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM dispatches WHERE task_id=? AND generation=?", (task, generation)).fetchone()
        return dict(row) if row else None

    def backup(self, destination: Path) -> None:
        reject_symlink(destination)
        if destination.exists():
            raise Conflict("Backup destination already exists")
        private_dir(destination.parent)
        target = sqlite3.connect(destination)
        try:
            self.conn.backup(target)
        finally:
            target.close()
        if os.name == "posix":
            destination.chmod(0o600)
