#!/usr/bin/env python3
"""Validate and reproducibly package the standalone Cyrillic-extension skill."""
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT=Path('skills/ofl-cyrillic-extension')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def source_files():
    return {str(p.relative_to(ROOT)):p.read_bytes() for p in sorted(ROOT.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='bundle-manifest.json'}


def main():
    cfg=json.loads((ROOT/'skill.json').read_text());files=source_files()
    assert re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',cfg['name']) and len(cfg['name'])<=64
    assert re.fullmatch(r'\d+\.\d+\.\d+',cfg['version'])
    for name in ('SKILL.md','README.md','LICENSE.txt','NOTICE.md','scripts/font_probe.py','references/workflow.ru.md','tests/test_portable_skill.py'):assert name in files,name
    front=(ROOT/'SKILL.md').read_text().split('---',2)[1]
    assert re.search(r'^name: '+re.escape(cfg['name'])+r'$',front,re.M) and 'description: >-' in front
    for name,raw in files.items():
        assert Path(name).suffix.lower() not in ('.ttf','.otf','.woff','.woff2','.ttc'),name
        if name.endswith('.py'):ast.parse(raw,filename=name)
        if name.endswith('.md'):
            for match in re.findall(r'\[[^\]]*\]\(([^)]+)\)',raw.decode()):
                dest=match.split('#',1)[0]
                if not dest or re.match(r'[a-z]+:',dest):continue
                assert (ROOT/Path(name).parent/dest).resolve().is_file(),(name,dest)
    assert files['references/workflow.ru.md']==Path('docs/cyrillic-extension-playbook.md').read_bytes(),'Standalone instruction drift'
    manifest={'schema':1,'name':cfg['name'],'version':cfg['version'],'date':cfg['release_date'],'files':{name:sha(raw) for name,raw in files.items()},'note':'Manifest excludes itself; caches and input fonts are never packaged.'}
    raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode()+b'\n';(ROOT/'bundle-manifest.json').write_bytes(raw);files['bundle-manifest.json']=raw
    prefix=cfg['name']+'/';date=tuple(map(int,cfg['release_date'].split('-')))+(0,0,0);buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(prefix+name,date_time=date);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,raw)
    content=buffer.getvalue();dest=Path('dist/skills')/(cfg['name']+'-'+cfg['version']+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert dest.read_bytes()==content,'Published skill archive is immutable; increment the skill version'
    else:dest.write_bytes(content)
    with zipfile.ZipFile(dest) as archive:
        assert archive.testzip() is None
        assert all(archive.read(prefix+n)==raw for n,raw in files.items())
        loaded=json.loads(archive.read(prefix+'bundle-manifest.json'))
        assert all(sha(archive.read(prefix+n))==digest for n,digest in loaded['files'].items())
    dest.with_suffix('.sha256').write_text(sha(content)+'  '+dest.name+'\n')
    print(json.dumps({'archive':str(dest),'sha256':sha(content),'files':len(files),'bytes':len(content)},ensure_ascii=False))


if __name__=='__main__':main()
