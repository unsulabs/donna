"""Narrow public CLI adapter. No HTTP server, SQL access or automatic installs.

Contract: official Hermes Kanban documentation, consulted 2026-09-22.
Raw subprocess output is never copied to errors, logs or notifications.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
from typing import Any

from .common import NativeError, slug
from .config import Config
from .models import NATIVE_STATES


class Hermes:
    def __init__(self, config: Config):
        self.config = config

    def run(self, arguments: list[str], *, json_output: bool = True) -> Any:
        command = [*self.config.hermes_command, "-p", self.config.profile, *arguments]
        env = os.environ.copy()
        # Explicit profile selector wins; keep worker ownership variables intact.
        env["HERMES_HOME"] = str(self.config.profile_home)
        env["NO_COLOR"] = "1"
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                        env=env, shell=False, start_new_session=(os.name == "posix"))
            except OSError as exc:
                raise NativeError("Hermes executable could not be started; check trusted hermes_command") from exc
            try:
                code = proc.wait(timeout=self.config.native_timeout)
            except subprocess.TimeoutExpired as exc:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.wait()
                raise NativeError("Hermes CLI timed out; outcome may be unknown, retry only with the same key") from exc
            if code != 0:
                raise NativeError(f"Hermes CLI exited {code}; inspect locally, no raw output included")
            if out.tell() > 2_000_000:
                raise NativeError("Hermes output exceeds the 2 MB contract limit")
            out.seek(0)
            try:
                content = out.read().decode("utf-8")
                return json.loads(content) if json_output else content
            except (UnicodeError, ValueError) as exc:
                raise NativeError("Hermes returned non-JSON/invalid encoding; adapter fails closed") from exc

    def kanban(self, arguments: list[str], *, json_output: bool = True) -> Any:
        return self.run(["kanban", "--board", self.config.board, *arguments], json_output=json_output)

    @staticmethod
    def identifier(raw: Any) -> str:
        if not isinstance(raw, dict):
            raise NativeError("Create response must be an object")
        candidates = [raw[k] for k in ("id", "task_id") if raw.get(k)]
        if isinstance(raw.get("task"), dict):
            candidates.extend(raw["task"][k] for k in ("id", "task_id") if raw["task"].get(k))
        if not candidates or any(not isinstance(v, str) for v in candidates) or len(set(candidates)) != 1:
            raise NativeError("Ambiguous/missing native card id")
        try:
            return slug(candidates[0], "native card id")
        except Exception as exc:
            raise NativeError("Invalid native card id") from exc

    def create(self, payload: dict[str, Any]) -> str:
        if os.environ.get("HERMES_KANBAN_TASK"):
            raise NativeError("Coordinator adapter cannot create from an inherited worker scope; use native worker tools")
        args = ["create", payload["title"], "--body", payload["body"], "--assignee", payload["assignee"],
                "--tenant", payload["tenant"], "--workspace", payload["workspace"],
                "--idempotency-key", payload["idempotency_key"],
                "--max-runtime", self.config.native_max_runtime,
                "--max-retries", str(self.config.native_max_retries), "--json"]
        for parent in payload["parents"]:
            args.extend(["--parent", parent])
        for skill in payload["skills"]:
            args.extend(["--skill", skill])
        return self.identifier(self.kanban(args))

    def show(self, card_id: str) -> dict[str, Any]:
        slug(card_id, "card_id")
        raw = self.kanban(["show", card_id, "--json"])
        if not isinstance(raw, dict):
            raise NativeError("show response must be an object")
        task = raw.get("task", raw)
        if not isinstance(task, dict):
            raise NativeError("Invalid native task envelope")
        got = self.identifier(raw)
        if got != card_id:
            raise NativeError("Native response belongs to a different card")
        status = task.get("status")
        if status not in NATIVE_STATES:
            raise NativeError("Unknown/missing native status; no inferred completion")
        tenant = task.get("tenant")
        if tenant is not None and not isinstance(tenant, str):
            raise NativeError("Invalid native tenant")
        # Stable handoff data, not changing poll timestamps; event-dedup uses this.
        return {"id": got, "status": status, "tenant": tenant, "assignee": task.get("assignee"),
                "result": task.get("result"), "updated_at": task.get("updated_at"),
                "run_id": task.get("run_id", task.get("current_run_id")),
                "last_failure_error": bool(task.get("last_failure_error"))}

    def profiles(self) -> set[str]:
        raw = self.kanban(["assignees", "--json"])
        if isinstance(raw, dict):
            raw = raw.get("assignees", raw.get("profiles"))
        if not isinstance(raw, list):
            raise NativeError("Unknown assignees response schema; verify adapter against the installed version")
        names: set[str] = set()
        for item in raw:
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                name = item.get("profile", item.get("name", item.get("assignee")))
            else:
                raise NativeError("Invalid assignees entry")
            if not isinstance(name, str):
                raise NativeError("Assignees entry lacks profile/name")
            try:
                names.add(slug(name, "native profile"))
            except Exception as exc:
                raise NativeError("Invalid native profile name") from exc
        return names

    def doctor(self) -> dict[str, Any]:
        result: dict[str, Any] = {"contract": "documented CLI; live version checked here", "ok": True, "checks": []}
        checks = [(["--version"], None),
                  (["kanban", "create", "--help"], ["--idempotency-key", "--json", "--max-runtime", "--max-retries", "--parent"]),
                  (["kanban", "show", "--help"], ["--json"]),
                  (["cron", "create", "--help"], ["--skill", "--script"])]
        for args, options in checks:
            try:
                output = self.run(args, json_output=False)
                if options and any(option not in output for option in options):
                    raise NativeError("Required option absent from native CLI help")
                item = {"command": " ".join(args), "ok": True}
                if args == ["--version"]:
                    item["version"] = output.strip()[:200]
                result["checks"].append(item)
            except NativeError as exc:
                result["ok"] = False
                result["checks"].append({"command": " ".join(args), "ok": False, "error": str(exc)})
        try:
            result["profiles"] = sorted(self.profiles())
            result["diagnostics"] = self.kanban(["diagnostics", "--json"])
        except NativeError as exc:
            result["ok"] = False
            result["checks"].append({"command": "native schema", "ok": False, "error": str(exc)})
        return result
