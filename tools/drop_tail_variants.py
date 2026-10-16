#!/usr/bin/env python3
"""[РЕШЕНИЕ] Teardrop tails from the user's reference; old tails retained.

Run from repository root. Only the below-baseline tail interval is redrawn.
The old primary/alternate/context GLIFs are referenced as tail alternatives.
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
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
from audit_author_glyphs import inspect,rectangle

DATA=Path('data/drop-tail-variants')
BUILD=Path('build/drop-tail-variants')
CHARS='цщқңЦЩҚҢ'


def xy(p):return float(p.get('x')),float(p.get('y'))
def unit(v):
    n=math.hypot(*v);return v[0]/n,v[1]/n
def path_from(root):
    p=pathops.Path();readGlyphFromString(ET.tostring(root,encoding='unicode'),SimpleNamespace(),PointToSegmentPen(p.getPen()));return p


def transform(ch,item):
    source=Path(item['path']);root=ET.fromstring(source.read_bytes());original=path_from(root)
    outline=root.find('outline');changed=False
    for contour in outline.findall('contour'):
        pts=list(contour);on=[p for p in pts if p.get('type')]
        ys=[xy(p)[1] for p in on]
        if min(ys)>-150:continue
        k=ys.index(min(ys));a=b=k
        while ys[(a-1)%len(on)]<0:a=(a-1)%len(on)
        while ys[(b+1)%len(on)]<0:b=(b+1)%len(on)
        first,last=on[a],on[b];i,j=pts.index(first),pts.index(last)
        assert i<j,'Unexpected wrapping tail'
        ax,ay=xy(first);bx,by=xy(last)
        incoming=unit((ax-xy(pts[i-1])[0],ay-xy(pts[i-1])[1]))
        outgoing=unit((xy(pts[j+1])[0]-bx,xy(pts[j+1])[1]-by))
        assert incoming[1]<0 and outgoing[1]>0
        # [РЕШЕНИЕ] Reference proportions: rounded terminal, about130 deep.
        # Scale the module by the existing tail neck, not by the Latin body.
        s=(bx-ax)/46
        d=(ax+65*s,-126*s);e=(ax+126*s,-95*s);f=(ax+85*s,-52*s)
        segments=[((ax+incoming[0]*35*s,ay+incoming[1]*35*s),(ax+30*s,-112*s),d),
                  ((ax+89.5*s,-135.8*s),(ax+126*s,-123*s),e),
                  ((ax+126*s,-70*s),(ax+110*s,-52*s),f),
                  ((ax+58*s,-52*s),(bx-outgoing[0]*27*s,by-outgoing[1]*27*s),(bx,by))]
        for node in pts[i+1:j+1]:contour.remove(node)
        insertion=i+1
        for c1,c2,end in segments:
            for coords,kind in ((c1,None),(c2,None),(end,'curve')):
                node=ET.Element('point',x=format(coords[0],'.12g'),y=format(coords[1],'.12g'))
                if kind:node.set('type',kind);node.set('smooth','yes')
                contour.insert(insertion,node);insertion+=1
        changed=True;break
    assert changed,'No author tail interval found'
    note=root.find('note')
    if note is None:note=ET.SubElement(root,'note')
    note.text='[РЕШЕНИЕ · 16.10.2026] Основной хвост заменён каплевидным по изображению пользователя. Корпус выше базовой линии и ширина сохранены. Прежний хвост доступен как альтернатива: '+str(source)+'. Кривые окончания — новое предложение; финальные интервалы открыты.'
    filename=DATA/f'uni{ord(ch):04X}-{item["role"]}.glif'
    ET.indent(root,space='  ');ET.ElementTree(root).write(filename,encoding='utf-8',xml_declaration=True)
    current=path_from(root)
    # Exact geometric preservation above baseline; no debris or holes added.
    difference=pathops.op(original,current,pathops.PathOp.XOR)
    above=pathops.op(difference,rectangle(-1000,0,3000,2000),pathops.PathOp.INTERSECTION)
    assert above.area<.02,(ch,above.area)
    assert len(list(current.contours))==len(list(original.contours))
    result=copy.deepcopy(item)
    result.update(path=str(filename),glif_sha256=hashlib.sha256(filename.read_bytes()).hexdigest(),
                  bounds=list(current.bounds),contours=len(list(current.contours)),tail_style='drop',
                  tail_source_glif=str(source),note=note.text,
                  status='author body; new drop tail requested by user; metrics provisional')
    audit=inspect(ch,result)
    assert all(r['simple_approx'] for r in audit['ring_diagnostics'])
    assert audit['open_contours']==0 and audit['matches_registered_hash']
    return result,{'character':ch,'role':item['role'],'source':str(source),'path':str(filename),
                   'bounds_before':list(original.bounds),'bounds_after':list(current.bounds),
                   'body_difference_area_above_baseline':above.area,
                   'width_preserved':float(root.find('advance').get('width')),
                   'tangent_candidates':audit['tangent_candidates']}


def render(cfg):
    from alphabet_sheet import canvas,text,glyph
    import matplotlib.pyplot as plt
    fig,ax=canvas(2200,1550)
    text(ax,40,25,'Хвостики: сверху прежняя альтернатива, снизу новая капля',30)
    for i,ch in enumerate(CHARS):
        x=275+(i%4)*550;y=(i//4)*720
        entry=cfg['user'][ch]
        old=next(v for v in entry['tail_alternatives'] if v['role']=='primary')
        new=next(v for v in entry['variants'] if v['role']=='primary')
        scale=min(.31,450/(old['bounds'][2]-old['bounds'][0]))
        text(ax,x,y+105,ch,26,ha='center')
        glyph(ax,old['path'],x,y+395,scale,'#9a9390')
        glyph(ax,new['path'],x,y+690,scale)
    fig.savefig('docs/img/drop_tail_variants.svg');fig.savefig(BUILD/'comparison.png',dpi=100);plt.close(fig)


def main():
    DATA.mkdir(parents=True,exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());manifest=[]
    for ch in CHARS:
        entry=cfg['user'][ch]
        if 'tail_alternatives' not in entry:entry['tail_alternatives']=copy.deepcopy(entry['variants'])
        entry['variants']=[]
        for old in entry['tail_alternatives']:
            new,record=transform(ch,old);entry['variants'].append(new);manifest.append(record)
        entry['tail_style']='drop';entry['status']='author body; drop tail primary, previous tail alternative'
    cfg['tail_styles']={'active':'drop','alternative':'previous',
        'characters':list(CHARS),'note':'Previous locally repaired tails retained per glyph in tail_alternatives; OpenType stylistic-set number not assigned.'}
    context=json.loads(Path('data/context/serif_bl.json').read_text())
    from check_context_classes import load,test,test_top
    for ch in CHARS:
        item=next(v for v in cfg['user'][ch]['variants'] if v['role']=='primary')
        context['built_bases'][ch]=item['path'];p=load(item['path'])
        for rule,inside in [(context,test(p)[0])]+([(context['ka_short'],test_top(p)[0])] if ch.islower() else []):
            members=rule['declared_class']['lower' if ch.islower() else 'upper'];outside=rule['expected_not_in_class']
            if ch in members:members.remove(ch)
            if ch in outside:outside.remove(ch)
            (members if inside else outside).append(ch)
    event='16.10.2026: по изображению пользователя каплевидные хвосты сделаны основными у ц щ қ ң Ц Щ Қ Ң; прежние исправленные хвосты сохранены в tail_alternatives.'
    if event not in context['history']:context['history'].append(event)
    for target,data in [(Path('data/alphabet.json'),cfg),(Path('data/context/serif_bl.json'),context),(DATA/'manifest.json',manifest)]:
        target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    render(cfg);print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
