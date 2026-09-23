#!/usr/bin/env python3
"""Read-only model drift check. This version never rewrites a user's model.

Legacy auto-restore behavior is removed. Adopt only after pausing/reviewing its old
cron. Model/provider edits belong to an explicit native Hermes configuration action.
"""
import argparse
import json
import os
import subprocess
import sys


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', default=os.environ.get('DONNA_PROFILE'))
    p.add_argument('--expect',action='append',default=[])
    args=p.parse_args(argv)
    wanted={}
    try:
        for item in args.expect:
            key,sep,value=item.partition('=')
            if not sep or key not in {'model.provider','model.default'} or not value:
                raise ValueError('Only explicit model.provider/model.default expectations are supported')
            wanted[key]=value
        for suffix,key in [('MODEL_PROVIDER','model.provider'),('MODEL_DEFAULT','model.default')]:
            if os.environ.get('DONNA_EXPECT_'+suffix): wanted.setdefault(key,os.environ['DONNA_EXPECT_'+suffix])
        if not wanted: return 0
        if not args.profile: raise ValueError('An explicit profile is required')
        drift=[]
        for key,value in wanted.items():
            result=subprocess.run(['hermes','-p',args.profile,'config','get',key],stdin=subprocess.DEVNULL,
                                  capture_output=True,text=True,timeout=30,check=False)
            if result.returncode: raise ValueError('Native config read failed; no values copied to report')
            if result.stdout.strip()!=value: drift.append(key)
        if drift:
            print(json.dumps({'drift':drift,'changed':False,'action':'Review locally; no automatic provider/model restore'}))
            return 3
        return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print(json.dumps({'ok':False,'error':type(exc).__name__,'changed':False}),file=sys.stderr);return 2

if __name__=='__main__': raise SystemExit(main())
