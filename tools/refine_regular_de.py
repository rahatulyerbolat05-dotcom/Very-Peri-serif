#!/usr/bin/env python3
"""[РЕШЕНИЕ] Quiet printed Regular д; preserve the previous looped source."""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from sketchlib import SUB,write_glif
from check_context_classes import test,test_top

def main():
    params=json.loads(Path('data/params.json').read_text())
    design=params['regular_de']
    # Explicit new drawing, never a scaled capital Д or a transformed Latin d.
    # Native lowercase stem weight and cap-bar weight; cubic terminal transitions.
    assert design['stem']==params['regular']['stems_hairlines']['n_stem']
    def contour(commands):
        p=pathops.Path();pen=p.getPen()
        for operation,points in commands:getattr(pen,operation)(*(tuple(pt) for pt in points))
        return p
    p=contour(design['outer']);hole=contour(design['counter'])
    p=SUB(p,hole);out=Path('data/regular-de-refinement');out.mkdir(exist_ok=True)
    target=out/'uni0434.glif';write_glif(p,'uni0434',design['advance'],0x434,str(target))
    cfg=json.loads(Path('data/alphabet.json').read_text());old=cfg['codex']['д']
    if old['variants'][0]['path']!=str(target):cfg['rejected_drawings']['д-before-printed-refinement']=copy.deepcopy(old)
    item=dict(path=str(target),variant='01',label='Печатная, короткие ножки',advance=design['advance'],bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='selected')
    cfg['codex']['д']=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Codex; quieter printed form requested by author, 17.10.2026')
    ctx=json.loads(Path('data/context/serif_bl.json').read_text());ctx['built_bases']['д']=str(target)
    for rule,inside in [(ctx,test(p)[0]),(ctx['ka_short'],test_top(p)[0])]:
        members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
        if 'д' in members:members.remove('д')
        if 'д' in outside:outside.remove('д')
        (members if inside else outside).append('д')
    event='17.10.2026: д заменена спокойной печатной формой с короткими ножками; прежняя петлевая сохранена; контекстные классы пересчитаны.'
    if event not in ctx['history']:ctx['history'].append(event)
    for path,value in [('data/params.json',params),('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),item)]:Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=1 if path=='data/params.json' else 2)+'\n')
if __name__=='__main__':main()
