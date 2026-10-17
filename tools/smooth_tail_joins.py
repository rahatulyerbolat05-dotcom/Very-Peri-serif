#!/usr/bin/env python3
"""Smooth the attachment only: preserve the approved drop below y=-30 exactly."""
import copy,hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.misc.bezierTools import splitCubic,splitLine
from audit_author_glyphs import Segments,tangent,inspect
from sketchlib import AND,rect,write_glif
from finish_regular import load
from check_context_classes import test,test_top


PARAM=json.loads(Path('data/params.json').read_text())['tail_join_refinement']

def unit(v):
    n=math.hypot(*v);assert n>1e-10;return v[0]/n,v[1]/n

def cubic(seg):
    if len(seg)!=3:return list(seg)
    a,b,c=seg
    return [a,(a[0]+(b[0]-a[0])*2/3,a[1]+(b[1]-a[1])*2/3),(c[0]+(b[0]-c[0])*2/3,c[1]+(b[1]-c[1])*2/3),c]

def outer_join(segments,target,height):
    e=min(range(len(segments)),key=lambda i:math.dist(segments[i][-1],target));assert math.dist(segments[e][-1],target)<.1
    # Rotate the outer boundary so the complete descending neck is contiguous.
    segments=segments[e+1:]+segments[:e+1];end=segments[-1][-1]
    k=next(i for i in range(len(segments)-1,-1,-1) if segments[i][0][1]>=height and segments[i][-1][1]<height)
    seg=segments[k]
    pieces=splitLine(*seg,height,True) if len(seg)==2 else splitCubic(*seg,height,True)
    upper=pieces[0];assert abs(upper[-1][1]-height)<.01
    p=upper[-1];a=unit(tangent(upper,True));b=unit(tangent(segments[0]));distance=math.dist(p,end)
    h1=min(distance*PARAM['outer_body_handle_ratio'],PARAM['outer_body_handle_max']);h2=min(distance*PARAM['outer_spur_handle_ratio'],PARAM['outer_spur_handle_max'])
    joined=[p,(p[0]+a[0]*h1,p[1]+a[1]*h1),(end[0]-b[0]*h2,end[1]-b[1]*h2),end]
    return segments[:k]+[list(upper),joined]

def repair_join_edges(segments,left):
    # Boolean joins can leave tiny connector edges or a curve that doubles back.
    # Resolve only the attachment zone, including its cyclic closing edge.
    i=0
    while i<len(segments):
        edge=segments[i];prev=segments[i-1];nxt=segments[(i+1)%len(segments)]
        x,y=edge[-1]
        if len(edge)==2 and -29<y<161 and x>left-80:
            if math.dist(*edge)<PARAM['tiny_connector_max']:
                if len(prev)==len(nxt)==2 and abs(prev[0][1]-prev[-1][1])<.01 and abs(nxt[0][1]-nxt[-1][1])<.01:
                    # A sub-unit vertical step in an otherwise horizontal bottom bar.
                    end=(nxt[-1][0],prev[-1][1]);prev[-1]=end
                    segments[(i+2)%len(segments)][0]=end
                    segments.pop((i+1)%len(segments));segments.pop(i);continue
                prev[-1]=edge[-1];segments.pop(i);continue
            if len(prev)==4:
                a,b=unit(tangent(prev,True)),unit(tangent(edge))
                if sum(u*v for u,v in zip(a,b))<-.999 and math.dist(*edge)<PARAM['backtrack_max']:
                    end=edge[-1];v=unit(tangent(nxt));h=math.dist(prev[-2],prev[-1])
                    prev[-1]=end;prev[-2]=(end[0]-v[0]*h,end[1]-v[1]*h)
                    segments.pop(i);continue
        i+=1
    return segments

def flat_bar_join(segments,pivot):
    i=min(range(len(segments)),key=lambda i:math.dist(segments[i][-1],pivot));assert math.dist(segments[i][-1],pivot)<.02
    # The original contour closes at the bottom bar after this point.
    assert len(segments)==i+3 and len(segments[-1])==2
    p=segments[i][-1];radius=-p[1];end=(p[0]-radius,0);h=radius*.5522847498
    segments[0][0]=end;segments[-1][-1]=end
    segments[i+1]=[p,(p[0],p[1]+h),(end[0]+h,0),end]
    return segments[:i+2]

def align_tangents(segments,left):
    for prev,nxt in zip(segments,segments[1:]+segments[:1]):
        p=prev[-1]
        if not (-29<p[1]<161 and p[0]>left-80):continue
        if len(prev)==len(nxt)==2:continue
        va,vb=tangent(prev,True),tangent(nxt);a,b=unit(va),unit(vb)
        if sum(x*y for x,y in zip(a,b))<0:continue  # intentional corner, never round blindly
        if len(prev)==2:v=a
        elif len(nxt)==2:v=b
        else:v=unit((a[0]+b[0],a[1]+b[1]))
        if len(prev)==4:
            h=math.hypot(*va);prev[-2]=(p[0]-v[0]*h,p[1]-v[1]*h)
        if len(nxt)==4:
            h=math.hypot(*vb);nxt[1]=(p[0]+v[0]*h,p[1]+v[1]*h)

def build(ch,source,record):
    original,advance=load(source);pen=Segments();readGlyphFromString(Path(source).read_text(),SimpleNamespace(),PointToSegmentPen(pen))
    contours=[[cubic(seg) for seg in contour] for contour in pen.contours]
    removed=[]
    if ch in 'ЦЩ':
        for i,c in enumerate(original.contours):
            if not c.clockwise:
                assert c.area<600 and c.bounds[2]-c.bounds[0]<10 and c.bounds[1]>20
                removed.append(i)
        assert len(removed)==1
        contours=[c for i,c in enumerate(contours) if i not in removed]
    s,_,_,_,dx,dy=record['transform'];mapped=lambda x,y:(s*x+dx,-s*y+dy)
    target=mapped(633.595,432.478);pivot=mapped(541.475,534.523);left=mapped(543,390)[0]
    result=[]
    for contour in contours:
        contour=repair_join_edges(contour,left)
        if ch in 'ЦЩ':contour=flat_bar_join(contour,pivot)
        if min(math.dist(seg[-1],target) for seg in contour)<.1:contour=outer_join(contour,target,PARAM['outer_join_y'])
        align_tangents(contour,left)
        result.append(contour)
    p=pathops.Path();q=p.getPen()
    for contour in result:
        q.moveTo(contour[0][0])
        for seg in contour:
            if len(seg)==2:q.lineTo(seg[-1])
            else:q.curveTo(*seg[1:])
        q.closePath()
    p=pathops.simplify(p,fix_winding=True,clockwise=True)
    def difference(zone):return pathops.op(AND(original,zone),AND(p,zone),pathops.PathOp.XOR).area
    below=difference(rect(-1000,-1000,3000,PARAM['unchanged_drop_max_y']));above=difference(rect(-1000,PARAM['unchanged_body_min_y'],3000,2000))
    assert below<.03 and above<.03,(ch,below,above)
    return p,advance,dict(approved_drop_xor_area=below,upper_body_xor_area=above,removed_join_holes=len(removed))

def main():
    current=json.loads(Path('data/alphabet.json').read_text())
    if any(v['path'].startswith('data/width-refinement/') for section in ('user','codex') for e in current.get(section,{}).values() for v in e['variants']):
        print('Keeping width refinements; run tools/refine_widths.py to regenerate the active shapes.');return
    cfg=json.loads(Path('data/alphabet.json').read_text());ctx=json.loads(Path('data/context/serif_bl.json').read_text());out=Path('data/smooth-tail-joins');out.mkdir(exist_ok=True);manifest=[]
    for r in json.loads(Path('data/exact-author-tails/manifest.json').read_text()):
        ch,role=r['character'],r['role'];entry=cfg['user'][ch];source=r['path'];p,advance,audit=build(ch,source,r)
        target=out/f'uni{ord(ch):04X}-{role}.glif';write_glif(p,f'uni{ord(ch):04X}',advance,ord(ch),str(target))
        item=next(v for v in entry['variants'] if v['role']==role)
        if not item['path'].startswith(str(out)):cfg['rejected_drawings'].setdefault('tails-before-smooth-joins',{}).setdefault(ch,copy.deepcopy(entry))
        item.update(path=str(target),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bounds=list(p.bounds),status='approved drop retained; attachment smoothed',tail_source_glif=source)
        check=inspect(ch,item)
        assert check['matches_registered_hash'] and check['open_contours']==0
        assert len(check['contours'])==1 and all(r['simple_approx'] for r in check['ring_diagnostics'])
        pen=Segments();readGlyphFromString(target.read_text(),SimpleNamespace(),PointToSegmentPen(pen));angles=[]
        left=r['transform'][0]*543+r['transform'][4]
        for contour in pen.contours:
            for a,b in zip(contour,contour[1:]+contour[:1]):
                x,y=a[-1]
                if not (-29<y<161 and x>left-80):continue
                va,vb=unit(tangent(a,True)),unit(tangent(b))
                angles.append(math.degrees(math.acos(max(-1,min(1,sum(u*v for u,v in zip(va,vb)))))))
        audit['max_attachment_tangent_angle_degrees']=max(angles,default=0)
        audit['closed_simple_contours']=True
        assert audit['max_attachment_tangent_angle_degrees']<PARAM['joint_tangent_tolerance_degrees'],(ch,role,audit)
        if role=='primary':
            ctx['built_bases'][ch]=str(target)
            for rule,inside in [(ctx,test(p)[0])]+([(ctx['ka_short'],test_top(p)[0])] if ch.islower() else []):
                members=rule['declared_class']['upper' if ch.isupper() else 'lower'];outside=rule['expected_not_in_class']
                if ch in members:members.remove(ch)
                if ch in outside:outside.remove(ch)
                (members if inside else outside).append(ch)
        manifest.append(dict(character=ch,role=role,path=str(target),previous=source,changed_zone_y=[-30,161],**audit))
    cfg['tail_styles']['note']='Author drop retained exactly below -30; body-to-tail attachments smoothed. ss09 unchanged.'
    for file,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),manifest)]:Path(file).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
