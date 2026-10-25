#!/usr/bin/env python3
"""Verify frozen base glyphs against 1.112; ss10 has a separate full-font gate."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from italic_el_alternate import legacy_font as TTFont  # base-glyph regression; ss10 has its own gate
from exact_node_reduction import canonical_outline, geometry_fingerprint


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='fonts');args=ap.parse_args()
    manifest=json.loads(Path('data/node-reduction/manifest.json').read_text())
    cfg=json.loads(Path('data/params.json').read_text())['regular_release']
    checks={};stats={}
    def ck(label,value):
        checks[label]=bool(value)
        if not value:raise AssertionError(label)
    for style,rows in manifest['styles'].items():
        root=Path(args.root)
        current_path=root/'ttf'/f'VeryPeriSerif-{style}.ttf' if root.name=='fonts' else root/f'VeryPeriSerif-{style}.ttf'
        old=TTFont(io.BytesIO(subprocess.check_output(['git','show',manifest['baseline_commit']+f':fonts/ttf/VeryPeriSerif-{style}.ttf'])))
        new=TTFont(current_path);changed=[];removed=0
        ck(style+' glyph order',old.getGlyphOrder()==new.getGlyphOrder())
        for tag in old.keys():
            if tag not in ('GlyphOrder','head','name','glyf','loca','maxp'):
                ck(style+' unchanged table '+tag,old.getTableData(tag)==new.getTableData(tag))
        for name in old.getGlyphOrder():
            a,b=old['glyf'][name],new['glyf'][name]
            if a.compile(old['glyf'])!=b.compile(new['glyf']):
                changed.append(name)
                ck(style+' exact path '+name,canonical_outline(old,name)==canonical_outline(new,name))
                ck(style+' point count '+name,len(a.coordinates)-len(b.coordinates)==rows['glyphs'][name]['points_before']-rows['glyphs'][name]['points_after'])
                ck(style+' no hinted simplification '+name,not a.program.getBytecode())
                ck(style+' bounds '+name,all(getattr(a,k)==getattr(b,k) for k in ('xMin','yMin','xMax','yMax')))
                ck(style+' source hash '+name,geometry_fingerprint(new,name)==rows['glyphs'][name]['geometry_sha256'])
                removed+=len(a.coordinates)-len(b.coordinates)
        ck(style+' exact changed set',set(changed)==set(rows['glyphs']))
        ck(style+' exact removed count',removed==rows['points_removed'])
        # Components inherit the same path despite changes in base encoding.
        for name in rows['cff_only_dependencies']:
            ck(style+' exact composite '+name,canonical_outline(old,name)==canonical_outline(new,name))
        before=TTFont(io.BytesIO(subprocess.check_output(['git','show',manifest['baseline_commit']+f':fonts/otf/VeryPeriSerif-{style}.otf'])))
        otf_path=root/'otf'/f'VeryPeriSerif-{style}.otf' if root.name=='fonts' else root/f'VeryPeriSerif-{style}.otf'
        after=TTFont(otf_path)
        ca,cb=[f['CFF '].cff.topDictIndex[0].CharStrings for f in (before,after)]
        for name in before.getGlyphOrder():
            ca[name].decompile();cb[name].decompile()
            ck(style+' exact accepted CFF '+name,ca[name].program==cb[name].program)
        for fmt,sub in (('ttf','ttf'),('otf','otf'),('woff2','webfonts')):
            p=root/sub/f'VeryPeriSerif-{style}.{fmt}' if root.name=='fonts' else root/f'VeryPeriSerif-{style}.{fmt}'
            f=TTFont(p);n=f['name']
            ck(style+' '+fmt+' full designer',cfg['cyrillic_author'] in n.getDebugName(9))
            ck(style+' '+fmt+' full copyright',cfg['copyright'] in n.getDebugName(0))
            ck(style+' '+fmt+' manufacturer',n.getDebugName(8)==cfg['manufacturer'])
            ck(style+' '+fmt+' OFL',n.getDebugName(14)=='https://openfontlicense.org' and f['OS/2'].fsType==0)
            ck(style+' '+fmt+' version',n.getDebugName(5)=='Version '+cfg['version'])
        stats[style]={'glyphs':len(changed),'points_removed':removed,'ttf_sha256':hashlib.sha256(current_path.read_bytes()).hexdigest(),'cff_programs_unchanged':len(before.getGlyphOrder())}
    report={'version':cfg['version'],'baseline_commit':manifest['baseline_commit'],'passed':len(checks),'failed':0,'styles':stats,
            'scope':'Frozen base glyphs: exact geometric preservation, metrics, hinting, shaping and metadata. Added ss10 is independently checked by check_italic_el_alternate.py; not universal artistic acceptance.'}
    Path('docs/qa/final-freeze.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
