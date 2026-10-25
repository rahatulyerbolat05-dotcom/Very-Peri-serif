#!/usr/bin/env python3
"""Install this portable skill into an explicit project; preserve differing existing copies."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]


def files(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def install(project,client='both',replace=False):
    project=Path(project).resolve();project.mkdir(parents=True,exist_ok=True)
    expected=files(ROOT);result=[]
    for folder in (['.agents','.claude'] if client=='both' else ['.agents' if client=='codex' else '.claude']):
        dest=project/folder/'skills'/'ofl-cyrillic-extension';backup=None
        if dest.resolve()==ROOT:
            result.append({'client':folder,'path':str(dest),'status':'already_current'});continue
        if dest.parent.resolve().is_relative_to(ROOT):raise ValueError('Destination must not be inside the source skill')
        if dest.exists() or dest.is_symlink():
            if dest.is_dir() and files(dest)==expected:
                result.append({'client':folder,'path':str(dest),'status':'already_current'});continue
            if not replace:raise ValueError('Different existing skill; use --replace to preserve it in a backup: '+str(dest))
            stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            backup=dest.with_name(dest.name+'.backup-'+stamp);n=1
            while backup.exists() or backup.is_symlink():backup=dest.with_name(dest.name+'.backup-'+stamp+'-'+str(n));n+=1
            dest.rename(backup)
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            shutil.copytree(ROOT,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            if files(dest)!=expected:raise ValueError('Installed copy did not match the source manifest')
        except BaseException:
            if dest.exists():shutil.rmtree(dest)
            if backup:backup.rename(dest)
            raise
        result.append({'client':folder,'path':str(dest),'status':'installed','backup':str(backup) if backup else None})
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project',type=Path,required=True);ap.add_argument('--client',choices=('codex','claude','both'),default='both');ap.add_argument('--replace',action='store_true');args=ap.parse_args()
    try:r=install(args.project,args.client,args.replace)
    except ValueError as e:ap.error(str(e))
    print(json.dumps(r,ensure_ascii=False))


if __name__=='__main__':main()
