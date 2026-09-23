"""Small, dependency-free I/O and validation helpers. Python 3.10+."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


class DonnaError(Exception):
    """An expected, actionable failure safe to expose without subprocess output."""
    code = "invalid_operation"


class Conflict(DonnaError):
    code = "conflict"


class NativeError(DonnaError):
    code = "native_error"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stamp(value: datetime | None = None) -> str:
    return (value or utcnow()).astimezone(timezone.utc).isoformat(timespec="seconds")


def instant(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise DonnaError("Expected an ISO-8601 timestamp with a timezone") from exc
    if result.tzinfo is None:
        raise DonnaError("Timestamp must include a timezone; no implicit UTC")
    return result.astimezone(timezone.utc)


def day(value: str) -> date:
    try:
        result = date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise DonnaError("Expected a YYYY-MM-DD date") from exc
    if result.isoformat() != value:
        raise DonnaError("Date must use YYYY-MM-DD")
    return result


def text(value: Any, name: str, *, maximum: int = 20000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise DonnaError(f"{name} must be nonempty text, at most {maximum} characters")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise DonnaError(f"Control character in {name}")
    return value.strip()


def slug(value: Any, name: str = "id") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise DonnaError(f"{name}: use 1-64 lowercase letters, digits, hyphens or underscores")
    return value


def number(value: Any, name: str, minimum: float = 0, maximum: float = 1e6) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DonnaError(f"{name} must be a number")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise DonnaError(f"{name} must be finite and between {minimum} and {maximum}")
    return float(value)


def enum(value: Any, choices: set[str], name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise DonnaError(f"{name} must be one of {', '.join(sorted(choices))}")
    return value


def strings(value: Any, name: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value) or len(value) > 500:
        raise DonnaError(f"{name} must be a list{' with entries' if nonempty else ''} (max 500)")
    return [text(item, name, maximum=4000) for item in value]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    raw = value if isinstance(value, str) else canonical(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_json(path: Path, *, max_bytes: int = 2_000_000) -> Any:
    reject_symlink(path)
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise DonnaError(f"Missing, nonregular or oversized JSON file: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (ValueError, UnicodeError) as exc:
        raise DonnaError(f"Invalid UTF-8 JSON: {path.name}") from exc


def reject_symlink(path: Path) -> None:
    """Reject symlinks along the explicitly configured write/read path.

    This is a trusted-local-user guard, not a sandbox against malicious races.
    """
    if not path.is_absolute():
        raise DonnaError("An absolute path is required")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise DonnaError(f"Symlink not allowed on managed path: {part.name}")


def absolute(value: Any, name: str, *, exists: bool = False) -> Path:
    path = Path(text(value, name)).expanduser()
    if not path.is_absolute() or ".." in path.parts:
        raise DonnaError(f"{name} must be absolute, without '..'")
    reject_symlink(path)
    if exists and not path.is_dir():
        raise DonnaError(f"{name} must be an existing directory")
    return path


def relative(value: Any, name: str) -> Path:
    raw = text(value, name, maximum=300)
    path = Path(raw)
    if path.is_absolute() or any(p in (".", "..", ".obsidian", ".git") for p in path.parts) or "\\" in raw:
        raise DonnaError(f"Unsafe relative path in {name}")
    if not path.parts or path.as_posix() != raw or raw.startswith("."):
        raise DonnaError(f"Use a normalized visible relative path for {name}")
    return path


def private_dir(path: Path) -> None:
    reject_symlink(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise DonnaError("Expected a directory")
    # Only tighten the directory we own, never the user's parent or vault.
    if os.name == "posix":
        path.chmod(0o700)


def atomic_write(path: Path, content: str, *, expected: str | None = None,
                 create_only: bool = False) -> None:
    """Same-directory atomic replacement, optional optimistic content check.

    A concurrent editor is checked immediately before replace. SQLite serializes
    Donna writers; an unrelated editor does not participate in that lock.
    """
    reject_symlink(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_file():
        raise DonnaError("Refusing to replace a nonregular file")
    if create_only and path.exists():
        raise Conflict(f"File already exists: {path.name}")
    if expected is not None:
        if not path.is_file() or digest(path.read_text(encoding="utf-8")) != expected:
            raise Conflict(f"File changed: {path.name}")
    fd, temp = tempfile.mkstemp(prefix=".donna-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        reject_symlink(path)
        if expected is not None and (not path.is_file() or digest(path.read_text(encoding="utf-8")) != expected):
            raise Conflict(f"Concurrent edit: {path.name}")
        if create_only:
            # link creates a new name atomically and never overwrites a race winner.
            os.link(temp, path)
            os.unlink(temp)
        else:
            os.replace(temp, path)
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
