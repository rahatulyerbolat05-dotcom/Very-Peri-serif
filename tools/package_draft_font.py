#!/usr/bin/env python3
"""Package the validated desktop/web draft with license and quality evidence."""
import hashlib
import json
import re
from pathlib import Path
import shutil
import sys
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_draft_font import OUT,TTF
import ots


def main():
    digest=hashlib.sha256(TTF.read_bytes()).hexdigest()
    validation=json.loads((OUT/'validation.json').read_text())
    assert validation['ttf_sha256']==digest and validation['failed']==0,'Re-run check_draft_font.py'
    build=Path('build/draft-font');build.mkdir(parents=True,exist_ok=True)
    sanitized=ots.sanitize(str(TTF),str(build/'ots-validated.ttf'),capture_output=True)
    assert sanitized.returncode==0,sanitized.stderr
    quality={'ttf_sha256':digest,'opentype_sanitizer':'PASS',
             'harfbuzz_checks_passed':validation['passed'],'fontbakery_network_checks':'SKIPPED'}
    warning_ids={}
    for kind in ('native','draft'):
        filename=build/f'fontbakery-{kind}.json'
        if filename.exists() and (kind=='native' or filename.stat().st_mtime>=TTF.stat().st_mtime):
            report=json.loads(filename.read_text());quality['fontbakery_'+kind]=report['result']
            warning_ids[kind]=[c['key'][1] for s in report['sections'] for c in s['checks']
                               if any(l['status']=='WARN' for l in c['logs'])]
        else:quality['fontbakery_'+kind]='NOT RUN FOR THIS BUILD'
    if set(warning_ids)=={'native','draft'}:
        quality['additional_warning_checks']=sorted(set(warning_ids['draft'])-set(warning_ids['native']))
    log=build/'hyperglot.log'
    if log.exists() and log.stat().st_mtime>=TTF.stat().st_mtime:
        text=log.read_text()
        section=re.search(r'\d+ languages of Cyrillic script:\n-+\n([^\n]+)',text)
        languages=section.group(1).split(', ') if section else []
        quality['hyperglot_base_primary']={x:x in languages for x in ('Russian','Kazakh')}
    else:quality['hyperglot_base_primary']='NOT RUN FOR THIS BUILD'
    (OUT/'quality-summary.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile('font/README.md',OUT/'README.md')
    archive=Path('dist/VeryPeriSerifDraft-Regular.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
        for file in sorted(OUT.iterdir()):
            if file.is_file():package.write(file,Path('VeryPeriSerifDraft')/file.name)
    with zipfile.ZipFile(archive) as package:assert package.testzip() is None
    print(json.dumps({'archive':str(archive),'ttf':str(TTF),'quality':quality},ensure_ascii=False))


if __name__=='__main__':main()
