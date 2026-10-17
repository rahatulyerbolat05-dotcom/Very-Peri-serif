#!/usr/bin/env python3
"""Replace wobbling runs of tiny cubics by one smooth cubic (ж feet necks) and clean a clustered tip (д flag).
The declump/condense warps left 2-5 nodes closer than 12 units apart where the thick diagonals of ж
run into the foot brackets (position wobble 1-3 units, tangent breaks up to 21 degrees), and three
nodes within 6 units at the д stem tip. Each run is replaced by a single cubic whose end tangents are
the neighbours' tangents (G1 joints) and whose handle lengths minimise the deviation from the old run.
Inputs pinned by SHA256, old outlines archived (rejected_drawings 'before-neck-repair').
"""
import copy,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_author_glyphs import inspect
from sketchlib import write_glif
from alphabet_sheet import source_items
from check_context_classes import test,test_top
from refine_widths import segments,path_from
from outline_clean import bez,norm,unit

OUT=Path('data/neck-repair')
# start/end are node positions in the source GLIF (font units); t0/t3 are the travel directions at the ends
RUNS={'ж':[
    dict(start=(54.8,58.0),end=(80.0,127.5),t0=(0.7,2.5),t3=(4.2,10.1)),        # left foot, outer edge
    dict(start=(194.4,260.0),end=(116.8,47.0),t0=(-13.4,-31.2),t3=(0,-1)),     # left foot, inner edge
    dict(start=(469.8,127.5),end=(499.0,51.1),t0=(4.2,-10.1),t3=(1.3,-2.1)),   # right foot, outer edge
    dict(start=(433.2,47.0),end=(394.6,166.5),t0=(0,1),t3=(-12.9,31.2)),       # right foot, inner edge
],'д':[
    dict(start=(372.2,510.82),end=(382.71,507.72),t0=(7.0,12.76),t3=(0,-1)),   # stem tip: three nodes within 6 units
]}
close=lambda a,b:abs(a[0]-b[0])<.06 and abs(a[1]-b[1])<.06


def dense(run,per=40):
    pts=[]
    for s in run:
        if len(s)==2:pts+= [(s[0][0]+(s[1][0]-s[0][0])*k/per,s[0][1]+(s[1][1]-s[0][1])*k/per) for k in range(per)]
        else:pts+= [bez(*s,k/per) for k in range(per)]
    return pts


def deviation(a,b):
    def one(P,Q):return max(min(math.hypot(p[0]-q[0],p[1]-q[1]) for q in Q) for p in P)
    return max(one(a,b),one(b,a))


def locate(contour,start,end):
    i=next(k for k,s in enumerate(contour) if close(s[0],start));j=next(k for k,s in enumerate(contour) if close(s[-1],end))
    assert i<=j,(start,end);return i,j


def smooth(run,t0,t3):
    p0,p3=run[0][0],run[-1][-1];u0=unit(t0);u3=unit(t3);old=dense(run);best=None
    for l1 in range(4,160,4):
        for l2 in range(4,160,4):
            c=(p0,(p0[0]+u0[0]*l1,p0[1]+u0[1]*l1),(p3[0]-u3[0]*l2,p3[1]-u3[1]*l2),p3)
            d=deviation(old,dense([c]))
            if best is None or d<best[0]:best=(d,c)
    return best


def repair(ch,source):
    contours=[list(c) for c in segments(source)];report=[]
    for run in RUNS.get(ch,[]):
        for c in contours:
            try:i,j=locate(c,run['start'],run['end'])
            except StopIteration:continue
            d,new=smooth(c[i:j+1],run['t0'],run['t3']);assert d<=3.5,(ch,run,d)
            report.append(dict(run=len(c[i:j+1]),segments_before=j-i+1,deviation=round(d,2)));c[i:j+1]=[new];break
        else:raise SystemExit(f'run not found {ch} {run}')
    return path_from(contours),report


def main():
    OUT.mkdir(exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());ctx=json.loads(Path('data/context/serif_bl.json').read_text())
    baseline=OUT/'baseline.json'
    if baseline.exists():inputs=json.loads(baseline.read_text())
    else:
        inputs=[]
        for ch in ('ж','д'):
            item=source_items(ch,cfg)[0];inputs.append(dict(character=ch,role='primary',source=item['path'],sha256=hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()))
        baseline.write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
    records=[]
    for row in inputs:
        ch,source=row['character'],row['source'];assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==row['sha256']
        from finish_regular import load
        old,advance=load(source);p,report=repair(ch,source)
        assert abs(p.bounds[1]-old.bounds[1])<.05 and abs(p.bounds[3]-old.bounds[3])<.05,(ch,p.bounds,old.bounds)
        target=OUT/f'uni{ord(ch):04X}-primary.glif';write_glif(p,f'uni{ord(ch):04X}',advance,ord(ch),str(target))
        item=dict(path=str(target),advance=advance,bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),role='primary',variant='01',label='Сглажены стыки',status='neck wobble repaired, requested by author',neck_source_glif=source)
        check=inspect(ch,item);assert check['open_contours']==0 and all(r['simple_approx'] for r in check['ring_diagnostics']),(ch,check['ring_diagnostics'])
        entry=cfg['codex'][ch];archive=cfg['rejected_drawings'].setdefault('before-neck-repair',{})
        if ch not in archive:archive[ch]=copy.deepcopy(entry)
        cfg['codex'][ch]=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Neck repair requested by author; previous sources archived')
        ctx['built_bases'][ch]=str(target)
        for rule,inside in [(ctx,test(p)[0]),(ctx['ka_short'],test_top(p)[0])]:
            members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
            if inside and ch not in members:members.append(ch)
            if not inside and ch in members:members.remove(ch)
            if inside and ch in outside:outside.remove(ch)
            if not inside and ch not in outside:outside.append(ch)
        records.append(dict(**row,path=str(target),repairs=report))
        print(ch,report)
    for path,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(OUT/'manifest.json'),records)]:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
