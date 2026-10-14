"""Select approved Cyrillic i and build two short-i studies from native breve.

No other builders are imported: prior fonts and glyphs are immutable inputs.
"""
from pathlib import Path
import copy, json, hashlib, math
from glyphsLib import GSFont, GSGlyph, GSLayer, GSAnchor, GSComponent, GSFeature
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.otlLib.builder import buildLookup, buildSingleSubstSubtable, buildLigatureSubstSubtable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.basePen import BasePen
import uharfbuzz as hb
import numpy as np
from shapely.geometry import Polygon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch

import argparse
from prepare_reference import verify_reference
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=ROOT/'build/regular')
parser.add_argument('--reference-dir', type=Path, default=ROOT/'reference/instrument-serif')
args = parser.parse_args()
REFERENCE = verify_reference(args.reference_dir)
OUT = args.output_dir.resolve()/'shorti'
OUT.mkdir(parents=True, exist_ok=True)
I = ROOT/'studies/regular/i'
SELECTED = args.output_dir.resolve()/'i-selected'
SELECTED.mkdir(parents=True, exist_ok=True)
SOURCE = GSFont(str(REFERENCE/'sources/Instrument_Serif.glyphs'))
ORIGINAL = TTFont(REFERENCE/'fonts/ttf/InstrumentSerif-Regular.ttf')
PROGRESS = OUT/'progress.json'
if not PROGRESS.exists():
    PROGRESS.write_bytes((ROOT/'data/progress.json').read_bytes())

def add_feature(tt, tag, lookup):
    table = tt['GSUB'].table
    li = len(table.LookupList.Lookup)
    table.LookupList.Lookup.append(lookup)
    table.LookupList.LookupCount = li + 1
    # Append to existing tag, preserving all original feature registrations.
    existing = [r for r in table.FeatureList.FeatureRecord if r.FeatureTag == tag]
    if existing:
        assert len(existing) == 1, tag
        existing[0].Feature.LookupListIndex.append(li)
        existing[0].Feature.LookupCount += 1
        return
    record = otTables.FeatureRecord()
    record.FeatureTag = tag
    record.Feature = otTables.Feature()
    record.Feature.FeatureParams = None
    record.Feature.LookupListIndex = [li]
    record.Feature.LookupCount = 1
    old = list(table.FeatureList.FeatureRecord)
    combined = old + [record]
    ordered = sorted(combined, key=lambda r: r.FeatureTag)
    remap = {i: next(j for j,r in enumerate(ordered) if r is item) for i,item in enumerate(combined)}
    for sr in table.ScriptList.ScriptRecord:
        langs = ([sr.Script.DefaultLangSys] if sr.Script.DefaultLangSys else []) + [r.LangSys for r in sr.Script.LangSysRecord]
        for lang in langs:
            lang.FeatureIndex = sorted([remap[i] for i in lang.FeatureIndex] + [remap[len(old)]])
            lang.FeatureCount = len(lang.FeatureIndex)
            if lang.ReqFeatureIndex != 65535:
                lang.ReqFeatureIndex = remap[lang.ReqFeatureIndex]
    table.FeatureList.FeatureRecord = ordered
    table.FeatureList.FeatureCount = len(ordered)

def add_order(tt, names):
    # Decode tables while the original glyph and metric counts still match.
    _ = tt['glyf'];_ = tt['hmtx'];_ = tt['loca']
    tt.setGlyphOrder(tt.getGlyphOrder() + list(names))
    tt['hhea'].numberOfHMetrics = len(tt.getGlyphOrder())
    tt['maxp'].numGlyphs = len(tt.getGlyphOrder())

def mark_base(tt, name, donor, top=None):
    gid = tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for sub in lookup.SubTable:
            if donor not in sub.BaseCoverage.glyphs:
                continue
            records = dict(zip(sub.BaseCoverage.glyphs, sub.BaseArray.BaseRecord))
            record = copy.deepcopy(records[donor])
            if top is not None:
                # Original top mark class is 0, as verified on u/breve.
                record.BaseAnchor[0].XCoordinate, record.BaseAnchor[0].YCoordinate = top
            records[name] = record
            sub.BaseCoverage.glyphs = sorted(records, key=gid.get)
            sub.BaseArray.BaseRecord = [records[n] for n in sub.BaseCoverage.glyphs]
            sub.BaseArray.BaseCount = len(records)

def inherit_native_kern(tt, aliases):
    """Transfer existing pairs/classes only to exact native-u bodies."""
    gid = tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType != 2:
            continue
        for sub in lookup.SubTable:
            if sub.Format == 2:
                coverage = set(sub.Coverage.glyphs)
                for target, donor in aliases.items():
                    if donor in coverage:
                        coverage.add(target)
                    for cd in [sub.ClassDef1, sub.ClassDef2]:
                        if donor in cd.classDefs:
                            cd.classDefs[target] = cd.classDefs[donor]
                sub.Coverage.glyphs = sorted(coverage, key=gid.get)
            elif sub.Format == 1:
                records = dict(zip(sub.Coverage.glyphs, sub.PairSet))
                original = copy.deepcopy(records)
                for target, donor in aliases.items():
                    if donor in original:
                        records[target] = copy.deepcopy(original[donor])
                for record in records.values():
                    pairs = {r.SecondGlyph:r for r in record.PairValueRecord}
                    oldpairs = dict(pairs)
                    for target, donor in aliases.items():
                        if donor in oldpairs:
                            r = copy.deepcopy(oldpairs[donor]);r.SecondGlyph = target
                            pairs[target] = r
                    record.PairValueRecord = [pairs[n] for n in sorted(pairs,key=gid.get)]
                    record.PairValueCount = len(record.PairValueRecord)
                sub.Coverage.glyphs = sorted(records, key=gid.get)
                sub.PairSet = [records[n] for n in sub.Coverage.glyphs]
                sub.PairSetCount = len(records)

def names(tt, suffix):
    family = 'Very Peri Regular Study ' + suffix
    values = {1:family,2:'Regular',3:family+';2026;study',4:family+' Regular',6:'VeryPeriRegularStudy'+suffix+'-Regular',16:family,17:'Regular'}
    for r in tt['name'].names:
        if r.nameID in values:
            r.string = values[r.nameID].encode(r.getEncoding())

def save_font(tt, path):
    tt.flavor = None;tt.save(path.with_suffix('.ttf'))
    tt = TTFont(path.with_suffix('.ttf'))
    tt.flavor = 'woff2';tt.save(path.with_suffix('.woff2'));tt.flavor = None
    return tt

def hb_shape(path, text, features=None):
    tt = TTFont(path);f = hb.Font(hb.Face(path.read_bytes()));f.scale = (1000,1000)
    b = hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(f,b,features or {})
    result = [(tt.getGlyphOrder()[g.codepoint],p.x_advance,p.y_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]
    assert all(g.codepoint for g in b.glyph_infos), text
    return result

base = TTFont(I/'i-02.ttf')
_=base['GSUB'].table;_=base['GPOS'].table
diagonal = TTFont(I/'i-01.ttf')
add_order(base,['i.altDiagonal'])
base['glyf']['i.altDiagonal'] = copy.deepcopy(diagonal['glyf']['uni0438'])
base['hmtx']['i.altDiagonal'] = diagonal['hmtx']['uni0438']
base['GDEF'].table.GlyphClassDef.classDefs['i.altDiagonal'] = 1
add_feature(base,'ss07',buildLookup([buildSingleSubstSubtable({'uni0438':'i.altDiagonal'})]))
mark_base(base,'uni0438','u');mark_base(base,'i.altDiagonal','n')
inherit_native_kern(base,{'uni0438':'u'})
names(base,'ISelected')
base = save_font(base,SELECTED/'VeryPeri-I-selected')

sf = GSFont(str(I/'i-02.glyphs'));sf.familyName = 'Very Peri Regular Study ISelected'
sf.glyphs['uni0438'].layers[0].anchors = [GSAnchor(a.name,tuple(a.position)) for a in SOURCE.glyphs['u'].layers[0].anchors]
ag = copy.deepcopy(GSFont(str(I/'i-01.glyphs')).glyphs['uni0438'])
ag.name = 'i.altDiagonal';ag.unicode = None
ag.layers[0].anchors = [GSAnchor(a.name,tuple(a.position)) for a in SOURCE.glyphs['n'].layers[0].anchors]
sf.glyphs.append(ag);sf.features.append(GSFeature('ss07','sub uni0438 by i.altDiagonal;'))
sf.save(str(SELECTED/'VeryPeri-I-selected.glyphs'))
assert hb_shape(SELECTED/'VeryPeri-I-selected.ttf','и')[0][0]=='uni0438'
assert hb_shape(SELECTED/'VeryPeri-I-selected.ttf','и',{'ss07':True})[0][0]=='i.altDiagonal'

def composite(tt, name, components, width, lsb):
    pen = TTGlyphPen(tt.getGlyphSet())
    for glyph, transform in components:
        pen.addComponent(glyph,transform)
    tt['glyf'][name] = pen.glyph();tt['hmtx'][name] = (width,lsb)

def sf_component(sf, name, unicode, components, width, anchors):
    g = GSGlyph(name);g.unicode = unicode;l = GSLayer()
    l.layerId = sf.masters[0].id;l.associatedMasterId = l.layerId;l.width = width
    for glyph, transform in components:
        c = GSComponent(glyph);c.transform = transform;l.components.append(c)
    for aname,xy in anchors:
        l.anchors.append(GSAnchor(aname,xy))
    g.layers.append(l);sf.glyphs.append(g)

class FlatPen(BasePen):
    def __init__(self,gs):
        super().__init__(gs);self.rings=[];self.points=[];self.p=None
    def _moveTo(self,p):self.p=np.array(p);self.points=[tuple(p)]
    def _lineTo(self,p):self.p=np.array(p);self.points.append(tuple(p))
    def _curveToOne(self,a,b,c):
        t=np.linspace(0,1,600)[1:,None];p0=self.p;p1=np.array(a);p2=np.array(b);p3=np.array(c)
        points=(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
        self.points.extend(map(tuple,points));self.p=p3
    def _closePath(self):self.rings.append(self.points);self.points=[]

metrics={};fonts={}
for v in ['01','02']:
    tt=TTFont(SELECTED/'VeryPeri-I-selected.ttf');_=tt['GSUB'].table;_=tt['GPOS'].table
    fs=GSFont(str(SELECTED/'VeryPeri-I-selected.glyphs'))
    add_order(tt,['uni0439','shorti.altDiagonal'] + (['breve.shortCompact'] if v=='02' else []))
    if v=='01':
        mark='uni0306';source_mark='brevecomb';shift_main=(12,0);shift_alt=(31,0);top=730
    else:
        mark='breve.shortCompact';source_mark=mark;shift_main=(0,0);shift_alt=(19,0);top=665
        # Similarity transform preserves all donor tangent directions and node count.
        transform=(.70,0,0,.70,216-.70*204,559-.70*579)
        pen=TTGlyphPen(None)
        SOURCE.glyphs['brevecomb'].layers[0].draw(TransformPen(Cu2QuPen(pen,max_err=.20,reverse_direction=True),transform))
        tt['glyf'][mark]=pen.glyph()
        tt['glyf'][mark].recalcBounds(tt['glyf'])
        # Native TrueType xMin includes rounded quadratic control extrema.
        # Match LSB to it so fontTools/FreeType do not shift the mark by 1 unit.
        tt['hmtx'][mark]=(0,tt['glyf'][mark].xMin)
        g=GSGlyph(mark);l=GSLayer();l.layerId=fs.masters[0].id;l.associatedMasterId=l.layerId;l.width=0
        SOURCE.glyphs['brevecomb'].layers[0].draw(TransformPen(l.getPen(),transform))
        l.anchors.append(GSAnchor('_top',(216,510)))
        l.anchors.append(GSAnchor('top',(216,665)))
        g.layers.append(l);fs.glyphs.append(g)
        tt['GDEF'].table.GlyphClassDef.classDefs[mark]=3
    for target,body,dxdy,width,lsb,cx in [('uni0439','uni0438',shift_main,454,11,216),('shorti.altDiagonal','i.altDiagonal',shift_alt,470,15,235)]:
        dx,dy=dxdy
        composite(tt,target,[(body,(1,0,0,1,0,0)),(mark,(1,0,0,1,dx,dy))],width,lsb)
        anchors=[(a.name,(cx,top) if a.name=='top' else tuple(a.position)) for a in fs.glyphs[body].layers[0].anchors]
        sf_component(fs,target,'0439' if target=='uni0439' else None,[(body,(1,0,0,1,0,0)),(source_mark,(1,0,0,1,dx,dy))],width,anchors)
        tt['GDEF'].table.GlyphClassDef.classDefs[target]=1
        mark_base(tt,target,'ubreve' if body=='uni0438' else 'n',top=(cx,top))
    for tab in tt['cmap'].tables:
        if tab.isUnicode():tab.cmap[0x439]='uni0439'
    # ss07 follows the already selected alternate i skeleton, including й.
    for lookup in tt['GSUB'].table.LookupList.Lookup:
        if lookup.LookupType==1:
            for sub in lookup.SubTable:
                if getattr(sub,'mapping',{}).get('uni0438')=='i.altDiagonal':
                    sub.mapping['uni0439']='shorti.altDiagonal'
    fs.features['ss07'].code += '\nsub uni0439 by shorti.altDiagonal;'
    add_feature(tt,'ccmp',buildLookup([buildLigatureSubstSubtable({('uni0438','uni0306'):'uni0439'})]))
    fs.features['ccmp'].code += '\nsub uni0438 brevecomb by uni0439;'
    inherit_native_kern(tt,{'uni0439':'ubreve'})
    names(tt,'ShortI'+v);fs.familyName='Very Peri Regular Study ShortI'+v
    tt=save_font(tt,OUT/f'shorti-{v}');fs.save(str(OUT/f'shorti-{v}.glyphs'))
    gs=tt.getGlyphSet();bp=BoundsPen(gs);gs['uni0439'].draw(bp)
    svgpen=SVGPathPen({g.name:g.layers[0] for g in fs.glyphs});fs.glyphs['uni0439'].layers[0].draw(svgpen)
    (OUT/f'shorti-{v}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 510 850"><title>й — вариант {v}</title><g transform="translate(20 790) scale(1 -1)"><path d="{svgpen.getCommands()}" fill="#282334"/></g></svg>')
    flat=FlatPen(gs);gs['uni0439'].draw(flat)
    assert len(flat.rings)==2 and all(Polygon(r).is_valid for r in flat.rings)
    assert Polygon(flat.rings[0]).disjoint(Polygon(flat.rings[1]))
    for text in ['й','и\u0306','йй','и\u0306и\u0306','йод','бой','дай','йoga','й\u0301']:
        hb_shape(OUT/f'shorti-{v}.ttf',text)
    assert hb_shape(OUT/f'shorti-{v}.ttf','й')==hb_shape(OUT/f'shorti-{v}.ttf','и\u0306')
    assert hb_shape(OUT/f'shorti-{v}.ttf','й',{'ss07':True})==hb_shape(OUT/f'shorti-{v}.ttf','и\u0306',{'ss07':True})
    assert hb_shape(OUT/f'shorti-{v}.ttf','и',{'ss07':True})[0][0]=='i.altDiagonal'
    assert hb_shape(OUT/f'shorti-{v}.ttf','й',{'ss07':True})[0][0]=='shorti.altDiagonal'
    for name in base.getGlyphOrder():
        assert base['glyf'][name].compile(base['glyf'])==tt['glyf'][name].compile(tt['glyf']),name
        assert base['hmtx'][name]==tt['hmtx'][name],name
    if v=='01':
        assert tt['glyf']['uni0439'].getCoordinates(tt['glyf'])[0]==ORIGINAL['glyf']['ubreve'].getCoordinates(ORIGINAL['glyf'])[0]
    assert TTFont(OUT/f'shorti-{v}.woff2').getBestCmap()[0x439]=='uni0439'
    assert GSFont(str(OUT/f'shorti-{v}.glyphs')).glyphs['uni0439'].unicode=='0439'
    metrics[v]={'name':'Родная кратка' if v=='01' else 'Компактная кратка','unicode':'U+0439','advance':454,'body':'byte-identical approved u-shaped и','bounds_ttf':bp.bounds,'contours_decomposed':2,'mark_center':216,'mark_scale':1 if v=='01' else .7,'mark_cubic_nodes':24,'mark_y_cubic':[579,730] if v=='01' else [559,664.7],'gap_above_body':69 if v=='01' else 49,'mark_bottom_thickness_cubic':57 if v=='01' else 39.9,'new_cyrillic_kerning':'pending; exact native u/ubreve positioning inherited','checks':{'sampled_contours_valid':True,'contours_disjoint':True,'previous_outlines_and_hmtx_unchanged':True,'precomposed_decomposed_match':True,'ss07_i_and_shorti_verified':True,'ttf_woff2_glyphs_reopened':True,'first_matches_native_ubreve_coordinates':v=='01'}}
    fonts[v]=tt

class PlotPen(BasePen):
    def __init__(self,gs):super().__init__(gs);self.v=[];self.c=[]
    def _moveTo(self,p):self.v.append(p);self.c.append(MP.MOVETO)
    def _lineTo(self,p):self.v.append(p);self.c.append(MP.LINETO)
    def _curveToOne(self,a,b,c):self.v.extend([a,b,c]);self.c.extend([MP.CURVE4]*3)
    def _closePath(self):self.v.append((0,0));self.c.append(MP.CLOSEPOLY)
def draw(ax,tt,name,x=0,y=0,scale=1,color='#282334'):
    gs=tt.getGlyphSet();pen=PlotPen(gs);gs[name].draw(pen)
    if pen.v:ax.add_patch(PathPatch(MP(np.array(pen.v)*scale+[x,y],pen.c),facecolor=color,lw=0))
def word(ax,text,v,x,y,scale):
    for name,adv,_,dx,dy in hb_shape(OUT/f'shorti-{v}.ttf',text,{'liga':False}):
        draw(ax,fonts[v],name,x+dx*scale,y+dy*scale,scale);x+=adv*scale

fig=plt.figure(figsize=(16,14),facecolor='#f5f1e9')
fig.text(.055,.957,'Instrument Serif / строчная й',fontsize=27,color='#282334')
fig.text(.055,.92,'Основа — выбранная чашеобразная и · два рисунка кратки',fontsize=12,color='#827b73')
for idx,v in enumerate(['01','02']):
    fig.text(.055+idx*.49,.868,f'{v} / {metrics[v]["name"]}',fontsize=19,color='#282334')
    ax=fig.add_axes([.08+idx*.49,.55,.34,.285]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-10,490);ax.set_ylim(-30,770)
    for y in [0,510,730]:ax.axhline(y,color='#c7c0b7',lw=.7,ls='--');ax.text(-8,y+8,str(y),fontsize=8,color='#827b73')
    draw(ax,fonts[v],'uni0439')
    proof=fig.add_axes([.055+idx*.49,.36,.425,.165]);proof.axis('off');proof.set_aspect('equal');proof.set_xlim(0,3600);proof.set_ylim(-170,950)
    for y in [0,510]:proof.axhline(y,color='#c7c0b7',lw=.6,ls='--')
    x=0
    for ch in ['й','и','ŭ','ă','u','n']:
        name=fonts[v].getBestCmap()[ord(ch)];draw(proof,fonts[v],name,x,color='#282334' if ch in ['й','и'] else '#8d8479')
        proof.text(x+fonts[v]['hmtx'][name][0]/2,875,ch,fontsize=10,ha='center',color='#827b73');x+=fonts[v]['hmtx'][name][0]+100
    line=fig.add_axes([.055+idx*.49,.10,.425,.235]);line.axis('off');line.set_aspect('equal');line.set_xlim(0,3800);line.set_ylim(-120,2400)
    for text,y in [('йод бой',1640),('дай гай',810),('ий йи йй',0)]:word(line,text,v,0,y,.7)
fig.text(.055,.05,'Серые знаки — оригинал. Диагональная и сохранена в ss07; й поддерживает ту же альтернативу.',fontsize=10,color='#827b73')
fig.text(.055,.027,'Проверены вектор, экспорт и «и + кратка». Специальные кириллические пары ещё не доведены.',fontsize=10,color='#827b73')
fig.savefig(OUT/'comparison.png',dpi=160,facecolor=fig.get_facecolor());fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());plt.close(fig)

for directory in [OUT,SELECTED]:(directory/'OFL.txt').write_bytes((I/'OFL.txt').read_bytes())
(OUT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
baseline=json.loads((I/'approved-baseline.json').read_text())
for name in ['uni0438','i.altDiagonal']:
    baseline['fixed_glyphs'][name]={'hmtx':list(base['hmtx'][name]),'glyf_sha256':hashlib.sha256(base['glyf'][name].compile(base['glyf'])).hexdigest()}
baseline['source_file']='VeryPeri-I-selected.ttf'
(SELECTED/'approved-baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n')
baseline['source_file']='shorti-01.ttf / shorti-02.ttf (й not selected yet)'
(OUT/'approved-baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n')
progress=json.loads(PROGRESS.read_text());progress['approved']['и']={'primary':'Чашеобразная','variant':'02','advance':454,'alternates':[{'name':'Прямая диагональ','variant':'01','feature':'ss07','advance':470}]}
progress['undecided_variants'].pop('и',None);progress['undecided_variants']['й']=['Родная кратка','Компактная кратка'];progress['latest_artifact']=str(OUT)
PROGRESS.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(metrics,ensure_ascii=False,indent=2))
