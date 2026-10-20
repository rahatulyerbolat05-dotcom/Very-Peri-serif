#!/usr/bin/env python3
"""Keep the selected rounded de; shorten only its overactive lower loop.

The previous source remains untouched. The smooth displacement is zero above
-10 and +30 at -280, with zero derivative at both ends. Bowl, width, terminals'
horizontal proportions and printed ss07 stay unchanged.
"""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.pens.recordingPen import RecordingPen
from alphabet_sheet import source_items
from sketchlib import write_glif
from build_draft_font import load


def main():
    cfg_path=Path('data/alphabet.json');cfg=json.loads(cfg_path.read_text())
    out=Path('data/premium-regular');out.mkdir(exist_ok=True)
    entry=cfg['codex']['д']
    selected=source_items('д',cfg)[0]['path']
    if selected.startswith(str(out)):
        previous=json.loads((out/'manifest.json').read_text())['source']
    else:previous=selected
    design=json.loads(Path('data/params.json').read_text())['premium_review']['regular_de']
    path,advance=load(previous);rec=RecordingPen();path.draw(rec)
    result=pathops.Path();pen=result.getPen()
    for op,pts in rec.value:
        mapped=[]
        for x,y in pts:
            t=max(0.,min(1.,(design['unchanged_above']-y)/(design['unchanged_above']-design['original_bottom'])))
            mapped.append((x,y+design['tail_displacement']*t*t*(3.-2.*t)))
        getattr(pen,op)(*mapped)
    result=pathops.simplify(result,fix_winding=True,clockwise=True)
    target=out/'uni0434.glif';write_glif(result,'uni0434',advance,0x434,str(target))
    old=entry['variants'][0].copy()
    variant=dict(old,path=str(target),bounds=list(result.bounds),advance=advance,
                 glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                 label='Округлая д: сохранена чаша, нижняя петля до −250',status='selected')
    cfg.setdefault('rejected_drawings',{})['д-before-premium-loop']=entry if selected!=str(target) else cfg['rejected_drawings']['д-before-premium-loop']
    cfg['codex']['д']=dict(entry,variants=[variant],selected=variant['variant'])
    cfg_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    cp=Path('data/context/serif_bl.json');context=json.loads(cp.read_text());context['built_bases']['д']=str(target);cp.write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n')
    manifest={'source':previous,'source_sha256':hashlib.sha256(Path(previous).read_bytes()).hexdigest(),
              'path':str(target),'before_bounds':list(path.bounds),'after_bounds':list(result.bounds),
              'method':__doc__,'printed_ss07':'unchanged','date':'2026-10-20'}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(manifest)


if __name__=='__main__':main()
