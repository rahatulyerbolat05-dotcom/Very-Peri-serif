#!/usr/bin/env python3
"""Rebalance wide Cyrillic shapes by moving stems and rebuilding connecting curves.
Native Latin is untouched. Immutable inputs and all decisions are recorded.
"""
import copy,hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.misc.bezierTools import splitCubicAtT
from audit_author_glyphs import Segments,tangent,sample,inspect,runs
from finish_regular import load
from sketchlib import Ref,OR,AND,rect,shift,write_glif
from alphabet_sheet import source_items
from glyphparts import yu_sign,yu_cap_sign
from check_context_classes import test,test_top

OUT=Path('data/width-refinement')

def elevated(s):
    a,d=s[0],s[-1]
    if len(s)==4:return list(s)
    if len(s)==2:return [a,tuple(a[i]+(d[i]-a[i])/3 for i in (0,1)),tuple(a[i]+(d[i]-a[i])*2/3 for i in (0,1)),d]
    b=s[1];return [a,tuple(a[i]+(b[i]-a[i])*2/3 for i in (0,1)),tuple(d[i]+(b[i]-d[i])*2/3 for i in (0,1)),d]

def segments(filename):
    p=Segments();readGlyphFromString(Path(filename).read_text(),SimpleNamespace(),PointToSegmentPen(p));return p.contours

def gap_edit(intervals):
    # Smooth translations across counter space. The Jacobian is identity on stems.
    def value(p):
        x,y=p;delta=0
        for lo,hi,amount in intervals:
            u=max(0,min(1,(x-lo)/(hi-lo)));delta+=amount*u*u*(3-2*u)
        return x-delta,y
    def vector(p,v):
        x,y=p;derivative=1
        for lo,hi,amount in intervals:
            u=(x-lo)/(hi-lo)
            if 0<u<1:derivative-=amount*6*u*(1-u)/(hi-lo)
        assert derivative>0,(p,intervals)
        return v[0]*derivative,v[1]
    return value,vector

def fit(s,value,vector,tolerance,depth=0):
    a,b,c,d=elevated(s);A,D=value(a),value(d)
    u=vector(a,(b[0]-a[0],b[1]-a[1]));v=vector(d,(d[0]-c[0],d[1]-c[1]))
    curve=[A,(A[0]+u[0],A[1]+u[1]),(D[0]-v[0],D[1]-v[1]),D]
    error=max(math.dist(value(sample([a,b,c,d],t)),sample(curve,t)) for t in (.125,.25,.5,.75,.875))
    if error<=tolerance:return [curve]
    assert depth<14,error
    left,right=splitCubicAtT(a,b,c,d,.5)
    return fit(left,value,vector,tolerance,depth+1)+fit(right,value,vector,tolerance,depth+1)

def path_from(contours):
    p=pathops.Path();q=p.getPen()
    for c in contours:
        q.moveTo(c[0][0])
        for s in c:
            if len(s)==2:q.lineTo(s[-1])
            else:q.curveTo(*s[1:])
        q.closePath()
    return pathops.simplify(p,fix_winding=True,clockwise=True)

def warp(source,intervals,tolerance):
    value,vector=gap_edit(intervals);result=[]
    for c in segments(source):
        out=[]
        for s in c:
            if len(s)==2 and (s[0][0]==s[-1][0] or s[0][1]==s[-1][1]):out.append([value(s[0]),value(s[-1])])
            else:out.extend(fit(s,value,vector,tolerance))
        result.append(out)
    return path_from(result)

def zhe(source,amount):
    # Move the outer terminals inward; shear each straight branch, retaining its
    # horizontal ink thickness. The central stem and its serifs translate rigidly.
    cs=segments(source);assert len(cs)==1 and len(cs[0])==94
    original=cs[0];half=amount/2;pivot=original[24][-1][1];top=max(s[-1][1] for s in original)
    def offset(i,p):
        y=p[1]
        if 11<=i<=24:return -amount+half*y/pivot
        if 25<=i<=38:return -half-half*(y-pivot)/(top-pivot)
        if 55<=i<=69:return -half+half*(y-pivot)/(top-pivot)
        if 70<=i<=82:return -half*y/pivot
        return -half
    result=[]
    for i,s in enumerate(original):
        v=elevated(s) if len(s)!=2 else list(s)
        result.append([(x+offset(i,(x,y)),y) for x,y in v])
    # One endpoint per shared knot, then restore originally smooth tangencies.
    for i,c in enumerate(result):c[0]=result[i-1][-1]
    for i,(a,b) in enumerate(zip(result,result[1:]+result[:1])):
        olda,oldb=original[i],original[(i+1)%len(original)];oa,ob=tangent(olda,True),tangent(oldb)
        cos=sum(u*v for u,v in zip(oa,ob))/(math.hypot(*oa)*math.hypot(*ob))
        if cos<.9999:continue
        va,vb=tangent(a,True),tangent(b);ha,hb=math.hypot(*va),math.hypot(*vb)
        if len(a)==2:v=(va[0]/ha,va[1]/ha)
        elif len(b)==2:v=(vb[0]/hb,vb[1]/hb)
        else:
            v=(va[0]/ha+vb[0]/hb,va[1]/ha+vb[1]/hb);h=math.hypot(*v);v=(v[0]/h,v[1]/h)
        x,y=a[-1]
        if len(a)==4:a[-2]=(x-v[0]*ha,y-v[1]*ha)
        if len(b)==4:b[1]=(x+v[0]*hb,y+v[1]*hb)
    return path_from([result])

def strengthen_ze(source,amount):
    import xml.etree.ElementTree as ET
    root=ET.parse(source).getroot();pts=root.findall('.//point');assert len(pts)==75
    for i,factor in [(18,.5),(19,1),(20,1),(21,1),(31,.5),(32,1),(33,1),(34,1),(35,.5)]:
        pts[i].set('x',str(float(pts[i].get('x'))-amount*factor))
    p=pathops.Path();readGlyphFromString(ET.tostring(root,encoding='unicode'),SimpleNamespace(),PointToSegmentPen(p.getPen()));return pathops.simplify(p,fix_winding=True,clockwise=True)

def build(ch,source,design,ref):
    old,advance=load(source);amount=design['reduction'];kind=design['method'];extra={}
    if kind=='gaps':p=warp(source,design['intervals'],.01)
    elif kind=='branch_shear':p=zhe(source,amount)
    elif kind=='separate_stem':
        cutoff=design['separate_stem_min_x'];cs=list(old.contours)
        candidates=[i for i,c in enumerate(cs) if c.bounds[0]>=cutoff];assert len(candidates)==1
        p=pathops.Path()
        moved=shift(cs[candidates[0]],-amount)
        assert all(AND(c,moved).area<.01 for i,c in enumerate(cs) if i not in candidates and c.clockwise==cs[candidates[0]].clockwise)
        for i,c in enumerate(cs):(moved if i in candidates else c).draw(p.getPen())
    elif kind=='shorter_link':
        p,info=(yu_cap_sign if ch.isupper() else yu_sign)(ref,link=design['link']);extra['link']=info['link']
        assert not info.get('stem_touches_oval',False) and info.get('min_gap_serif_oval',1)>0
    elif kind=='inner_weight':p=strengthen_ze(source,design['weight_addition'])
    else:raise ValueError(kind)
    p=pathops.simplify(p,fix_winding=True,clockwise=True)
    assert abs(p.bounds[1]-old.bounds[1])<.02 and abs(p.bounds[3]-old.bounds[3])<.02,(ch,p.bounds,old.bounds)
    before=runs(old,design['stem_probe_y']);after=runs(p,design['stem_probe_y'])
    extra.update(before_stem_runs=before,after_stem_runs=after)
    if kind!='inner_weight':
        assert len(before)==len(after),(ch,before,after)
        for i in design.get('protected_stem_indices',[]):
            assert abs((before[i][1]-before[i][0])-(after[i][1]-after[i][0]))<.03,(ch,i,before,after)
    if ch in 'щЩ':
        zone=rect(-1000,-1000,3000,-30)
        error=pathops.op(AND(p,zone),AND(shift(old,-amount),zone),pathops.PathOp.XOR).area
        assert error<.03,(ch,error);extra['approved_drop_translation_xor_area']=error
    return p,advance-amount,extra

def main():
    OUT.mkdir(exist_ok=True);cfg=json.loads(Path('data/alphabet.json').read_text());params=json.loads(Path('data/params.json').read_text())['width_refinement'];ctx=json.loads(Path('data/context/serif_bl.json').read_text());ref=Ref()
    baseline=OUT/'baseline.json'
    if baseline.exists():inputs=json.loads(baseline.read_text())
    else:
        inputs=[]
        for ch in params['letters']:
            item=source_items(ch,cfg)[0];inputs.append(dict(character=ch,role='primary',source=item['path'],sha256=hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()))
            for old in cfg.get('user',{}).get(ch,{}).get('tail_alternatives',[]):
                inputs.append(dict(character=ch,role='tail_old',source=old['path'],sha256=hashlib.sha256(Path(old['path']).read_bytes()).hexdigest()))
        baseline.write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
    records=[]
    for row in inputs:
        ch,role,source=row['character'],row['role'],row['source'];assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==row['sha256']
        design=params['letters'][ch];p,advance,audit=build(ch,source,design,ref);target=OUT/f'uni{ord(ch):04X}-{role}.glif';write_glif(p,f'uni{ord(ch):04X}',advance,ord(ch),str(target))
        item=dict(path=str(target),advance=advance,bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),role='primary',variant='01',label='Согласованные пропорции' if ch!='з' else 'Усиленные чаши',status='width/weight refinement requested by author',width_source_glif=source)
        check=inspect(ch,item);assert check['open_contours']==0 and all(r['simple_approx'] for r in check['ring_diagnostics']),(ch,role,check['ring_diagnostics'])
        section='user' if ch in cfg.get('user',{}) else 'codex';entry=cfg.get(section,{}).get(ch)
        archive=cfg['rejected_drawings'].setdefault('before-width-refinement',{})
        if ch not in archive:archive[ch]=copy.deepcopy(entry if entry else cfg['done'][ch])
        if role=='tail_old':
            old=next(v for v in entry['tail_alternatives'] if v['role']=='primary');old.update({k:v for k,v in item.items() if k not in ('role','variant')})
        elif section=='user':next(v for v in entry['variants'] if v['role']=='primary').update({k:v for k,v in item.items() if k not in ('role','variant')})
        else:cfg.setdefault('codex',{})[ch]=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Width/weight refinement requested by author; previous sources archived')
        if role=='primary':
            ctx['built_bases'][ch]=str(target)
            for rule,inside in [(ctx,test(p)[0])]+([(ctx['ka_short'],test_top(p)[0])] if ch.islower() else []):
                members=rule['declared_class']['upper' if ch.isupper() else 'lower'];outside=rule['expected_not_in_class']
                if inside and ch not in members:members.append(ch)
                if not inside and ch in members:members.remove(ch)
                if inside and ch in outside:outside.remove(ch)
                if not inside and ch not in outside:outside.append(ch)
        old,oldadvance=load(source)
        records.append(dict(**row,path=str(target),advance_before=oldadvance,advance_after=advance,reduction_percent=round(100*(oldadvance-advance)/oldadvance,2),method=design['method'],closed_simple_contours=True,**audit))
    for path,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(OUT/'manifest.json'),records)]:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print('Refined',len(records),'forms')
if __name__=='__main__':main()
