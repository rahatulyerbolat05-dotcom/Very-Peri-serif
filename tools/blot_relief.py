#!/usr/bin/env python3
"""Open the dark spots of ы and ю (author request).  1.013 thinned walls and was rejected (the bend showed);
1.015 moves whole parts apart instead: curves stay identical, only the gaps between parts grow.
(older description follows)
ы: 19 units between the bowl of ь and the right stem. ю: 47-60 units between stem and oval (Latin n m: 174).
Walls and stems are thinned inside a y-band by the monotone C1 x-map of tools/declump.py (serifs outside the
band keep their shape); the outer silhouette of the right stem, the counters and the advance stay.
Inputs pinned by SHA256, old outlines archived. Run after tools/declump.py.
"""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from audit_author_glyphs import inspect,runs
from declump import warp_2d
from finish_regular import load
from sketchlib import write_glif
from alphabet_sheet import source_items
from check_context_classes import test,test_top
from refine_widths import segments

OUT=Path('data/blot-relief')


def explode_lines(contours,step=24.):
    """Long non-horizontal straight pieces become short collinear cubics, so that the band warp can bend them."""
    out=[]
    for c in contours:
        new=[]
        for seg in c:
            if len(seg)==2 and abs(seg[1][1]-seg[0][1])>step:
                a,b=seg;n=int(abs(b[1]-a[1])//step)+1
                for i in range(n):
                    p0=(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n);p3=(a[0]+(b[0]-a[0])*(i+1)/n,a[1]+(b[1]-a[1])*(i+1)/n)
                    new.append((p0,(p0[0]+(p3[0]-p0[0])/3,p0[1]+(p3[1]-p0[1])/3),(p0[0]+2*(p3[0]-p0[0])/3,p0[1]+2*(p3[1]-p0[1])/3),p3))
            else:new.append(seg)
        out.append(new)
    return out


def anchored(design):
    """pchip pads its ends with unit-slope knots 300 units away, which bends the map inside a 300-unit span when the
    first/last knot has another slope. Two identity anchors 40 and 80 units outside each band keep the map exact there."""
    d=copy.deepcopy(design)
    if d.get('rigid'):     # pure part translation: after the last knot the map continues with its shift
        for b in d['bands']:
            k=sorted(map(tuple,b['knots']));lo,hi=k[0][0],k[-1][0];sh=k[-1][1]-k[-1][0]
            b['knots']=[[lo-80,lo-80],[lo-40,lo-40]]+[list(x) for x in k]+[[hi+40,hi+40+sh],[hi+80,hi+80+sh]]
        return d
    for b in d['bands']:
        k=sorted(map(tuple,b['knots']));lo,hi=k[0][0],k[-1][0]
        b['knots']=[[lo-80,lo-80],[lo-40,lo-40]]+[list(x) for x in k]+[[hi+40,hi+40],[hi+80,hi+80]]
    return d


def build(ch,source,design):
    design=anchored(design)
    from refine_widths import path_from
    old,advance=load(source);result=warp_2d(segments(source) if design.get('rigid') else explode_lines(segments(source)),design,.15)
    p=pathops.simplify(path_from(result),fix_winding=True,clockwise=True)
    assert abs(p.bounds[1]-old.bounds[1])<.02 and abs(p.bounds[3]-old.bounds[3])<.02,(ch,p.bounds,old.bounds)
    y=design['probe_y'];before=runs(old,y);after=runs(p,y)
    assert len(before)==len(after),(ch,before,after)
    return p,advance+design.get('advance_delta',0),dict(before_runs=before,after_runs=after)


def main():
    OUT.mkdir(exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());params=json.loads(Path('data/params.json').read_text())['blot_relief']
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
        item=dict(path=str(target),advance=advance,bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),role='primary',variant='01',label='Раскрытые пятна',status='thickness relief requested by author',relief_source_glif=source)
        check=inspect(ch,item);assert check['open_contours']==0 and all(r['simple_approx'] for r in check['ring_diagnostics']),(ch,check['ring_diagnostics'])
        entry=cfg['codex'][ch];archive=cfg['rejected_drawings'].setdefault('before-blot-relief',{})
        if ch not in archive:archive[ch]=copy.deepcopy(entry)
        cfg['codex'][ch]=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Blot relief requested by author; previous sources archived')
        ctx['built_bases'][ch]=str(target)
        for rule,inside in [(ctx,test(p)[0]),(ctx['ka_short'],test_top(p)[0])]:
            members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
            if inside and ch not in members:members.append(ch)
            if not inside and ch in members:members.remove(ch)
            if inside and ch in outside:outside.remove(ch)
            if not inside and ch not in outside:outside.append(ch)
        records.append(dict(**row,path=str(target),**audit));print(ch,audit['before_runs'],'->',audit['after_runs'])
    for path,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(OUT/'manifest.json'),records)]:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
