#!/usr/bin/env python3
"""Russian У gets a diagonal lower branch and hook; Kazakh Ү keeps upright Y."""
import copy,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.pens.recordingPen import RecordingPen
import pathops
from sketchlib import Ref,write_glif
from check_context_classes import test

def main():
    params=json.loads(Path('data/params.json').read_text());d=params['capital_u_revision'];ref=Ref();rec=RecordingPen();ref.gs['y'].draw(rec)
    p=pathops.Path();pen=p.getPen()
    for op,pts in rec.value:
        def mapped(x,y):
            blend=max(0,min(1,(d['transition_top']-y)/d['transition_top']))
            return x,y+d['upper_shift']-d['lower_adjustment']*blend
        getattr(pen,op)(*(mapped(x,y) for x,y in pts))
    assert abs(p.bounds[1]+9)<.01 and p.bounds[3]==720
    out=Path('data/capital-u-revision');out.mkdir(exist_ok=True);target=out/'uni0423.glif';write_glif(p,'uni0423',ref.adv('y'),0x423,str(target))
    cfg=json.loads(Path('data/alphabet.json').read_text());old=cfg['user'].get('У') or cfg['codex']['У']
    if not old['variants'][0]['path'].startswith(str(out)):cfg['rejected_drawings']['У-before-diagonal-revision']=copy.deepcopy(old)
    item=dict(character='У',role='primary',path=str(target),advance=ref.adv('y'),bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='Russian capital U: diagonal lower branch and hook',origin='Codex revision of erroneous Y mapping')
    cfg['user'].pop('У',None);item.update(variant='01',label='Диагональная нижняя ветвь и крючок')
    cfg['codex']['У']=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],origin='Codex',provenance='Native y branches and hook moved to cap zones; original Ү remains native Y',status='revised at author request')
    ctx=json.loads(Path('data/context/serif_bl.json').read_text());ctx['built_bases']['У']=str(target)
    members=ctx['declared_class']['upper'];outside=ctx['expected_not_in_class']
    if 'У' in members:members.remove('У')
    if 'У' in outside:outside.remove('У')
    (members if test(p)[0] else outside).append('У')
    for file,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),item)]:Path(file).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
