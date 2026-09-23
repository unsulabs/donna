#!/usr/bin/env python3
"""Apply the reviewed source overlay to a clean Git feature branch.

Dry-run unless --apply. No network, push, checkout, reset, credential access or live
profile installation. Manifest hashes detect corruption/drift, not authenticity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


class ApplyError(Exception):
    pass


def git(repo: Path, *args: str) -> str:
    result=subprocess.run(['git','-C',str(repo),*args],stdin=subprocess.DEVNULL,
                          capture_output=True,text=True,timeout=30)
    if result.returncode:
        raise ApplyError('Git check failed: '+args[0])
    return result.stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_hash(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def checked_path(root: Path, relative: str) -> Path:
    if not isinstance(relative,str) or '\\' in relative or '\x00' in relative:
        raise ApplyError('Invalid manifest path')
    path=PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts or path.as_posix()!=relative or '.git' in path.parts:
        raise ApplyError('Manifest path escapes permitted tree')
    result=root.joinpath(*path.parts)
    for current in [result,*result.parents]:
        if current.is_symlink(): raise ApplyError('Symlink path rejected: '+relative)
        if current==root:break
    return result


def replace(path: Path, content: bytes, mode: int):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.donna-overlay-',dir=path.parent)
    tmp=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(content);stream.flush();os.fsync(stream.fileno())
        os.chmod(tmp,mode)
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)


def apply_bundle(bundle: Path, repo: Path, *, apply=False):
    bundle=bundle.resolve();repo=repo.resolve()
    manifest=json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=1 or not isinstance(manifest.get('files'),list):
        raise ApplyError('Unknown manifest schema')
    if Path(git(repo,'rev-parse','--show-toplevel')).resolve()!=repo:
        raise ApplyError('Select the repository root')
    if git(repo,'rev-parse','HEAD')!=manifest['base_commit']:
        raise ApplyError('HEAD differs from audited base. Apply in a separate worktree at the base, then review/merge; no force overwrite.')
    branch=git(repo,'symbolic-ref','--short','HEAD')
    if apply and branch in {'main','master'}:
        raise ApplyError('Create a feature branch before --apply')
    if git(repo,'status','--porcelain','--untracked-files=all'):
        raise ApplyError('Working tree must be clean; preserve existing work separately, never reset it')
    seen=set(); prepared=[]
    for item in manifest['files']:
        name=item['path']
        if name in seen: raise ApplyError('Duplicate manifest path')
        seen.add(name)
        src=checked_path(bundle/'overlay',name);dest=checked_path(repo,name)
        if not src.is_file():raise ApplyError('Missing source: '+name)
        data=src.read_bytes()
        if sha256(data)!=item['sha256']:raise ApplyError('Source integrity failed: '+name)
        expected=item.get('base_blob')
        if dest.exists() and not dest.is_file():raise ApplyError('Destination is not a file: '+name)
        previous=dest.read_bytes() if dest.is_file() else None
        if expected:
            if previous is None or blob_hash(previous)!=expected:
                raise ApplyError('Preimage mismatch: '+name)
        elif previous is not None:
            raise ApplyError('New path collides with an existing file: '+name)
        mode=item.get('mode',0o644)
        if mode not in {0o644,0o755}:raise ApplyError('Invalid mode')
        prepared.append((name,dest,data,previous,stat.S_IMODE(dest.stat().st_mode) if previous is not None else None,mode))
    actual={p.relative_to(bundle/'overlay').as_posix() for p in (bundle/'overlay').rglob('*') if p.is_file()}
    if actual!=seen:raise ApplyError('Overlay contains unmanifested or missing files')
    changed=[]
    if apply:
        try:
            for name,dest,data,previous,oldmode,mode in prepared:
                now=dest.read_bytes() if dest.exists() else None
                if now!=previous:raise ApplyError('Concurrent file change: '+name)
                checked_path(repo,name)
                replace(dest,data,mode)
                changed.append((dest,data,previous,oldmode))
            git(repo,'diff','--check')
        except Exception as exc:
            conflicts=[]
            for dest,ours,previous,oldmode in reversed(changed):
                if not dest.is_file() or dest.read_bytes()!=ours:
                    conflicts.append(str(dest.relative_to(repo)));continue
                if previous is None:dest.unlink()
                else:replace(dest,previous,oldmode)
            if conflicts:raise ApplyError('Apply failed; concurrent edits preserved for manual reconciliation: '+', '.join(conflicts)) from exc
            raise ApplyError('Apply failed; written files rolled back (empty new directories may remain)') from exc
    return {'applied':apply,'base_commit':manifest['base_commit'],'branch':branch,'files':len(prepared),
            'changes':[{'path':name,'action':'replace' if previous is not None else 'add'} for name,_,_,previous,_,_ in prepared],
            'next':'Review git diff, run tests, perform live acceptance on staging. No commit or push was performed.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',required=True)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args(argv)
    try:
        print(json.dumps(apply_bundle(Path(__file__).resolve().parent,Path(args.repo),apply=args.apply),ensure_ascii=False,indent=2))
        return 0
    except (ApplyError,OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
