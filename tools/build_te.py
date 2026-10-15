"""Build handwritten Cyrillic te in Regular while preserving selected de01."""
from pathlib import Path
from array import array
import argparse, copy, hashlib, json
import numpy as np
from glyphsLib import GSFont, GSGlyph, GSLayer, GSAnchor
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, LinearRing, LineString
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch, Rectangle
from prepare_reference import verify_reference
from study_layout import add_order, mark_base, names, save_font, hb_shape

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'build/regular')
parser.add_argument('--base-dir',type=Path,default=ROOT/'studies/regular/de-reimagined')
parser.add_argument('--reference-dir',type=Path,default=ROOT/'reference/instrument-serif')
args=parser.parse_args()
ref=verify_reference(args.reference_dir)
native=TTFont(ref/'fonts/ttf/InstrumentSerif-Regular.ttf')
source=GSFont(str(ref/'sources/Instrument_Serif.glyphs'))
base=args.base_dir.resolve();out=args.output_dir.resolve()/'te';out.mkdir(parents=True,exist_ok=True)
design=json.loads((ROOT/'data/te-outlines.json').read_text())
selected=json.loads((ROOT/'data/selected-de.json').read_text())
target='uni0442'

def source_commands(name):
    layer=next(l for l in source.glyphs[name].layers if l.layerId=='m01')
    pen=RecordingPen();layer.draw(pen)
    return [[op,[list(p) for p in pts]] for op,pts in pen.value]

assert design['variants']['01']['commands']==source_commands('m')
native_m=source_commands('m');native_d=source_commands('d')
expected=native_m[:22]+[['lineTo',[[558,95]]],design['variants']['02']['new_connector']['command']]
expected += [[op,[[x+255,y] for x,y in pts]] for op,pts in native_d[4:9]]+native_m[32:]
assert design['variants']['02']['commands']==expected

def te_quadratic(variant):
    glyph=copy.deepcopy(native['glyf']['m'])
    if variant=='01': return glyph
    m=native['glyf']['m'];d=native['glyf']['d']
    assert len(m.coordinates)==105 and list(m.endPtsOfContours)==[104]
    assert tuple(m.coordinates[43])==(626,392) and tuple(m.coordinates[62])==(558,381)
    assert tuple(d.coordinates[30])==(371,95) and tuple(d.coordinates[42])==(370,-9)
    # Reverse only the new cubic connector; native m and d quadratic points stay exact.
    connector=design['variants']['02']['new_connector']
    p1,p2,end=connector['command'][1];start=connector['start']
    pen=TTGlyphPen(None);qpen=Cu2QuPen(pen,max_err=.20)
    qpen.moveTo(tuple(end));qpen.curveTo(tuple(p2),tuple(p1),tuple(start));qpen.endPath()
    bridge=pen.glyph();bridge.coordinates.toInt()
    assert tuple(bridge.coordinates[0])==(625,-9) and tuple(bridge.coordinates[-1])==(558,95)
    coords=list(m.coordinates[:44])+[(x+255,y) for x,y in d.coordinates[30:43]]
    flags=list(m.flags[:44])+list(d.flags[30:43])
    coords+=list(bridge.coordinates[1:])+list(m.coordinates[62:])
    flags+=list(bridge.flags[1:])+list(m.flags[62:])
    glyph.coordinates=GlyphCoordinates(coords);glyph.flags=array('B',flags)
    glyph.endPtsOfContours=[len(coords)-1];glyph.numberOfContours=1
    glyph.program=Program();glyph.program.fromBytecode(b'')
    glyph.recalcBounds(native['glyf'])
    assert list(glyph.coordinates[:44])==list(m.coordinates[:44])
    assert list(glyph.coordinates[-43:])==list(m.coordinates[62:])
    assert list(glyph.coordinates[44:57])==[(x+255,y) for x,y in d.coordinates[30:43]]
    return glyph

def inherit_edges(tt,left,right):
    """Add target pairs/classes by matching left and right edge roles."""
    gid=tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType!=2: continue
        for sub in lookup.SubTable:
            if sub.Format==2:
                if right in sub.Coverage.glyphs:
                    sub.Coverage.glyphs=sorted(sub.Coverage.glyphs+[target],key=gid.get)
                if right in sub.ClassDef1.classDefs:sub.ClassDef1.classDefs[target]=sub.ClassDef1.classDefs[right]
                if left in sub.ClassDef2.classDefs:sub.ClassDef2.classDefs[target]=sub.ClassDef2.classDefs[left]
            elif sub.Format==1:
                records=dict(zip(sub.Coverage.glyphs,sub.PairSet))
                if right in records:records[target]=copy.deepcopy(records[right])
                for record in records.values():
                    pairs={r.SecondGlyph:r for r in record.PairValueRecord}
                    if left in pairs:
                        r=copy.deepcopy(pairs[left]);r.SecondGlyph=target;pairs[target]=r
                    record.PairValueRecord=[pairs[n] for n in sorted(pairs,key=gid.get)]
                    record.PairValueCount=len(record.PairValueRecord)
                sub.Coverage.glyphs=sorted(records,key=gid.get)
                sub.PairSet=[records[n] for n in sub.Coverage.glyphs];sub.PairSetCount=len(records)

class SamplePen(BasePen):
    def __init__(self,gs=None):super().__init__(gs);self.rings=[];self.points=[];self.p=None
    def _moveTo(self,p):self.p=np.array(p);self.points=[tuple(p)]
    def _lineTo(self,p):self.p=np.array(p);self.points.append(tuple(p))
    def _curveToOne(self,a,b,c):
        t=np.linspace(0,1,601)[1:,None]
        pts=(1-t)**3*self.p+3*(1-t)**2*t*np.array(a)+3*(1-t)*t*t*np.array(b)+t**3*np.array(c)
        self.points.extend(map(tuple,pts));self.p=np.array(c)
    def _closePath(self):self.rings.append(self.points);self.points=[]

def check_shape(obj,gs=None):
    pen=SamplePen(gs);obj.draw(pen)
    assert len(pen.rings)==1
    ring=LinearRing(pen.rings[0]);poly=Polygon(ring)
    assert ring.is_simple and poly.is_valid and poly.area>0
    return ring,poly

fonts={};metrics={};combinations=[];audit={}
for variant,spec in design['variants'].items():
    layer=GSLayer();layer.width=spec['advance']
    if variant=='01':
        layer.paths=[copy.deepcopy(p) for p in source.glyphs['m'].layers[0].paths]
    else:
        pen=layer.getPen()
        for op,points in spec['commands']:getattr(pen,op)(*[tuple(p) for p in points])
    layer.anchors=[GSAnchor(k,tuple(v)) for k,v in spec['anchors'].items()]
    source_ring,source_poly=check_shape(layer)
    assert source_ring.is_ccw
    assert not any(tuple(n.position)==tuple(p.nodes[i-1].position) for p in layer.paths for i,n in enumerate(p.nodes))
    bp=BoundsPen(None);layer.draw(bp)
    svg=SVGPathPen(None);layer.draw(svg)
    (out/f'te-{variant}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 610"><title>т — {spec["name"]}</title><g transform="translate(30 555) scale(1 -1)"><path d="{svg.getCommands()}" fill="#282334"/></g></svg>')
    for ka in ['01','02']:
        for shorti in ['01','02']:
            directory=base if (ka,shorti)==('01','01') else base/f'with-ka{ka}-shorti{shorti}'
            file=directory/'de-01.ttf';old=TTFont(file);tt=TTFont(file)
            assert hashlib.sha256(tt['glyf']['uni0434'].compile(tt['glyf'])).hexdigest()==selected['glyf_sha256']
            _=tt['GSUB'].table;_=tt['GPOS'].table
            assert 0x442 not in tt.getBestCmap();add_order(tt,[target])
            tt['glyf'][target]=te_quadratic(variant);tt['glyf'][target].recalcBounds(tt['glyf'])
            tt['hmtx'][target]=(spec['advance'],tt['glyf'][target].xMin)
            for table in tt['cmap'].tables:
                if table.isUnicode():table.cmap[0x442]=target
            tt['GDEF'].table.GlyphClassDef.classDefs[target]=1
            mark_base(tt,target,'n',top=tuple(spec['anchors']['top']),bottom=tuple(spec['anchors']['bottom']),active_classes={0,2})
            inherit_edges(tt,'m','m' if variant=='01' else 'd')
            suffix=f'Te{variant}De01Ka{ka}ShortI{shorti}';names(tt,suffix)
            dest=out if (ka,shorti)==('01','01') else out/f'with-ka{ka}-shorti{shorti}'
            dest.mkdir(exist_ok=True);tt=save_font(tt,dest/f'te-{variant}')
            fs=GSFont(str(directory/'de-01.glyphs'));fs.familyName='Very Peri Regular Study '+suffix
            glyph=GSGlyph(target);glyph.unicode='0442'
            glyph.note='[ОТКРЫТО] '+spec['name']+'. '+', '.join(spec['feature_roles'])+'. '+spec['ductus']
            glyph.leftKerningGroup=source.glyphs['m'].leftKerningGroup
            glyph.rightKerningGroup=source.glyphs['m' if variant=='01' else 'd'].rightKerningGroup
            new_layer=GSLayer();new_layer.layerId=fs.masters[0].id;new_layer.associatedMasterId=new_layer.layerId
            new_layer.width=layer.width;new_layer.paths=[copy.deepcopy(p) for p in layer.paths]
            new_layer.anchors=[GSAnchor(a.name,tuple(a.position)) for a in layer.anchors]
            glyph.layers.append(new_layer);fs.glyphs.append(glyph);fs.save(str(dest/f'te-{variant}.glyphs'))
            for n in old.getGlyphOrder():
                assert old['glyf'][n].compile(old['glyf'])==tt['glyf'][n].compile(tt['glyf']),n
                assert old['hmtx'][n]==tt['hmtx'][n],n
            assert old['GSUB'].compile(old)==tt['GSUB'].compile(tt)
            assert TTFont(dest/f'te-{variant}.woff2').getBestCmap()[0x442]==target
            assert GSFont(str(dest/f'te-{variant}.glyphs')).glyphs[target].unicode=='0442'
            for text in ['тигр тогда','будто три','дитё тити','т\u0301','тAV','й','и\u0306']:
                hb_shape(dest/f'te-{variant}.ttf',text)
            assert hb_shape(dest/f'te-{variant}.ttf','й')==hb_shape(dest/f'te-{variant}.ttf','и\u0306')
            for text in ['AV','To','Ta','Yo','Wa','LT','Fo','oo','m.','mu']:
                assert hb_shape(dest/f'te-{variant}.ttf',text)==hb_shape(file,text)
            if (ka,shorti)==('01','01'):fonts[variant]=tt
            combinations.append({'te_variant':variant,'de_variant':'01','ka_variant':ka,'shorti_variant':shorti,'ttf':str((dest/f'te-{variant}.ttf').relative_to(out))})
    tt=fonts[variant];gs=tt.getGlyphSet();tt_ring,tt_poly=check_shape(gs[target],gs)
    assert not tt_ring.is_ccw
    distance=source_ring.hausdorff_distance(tt_ring);assert distance<1.25
    audit[variant]={'sampled_topology_valid':True,'contours':1,'closed_counters':0,'sample_points_per_cubic':600,
        'sampled_source_export_hausdorff_units':distance,'relative_area_difference':abs(tt_poly.area-source_poly.area)/source_poly.area,
        'all_existing_glyf_hmtx_and_gsub_preserved':True,'selected_de_hash_preserved':True,'original_m_preserved':True,
        'native_m_copy_exact':variant=='01','native_m_body_and_d_tail_points_exact':variant=='02'}
    metrics[variant]={'name':spec['name'],'character':'т','unicode':'U+0442','glyph':target,'status':spec.get('selection_status','unselected proposal'),
        'advance':layer.width,'bbox_cubic':bp.bounds,'bbox_ttf':[tt['glyf'][target].xMin,tt['glyf'][target].yMin,tt['glyf'][target].xMax,tt['glyf'][target].yMax],
        'cubic_nodes':sum(len(p.nodes) for p in layer.paths),'ttf_points':len(tt['glyf'][target].coordinates),
        'native_stem_width':68,'anchors_proposed':spec['anchors'],'construction':spec['construction'],'native_relationship':spec['native_relationship'],
        'kerning':'native m left edge / '+('m' if variant=='01' else 'd')+' right edge as initial values; Cyrillic pair review pending'}

class PlotPen(BasePen):
    def __init__(self,gs):super().__init__(gs);self.vertices=[];self.codes=[]
    def _moveTo(self,p):self.vertices.append(p);self.codes.append(MP.MOVETO)
    def _lineTo(self,p):self.vertices.append(p);self.codes.append(MP.LINETO)
    def _curveToOne(self,a,b,c):self.vertices.extend([a,b,c]);self.codes.extend([MP.CURVE4]*3)
    def _closePath(self):self.vertices.append((0,0));self.codes.append(MP.CLOSEPOLY)

def draw(ax,tt,name,x=0,y=0,scale=1,color='#282334'):
    gs=tt.getGlyphSet();p=PlotPen(gs);gs[name].draw(p)
    if p.vertices:ax.add_patch(PathPatch(MP(np.array(p.vertices)*scale+[x,y],p.codes),facecolor=color,lw=0))

def word(ax,text,v,x,y,scale,color='#282334'):
    for name,adv,_,dx,dy in hb_shape(out/f'te-{v}.ttf',text,{'liga':False}):
        draw(ax,fonts[v],name,x+dx*scale,y+dy*scale,scale,color);x+=adv*scale

fig=plt.figure(figsize=(16,14),facecolor='#f5f1e9')
fig.text(.055,.958,'т / две верхние арки',fontsize=27,color='#282334')
fig.text(.055,.921,'Very Peri Serif · письменная конструкция в Regular',fontsize=12,color='#827b73')
for idx,(v,spec) in enumerate(design['variants'].items()):
    x=.055+idx*.49
    fig.text(x,.86,f'{v} / {spec["name"]}',fontsize=19,color='#282334')
    ax=fig.add_axes([x,.59,.425,.235]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-25,765);ax.set_ylim(-30,555)
    draw(ax,fonts[v],target)
    ax=fig.add_axes([x,.395,.425,.17]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,4150);ax.set_ylim(-260,860)
    pos=0
    for ch in ['т','и','д','m','n','u']:
        n=fonts[v].getBestCmap()[ord(ch)];draw(ax,fonts[v],n,pos,color='#282334' if ch in ['т','и','д'] else '#8d8479')
        ax.text(pos+fonts[v]['hmtx'][n][0]/2,800,ch,ha='center',fontsize=10,color='#827b73');pos+=fonts[v]['hmtx'][n][0]+90
    ax=fig.add_axes([x,.10,.425,.265]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,4200);ax.set_ylim(-200,2650)
    for text,y in [('тигр тогда',1900),('будто три',950),('дитё тити',0)]:word(ax,text,v,0,y,.70)
fig.text(.055,.05,'Серые m/n/u — исходник. И и д01 — выбранные. Все строки набраны контурами пробного шрифта.',fontsize=10,color='#827b73')
fig.text(.055,.027,'Два варианта т к выбору; наклон Italic не используется. Интервалы и кернинг предварительные.',fontsize=10,color='#827b73')
fig.savefig(out/'comparison.png',dpi=160,facecolor=fig.get_facecolor());fig.savefig(out/'comparison.svg',facecolor=fig.get_facecolor());plt.close(fig)

# Actual 12/24/100-point outlines on a page measured in typographic points.
fig=plt.figure(figsize=(9,7),facecolor='#f5f1e9');ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,648);ax.set_ylim(0,504);ax.axis('off')
ax.add_patch(Rectangle((324,0),324,504,facecolor='#282334',lw=0))
for i,(v,spec) in enumerate(design['variants'].items()):
    top=475-i*245
    for x,color in [(20,'#282334'),(344,'#f5f1e9')]:
        ax.text(x,top,f'{v} / {spec["name"]}',fontsize=12,color=color)
        for size,dy in [(12,38),(24,87),(100,195)]:
            ax.text(x,top-dy+4,str(size)+' pt',fontsize=8,color=color)
            word(ax,'три',v,x+55,top-dy,size/1000,color)
fig.savefig(out/'sizes.png',dpi=180,facecolor=fig.get_facecolor());fig.savefig(out/'sizes.svg',facecolor=fig.get_facecolor());plt.close(fig)

(out/'metrics.json').write_text(json.dumps({'variants':metrics,'combinations':combinations},ensure_ascii=False,indent=2)+'\n')
(out/'outline-audit.json').write_text(json.dumps({'status':'passed','variants':audit,'limits':'Sampled topology and distance are not analytic proofs of all curve properties.','fontbakery':'not run','hyperglot':'not run'},ensure_ascii=False,indent=2)+'\n')
baseline=json.loads((base/'approved-baseline.json').read_text());baseline['fixed_glyphs']['uni0434']={'hmtx':selected['hmtx'],'glyf_sha256':selected['glyf_sha256']}
baseline['source_file']='te-02.ttf primary / te-01.ttf alternative; de01 selected'
(out/'approved-baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n')
(out/'OFL.txt').write_bytes((base/'OFL.txt').read_bytes())
print(json.dumps({'variants':metrics,'audit':audit,'combinations':len(combinations)},ensure_ascii=False,indent=2))
