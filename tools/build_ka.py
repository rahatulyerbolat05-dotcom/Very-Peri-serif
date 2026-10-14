"""Two Cyrillic lowercase ka studies from exact native k and u fragments.

The cubic source and native TrueType outlines are edited independently so
all untouched donor coordinates retain their original precision.
"""
from pathlib import Path
from array import array
import copy, json, hashlib
from glyphsLib import GSFont, GSGlyph, GSLayer, GSPath, GSNode, GSAnchor
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
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
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'build/regular')
parser.add_argument('--reference-dir',type=Path,default=ROOT/'reference/instrument-serif')
parser.add_argument('--base-dir',type=Path,default=ROOT/'studies/regular/shorti')
args=parser.parse_args()
REFERENCE=verify_reference(args.reference_dir)
OUT=args.output_dir.resolve()/'ka'
OUT.mkdir(parents=True,exist_ok=True)
BASE=args.base_dir.resolve()
SOURCE=GSFont(str(REFERENCE/'sources/Instrument_Serif.glyphs'))
NATIVE=TTFont(REFERENCE/'fonts/ttf/InstrumentSerif-Regular.ttf')
WIDTH=SOURCE.glyphs['k'].layers[0].width
GLYPH='uni043A'
NAMES={'01':'Головка u','02':'Наклонная головка k'}
K_NODES=list(SOURCE.glyphs['k'].layers[0].paths[0].nodes)
U_NODES=list(SOURCE.glyphs['u'].layers[0].paths[0].nodes)
HEAD_DX=K_NODES[70].position[0]-U_NODES[48].position[0]
HEAD_DY=SOURCE.masters[0].xHeight-max(n.position[1] for n in K_NODES)

def cubic_shape(variant):
    kn=list(SOURCE.glyphs['k'].layers[0].paths[0].nodes)
    un=list(SOURCE.glyphs['u'].layers[0].paths[0].nodes)
    assert tuple(kn[70].position)==(142,305)
    assert tuple(kn[71].position)==(142,724)
    assert tuple(kn[90].position)==(74,640)
    assert tuple(kn[91].position)==(74,67)
    assert tuple(un[48].position)==(138,495)
    assert tuple(un[62].position)==(70,449)
    def clone(n,dx=0,dy=0):
        x,y=n.position;return GSNode((x+dx,y+dy),n.type,n.smooth)
    nodes=[clone(n) for n in kn[:71]]
    nodes += [clone(n,HEAD_DX,0) for n in un[48:63]] if variant=='01' else [clone(n,0,HEAD_DY) for n in kn[71:91]]
    nodes += [clone(n) for n in kn[91:]]
    p=GSPath();p.closed=True;p.nodes=nodes
    assert len(nodes)==(97 if variant=='01' else 102)
    # Every point outside the head is identical, including on/off-curve type.
    for old,new in zip(kn[:71]+kn[91:],list(p.nodes)[:71]+list(p.nodes)[-len(kn[91:]):]):
        assert tuple(old.position)==tuple(new.position) and old.type==new.type
    return p

def native_shape(variant):
    k=NATIVE['glyf']['k'];u=NATIVE['glyf']['u']
    assert list(k.endPtsOfContours)==[83]
    assert tuple(k.coordinates[9])==(74,640)
    assert tuple(k.coordinates[24])==(142,724)
    assert tuple(u.coordinates[5])==(70,449)
    assert tuple(u.coordinates[16])==(138,495)
    coords=list(k.coordinates[:9]);flags=list(k.flags[:9])
    if variant=='01':
        coords += [(x+HEAD_DX,y) for x,y in u.coordinates[5:17]];flags+=list(u.flags[5:17])
    else:
        coords += [(x,y+HEAD_DY) for x,y in k.coordinates[9:25]];flags+=list(k.flags[9:25])
    coords += list(k.coordinates[25:]);flags+=list(k.flags[25:])
    g=copy.deepcopy(k);g.coordinates=GlyphCoordinates(coords);g.flags=array('B',flags)
    g.endPtsOfContours=[len(coords)-1];g.numberOfContours=1
    # A new point layout must not retain instructions referencing old indices.
    g.program=Program();g.program.fromBytecode(b'')
    g.recalcBounds(NATIVE['glyf'])
    assert (g.xMin,g.yMin,g.xMax,g.yMax)==(15,0,451,510)
    assert list(g.coordinates[:9])+list(g.coordinates[-59:])==list(k.coordinates[:9])+list(k.coordinates[25:])
    return g

def inherit_kern(tt,target,donor):
    """Native k pairs as provisional starting values, not final ka kerning."""
    gid=tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType!=2:continue
        for s in lookup.SubTable:
            if s.Format==2:
                if donor in s.Coverage.glyphs:s.Coverage.glyphs=sorted(s.Coverage.glyphs+[target],key=gid.get)
                for cd in [s.ClassDef1,s.ClassDef2]:
                    if donor in cd.classDefs:cd.classDefs[target]=cd.classDefs[donor]
            elif s.Format==1:
                records=dict(zip(s.Coverage.glyphs,s.PairSet))
                if donor in records:records[target]=copy.deepcopy(records[donor])
                for record in records.values():
                    pairs={r.SecondGlyph:r for r in record.PairValueRecord}
                    if donor in pairs:
                        r=copy.deepcopy(pairs[donor]);r.SecondGlyph=target;pairs[target]=r
                    record.PairValueRecord=[pairs[n] for n in sorted(pairs,key=gid.get)]
                    record.PairValueCount=len(record.PairValueRecord)
                s.Coverage.glyphs=sorted(records,key=gid.get)
                s.PairSet=[records[n] for n in s.Coverage.glyphs];s.PairSetCount=len(records)

def mark_base(tt):
    gid=tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType!=4:continue
        for s in lookup.SubTable:
            if 'k' not in s.BaseCoverage.glyphs:continue
            records=dict(zip(s.BaseCoverage.glyphs,s.BaseArray.BaseRecord))
            r=copy.deepcopy(records['k']);r.BaseAnchor[0].XCoordinate=226;r.BaseAnchor[0].YCoordinate=510
            records[GLYPH]=r;s.BaseCoverage.glyphs=sorted(records,key=gid.get)
            s.BaseArray.BaseRecord=[records[n] for n in s.BaseCoverage.glyphs];s.BaseArray.BaseCount=len(records)

def shape(path,text,features=None):
    tt=TTFont(path);f=hb.Font(hb.Face(path.read_bytes()));f.scale=(1000,1000)
    b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(f,b,features or {})
    assert all(i.codepoint for i in b.glyph_infos),text
    return [(tt.getGlyphOrder()[i.codepoint],p.x_advance,p.y_advance,p.x_offset,p.y_offset) for i,p in zip(b.glyph_infos,b.glyph_positions)]

class FlatPen(BasePen):
    def __init__(self,gs=None):super().__init__(gs);self.rings=[];self.points=[];self.p=None
    def _moveTo(self,p):self.p=np.array(p);self.points=[tuple(p)]
    def _lineTo(self,p):self.p=np.array(p);self.points.append(tuple(p))
    def _curveToOne(self,a,b,c):
        t=np.linspace(0,1,600)[1:,None];p0=self.p;p1=np.array(a);p2=np.array(b);p3=np.array(c)
        pts=(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
        self.points.extend(map(tuple,pts));self.p=p3
    def _closePath(self):self.rings.append(self.points);self.points=[]

def check_outline(obj,gs=None):
    p=FlatPen(gs);obj.draw(p)
    assert len(p.rings)==1 and Polygon(p.rings[0]).is_valid

fonts={};metrics={};cubic={v:cubic_shape(v) for v in NAMES}
for v in NAMES:
    p=cubic[v];nodes=list(p.nodes)
    assert not any(tuple(n.position)==tuple(nodes[i-1].position) for i,n in enumerate(nodes))
    layer=GSLayer();layer.paths.append(copy.deepcopy(p));check_outline(layer)
    bp=BoundsPen(None);layer.draw(bp);assert bp.bounds==(15,0,451,510)
    sp=SVGPathPen(None);layer.draw(sp)
    (OUT/f'ka-{v}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 620"><title>к — {NAMES[v]}</title><g transform="translate(20 570) scale(1 -1)"><path d="{sp.getCommands()}" fill="#282334"/></g></svg>')
    for shorti_variant in ['01','02']:
        directory=OUT if shorti_variant=='01' else OUT/'with-compact-shorti'
        directory.mkdir(exist_ok=True)
        stem=f'ka-{v}'
        old=TTFont(BASE/f'shorti-{shorti_variant}.ttf')
        tt=TTFont(BASE/f'shorti-{shorti_variant}.ttf')
        _=tt['GSUB'].table;_=tt['GPOS'].table;_=tt['glyf'];_=tt['hmtx'];_=tt['loca']
        tt.setGlyphOrder(tt.getGlyphOrder()+[GLYPH])
        tt['hhea'].numberOfHMetrics=len(tt.getGlyphOrder());tt['maxp'].numGlyphs=len(tt.getGlyphOrder())
        tt['glyf'][GLYPH]=native_shape(v);tt['hmtx'][GLYPH]=(451,15)
        tt['GDEF'].table.GlyphClassDef.classDefs[GLYPH]=1
        for cmap in tt['cmap'].tables:
            if cmap.isUnicode():cmap.cmap[0x43A]=GLYPH
        inherit_kern(tt,GLYPH,'k');mark_base(tt)
        family=f'Very Peri Regular Study Ka{v} ShortI{shorti_variant}'
        values={1:family,2:'Regular',3:family+';2026;study',4:family+' Regular',6:f'VeryPeriRegularStudyKa{v}ShortI{shorti_variant}-Regular',16:family,17:'Regular'}
        for r in tt['name'].names:
            if r.nameID in values:r.string=values[r.nameID].encode(r.getEncoding())
        tt.save(directory/f'{stem}.ttf');tt=TTFont(directory/f'{stem}.ttf')
        tt.flavor='woff2';tt.save(directory/f'{stem}.woff2');tt.flavor=None
        fs=GSFont(str(BASE/f'shorti-{shorti_variant}.glyphs'));fs.familyName=family
        g=GSGlyph(GLYPH);g.unicode='043A'
        g.leftKerningGroup=SOURCE.glyphs['k'].leftKerningGroup;g.rightKerningGroup=SOURCE.glyphs['k'].rightKerningGroup
        l=GSLayer();l.layerId=fs.masters[0].id;l.associatedMasterId=l.layerId;l.width=WIDTH;l.paths.append(copy.deepcopy(p))
        l.anchors=[GSAnchor('top',(226,510)),GSAnchor('bottom',(226,0))];g.layers.append(l);fs.glyphs.append(g)
        fs.save(str(directory/f'{stem}.glyphs'))
        for name in old.getGlyphOrder():
            assert old['glyf'][name].compile(old['glyf'])==tt['glyf'][name].compile(tt['glyf']),name
            assert old['hmtx'][name]==tt['hmtx'][name],name
        assert old['GSUB'].compile(old)==tt['GSUB'].compile(tt)
        gs=tt.getGlyphSet();check_outline(gs[GLYPH],gs)
        assert TTFont(directory/f'{stem}.woff2').getBestCmap()[0x43A]==GLYPH
        assert GSFont(str(directory/f'{stem}.glyphs')).glyphs[GLYPH].unicode=='043A'
        for text in ['какао','кедр','бок','крик','кк ик ки','к\u0301','кAV']:
            shape(directory/f'{stem}.ttf',text)
        for text,feature,name in [('и',{},'uni0438'),('и',{'ss07':True},'i.altDiagonal'),('й',{'ss07':True},'shorti.altDiagonal'),('б',{'ss02':True},'be.altFlag'),('г',{'ss05':True},'ghe.altBeak')]:
            assert shape(directory/f'{stem}.ttf',text,feature)[0][0]==name
        if shorti_variant=='01':fonts[v]=tt
    native=native_shape(v)
    metrics[v]={'name':NAMES[v],'character':'к','unicode':'U+043A','glyph_name':GLYPH,'advance':451,'bbox_cubic':[15,0,451,510],'bbox_ttf':[native.xMin,native.yMin,native.xMax,native.yMax],'lsb':15,'rsb':0,'stem':68,'cubic_nodes':len(nodes),'ttf_points':len(native.coordinates),'contours':1,'head_donor':'u nodes48…62 translated(+4,0)' if v=='01' else 'k nodes71…90 translated(0,−230)','ttf_head_donor':'u points5…16 translated(+4,0)' if v=='01' else 'k points9…24 translated(0,−230)','new_join_tangent_jump_deg':0,'diagonal_angles_native':[62.8189,62.4958,47.1211],'anchors':{'top':[226,510],'bottom':[226,0]},'kerning':'native k classes/pairs as provisional starting values; Cyrillic optical review pending','checks':{'native_branches_and_feet_exact_in_cubic_and_ttf':True,'sampled_cubic_and_ttf_contour_valid':True,'no_adjacent_cubic_duplicates':True,'previous_glyf_hmtx_and_gsub_unchanged':True,'previous_alternates_preserved':True,'all_exports_reopened':True,'both_unselected_shorti_bases_preserved':True}}

class PlotPen(BasePen):
    def __init__(self,gs):super().__init__(gs);self.v=[];self.c=[]
    def _moveTo(self,p):self.v.append(p);self.c.append(MP.MOVETO)
    def _lineTo(self,p):self.v.append(p);self.c.append(MP.LINETO)
    def _curveToOne(self,a,b,c):self.v.extend([a,b,c]);self.c.extend([MP.CURVE4]*3)
    def _closePath(self):self.v.append((0,0));self.c.append(MP.CLOSEPOLY)
def draw(ax,tt,name,x=0,y=0,scale=1,color='#282334'):
    gs=tt.getGlyphSet();p=PlotPen(gs);gs[name].draw(p)
    if p.v:ax.add_patch(PathPatch(MP(np.array(p.v)*scale+[x,y],p.c),facecolor=color,lw=0))
def word(ax,text,v,x,y,scale):
    for name,adv,_,dx,dy in shape(OUT/f'ka-{v}.ttf',text,{'liga':False}):
        draw(ax,fonts[v],name,x+dx*scale,y+dy*scale,scale);x+=adv*scale

fig=plt.figure(figsize=(16,14),facecolor='#f5f1e9')
fig.text(.055,.957,'Instrument Serif / строчная к',fontsize=27,color='#282334')
fig.text(.055,.92,'Родные диагонали и узел k · высота 510 · ствол 68',fontsize=12,color='#827b73')
for idx,v in enumerate(NAMES):
    fig.text(.055+idx*.49,.868,f'{v} / {NAMES[v]}',fontsize=19,color='#282334')
    ax=fig.add_axes([.08+idx*.49,.55,.34,.285]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-10,490);ax.set_ylim(-30,555)
    for y in [0,510]:ax.axhline(y,color='#c7c0b7',lw=.7,ls='--');ax.text(-8,y+8,str(y),fontsize=8,color='#827b73')
    draw(ax,fonts[v],GLYPH)
    proof=fig.add_axes([.055+idx*.49,.365,.425,.16]);proof.axis('off');proof.set_aspect('equal');proof.set_xlim(0,3370);proof.set_ylim(-160,880)
    for y in [0,510]:proof.axhline(y,color='#c7c0b7',lw=.6,ls='--')
    x=0
    for ch in ['к','k','x','n','u']:
        name=fonts[v].getBestCmap()[ord(ch)];draw(proof,fonts[v],name,x,color='#282334' if ch=='к' else '#8d8479')
        proof.text(x+fonts[v]['hmtx'][name][0]/2,820,ch,fontsize=10,ha='center',color='#827b73');x+=fonts[v]['hmtx'][name][0]+100
    line=fig.add_axes([.055+idx*.49,.10,.425,.235]);line.axis('off');line.set_aspect('equal');line.set_xlim(0,4100);line.set_ylim(-160,2400)
    for text,y in [('какао кедр',1640),('бок крик',810),('кк ик ки',0)]:word(line,text,v,0,y,.67)
fig.text(.055,.05,'Серые знаки — оригинал. Диагонали и нижние окончания к перенесены без изменений.',fontsize=10,color='#827b73')
fig.text(.055,.027,'Основная и — чашеобразная. Оба варианта й сохранены. Кернинг к предварительный.',fontsize=10,color='#827b73')
fig.savefig(OUT/'comparison.png',dpi=160,facecolor=fig.get_facecolor());fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());plt.close(fig)

(OUT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
(OUT/'OFL.txt').write_bytes((BASE/'OFL.txt').read_bytes())
baseline=json.loads((BASE/'approved-baseline.json').read_text())
baseline['source_file']='ka-01.ttf / ka-02.ttf (к not selected yet)'
(OUT/'approved-baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n')
progress_path=OUT/'progress.json'
if not progress_path.exists():progress_path.write_bytes((ROOT/'data/progress.json').read_bytes())
progress=json.loads(progress_path.read_text());progress['undecided_variants']['к']=list(NAMES.values());progress['latest_artifact']=str(OUT)
progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(metrics,ensure_ascii=False,indent=2))
