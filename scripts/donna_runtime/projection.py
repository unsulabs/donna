"""Conflict-aware Obsidian views: one managed block, free notes outside it.

No .obsidian settings are installed or changed. Markdown remains readable without
community plugins. Generated Kanban syntax is compatible with Markdown boards;
GUI/plugin behavior requires the live acceptance check documented in docs/.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import models
from .common import Conflict, DonnaError, atomic_write, canonical, digest, pretty, reject_symlink, stamp
from .engine import Engine

BEGIN = "<!-- DONNA:BEGIN v1 -->"
END = "<!-- DONNA:END -->"


def split_document(content: str) -> tuple[str, str, str]:
    if content.count(BEGIN) != 1 or content.count(END) != 1:
        raise Conflict("Managed block markers are missing or duplicated")
    before, remainder = content.split(BEGIN, 1)
    block, after = remainder.split(END, 1)
    return before, block, after


def safe_label(value: str) -> str:
    """Prevent user data from becoming a heading/link/block delimiter."""
    value = " ".join(value.split())
    for old, new in [("[", "（"), ("]", "）"), ("|", "∣"), ("<", "‹"), (">", "›"), ("`", "ˋ")]:
        value = value.replace(old, new)
    return value


def safe_json(value: Any) -> str:
    # Do not let a literal Markdown fence or control marker inside JSON data
    # prematurely end the editable block. These escapes round-trip in json.loads.
    return pretty(value).replace("`", "\\u0060").replace("<", "\\u003c").replace(">", "\\u003e")


class Projection:
    def __init__(self, engine: Engine):
        self.e = engine
        self.db = engine.db
        self.root = engine.cfg.projection_root
        reject_symlink(self.root)

    def project_block(self, p: dict[str, Any]) -> str:
        editable = {k: p[k] for k in sorted(models.EDITABLE_PROJECT)}
        header = {"id": p["id"], "revision": p["_revision"], "editable": editable}
        lines = ["", f"# {safe_label(p['title'])}", "", "## Datos editables", "",
                 "Edita únicamente `editable`. Luego Donna importa y valida el cambio; no ejecuta trabajo por una edición incidental.", "", "```json", safe_json(header).rstrip(), "```", "",
                 f"**Clase:** {p['kind']} · **Estado:** {p['state']} · **Prioridad:** {p['priority']}", "",
                 "## Criterios de cierre", ""]
        lines += [f"- {c['id']}: {safe_label(c['description'])}" for c in p["criteria"]]
        lines += ["", "## Trabajo relacionado", ""]
        for t in self.db.all("task", p["id"]):
            lines.append(f"- [[../Tasks/{t['id']}|{safe_label(t['title'])}]] — {t['owner']['kind']}:{t['owner']['id']} — {t['state']}")
        lines += ["", "## Previsión (no es una promesa de fecha)", "", "```json", safe_json(self.e.forecast(p["id"])).rstrip(), "```", ""]
        return "\n".join(lines)

    def task_block(self, t: dict[str, Any]) -> str:
        d = self.db.dispatch(t["id"], t["generation"])
        native = json.loads(d["snapshot"])["status"] if d and d["snapshot"] else "no observado"
        lines = ["", f"# {safe_label(t['title'])}", "", f"**ID:** {t['id']} · **Responsable:** {t['owner']['kind']}:{t['owner']['id']}",
                 f"**Estado de coordinación:** {t['state']} · **Estado Hermes:** {native}",
                 f"**Tarjeta Hermes:** {d['card_id'] if d and d['card_id'] else 'no creada'} · **Intento:** {t['generation']}", "",
                 f"**Proyecto:** [[../Projects/{t['project_id']}]]", "", "## Resultado esperado", "", safe_label(t["outcome"]), "",
                 "## Criterios", ""]
        lines += [f"- {c['id']}: {safe_label(c['description'])}" for c in t["criteria"]]
        lines += ["", "## Dependencias verificadas antes de ejecutar", ""]
        lines += [f"- [[{dep}]]" for dep in t["dependencies"]] or ["- Sin dependencias registradas."]
        lines += ["", "## Decisiones y aprobación", "", f"Clase de acción: {t['action_class']}.",
                  "Una casilla marcada o tarjeta movida solicita revisión; no acredita un resultado.", ""]
        return "\n".join(lines)

    def board_block(self) -> str:
        categories = ["Por organizar", "En curso", "Revisión", "Bloqueado", "Verificado", "Pausado"]
        buckets = {name: [] for name in categories}
        projects = {p["id"]: p for p in self.db.all("project")}
        for t in self.db.all("task"):
            p = projects[t["project_id"]]
            category = {"planned": "Por organizar", "dispatching": "En curso", "dispatched": "En curso", "waiting": "Bloqueado", "awaiting_review": "Revisión", "needs_changes": "Revisión", "verified": "Verificado"}.get(t["state"], "Pausado")
            if p["state"] in {"planned", "incubating", "paused"}:
                category = "Pausado"
            elif t["state"] == "planned" and any(self.db.get("task", dep)["state"] != "verified" for dep in t["dependencies"]):
                category = "Bloqueado"
            mark = "x" if t["state"] == "verified" else " "
            item = f"- [{mark}] [[Tasks/{t['id']}|{safe_label(t['title'])}]] · {t['owner']['kind']}:{t['owner']['id']} <!-- donna-task:{t['id']} -->"
            buckets[category].append(item)
        lines = ["", "# Donna · coordinación", "", "Mover tarjetas solicita una revisión; Hermes conserva la autoridad sobre ejecución.", ""]
        for cat in categories:
            lines += ["## " + cat, "", *buckets[cat], ""]
        return "\n".join(lines)

    def _write(self, relative_path: str, kind: str, entity: str, revision: int, block: str, *, board: bool = False) -> dict[str, Any]:
        target = self.root / relative_path
        reject_symlink(target)
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if target.exists() and not target.is_file():
            raise Conflict("Managed view path is not a regular file")
        old = self.db.conn.execute("SELECT * FROM projections WHERE path=?", (relative_path,)).fetchone()
        before = "---\nkanban-plugin: board\n---\n\n" if board else ""
        after = "\n\n## Notas personales\n\nEste espacio está fuera del bloque administrado y se conserva al actualizar.\n"
        mismatch = False
        actual_block = ""
        if current is not None:
            try:
                before, actual_block, after = split_document(current)
                mismatch = (old is None) or (digest(actual_block) != old["block_hash"] and actual_block != block)
            except Conflict:
                mismatch = True
        elif old is not None:
            mismatch = True  # Deleted by user: do not silently recreate.
        if mismatch:
            actual_hash = digest(current or "<deleted>")
            cid = "conflict-" + digest({"path": relative_path, "actual": actual_hash, "revision": revision})[:24]
            proposal: dict[str, Any] = {"reason": "Managed section changed/deleted; no overwrite", "editable": None}
            if kind == "project" and actual_block:
                try:
                    match = re.search(r"```json\n(.*?)\n```", actual_block, re.S)
                    raw = json.loads(match.group(1)) if match else None
                    if isinstance(raw, dict) and raw.get("id") == entity and set(raw) == {"id", "revision", "editable"}:
                        proposal["editable"] = raw["editable"]
                        proposal["document_revision"] = raw["revision"]
                except (ValueError, TypeError):
                    pass
            if kind == "board":
                proposal["reason"] = "Board edit requires intent review. Moving to Verificado is NOT evidence of completion."
            # One current open conflict per file. Old variants remain recorded as superseded.
            self.db.conn.execute("UPDATE conflicts SET status='superseded' WHERE path=? AND status='open' AND id<>?", (relative_path, cid))
            self.db.conn.execute("INSERT INTO conflicts(id,path,kind,entity_id,actual_hash,proposed_hash,base_revision,proposal,at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET proposed_hash=excluded.proposed_hash,proposal=excluded.proposal",
                                 (cid, relative_path, kind, entity, actual_hash, digest(block), old["revision"] if old else -1, canonical(proposal), stamp()))
            return {"path": relative_path, "status": "conflict", "conflict_id": cid}
        content = before + BEGIN + block + END + after
        if content != current:
            atomic_write(target, content, expected=digest(current) if current is not None else None, create_only=current is None)
        self.db.conn.execute("INSERT INTO projections(path,kind,entity_id,block_hash,revision) VALUES(?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET block_hash=excluded.block_hash,revision=excluded.revision",
                             (relative_path, kind, entity, digest(block), revision))
        return {"path": relative_path, "status": "updated" if content != current else "unchanged"}

    def render(self) -> dict[str, Any]:
        results = []
        with self.db.transaction():
            for p in self.db.all("project"):
                results.append(self._write(f"Projects/{p['id']}.md", "project", p["id"], p["_revision"], self.project_block(p)))
            for t in self.db.all("task"):
                results.append(self._write(f"Tasks/{t['id']}.md", "task", t["id"], t["_revision"], self.task_block(t)))
            revisions = sum(t["_revision"] for t in self.db.all("task")) + sum(p["_revision"] for p in self.db.all("project"))
            results.append(self._write("Board.md", "board", "board", revisions, self.board_block(), board=True))
        return {"files": results, "conflicts": sum(x["status"] == "conflict" for x in results), "root": str(self.root)}

    def conflicts(self) -> list[dict[str, Any]]:
        rows = self.db.conn.execute("SELECT * FROM conflicts WHERE status='open' ORDER BY at,id").fetchall()
        return [{**dict(r), "proposal": json.loads(r["proposal"])} for r in rows]

    def resolve(self, cid: str, *, expected_hash: str, action: str, reason: str) -> dict[str, Any]:
        if action not in {"import-project", "keep-state"} or not reason.strip():
            raise DonnaError("Resolution needs import-project or keep-state and a meaningful reason")
        row = self.db.conn.execute("SELECT * FROM conflicts WHERE id=? AND status='open'", (cid,)).fetchone()
        if not row:
            raise DonnaError("Open conflict not found")
        target = self.root / row["path"]
        reject_symlink(target)
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        actual = digest(current or "<deleted>")
        if actual != expected_hash or actual != row["actual_hash"]:
            raise Conflict("Document changed again; render and inspect the new conflict")
        proposal = json.loads(row["proposal"])
        if action == "import-project":
            if row["kind"] != "project" or not isinstance(proposal.get("editable"), dict):
                raise DonnaError("This is not a valid editable project proposal; review intent manually")
            p = self.db.get("project", row["entity_id"])
            if p["_revision"] != row["base_revision"] or proposal.get("document_revision") != row["base_revision"]:
                raise Conflict("Both the project and the note changed; reconcile explicitly using current revision")
            # Validation and journal update happen before authorizing a replacement.
            self.e.amend_project(p["id"], proposal["editable"], p["_revision"])
        # Preserve the edited file before restoring managed truth. No deletion.
        backup = self.e.cfg.state_dir / "edit-backups" / (cid + ".md")
        if not backup.exists():
            atomic_write(backup, current or "<deleted by user>\n", create_only=True)
        with self.db.transaction():
            latest = target.read_text(encoding="utf-8") if target.is_file() else None
            if digest(latest or "<deleted>") != actual:
                raise Conflict("Document changed during resolution; original edit preserved in backup")
            if current is None:
                self.db.conn.execute("DELETE FROM projections WHERE path=?", (row["path"],))
            else:
                try:
                    before, block, after = split_document(current)
                except Conflict:
                    # Explicit keep-state can recover malformed markers, with backup.
                    # Keep the complete user text outside the newly managed block.
                    if action != "keep-state":
                        raise
                    prefix = "---\nkanban-plugin: board\n---\n\n" if row["kind"] == "board" else ""
                    safe_original = current.replace(BEGIN, "<!-- Original DONNA BEGIN -->").replace(END, "<!-- Original DONNA END -->")
                    current = prefix + BEGIN + "\n" + END + "\n\n## Texto conservado de la edición\n\n" + safe_original
                    atomic_write(target, current, expected=actual)
                    block = "\n"
                self.db.conn.execute("INSERT INTO projections(path,kind,entity_id,block_hash,revision) VALUES(?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET block_hash=excluded.block_hash",
                                     (row["path"], row["kind"], row["entity_id"], digest(block), row["base_revision"]))
            self.db.conn.execute("UPDATE conflicts SET status='resolved' WHERE id=?", (cid,))
            self.db.event("projection_resolved", row["entity_id"], {"conflict": cid, "action": action, "reason": reason, "backup": str(backup)})
        return {"resolved": cid, "backup": str(backup), "render": self.render()}
