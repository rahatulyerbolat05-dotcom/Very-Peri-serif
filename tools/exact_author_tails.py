#!/usr/bin/env python3
"""Replace the whole tail motif from the author's shcha SVG, not just its tip."""
import copy,hashlib,json,sys,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen
from sketchlib import AND,OR,SUB,rect,tf,write_glif
from finish_regular import load
from audit_author_glyphs import runs
from check_context_classes import test,test_top


def splice_u_body(filename,svg_commands,mapped):
    # The two u-shaped bodies share the author's actual notch nodes. Splice
    # there directly, so clipping cannot leave a sliver of the old stem.
    from drop_tail_variants import path_from
    root=ET.parse(filename).getroot();contour=root.find('outline/contour');nodes=list(contour)
    on=[p for p in nodes if p.get('type')]
    import math
    xy=lambda p:(float(p.get('x')),float(p.get('y')))
    a=(529.086,448.386);b=(611.,403.)
    first=min(on,key=lambda p:math.dist(xy(p),mapped(a)));last=min(on,key=lambda p:math.dist(xy(p),mapped(b)))
    assert math.dist(xy(first),mapped(a))<.02 and math.dist(xy(last),mapped(b))<5
    k=nodes.index(first);nodes=nodes[k:]+nodes[:k];end=nodes.index(last)
    ii=next(i for i,(_,pts) in enumerate(svg_commands) if pts and pts[-1]==a)
    jj=next(i for i,(_,pts) in enumerate(svg_commands) if pts and pts[-1]==b)
    added=[]
    for op,pts in svg_commands[ii+1:jj+1]:
        values=[mapped(p) for p in pts]
        if op=='curveTo' and pts[-1]==b:
            delta=(xy(last)[0]-values[-1][0],xy(last)[1]-values[-1][1])
            values[-2]=(values[-2][0]+delta[0],values[-2][1]+delta[1]);values[-1]=xy(last)
        assert op in ('curveTo','lineTo')
        for n,coords in enumerate(values):
            q=ET.Element('point',x=str(coords[0]),y=str(coords[1]))
            if n==len(values)-1:q.set('type','curve' if op=='curveTo' else 'line')
            added.append(q)
    contour[:]=[nodes[0]]+added+nodes[end+1:]
    return path_from(root)

def main():
    cfg=json.loads(Path('data/alphabet.json').read_text());ctx=json.loads(Path('data/context/serif_bl.json').read_text())
    out=Path('data/exact-author-tails');out.mkdir(exist_ok=True)
    uploaded=Path('/workspace/attachments/cbe95999-4089-460d-982c-35088abe0229/пример хвостика.svg')
    source=out/'author-shcha.svg'
    if uploaded.exists():shutil.copyfile(uploaded,source)
    root=ET.parse(source).getroot();black=next(p for p in root if p.get('fill')=='black')
    rec=RecordingPen();parse_path(black.get('d'),rec)
    a=(546.006,453.357);b=(611.,403.)
    i=next(i for i,(_,pts) in enumerate(rec.value) if pts and pts[-1]==a)
    j=next(i for i,(_,pts) in enumerate(rec.value) if pts and pts[-1]==b)
    commands=rec.value[i+1:j+1];assert len(commands)>20
    original_svg=pathops.Path();parse_path(black.get('d'),original_svg.getPen())
    records=[]
    for prior in json.loads(Path('data/drop-tail-variants/manifest.json').read_text()):
        ch,role=prior['character'],prior['role'];entry=cfg['user'][ch]
        old=next(v for v in entry['variants'] if v['role']==role)
        if old['path'].startswith(str(out)):
            old=next(v for v in cfg['rejected_drawings']['tails-before-full-svg'][ch]['variants'] if v['role']==role)
        else:cfg['rejected_drawings'].setdefault('tails-before-full-svg',{}).setdefault(ch,copy.deepcopy(entry))
        base,advance=load(old['path']);s=prior['svg_uniform_scale'];_,_,_,_,dx,dy=prior['svg_transform']
        def mapped(p):return p[0]*s+dx,-p[1]*s+dy
        join=mapped((611,390))[1];L,R=runs(base,join)[-1];Lu,Ru=runs(base,join+1)[-1]
        module=pathops.Path();pen=module.getPen();pen.moveTo(mapped(a))
        for op,pts in commands:getattr(pen,op)(*(mapped(p) for p in pts))
        bx,by=mapped(b);ax,ay=mapped(a);h=(join-by)/3
        pen.curveTo((bx,by+h),(R-(Ru-R)*h,join-h),(R,join));pen.lineTo((L,join))
        pen.curveTo((L-(Lu-L)*20*s,join-20*s),(ax,ay+20*s),(ax,ay));pen.closePath()
        cutL=min(L,mapped((543,390))[0]);lowL=cutL-40*s
        body=SUB(base,OR(rect(cutL,0,3000,join),rect(lowL,-1000,3000,0)))
        result=OR(body,module)
        if ch in 'ЦЩ':
            # Connect the existing flat bottom bar to the imported neck.
            result=OR(result,rect(L-30*s,0,mapped((543,390))[0]+12*s,30*s))
        if ch in 'цщ':result=splice_u_body(old['path'],rec.value,mapped)
        result=pathops.simplify(result,fix_winding=True,clockwise=True)
        reference=tf(original_svg,(s,0,0,-s,dx,dy));zone=rect(lowL,-1000,3000,-30)
        error=pathops.op(AND(result,zone),AND(reference,zone),pathops.PathOp.XOR).area
        assert error<.03,(ch,role,error)
        above=pathops.op(AND(base,rect(-1000,join+.01,3000,2000)),AND(result,rect(-1000,join+.01,3000,2000)),pathops.PathOp.XOR).area
        assert above<.03,(ch,role,above)
        target=out/f'uni{ord(ch):04X}-{role}.glif';write_glif(result,f'uni{ord(ch):04X}',advance,ord(ch),str(target))
        item=copy.deepcopy(old);item.update(path=str(target),bounds=list(result.bounds),advance=advance,glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),tail_source_glif=old['path'],tail_style='full-author-svg',status='full author SVG motif; upper body preserved')
        current=next(v for v in entry['variants'] if v['role']==role);current.clear();current.update(item)
        records.append(dict(character=ch,role=role,path=str(target),previous=old['path'],svg_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),transform=[s,0,0,-s,dx,dy],exact_source_commands=len(commands),upper_adapters=2,lower_tail_xor_area=error,upper_body_xor_area=above,join_y=join))
        if role=='primary':
            ctx['built_bases'][ch]=str(target)
            for rule,inside in [(ctx,test(result)[0])]+([(ctx['ka_short'],test_top(result)[0])] if ch.islower() else []):
                members=rule['declared_class']['upper' if ch.isupper() else 'lower'];outside=rule['expected_not_in_class']
                if ch in members:members.remove(ch)
                if ch in outside:outside.remove(ch)
                (members if inside else outside).append(ch)
    cfg['tail_styles']['note']='Full contiguous author SVG motif including entry, drop, inner return and spur; old angular tails retained as ss09.'
    for file,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),records)]:Path(file).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
