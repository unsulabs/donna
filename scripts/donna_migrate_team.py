#!/usr/bin/env python3
"""One-time, explicit legacy .team migration. Never preserve unproven readiness.

JSON input uses stdlib. Legacy YAML optionally requires PyYAML in the selected
interpreter (Hermes may already have it); this script does not install anything.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from donna_runtime.common import DonnaError, atomic_write, pretty, reject_symlink
from donna_runtime.models import member


def convert(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('members'), list):
        raise DonnaError('Legacy roster needs a members list')
    output = []
    warnings = []
    for entry in raw['members']:
        if not isinstance(entry, dict):
            raise DonnaError('Invalid legacy member')
        identifier = entry.get('id')
        if identifier == raw.get('orchestrator', 'donna'):
            warnings.append('Coordinator omitted from specialist roster; Donna remains coordinator')
            continue
        converted = {'id': identifier, 'profile': entry.get('profile', identifier),
                     'role': entry.get('role', ''), 'capabilities': entry.get('capabilities', []),
                     'skills': [], 'doctrine_paths': entry.get('doctrine_paths', []),
                     'status': 'disabled' if entry.get('status') == 'disabled' else 'configured',
                     'verified_at': None, 'checks': {}}
        output.append(member(converted))
        warnings.append(str(identifier) + ': capabilities and exact installed skills require review; readiness reset')
    if len({m['id'] for m in output}) != len(output):
        raise DonnaError('Duplicate member IDs')
    return {'schema_version': 2, 'members': output}, warnings


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy', required=True)
    p.add_argument('--out', required=True, help='NEW private file; never overwrites the live .team')
    p.add_argument('--apply', action='store_true')
    args=p.parse_args(argv)
    try:
        source=Path(args.legacy).expanduser().absolute(); dest=Path(args.out).expanduser().absolute()
        reject_symlink(source); reject_symlink(dest)
        if source == dest or dest.exists():
            raise DonnaError('Destination must be a different new file')
        content=source.read_text(encoding='utf-8')
        try:
            raw=json.loads(content)
        except ValueError:
            try:
                import yaml
            except ImportError as exc:
                raise DonnaError('Legacy YAML needs PyYAML; use a reviewed interpreter with that dependency. Nothing changed.') from exc
            try:
                raw=yaml.safe_load(content)
            except yaml.YAMLError as exc:
                raise DonnaError('Invalid legacy YAML') from exc
        result,warnings=convert(raw)
        if args.apply:
            atomic_write(dest,pretty(result),create_only=True)
        print(pretty({'applied':args.apply,'candidate':result,'warnings':warnings}),end='')
        return 0
    except (DonnaError,OSError,UnicodeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
