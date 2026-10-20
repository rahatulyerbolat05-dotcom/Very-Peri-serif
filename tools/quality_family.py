#!/usr/bin/env python3
"""Fresh offline FontBakery Universal and Hyperglot checks of both final TTFs."""
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from hyperglot.checker import FontChecker


def main():
    root=Path('build/release');root.mkdir(parents=True,exist_ok=True)
    fonts=[root/f'VeryPeriSerif-{s}.ttf' for s in ('Regular','Italic')]
    report=root/'fontbakery-universal.json'
    report.unlink(missing_ok=True)
    with (root/'fontbakery-universal.log').open('w') as log:
        result=subprocess.run([sys.executable,'-m','fontbakery','check-universal','--skip-network',
                               '--no-progress','--no-colors','--json',str(report),*map(str,fonts)],
                              stdout=log,stderr=subprocess.STDOUT)
    if not report.exists():
        raise RuntimeError('FontBakery did not produce a current report; see '+str(log.name))
    fb=json.loads(report.read_text())
    if result.returncode or fb['result'].get('FAIL',0) or fb['result'].get('ERROR',0):
        raise RuntimeError('FontBakery failed: '+str(fb['result']))
    warnings=[{'font':c.get('filename'),'check':c['key'][1],
               'messages':[l['message'] for l in c['logs'] if l['status']=='WARN']}
              for section in fb['sections'] for c in section['checks']
              if any(l['status']=='WARN' for l in c['logs'])]
    languages={}
    for path in fonts:
        checker=FontChecker(str(path))
        languages[path.name]={iso:bool(checker.supports_language(iso)) for iso in ('rus','kaz')}
        assert all(languages[path.name].values()),languages
    summary={'fonts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fonts},
             'tools':{m:importlib.metadata.version(m) for m in ('fonttools','fontbakery','hyperglot','uharfbuzz')},
             'fontbakery_profile':'universal','network_checks':'SKIPPED','fontbakery':fb['result'],
             'warnings':warnings,'hyperglot_primary_with_shaping':languages,'failed':0}
    (root/'quality-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
