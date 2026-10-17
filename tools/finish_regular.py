#!/usr/bin/env python3
"""[РЕШЕНИЕ] Narrow ү/ұ, local weight corrections, required text symbols.
Original outlines are preserved. Run from repository root.
"""
import copy,hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sketchlib import Ref,AND,OR,SUB,rect,shift,tf,write_glif
from glyphparts import _rrect
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.pens.pointPen import PointToSegmentPen
import pathops

DATA=Path('data/regular-refinement')
SYMBOLS=Path('data/text-symbols')
PARAMS=json.loads(Path('data/params.json').read_text())
VERTICAL=PARAMS['regular']['vertical']
WEIGHT=PARAMS['regular']['stems_hairlines']

def narrow_u(ref):
    rec=RecordingPen();ref.gs['Y'].draw(rec)
    out=RecordingPen();drop=VERTICAL['flat_cap']-VERTICAL['flat_x']
    def delta(y):return 45*min(1,max(0,(y-370)/290))
    for i,(op,pts) in enumerate(rec.value):
        side=1 if 6<=i<=17 else -1 if 19<=i<=30 else 0
        moved=[(x+side*delta(y),y-drop) for x,y in pts]
        if i==6:
            # Cubic tangent adapter: vertical into the narrowing diagonal.
            endpoint=(194.,138.);upper=(47+delta(656),446.)
            dx=(upper[0]-endpoint[0])/(upper[1]-endpoint[1])
            out.curveTo((204,110),(endpoint[0]-dx*15,123),endpoint);continue
        if i==18:
            # Tangents meet both narrowed inner diagonals.
            start=out.value[-1][1][-1];end=(268-delta(391),181)
            left=(125+delta(653),443);right=(386-delta(632),422)
            moved=[(start[0]+(start[0]-left[0])/(start[1]-left[1])*(-7),174),
                   (end[0]-(right[0]-end[0])/(right[1]-end[1])*7,174),end]
        if i==30:
            start=out.value[-1][1][-1];prev=(419-delta(631),421)
            moved[0]=(start[0]+(start[0]-prev[0])/(start[1]-prev[1])*(-14),144)
        out.value.append((op,tuple(moved)))
    p=pathops.Path();out.replay(p.getPen())
    upper=AND(p,rect(-1000,-139,2000,1000))
    foot=AND(shift(ref.glyph('I'),115,-205),rect(-1000,-1000,2000,-139))
    return OR(upper,foot),ref.adv('Y')


def load(path):
    p=pathops.Path();meta=SimpleNamespace();readGlyphFromString(Path(path).read_text(),meta,PointToSegmentPen(p.getPen()));return p,meta.width

def local_weight(ch,source):
    root=ET.parse(source).getroot();pts=root.findall('.//point')
    if ch in 'Зз':
        # Inside edges only: outer silhouette and fine horizontal strokes stay.
        end=next(i for i,p in enumerate(pts) if p.get('type') and float(p.get('y'))==(405 if ch=='З' else 285))
        start=next(i for i,p in enumerate(pts) if p.get('type') and float(p.get('y'))==(18 if ch=='З' else 16))
        for p in pts[start+1:end]:
            if float(p.get('x')) >= (237 if ch=='З' else 228):p.set('x',str(float(p.get('x'))-(8 if ch=='З' else 6)))
        # Upper bowl inner vertical and adjacent handles.
        for p in pts[end+1:]:
            x,y=float(p.get('x')),float(p.get('y'))
            if (ch=='З' and x in (224,246,232) and 434<=y<=676) or (ch=='з' and x==222 and y>=412):
                p.set('x',str(x-(8 if ch=='З' else 6)))
    else:
        start=next(i for i,p in enumerate(pts) if float(p.get('x'))==326 and float(p.get('y'))==-5)
        end=next(i for i,p in enumerate(pts[start:],start) if float(p.get('x'))==300 and float(p.get('y'))==288)
        for p in pts[start:end+1]:p.set('x',str(float(p.get('x'))-5))
    p=pathops.Path();meta=SimpleNamespace();readGlyphFromString(ET.tostring(root,encoding='unicode'),meta,PointToSegmentPen(p.getPen()))
    return p,meta.width


def symbols(ref):
    # [РЕШЕНИЕ] Native outlines are reused without geometric scaling.
    p=ref.glyph('P');bar=WEIGHT['H_crossbar']
    rub=OR(p,_rrect(55,210,340,210+bar,4))
    # Hryvnia: native S and two horizontal strokes; native bowl weight retained.
    hry=OR(ref.glyph('S'),_rrect(20,300,390,300+bar,4),_rrect(20,390,390,390+bar,4))
    # Numero: native N plus a newly drawn small ring (no scaled Latin O).
    n=ref.glyph('N');dx=ref.adv('N')+8;ring=SUB(_rrect(dx,480,dx+152,720,76),_rrect(dx+30,510,dx+122,690,46))
    numero=OR(n,ring,_rrect(dx,425,dx+152,450,4))
    dotted=[];cx,cy,radius,dot=285,255,225,15
    for i in range(12):
        x=cx+radius*math.cos(i*math.tau/12);y=cy+radius*math.sin(i*math.tau/12)
        # True cubic circles, not a polygonal dotted outline.
        p=pathops.Path();q=p.getPen();k=.5522847498307936*dot
        q.moveTo((x+dot,y));q.curveTo((x+dot,y+k),(x+k,y+dot),(x,y+dot));q.curveTo((x-k,y+dot),(x-dot,y+k),(x-dot,y));q.curveTo((x-dot,y-k),(x-k,y-dot),(x,y-dot));q.curveTo((x+k,y-dot),(x+dot,y-k),(x+dot,y));q.closePath();dotted.append(p)
    return {'₽':(rub,ref.adv('P')),'₴':(hry,ref.adv('S')),'№':(numero,round(dx+182)),
            'ʼ':(ref.glyph('quoteright'),ref.adv('quoteright')),
            '‑':(ref.glyph('hyphen'),ref.adv('hyphen')),
            '\u2009':(pathops.Path(),200),'\u202f':(pathops.Path(),200),
            '◌':(OR(*dotted),570)}


def main():
    current=json.loads(Path('data/alphabet.json').read_text())
    if any(v['path'].startswith('data/width-refinement/') for section in ('user','codex') for e in current.get(section,{}).values() for v in e['variants']):
        print('Keeping width refinements; run tools/refine_widths.py to regenerate the active shapes.');return
    DATA.mkdir(exist_ok=True);SYMBOLS.mkdir(exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());ctx=json.loads(Path('data/context/serif_bl.json').read_text());ref=Ref();manifest={}
    shapes={};u,advance=narrow_u(ref);shapes['ү']=(u,advance)
    cy=VERTICAL['descender_p']/3;t=WEIGHT['e_crossbar']
    shapes['ұ']=(OR(u,_rrect(150.5,cy-t/2,328.5,cy+t/2,4)),advance)
    for ch in 'Ззч':
        source=f'data/codex/uni{ord(ch):04X}-01.glif';shapes[ch]=local_weight(ch,source)
    from check_context_classes import test,test_top
    for ch,(p,advance) in shapes.items():
        path=DATA/f'uni{ord(ch):04X}.glif';write_glif(p,f'uni{ord(ch):04X}',advance,ord(ch),str(path))
        old=cfg['codex'][ch]
        if not old['variants'][0]['path'].startswith(str(DATA)):
            cfg.setdefault('rejected_drawings',{})[ch+'-before-optical-review']=copy.deepcopy(old)
        item={'path':str(path),'variant':'01','label':'Уточнённая развилка' if ch in 'үұ' else 'Оптическая правка веса',
              'advance':advance,'bounds':list(p.bounds),'glif_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'status':'revised at user request; optical review proposal'}
        cfg['codex'][ch]=dict(selected=None,shared_with_claude=False,conflict=False,variants=[item],provenance='Codex; optical correction requested by user')
        ctx['built_bases'][ch]=str(path)
        for rule,inside in [(ctx,test(p)[0])]+([(ctx['ka_short'],test_top(p)[0])] if ch.islower() else []):
            members=rule['declared_class']['upper' if ch.isupper() else 'lower'];outside=rule['expected_not_in_class']
            if ch in members:members.remove(ch)
            if ch in outside:outside.remove(ch)
            (members if inside else outside).append(ch)
        manifest[ch]=item
    event='16.10.2026: сужены развилки ү/ұ; локально уточнён вес З/з/ч по оптической проверке и PDF пользователя; кернинг отложен.'
    if event not in ctx['history']:ctx['history'].append(event)
    for file,obj in [(Path('data/alphabet.json'),cfg),(Path('data/context/serif_bl.json'),ctx),(DATA/'manifest.json',manifest)]:file.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    entries={}
    for ch,(p,advance) in symbols(ref).items():
        path=SYMBOLS/f'uni{ord(ch):04X}.glif';write_glif(p,f'uni{ord(ch):04X}',advance,ord(ch),str(path))
        entries[ch]={'path':str(path),'advance':advance,'unicode':f'U+{ord(ch):04X}',
                     'glif_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'status':'required text symbol; draft design'}
    (SYMBOLS/'manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
