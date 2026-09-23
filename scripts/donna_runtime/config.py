"""Donna-owned configuration; deliberately separate from Hermes config.yaml."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .common import DonnaError, absolute, atomic_write, number, pretty, read_json, relative, slug, text


@dataclass(frozen=True)
class Config:
    source: Path
    instance_id: str
    profile: str
    profile_home: Path
    vault: Path
    state_dir: Path
    area: Path
    board: str
    timezone: str
    human_capacity_hours: float | None
    hermes_command: tuple[str, ...]
    workspace_roots: tuple[Path, ...] = ()
    max_dispatch_per_run: int = 4
    max_sync_per_run: int = 40
    native_timeout: int = 30
    max_transport_attempts: int = 3
    max_rework: int = 2
    max_wakes: int = 3
    lease_seconds: int = 900
    readiness_days: int = 30
    native_max_runtime: str = "30m"
    native_max_retries: int = 2

    @property
    def projection_root(self) -> Path:
        return self.vault / self.area

    @classmethod
    def load(cls, filename: str | Path | None = None) -> "Config":
        if filename is None:
            selected = os.environ.get("DONNA_OPS_CONFIG")
            if not selected:
                home = os.environ.get("HERMES_HOME")
                if not home:
                    raise DonnaError("Set --config or DONNA_OPS_CONFIG; no default-profile guess")
                selected = str(Path(home) / "donna-ops.json")
            filename = selected
        path = Path(filename).expanduser().absolute()
        raw = read_json(path)
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise DonnaError("Unsupported Donna configuration schema")
        allowed = {"schema_version", "instance_id", "profile", "profile_home", "vault", "state_dir", "area", "board", "timezone", "human_capacity_hours", "hermes_command", "limits", "workspace_roots"}
        if set(raw) - allowed:
            raise DonnaError("Unknown Donna configuration keys; review rather than ignoring them")
        try:
            uuid.UUID(raw["instance_id"])
            profile = slug(raw["profile"], "profile")
            home = absolute(raw["profile_home"], "profile_home", exists=True)
            vault = absolute(raw["vault"], "vault", exists=True)
            state = absolute(raw["state_dir"], "state_dir")
            area = relative(raw["area"], "area")
            board = slug(raw["board"], "board")
            zone = text(raw["timezone"], "timezone")
            ZoneInfo(zone)
        except (KeyError, ValueError, ZoneInfoNotFoundError) as exc:
            raise DonnaError("Missing/invalid configuration identity, path or timezone") from exc
        if state == vault or state.is_relative_to(vault) or vault.is_relative_to(state):
            raise DonnaError("state_dir and vault must be disjoint: operational data stays outside the vault")
        if not state.is_relative_to(home):
            raise DonnaError("state_dir must be inside the explicitly selected profile_home")
        capacity = raw.get("human_capacity_hours")
        if capacity is not None:
            capacity = number(capacity, "human_capacity_hours", 0, 168)
        command = raw.get("hermes_command", ["hermes"])
        if not isinstance(command, list) or not command or len(command) > 8:
            raise DonnaError("hermes_command must be a short argv list from trusted local configuration")
        command = tuple(text(s, "hermes_command argument", maximum=1000) for s in command)
        limits = raw.get("limits", {})
        if not isinstance(limits, dict):
            raise DonnaError("limits must be an object")
        ranges = {"max_dispatch_per_run": (1, 20), "max_sync_per_run": (1, 200), "native_timeout": (1, 120),
                  "max_transport_attempts": (1, 10), "max_rework": (0, 10), "max_wakes": (1, 10),
                  "lease_seconds": (30, 7200), "readiness_days": (1, 365), "native_max_retries": (1, 10)}
        if set(limits) - (set(ranges) | {"native_max_runtime"}):
            raise DonnaError("Unknown operational limit")
        for name, (lo, hi) in ranges.items():
            if name in limits:
                number(limits[name], name, lo, hi)
                if type(limits[name]) is not int:
                    raise DonnaError(f"{name} must be an integer")
        if "native_max_runtime" in limits:
            import re
            if not re.fullmatch(r"[1-9][0-9]{0,4}[smhd]?", str(limits["native_max_runtime"])):
                raise DonnaError("Invalid native_max_runtime")
        roots = raw.get("workspace_roots", [])
        if not isinstance(roots, list):
            raise DonnaError("workspace_roots must be a list of explicitly approved directories")
        roots = tuple(absolute(r, "workspace_root", exists=True) for r in roots)
        return cls(path, raw["instance_id"], profile, home, vault, state, area, board, zone, capacity, command, workspace_roots=roots, **limits)


def initialize(path: Path, *, profile: str, profile_home: Path, vault: Path,
               area: str, board: str, zone: str, capacity: float | None,
               apply: bool = False) -> dict[str, Any]:
    raw = {"schema_version": 1, "instance_id": str(uuid.uuid4()), "profile": profile,
           "profile_home": str(profile_home), "vault": str(vault),
           "state_dir": str(profile_home / "donna-state"), "area": area, "board": board,
           "timezone": zone, "human_capacity_hours": capacity, "hermes_command": ["hermes"], "limits": {}}
    # Validate without touching the real destination or vault.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        probe = Path(td) / "config.json"
        probe.write_text(pretty(raw), encoding="utf-8")
        Config.load(probe)
    if apply:
        atomic_write(path, pretty(raw), create_only=True)
    return {"applied": apply, "config": raw, "path": str(path),
            "note": "Only configuration created. No vault scaffold, account, model, service or global config changed."}
