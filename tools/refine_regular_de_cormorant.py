#!/usr/bin/env python3
"""[РЕШЕНИЕ] Cormorant-like construction, newly drawn in Very Peri weights.
Cormorant supplies design direction only; no reference font contours are used.
Native q crown and j terminal are copied unchanged, with translation only.
"""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.pens.recordingPen import RecordingPen
from sketchlib import Ref,SUB,AND,rect,write_glif
from check_context_classes import test,test_top

def native_section(ref,name,first,last,dx,dy=0):
    rec=RecordingPen();ref.gs[name].draw(rec);active=False;out=[]
    for op,pts in rec.value:
        if pts==tuple(tuple(p) for p in first):active=True
        if active:
            out.append((op,tuple((x+dx,y+dy) for x,y in pts)))
            if pts==tuple(tuple(p) for p in last):return out
    raise AssertionError((name,'native module not found'))

def main():
    if json.loads(Path('data/alphabet.json').read_text())['codex']['д']['variants'][0]['path'].startswith('data/cormorant-de/'):
        raise SystemExit('Historical de1.008 rejected; use tools/cormorant_de_proportions.py')
    params=json.loads(Path('data/params.json').read_text());d=params['regular_de_cormorant'];ref=Ref()
    crown=native_section(ref,'q',d['crown_first'],d['crown_last'],d['crown_dx'])
    terminal=native_section(ref,'j',d['terminal_first'],d['terminal_last'],d['terminal_dx'],d['terminal_dy'])
    path=pathops.Path();pen=path.getPen()
    def replay(commands):
        for op,pts in commands:getattr(pen,op)(*(tuple(p) for p in pts))
    replay(d['upper']);replay(crown);replay(d['outer_tail']);replay(terminal)
    replay(d['inner_tail_and_bowl'])
    counter=pathops.Path();counter_pen=counter.getPen()
    for op,pts in d['counter']:getattr(counter_pen,op)(*(tuple(p) for p in pts))
    path=SUB(path,counter)
    path=pathops.simplify(path,fix_winding=True,clockwise=True)
    # A counter must survive boolean assembly; native weights stay intact.
    assert len(list(path.contours))==2
    assert not list(AND(path,rect(200,250,210,260)).contours)
    for x0,x1,weight in [(-1000,200,d['left_stem']),(300,1000,d['right_stem'])]:
        sl=AND(path,rect(x0,253.99,x1,254.01));assert abs(sl.bounds[2]-sl.bounds[0]-weight)<.05
    assert abs(path.bounds[1]-d['tail_bottom'])<.01 and abs(path.bounds[3]-d['bowl_top'])<.01
    out=Path('data/regular-de-cormorant');out.mkdir(exist_ok=True);target=out/'uni0434.glif'
    write_glif(path,'uni0434',d['advance'],0x434,str(target))
    cfg=json.loads(Path('data/alphabet.json').read_text());previous=cfg['codex']['д']
    if previous['variants'][0]['path']!=str(target):cfg['rejected_drawings']['д-before-cormorant-direction']=copy.deepcopy(previous)
    item=dict(path=str(target),variant='01',label='Широкая округлая чаша, плавный нижний хвост',advance=d['advance'],bounds=list(path.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),status='selected')
    cfg['codex']['д']=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Author selected Cormorant Garamond ss10 / Infant direction; Very Peri contours, 17.10.2026')
    ctx=json.loads(Path('data/context/serif_bl.json').read_text());ctx['built_bases']['д']=str(target)
    for rule,inside in [(ctx,test(path)[0]),(ctx['ka_short'],test_top(path)[0])]:
        members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
        if 'д' in members:members.remove('д')
        if 'д' in outside:outside.remove('д')
        (members if inside else outside).append('д')
    event='17.10.2026: автор выбрал направление Cormorant Garamond/Infant; д перерисована с более широкой чашей и открытым хвостом под буквой; печатная ss07 сохранена.'
    if event not in ctx['history']:ctx['history'].append(event)
    manifest=dict(item,design_reference='Cormorant Garamond Regular ss10 and Cormorant Infant Regular; construction only',native_modules={'crown':{'glyph':'q','translation':[d['crown_dx'],0]},'terminal':{'glyph':'j','translation':[d['terminal_dx'],d['terminal_dy']]}},bowl='new cubic drawing; native stem/hairline model',printed_alternative=cfg['stylistic_alternates']['д'][0])
    for file,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),manifest)]:Path(file).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
