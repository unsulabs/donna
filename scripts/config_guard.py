#!/usr/bin/env python3
"""Optional config guardian for a Donna profile.

Detects drift on selected config keys (e.g. desktop login overwriting model)
and restores expected values via `hermes config set` (never by editing YAML).

No secrets. Expected values come from env or CLI flags — nothing hardcoded
to a specific provider.

Silent when healthy (empty stdout → no cron delivery noise).
Prints a short report when drift is fixed or verification fails.

Examples:
  DONNA_EXPECT_MODEL_PROVIDER=<your-provider> \\
  DONNA_EXPECT_MODEL_DEFAULT=<your-model> \\
  python3 scripts/config_guard.py --profile donna

  python3 scripts/config_guard.py --profile donna \\
    --expect model.provider=<provider> --expect model.default=<model-id>
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def hermes_bin() -> str:
    return shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")


def run(profile: str, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [hermes_bin(), "--profile", profile, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def get_key(profile: str, key: str) -> str | None:
    try:
        proc = run(profile, ["config", "get", key])
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def set_key(profile: str, key: str, value: str) -> bool:
    proc = run(profile, ["config", "set", key, value])
    return proc.returncode == 0


def parse_expects(items: list[str], env_prefix: str = "DONNA_EXPECT_") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for raw in items:
        if "=" not in raw:
            raise SystemExit(f"bad --expect {raw!r}; use key=value")
        k, v = raw.split("=", 1)
        out.append((k.strip(), v.strip()))
    # env: DONNA_EXPECT_MODEL_PROVIDER → model.provider
    for ek, ev in os.environ.items():
        if not ek.startswith(env_prefix) or not ev:
            continue
        leaf = ek[len(env_prefix) :].lower()
        if leaf == "model_provider":
            key = "model.provider"
        elif leaf == "model_default":
            key = "model.default"
        else:
            key = leaf.replace("_", ".")
        out.append((key, ev))
    # dedupe keeping last
    merged: dict[str, str] = {}
    for k, v in out:
        merged[k] = v
    return list(merged.items())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=os.environ.get("DONNA_PROFILE", "donna"))
    ap.add_argument("--expect", action="append", default=[], help="key=value (repeatable)")
    args = ap.parse_args()

    expects = parse_expects(args.expect)
    if not expects:
        # nothing configured → stay silent
        return 0

    if not hermes_bin():
        print(f"Donna config guard: hermes binary not found; drift NOT checked.")
        return 0

    drift: list[tuple[str, str, str]] = []
    for key, want in expects:
        got = get_key(args.profile, key)
        if got is None:
            print(f"Donna config guard: could not read {key}; drift NOT verified.")
            return 0
        if got != want:
            drift.append((key, got, want))

    if not drift:
        return 0  # silent OK

    lines = ["Donna config guard: drift detected and restore attempted:"]
    for key, got, want in drift:
        ok = set_key(args.profile, key, want)
        back = get_key(args.profile, key)
        status = "restored" if ok and back == want else "FAILED"
        lines.append(f"  - {key}: was {got!r} → want {want!r} [{status}]")
    print("\n".join(lines))
    print(
        "Note: if a long-running gateway process holds old config in memory, "
        "restart it from a shell outside the gateway "
        "(e.g. systemctl --user restart <your-donna-gateway-unit>)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
