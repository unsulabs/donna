#!/usr/bin/env python3
"""Explicit NEW-vault utility; not a migration/repair operation.

Default is a dry run. --apply publishes a staged starter into a new destination.
Existing directories, symlinks and force overwrites are rejected.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from donna_runtime.common import DonnaError, reject_symlink, pretty


def scaffold(vault: Path, starter: Path, *, apply=False):
    vault=vault.expanduser().absolute(); starter=starter.expanduser().absolute()
    reject_symlink(vault); reject_symlink(starter)
    if vault.exists():
        raise DonnaError('Existing vault must be attached with donna_ops init, never scaffolded')
    if not vault.parent.is_dir() or not starter.is_dir():
        raise DonnaError('Parent directory and reviewed starter must exist')
    files=[]
    for path in sorted(starter.rglob('*')):
        reject_symlink(path)
        if path.is_file(): files.append(path.relative_to(starter).as_posix())
    if not files: raise DonnaError('Starter is empty')
    if apply:
        stage=Path(tempfile.mkdtemp(prefix='.donna-new-vault-',dir=vault.parent))
        try:
            for name in files:
                dest=stage/name; dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(starter/name,dest)
            # Reserve destination exclusively; do not replace concurrent user content.
            vault.mkdir(mode=0o700)
            try:
                for name in files:
                    dest=vault/name; dest.parent.mkdir(parents=True,exist_ok=True)
                    with dest.open('xb') as output: output.write((stage/name).read_bytes())
            except Exception:
                # Keep partial files for diagnosis rather than deleting possible user edits.
                raise DonnaError('New-vault copy interrupted; preserve destination and inspect before retry')
        finally:
            shutil.rmtree(stage)
    return {'applied':apply,'new_vault':str(vault),'files':files}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vault',required=True)
    p.add_argument('--starter',default=str(Path(__file__).resolve().parent.parent/'assets/vault-starter'))
    p.add_argument('--apply',action='store_true')
    p.add_argument('--dry-run',action='store_true',help='Explicit default; incompatible with --apply')
    args=p.parse_args(argv)
    try:
        if args.apply and args.dry_run: raise DonnaError('Choose --apply or --dry-run')
        print(pretty(scaffold(Path(args.vault),Path(args.starter),apply=args.apply)),end='')
        return 0
    except (DonnaError,OSError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}),file=sys.stderr);return 2

if __name__=='__main__': raise SystemExit(main())
