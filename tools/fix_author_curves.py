#!/usr/bin/env python3
"""Apply reviewed author-curve fixes; preserve all original files.

Run from repository root. Repairs are intentionally local except for the
requested ф bowl weight correction. No global smoothing is performed.
"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.ufoLib.glifLib import readGlyphFromString,writeGlyphToString
from fontTools.pens.pointPen import PointToSegmentPen,SegmentToPointPen
from audit_author_glyphs import inspect,runs

DATA=Path('data/author-curve-fixes')
TARGETS='щқфЩҚ'


def xy(p): return float(p.get('x')),float(p.get('y'))
def put(p,v):p.set('x',format(v[0],'.12g'));p.set('y',format(v[1],'.12g'))
def add(a,b):return a[0]+b[0],a[1]+b[1]
def sub(a,b):return a[0]-b[0],a[1]-b[1]
def mul(a,t):return a[0]*t,a[1]*t
def unit(v):return mul(v,1/math.hypot(*v))


def load_path(root):
    p=pathops.Path()
    readGlyphFromString(ET.tostring(root,encoding='unicode'),SimpleNamespace(),PointToSegmentPen(p.getPen()))
    return p


def smooth_at(root,point):
    for contour in root.findall('.//contour'):
        pts=list(contour)
        for i,node in enumerate(pts):
            if math.dist(xy(node),point)>.002:continue
            before=pts[i-1];after=pts[(i+1)%len(pts)];v=xy(node)
            incoming=sub(v,xy(before));outgoing=sub(xy(after),v)
            in_curve=node.get('type')=='curve'
            out_curve=after.get('type') is None
            if in_curve and out_curve:
                direction=unit(add(unit(incoming),unit(outgoing)))
                put(before,sub(v,mul(direction,math.hypot(*incoming))))
                put(after,add(v,mul(direction,math.hypot(*outgoing))))
            elif in_curve:
                put(before,sub(v,mul(unit(outgoing),math.hypot(*incoming))))
            elif out_curve:
                put(after,add(v,mul(unit(incoming),math.hypot(*outgoing))))
            else:raise ValueError('Cannot smooth a deliberate line/line corner')
            node.set('smooth','yes');return
    raise ValueError(('Missing repair node',point))


def split_cubic(points,t):
    a=[add(mul(x,1-t),mul(y,t)) for x,y in zip(points,points[1:])]
    b=[add(mul(x,1-t),mul(y,t)) for x,y in zip(a,a[1:])]
    c=add(mul(b[0],1-t),mul(b[1],t))
    return [points[0],a[0],b[0],c]


def round_phi_join(root):
    contour=root.find('.//contour');pts=list(contour)
    i=next(i for i,p in enumerate(pts) if math.dist(xy(p),(307,15))<.002)
    curve=[xy(p) for p in pts[i-3:i+1]];lo,hi=0.,1.
    # [РЕШЕНИЕ] A local8-unit fillet replaces the sharp re-entrant corner.
    for _ in range(60):
        t=(lo+hi)/2;left=split_cubic(curve,t)
        if math.dist(left[-1],curve[-1])>8:lo=t
        else:hi=t
    left=split_cubic(curve,(lo+hi)/2);a=left[-1];b=(307,7)
    put(pts[i-2],left[1]);put(pts[i-1],left[2]);put(pts[i],a)
    c1=add(a,mul(unit(sub(a,left[2])),4.8));c2=(307,11.8)
    for offset,(v,typ) in enumerate(((c1,None),(c2,None),(b,'curve')),1):
        p=ET.Element('point');put(p,v)
        if typ:p.set('type',typ);p.set('smooth','yes')
        contour.insert(i+offset,p)
    pts[i].set('smooth','yes')


def clean_tail_hairline(root):
    """Remove the SVG exporter backtrack only0.025 units high."""
    count=0
    for contour in root.findall('.//contour'):
        pts=list(contour)
        for i,a in enumerate(pts):
            if a.get('type')!='line' or xy(a)[1]>=0:continue
            for j in range(i+3,min(i+10,len(pts))):
                b=pts[j]
                if b.get('type')!='curve':continue
                if math.dist(xy(a),xy(b))<.1 and max(xy(v)[0] for v in pts[i:j+1])-xy(a)[0]>5:
                    for node in pts[i:j]:contour.remove(node)
                    b.set('type','line');b.attrib.pop('smooth',None);count+=1;break
            if count:break
    return count


def fix(ch,item):
    source=Path(item.get('original_glif',item['path']))
    raw=source.read_bytes();root=ET.fromstring(raw);before=load_path(root)
    operations=[]
    if ch in 'щқ':
        outline=root.find('outline');contours=list(outline.findall('contour'))
        for node,shape in zip(contours,list(before.contours)):
            if shape.area<2:
                outline.remove(node);operations.append({'remove_microcontour_area':shape.area})
        body=load_path(root);clean=pathops.simplify(body)
        assert abs(clean.area-body.area)<.02
        assert len(list(clean.contours))==1
        # Preserve the simplified body only; tiny loops are archived in source.
        meta=SimpleNamespace();readGlyphFromString(ET.tostring(root,encoding='unicode'),meta)
        root=ET.fromstring(writeGlyphToString(root.get('name'),meta,
            lambda pp:clean.draw(SegmentToPointPen(pp)),formatVersion=2))
    if ch=='ф':
        old_slices=runs(before,250);params=json.loads(Path('data/params.json').read_text())
        wall=params['regular']['stems_hairlines']['o_side']
        left_outer=old_slices[0][0];left_inner=old_slices[0][1]
        right_inner=old_slices[-1][0];right_outer=old_slices[-1][1]
        factors={1:((right_outer-wall-307)/(right_inner-307),307),
                 2:((239-left_outer-wall)/(239-left_inner),239)}
        for idx,(factor,anchor) in factors.items():
            for node in root.findall('.//contour')[idx]:
                x,y=xy(node);put(node,(anchor+(x-anchor)*factor,y))
        operations.append({'bowl_wall_at_y250':wall,'counter_x_factors':factors})
        round_phi_join(root);operations.append({'fillet_at':[307,15],'trim_distance':8})
    else:
        removed=clean_tail_hairline(root)
        if removed:operations.append({'remove_exporter_tail_backtrack':removed,'height_under':.1})
    # Reviewed nodes only. Head-serif corners are deliberately excluded.
    candidate=copy.deepcopy(item);temp=DATA/'working.glif'
    temp.write_bytes(ET.tostring(root));candidate['path']=str(temp)
    r=inspect(ch,candidate)
    for joint in r['tangent_candidates']:
        x,y=joint['xy']
        repair=(ch in 'щқЩҚ' and y<120 and joint['angle']<25 or
                ch=='ф' and math.dist((x,y),(312,466))<.01)
        if repair:
            smooth_at(root,(x,y));operations.append({'align_tangents_at':[x,y],'old_angle':joint['angle']})
    temp.unlink()
    filename=DATA/f'uni{ord(ch):04X}-{item["role"]}.glif'
    note=root.find('note')
    if note is None:note=ET.SubElement(root,'note')
    note.text='[РЕШЕНИЕ · 16.10.2026] Локальные исправления авторских кривых по запросу пользователя; исходный GLIF сохранён в '+str(source)+'. Операции перечислены в data/author-curve-fixes/manifest.json. F-детали и форма хвоста сохранены; у ф уточнены вес чаш и нижний стык. Интервалы предварительные.'
    ET.indent(root,space='  ');ET.ElementTree(root).write(filename,encoding='utf-8',xml_declaration=True)
    after=load_path(root);updated=copy.deepcopy(item)
    updated.update(path=str(filename),original_glif=str(source),
                   original_glif_sha256=hashlib.sha256(raw).hexdigest(),
                   glif_sha256=hashlib.sha256(filename.read_bytes()).hexdigest(),
                   bounds=list(after.bounds),contours=len(list(after.contours)),
                   note=note.text,
                   status='author drawing with local curve repairs requested by user')
    check=inspect(ch,updated)
    assert check['open_contours']==0 and check['matches_registered_hash']
    assert all(v['simple_approx'] for v in check['ring_diagnostics'])
    assert len(list(after.contours))==(3 if ch=='ф' else 1)
    if ch=='ф':
        sections=runs(after,250)
        assert all(abs((b-a)-76)<.02 for a,b in (sections[0],sections[-1]))
        assert abs((sections[1][1]-sections[1][0])-68)<.02
    return updated,{'character':ch,'role':item['role'],'source':str(source),
                    'path':str(filename),'operations':operations,
                    'area_before':before.area,'area_after':after.area,
                    'bounds_before':list(before.bounds),'bounds_after':list(after.bounds),
                    'remaining_tangent_candidates':check['tangent_candidates']}


def render(records):
    from alphabet_sheet import canvas,text,glyph
    import matplotlib.pyplot as plt
    output=Path('build/author-curve-fixes');output.mkdir(parents=True,exist_ok=True)
    fig,ax=canvas(2100,1350)
    text(ax,40,20,'Правки авторских контуров · сверху исходник, снизу исправление',30)
    for i,ch in enumerate(TARGETS):
        r=next(v for v in records if v['character']==ch and v['role']=='primary')
        x=210+i*420;scale=min(.45,370/(r['bounds_before'][2]-r['bounds_before'][0]))
        for baseline,key,color in [(590,'source','#9a9390'),(1160,'path','#272333')]:
            glyph(ax,r[key],x,baseline,scale,color)
        text(ax,x,100,ch,28,ha='center')
    text(ax,40,1290,'Форма хвостов сохранена. У ф изменён вес чаш; у остальных — только локальные стыки и микроконтуры.',22)
    fig.savefig('docs/img/author_curve_fixes.svg');fig.savefig(output/'comparison.png',dpi=100);plt.close(fig)


def main():
    DATA.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());manifest=[]
    if cfg.get('tail_styles',{}).get('active')=='drop':
        raise SystemExit('Current tails are drop variants. Base repairs are already retained in tail_alternatives; use tools/drop_tail_variants.py to refresh without reverting tail choice.')
    for ch in TARGETS:
        for i,item in enumerate(cfg['user'][ch]['variants']):
            updated,record=fix(ch,item);cfg['user'][ch]['variants'][i]=updated;manifest.append(record)
        cfg['user'][ch]['status']='author geometry locally repaired at user request; metrics provisional'
    # Register every active purple primary; the old checker skipped8 of them.
    context=json.loads(Path('data/context/serif_bl.json').read_text())
    from check_context_classes import load,test,test_top
    for ch,entry in cfg['user'].items():
        if entry.get('origin')=='Claude':continue
        primary=next(v for v in entry['variants'] if v['role']=='primary')
        context['built_bases'][ch]=primary['path'];p=load(primary['path'])
        for rule,inside in [(context,test(p)[0])]+([(context['ka_short'],test_top(p)[0])] if ch.islower() else []):
            members=rule['declared_class']['lower' if ch.islower() else 'upper'];outside=rule['expected_not_in_class']
            if ch in members:members.remove(ch)
            if ch in outside:outside.remove(ch)
            (members if inside else outside).append(ch)
    event='16.10.2026: по запросу пользователя исправлены микроконтуры щ/қ, стыки щ/қ/Щ/Қ и вес чаш/острый стык ф; все активные авторские основы включены в геометрическую проверку calt.'
    if event not in context['history']:context['history'].append(event)
    for target,data in [(Path('data/alphabet.json'),cfg),(Path('data/context/serif_bl.json'),context),
                        (DATA/'manifest.json',manifest)]:
        target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    render(manifest)


if __name__=='__main__':main()
