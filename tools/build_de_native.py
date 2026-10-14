"""Explore Cyrillic de through the typeface's native two-storey g drawings.

These are unselected alternatives, preserving old de studies and all other
approved glyphs. No reinterpretation of curves or deformation is applied.
"""
from pathlib import Path
import argparse, copy, json
from glyphsLib import GSFont, GSAnchor
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.basePen import BasePen
import numpy as np
from shapely.geometry import Polygon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch
from prepare_reference import verify_reference
from study_layout import mark_base, inherit_native_kern, names, save_font, hb_shape

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'build/regular')
parser.add_argument('--reference-dir',type=Path,default=ROOT/'reference/instrument-serif')
parser.add_argument('--base-dir',type=Path,default=ROOT/'studies/regular/ka')
args=parser.parse_args()
REFERENCE=verify_reference(args.reference_dir)
OUT=args.output_dir.resolve()/'de-native';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=GSFont(str(REFERENCE/'sources/Instrument_Serif.glyphs'))
NATIVE=TTFont(REFERENCE/'fonts/ttf/InstrumentSerif-Regular.ttf')
BASE=args.base_dir.resolve()
GLYPH='uni0434'
DONORS={'01':'g.ss01','02':'g'}
LABELS={'01':'Короткое ухо','02':'Каплевидное ухо'}

class FlatPen(BasePen):
    def __init__(self,gs=None):super().__init__(gs);self.rings=[];self.points=[];self.p=None
    def _moveTo(self,p):self.p=np.array(p);self.points=[tuple(p)]
    def _lineTo(self,p):self.p=np.array(p);self.points.append(tuple(p))
    def _curveToOne(self,a,b,c):
        t=np.linspace(0,1,600)[1:,None];p0=self.p;p1=np.array(a);p2=np.array(b);p3=np.array(c)
        pts=(1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3
        self.points.extend(map(tuple,pts));self.p=p3
    def _closePath(self):self.rings.append(self.points);self.points=[]

def topology(obj,gs=None):
    pen=FlatPen(gs);obj.draw(pen)
    assert len(pen.rings)==3
    assert Polygon(pen.rings[0],pen.rings[1:]).is_valid
    return True

fonts={};metrics={};combinations=[]
for v,donor in DONORS.items():
    layer=SOURCE.glyphs[donor].layers[0]
    topology(layer)
    bp=BoundsPen(None);layer.draw(bp)
    sp=SVGPathPen(None);layer.draw(sp)
    (OUT/f'de-{v}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 490 900"><title>д — {LABELS[v]}, native {donor}</title><g transform="translate(25 645) scale(1 -1)"><path d="{sp.getCommands()}" fill="#282334"/></g></svg>')
    duplicates=sum(tuple(n.position)==tuple(p.nodes[i-1].position) for p in layer.paths for i,n in enumerate(p.nodes))
    assert duplicates==0
    for ka in ['01','02']:
        for shorti in ['01','02']:
            input_dir=BASE if shorti=='01' else BASE/'with-compact-shorti'
            parent=TTFont(input_dir/f'ka-{ka}.ttf')
            tt=TTFont(input_dir/f'ka-{ka}.ttf');_=tt['GSUB'].table;_=tt['GPOS'].table
            tt['glyf'][GLYPH]=copy.deepcopy(NATIVE['glyf'][donor]);tt['hmtx'][GLYPH]=NATIVE['hmtx'][donor]
            tt['GDEF'].table.GlyphClassDef.classDefs[GLYPH]=1
            mark_base(tt,GLYPH,donor);inherit_native_kern(tt,{GLYPH:donor})
            # ss06 remains the explicit historical de alternative; do not rewrite it.
            suffix=f'DeNative{v}Ka{ka}ShortI{shorti}';names(tt,suffix)
            directory=OUT if (ka,shorti)==('01','01') else OUT/f'with-ka{ka}-shorti{shorti}'
            directory.mkdir(exist_ok=True)
            tt=save_font(tt,directory/f'de-{v}')
            fs=GSFont(str(input_dir/f'ka-{ka}.glyphs'));fs.familyName='Very Peri Regular Study '+suffix
            target=fs.glyphs[GLYPH].layers[0]
            target.paths=[copy.deepcopy(p) for p in layer.paths];target.components=[];target.width=layer.width
            target.anchors=[GSAnchor(a.name,tuple(a.position)) for a in layer.anchors]
            fs.glyphs[GLYPH].leftKerningGroup=SOURCE.glyphs[donor].leftKerningGroup
            fs.glyphs[GLYPH].rightKerningGroup=SOURCE.glyphs[donor].rightKerningGroup
            fs.save(str(directory/f'de-{v}.glyphs'))
            for n in parent.getGlyphOrder():
                if n==GLYPH:continue
                assert parent['glyf'][n].compile(parent['glyf'])==tt['glyf'][n].compile(tt['glyf']),n
                assert parent['hmtx'][n]==tt['hmtx'][n],n
            assert parent['GSUB'].compile(parent)==tt['GSUB'].compile(tt)
            assert tt['glyf'][GLYPH].compile(tt['glyf'])==NATIVE['glyf'][donor].compile(NATIVE['glyf'])
            assert tt['hmtx'][GLYPH]==NATIVE['hmtx'][donor]
            gs=tt.getGlyphSet();topology(gs[GLYPH],gs)
            assert TTFont(directory/f'de-{v}.woff2').getBestCmap()[0x434]==GLYPH
            assert GSFont(str(directory/f'de-{v}.glyphs')).glyphs[GLYPH].unicode=='0434'
            for text in ['дед беда','оддо доди','дg gд','д\u0301','и\u0306']:
                hb_shape(directory/f'de-{v}.ttf',text)
            assert hb_shape(directory/f'de-{v}.ttf','и',{'ss07':True})[0][0]=='i.altDiagonal'
            assert hb_shape(directory/f'de-{v}.ttf','д',{'ss06':True})[0][0]=='de.altAsymmetric'
            if (ka,shorti)==('01','01'):fonts[v]=tt
            combinations.append({'de_variant':v,'ka_variant':ka,'shorti_variant':shorti,'ttf':str((directory/f'de-{v}.ttf').relative_to(OUT))})
    metrics[v]={'name':LABELS[v],'unicode':'U+0434','glyph':GLYPH,'donor':donor,'construction':'unmodified native two-storey g proposed as Cyrillic de','status':'unselected design exploration','advance':layer.width,'bbox_cubic':bp.bounds,'hmtx':list(NATIVE['hmtx'][donor]),'cubic_nodes':sum(len(p.nodes) for p in layer.paths),'ttf_points':len(NATIVE['glyf'][donor].coordinates),'contours':3,'kerning':'exact native donor inherited; Cyrillic contextual review pending','checks':{'native_ttf_glyph_and_metrics_byte_identical':True,'native_cubic_paths_unchanged':True,'sampled_topology_valid':True,'adjacent_cubic_duplicates':0,'all_other_glyphs_and_hmtx_unchanged':True,'gsub_unchanged_ss06_legacy_preserved':True,'all_exports_reopened':True}}

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
    for n,adv,_,dx,dy in hb_shape(OUT/f'de-{v}.ttf',text,{'liga':False}):
        draw(ax,fonts[v],n,x+dx*scale,y+dy*scale,scale);x+=adv*scale

fig=plt.figure(figsize=(16,14),facecolor='#f5f1e9')
fig.text(.055,.957,'Instrument Serif / д: родная двухчашевая конструкция',fontsize=23,color='#282334')
fig.text(.055,.92,'Две пробы по g и g.ss01 · родные чаши, петля и переходы · выбор открыт',fontsize=12,color='#827b73')
previous=TTFont(BASE/'ka-01.ttf')
for idx,v in enumerate(DONORS):
    fig.text(.055+idx*.49,.868,f'{v} / {LABELS[v]}',fontsize=19,color='#282334')
    ax=fig.add_axes([.08+idx*.49,.53,.34,.305]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-10,435);ax.set_ylim(-240,640)
    for y in [-215,0,510]:ax.axhline(y,color='#c7c0b7',lw=.7,ls='--');ax.text(-8,y+8,str(y),fontsize=8,color='#827b73')
    draw(ax,fonts[v],GLYPH)
    proof=fig.add_axes([.055+idx*.49,.345,.425,.16]);proof.axis('off');proof.set_aspect('equal');proof.set_xlim(0,3380);proof.set_ylim(-270,850)
    for y in [0,510]:proof.axhline(y,color='#c7c0b7',lw=.6,ls='--')
    x=0
    for ch in ['д','g','o','p']:
        n=fonts[v].getBestCmap()[ord(ch)];draw(proof,fonts[v],n,x,color='#282334' if ch=='д' else '#8d8479')
        proof.text(x+fonts[v]['hmtx'][n][0]/2,790,ch,fontsize=10,ha='center',color='#827b73');x+=fonts[v]['hmtx'][n][0]+100
    draw(proof,previous,GLYPH,x,color='#b7aea2');proof.text(x+205,790,'прежняя д',fontsize=9,ha='center',color='#827b73')
    line=fig.add_axes([.055+idx*.49,.10,.425,.215]);line.axis('off');line.set_aspect('equal');line.set_xlim(0,3700);line.set_ylim(-240,2450)
    for text,y in [('дед беда',1640),('оддо доди',810),('дд ди ид',0)]:word(line,text,v,0,y,.72)
fig.text(.055,.05,'Серые g/o/p — оригинал; светлая д — предыдущий рисунок. Прежние версии сохранены.',fontsize=10,color='#827b73')
fig.text(.055,.027,'Пробы д не утверждены. Основная и и оба варианта к/й сохранены; старый ss06 остаётся архивной альтернативой.',fontsize=10,color='#827b73')
fig.savefig(OUT/'comparison.png',dpi=160,facecolor=fig.get_facecolor());fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());plt.close(fig)
(OUT/'metrics.json').write_text(json.dumps({'variants':metrics,'combinations':combinations},ensure_ascii=False,indent=2)+'\n')
(OUT/'approved-baseline.json').write_bytes((BASE/'approved-baseline.json').read_bytes())
(OUT/'OFL.txt').write_bytes((BASE/'OFL.txt').read_bytes())
print(json.dumps(metrics,ensure_ascii=False,indent=2))
