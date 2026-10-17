#!/usr/bin/env python3
"""Narrow Cyrillic bowls that are wider than the native Latin counter (д ю).
Same monotone C1 x-map as lighten_dense: walls, stems and outer shapes keep their
thickness, only the counter shrinks to the Latin standard and the advance follows.
Inputs pinned by SHA256, old outlines archived. Run after tools/lighten_dense.py.
"""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from audit_author_glyphs import inspect,runs
from finish_regular import load
from sketchlib import write_glif
from alphabet_sheet import source_items
from check_context_classes import test,test_top
from refine_widths import segments,fit,path_from

OUT=Path('data/condense-bowls')


def pchip(knots):
    """Monotone cubic Hermite map through (old,new) knots, identity slope outside."""
    pts=sorted((float(a),float(b)) for a,b in knots)
    pts=[(pts[0][0]-300,pts[0][1]-300)]+pts+[(pts[-1][0]+300,pts[-1][1]+300)]
    xs=[a for a,_ in pts];ys=[b for _,b in pts];n=len(xs)
    h=[xs[i+1]-xs[i] for i in range(n-1)];d=[(ys[i+1]-ys[i])/h[i] for i in range(n-1)]
    assert all(x>0 for x in d),'knots must stay monotone'
    m=[d[0]]+[0 if d[i-1]*d[i]<=0 else 2*d[i-1]*d[i]/(d[i-1]+d[i]) for i in range(1,n-1)]+[d[-1]]
    def locate(x):
        if x<=xs[0]:return 0
        if x>=xs[-1]:return n-2
        return next(i for i in range(n-1) if xs[i]<=x<=xs[i+1])
    def value(p):
        x,y=p;i=locate(x);t=(x-xs[i])/h[i]
        if x<=xs[0]:return ys[0]+(x-xs[0]),y
        if x>=xs[-1]:return ys[-1]+(x-xs[-1]),y
        h00,h10,h01,h11=2*t**3-3*t**2+1,t**3-2*t**2+t,-2*t**3+3*t**2,t**3-t**2
        return h00*ys[i]+h10*h[i]*m[i]+h01*ys[i+1]+h11*h[i]*m[i+1],y
    def vector(p,v):
        x,y=p;i=locate(x);t=(x-xs[i])/h[i]
        if x<=xs[0] or x>=xs[-1]:return v
        dh00,dh10,dh01,dh11=6*t**2-6*t,3*t**2-4*t+1,-6*t**2+6*t,3*t**2-2*t
        slope=(dh00*ys[i]+dh10*h[i]*m[i]+dh01*ys[i+1]+dh11*h[i]*m[i+1])/h[i]
        assert slope>0,(p,slope);return v[0]*slope,v[1]
    return value,vector


def warp_contours(contours,knots,tolerance):
    value,vector=pchip(knots);result=[]
    for c in contours:
        out=[]
        for s in c:
            if len(s)==2 and (s[0][0]==s[-1][0] or s[0][1]==s[-1][1]):out.append([value(s[0]),value(s[-1])])
            else:out.extend(fit(s,value,vector,tolerance))
        result.append(out)
    return result


def thin_zhe_branches(contours,thickness,foot_share):
    """Thin the two thick diagonals of ж by moving one straight edge each (104-segment source)."""
    assert len(contours)==1 and len(contours[0])==104
    c=[list(s) for s in contours[0]]
    def move(i,top_dx,bottom_dx):
        a,b=c[i][0],c[i][-1];assert len(c[i])==2
        hi,lo=(a,b) if a[1]>b[1] else (b,a)
        for k,(pt,dx) in enumerate([(hi,top_dx),(lo,bottom_dx)]):
            moved=(pt[0]+dx,pt[1])
            for j in (i-1,i,(i+1)%len(c)):
                c[j]=[moved if q==pt else q for q in c[j]]
    # left thick branch: its right edge goes left; right thick branch: its left edge goes right
    move(4,-thickness,-thickness*foot_share);move(87,thickness,thickness*foot_share)
    return [c]


def build(ch,source,design):
    old,advance=load(source);contours=segments(source)
    if design['method']=='branches_and_stem':contours=thin_zhe_branches(contours,design['branch_thinning'],design['foot_share'])
    p=pathops.simplify(path_from(warp_contours(contours,design['knots'],.15)),fix_winding=True,clockwise=True)
    assert abs(p.bounds[1]-old.bounds[1])<.02 and abs(p.bounds[3]-old.bounds[3])<.02,(ch,p.bounds,old.bounds)
    y=design['stem_probe_y'];before=runs(old,y);after=runs(p,y)
    assert len(before)==len(after),(ch,before,after)
    return p,advance-design['reduction'],dict(before_stem_runs=before,after_stem_runs=after)


def main():
    OUT.mkdir(exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());params=json.loads(Path('data/params.json').read_text())['condense_bowls']
    ctx=json.loads(Path('data/context/serif_bl.json').read_text())
    baseline=OUT/'baseline.json'
    if baseline.exists():inputs=json.loads(baseline.read_text())
    else:
        inputs=[]
        for ch in params['letters']:
            item=source_items(ch,cfg)[0];inputs.append(dict(character=ch,role='primary',source=item['path'],sha256=hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()))
        baseline.write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
    records=[]
    for row in inputs:
        ch,source=row['character'],row['source'];assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==row['sha256']
        design=params['letters'][ch];p,advance,audit=build(ch,source,design)
        target=OUT/f'uni{ord(ch):04X}-primary.glif';write_glif(p,f'uni{ord(ch):04X}',advance,ord(ch),str(target))
        item=dict(path=str(target),advance=advance,bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),role='primary',variant='01',label='Ужатая чаша',status='bowl condensed to the Latin counter, requested by author',condense_source_glif=source)
        check=inspect(ch,item);assert check['open_contours']==0 and all(r['simple_approx'] for r in check['ring_diagnostics']),(ch,check['ring_diagnostics'])
        section='user' if ch in cfg.get('user',{}) else 'codex';entry=cfg.get(section,{}).get(ch)
        archive=cfg['rejected_drawings'].setdefault('before-condense-bowls',{})
        if ch not in archive:archive[ch]=copy.deepcopy(entry if entry else cfg['done'][ch])
        if section=='user':next(v for v in entry['variants'] if v['role']=='primary').update({k:v for k,v in item.items() if k not in ('role','variant')})
        else:cfg.setdefault('codex',{})[ch]=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Bowl condense requested by author; previous sources archived')
        ctx['built_bases'][ch]=str(target)
        for rule,inside in [(ctx,test(p)[0]),(ctx['ka_short'],test_top(p)[0])]:
            members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
            if inside and ch not in members:members.append(ch)
            if not inside and ch in members:members.remove(ch)
            if inside and ch in outside:outside.remove(ch)
            if not inside and ch not in outside:outside.append(ch)
        old,oldadvance=load(source)
        records.append(dict(**row,path=str(target),advance_before=oldadvance,advance_after=advance,**audit))
    for path,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(OUT/'manifest.json'),records)]:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print('Condensed',len(records),'forms')

if __name__=='__main__':main()
