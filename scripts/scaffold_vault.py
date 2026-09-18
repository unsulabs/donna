#!/usr/bin/env python3
"""Scaffold a Donna PARA Obsidian vault from the distribution starter tree.

Idempotent: never overwrites existing files unless --force.
Does not touch secrets or personal notes outside the starter set.

Usage:
  python3 scripts/scaffold_vault.py --vault /absolute/path/to/Vault
  python3 scripts/scaffold_vault.py --vault ~/Documents/Donna-Vault --force
  python3 scripts/scaffold_vault.py --vault /path --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def copy_tree(src: Path, dst: Path, *, force: bool, dry_run: bool) -> tuple[int, int, int]:
    created = skipped = overwritten = 0
    if not src.is_dir():
        raise SystemExit(f"starter vault missing: {src}")

    for root, dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)
        # skip nothing special beyond walk
        target_dir = dst / rel_root
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            s = Path(root) / name
            t = target_dir / name
            if t.exists() and not force:
                skipped += 1
                continue
            if t.exists() and force:
                overwritten += 1
            else:
                created += 1
            if dry_run:
                action = "overwrite" if t.exists() else "create"
                print(f"  {action}: {t}")
                continue
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, t)
    return created, skipped, overwritten


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", required=True, help="Destination vault directory (absolute or ~)")
    p.add_argument("--starter", default=None, help="Override starter tree path")
    p.add_argument("--force", action="store_true", help="Overwrite existing files")
    p.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = p.parse_args()

    dst = expand(args.vault)
    src = Path(args.starter).resolve() if args.starter else (repo_root() / "assets" / "vault-starter")

    print(f"starter: {src}")
    print(f"vault:   {dst}")
    if args.dry_run:
        print("mode:    dry-run")
    if args.force:
        print("mode:    force overwrite")

    if not args.dry_run:
        dst.mkdir(parents=True, exist_ok=True)

    created, skipped, overwritten = copy_tree(src, dst, force=args.force, dry_run=args.dry_run)
    print(f"done: created={created} skipped={skipped} overwritten={overwritten}")
    if not args.dry_run:
        # light verify
        need = ["Home.md", "MOC.md", "Inbox.md", ".obsidian/app.json", "Resources/Templates/Daily note.md"]
        missing = [n for n in need if not (dst / n).is_file()]
        if missing:
            print("verify FAIL missing:", ", ".join(missing), file=sys.stderr)
            return 1
        print("verify OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
