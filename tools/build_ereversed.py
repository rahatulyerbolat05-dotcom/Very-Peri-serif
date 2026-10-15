"""Build two authored lowercase Cyrillic e-reversed studies in upright Regular."""
from pathlib import Path
import argparse,copy,hashlib,json,math
import numpy as np
from glyphsLib import GSFont,GSGlyph,GSLayer,GSAnchor
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from shapely.geometry import Polygon,LinearRing
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Rectangle
from prepare_reference import verify_reference
from study_layout import add_order,mark_base,names,save_font,hb_shape

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'build/regular')
parser.add_argument('--base-dir',type=Path,default=ROOT/'studies/regular/te')
parser.add_argument('--reference-dir',type=Path,default=ROOT/'reference/instrument-serif')
args=parser.parse_args();ref=verify_reference(args.reference_dir)
base=args.base_dir.resolve();out=args.output_dir.resolve()/'ereversed';out.mkdir(parents=True,exist_ok=True)
source=GSFont(str(ref/'sources/Instrument_Serif.glyphs'))
design=json.loads((ROOT/'data/ereversed-outlines.json').read_text())
export_recipe=json.loads((ROOT/'data/ereversed-export.json').read_text())
pins=[json.loads((ROOT/f'data/selected-{name}.json').read_text()) for name in ['de','te']]
target='uni044D'

class SamplePen(BasePen):
    def __init__(self,gs=None):super().__init__(gs);self.rings=[];self.points=[];self.p=None
    def _moveTo(self,p):self.p=np.array(p);self.points=[tuple(p)]
    def _lineTo(self,p):self.p=np.array(p);self.points.append(tuple(p))
    def _curveToOne(self,a,b,c):
        t=np.linspace(0,1,601)[1:,None]
        pts=(1-t)**3*self.p+3*(1-t)**2*t*np.array(a)+3*(1-t)*t*t*np.array(b)+t**3*np.array(c)
        self.points.extend(map(tuple,pts));self.p=np.array(c)
    def _closePath(self):self.rings.append(self.points);self.points=[]
def topology(obj,gs=None):
    pen=SamplePen(gs);obj.draw(pen);assert len(pen.rings)==1
    ring=LinearRing(pen.rings[0]);poly=Polygon(ring)
    assert ring.is_simple and poly.is_valid and poly.area>0
    return ring,poly

def inherit_right_edge(tt):
    """Only outgoing o kerning is inherited; no Latin donor for the open left edge."""
    gid=tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType!=2:continue
        for s in lookup.SubTable:
            if s.Format==2:
                if 'o' in s.Coverage.glyphs:s.Coverage.glyphs=sorted(s.Coverage.glyphs+[target],key=gid.get)
                if 'o' in s.ClassDef1.classDefs:s.ClassDef1.classDefs[target]=s.ClassDef1.classDefs['o']
            elif s.Format==1:
                records=dict(zip(s.Coverage.glyphs,s.PairSet))
                if 'o' in records:records[target]=copy.deepcopy(records['o'])
                s.Coverage.glyphs=sorted(records,key=gid.get)
                s.PairSet=[records[n] for n in s.Coverage.glyphs];s.PairSetCount=len(records)

def source_joins(commands):
    segments=[];point=None
    for op,pts in commands:
        if op=='moveTo':point=pts[0]
        elif op in {'lineTo','curveTo'}:segments.append([point]+pts);point=pts[-1]
    errors=[]
    for i,seg in enumerate(segments):
        n=segments[(i+1)%len(segments)];assert seg[-1]==n[0]
        a=np.array(seg[-1])-seg[-2];b=np.array(n[1])-n[0]
        cross=a[0]*b[1]-a[1]*b[0]
        angle=math.degrees(math.atan2(abs(float(cross)),float(a@b)))
        errors.append(angle)
    return max(errors)

def integer_joins(glyph):
    """Check explicit joins in the saved quadratic outline, not just source curves."""
    assert glyph.numberOfContours==1
    ring=list(glyph.coordinates);flags=list(glyph.flags);checked=[]
    assert len(set(ring))==len(ring)
    for i,point in enumerate(ring):
        if not flags[i]&1:continue
        before=ring[i-1];after=ring[(i+1)%len(ring)]
        a=(point[0]-before[0],point[1]-before[1]);b=(after[0]-point[0],after[1]-point[1])
        assert a[0]*b[1]-a[1]*b[0]==0,i
        assert a[0]*b[0]+a[1]*b[1]>0,i
        checked.append(i)
    return checked

def polish_integer_export(tt,variant):
    """Apply a pinned <=1u fitting correction only to the newly authored glyph."""
    glyph=tt['glyf'][target];recipe=export_recipe['variants'][variant]
    raw=glyph.compile(tt['glyf'])
    assert hashlib.sha256(raw).hexdigest()==recipe['raw_glyf_sha256']
    glyph.coordinates.toInt()
    assert len(glyph.coordinates)==recipe['point_count']
    assert glyph.numberOfContours==recipe['contours']
    for change in recipe['adjustments']:
        i=change['point_index'];assert list(glyph.coordinates[i])==change['before']
        assert bool(glyph.flags[i]&1)==change['on_curve']
        assert max(abs(a-b) for a,b in zip(change['before'],change['after']))<=1
        glyph.coordinates[i]=tuple(change['after'])
    glyph.recalcBounds(tt['glyf'])
    assert [glyph.xMin,glyph.yMin,glyph.xMax,glyph.yMax]==recipe['bbox']
    assert integer_joins(glyph)==recipe['exact_integer_g1_oncurve_indices']

fonts={};metrics={};checks={};combinations=[]
for variant,spec in design['variants'].items():
    layer=GSLayer();layer.width=spec['advance'];pen=layer.getPen()
    for op,pts in spec['commands']:getattr(pen,op)(*[tuple(p) for p in pts])
    layer.anchors=[GSAnchor(k,tuple(v)) for k,v in spec['anchors'].items()]
    ring,poly=topology(layer);assert ring.is_ccw
    duplicates=sum(tuple(n.position)==tuple(p.nodes[i-1].position) for p in layer.paths for i,n in enumerate(p.nodes))
    assert duplicates==0
    tangent_error=source_joins(spec['commands']);assert tangent_error<1e-6
    bp=BoundsPen(None);layer.draw(bp)
    svg=SVGPathPen(None);layer.draw(svg)
    (out/f'ereversed-{variant}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 430 610"><title>э — {spec["name"]}</title><g transform="translate(25 555) scale(1 -1)"><path d="{svg.getCommands()}" fill="#282334"/></g></svg>')
    for ka in ['01','02']:
        for shorti in ['01','02']:
            input_dir=base if (ka,shorti)==('01','01') else base/f'with-ka{ka}-shorti{shorti}'
            file=input_dir/'te-02.ttf';old=TTFont(file);tt=TTFont(file)
            for pin in pins:
                assert list(tt['hmtx'][pin['glyph']])==pin['hmtx']
                assert hashlib.sha256(tt['glyf'][pin['glyph']].compile(tt['glyf'])).hexdigest()==pin['glyf_sha256']
            _=tt['GSUB'].table;_=tt['GPOS'].table
            assert 0x44D not in tt.getBestCmap();add_order(tt,[target])
            pen=TTGlyphPen(None);layer.draw(Cu2QuPen(pen,max_err=.20,reverse_direction=True))
            tt['glyf'][target]=pen.glyph();tt['glyf'][target].recalcBounds(tt['glyf'])
            polish_integer_export(tt,variant)
            tt['hmtx'][target]=(spec['advance'],tt['glyf'][target].xMin)
            for table in tt['cmap'].tables:
                if table.isUnicode():table.cmap[0x44D]=target
            tt['GDEF'].table.GlyphClassDef.classDefs[target]=1
            mark_base(tt,target,'o',top=tuple(spec['anchors']['top']),bottom=tuple(spec['anchors']['bottom']),active_classes={0,2})
            inherit_right_edge(tt)
            suffix=f'Ereversed{variant}Te02De01Ka{ka}ShortI{shorti}';names(tt,suffix)
            dest=out if (ka,shorti)==('01','01') else out/f'with-ka{ka}-shorti{shorti}';dest.mkdir(exist_ok=True)
            tt=save_font(tt,dest/f'ereversed-{variant}')
            fs=GSFont(str(input_dir/'te-02.glyphs'));fs.familyName='Very Peri Regular Study '+suffix
            glyph=GSGlyph(target);glyph.unicode='044D';glyph.note='[ОТКРЫТО] '+spec['name']+'. '+', '.join(spec['feature_roles'])+'. '+spec['ductus']
            glyph.leftKerningGroup=None;glyph.rightKerningGroup=source.glyphs['o'].rightKerningGroup
            new=GSLayer();new.layerId=fs.masters[0].id;new.associatedMasterId=new.layerId;new.width=layer.width
            new.paths=[copy.deepcopy(p) for p in layer.paths];new.anchors=[GSAnchor(a.name,tuple(a.position)) for a in layer.anchors]
            glyph.layers.append(new);fs.glyphs.append(glyph);fs.save(str(dest/f'ereversed-{variant}.glyphs'))
            for n in old.getGlyphOrder():
                assert old['glyf'][n].compile(old['glyf'])==tt['glyf'][n].compile(tt['glyf']),n
                assert old['hmtx'][n]==tt['hmtx'][n],n
            assert old['GSUB'].compile(old)==tt['GSUB'].compile(tt)
            assert TTFont(dest/f'ereversed-{variant}.woff2').getBestCmap()[0x44D]==target
            assert GSFont(str(dest/f'ereversed-{variant}.glyphs')).glyphs[target].unicode=='044D'
            for text in ['это эра','эге эго','дуэт эхо','э\u0301','эо оэ','и\u0306','гтд']:
                hb_shape(dest/f'ereversed-{variant}.ttf',text)
            assert hb_shape(dest/f'ereversed-{variant}.ttf','г',{'ss05':True})[0][0]=='ghe.altBeak'
            for text in ['AV','To','Ta','Yo','oo','m.','mu','тигр','город']:
                assert hb_shape(dest/f'ereversed-{variant}.ttf',text)==hb_shape(file,text)
            if (ka,shorti)==('01','01'):fonts[variant]=tt
            combinations.append({'ereversed_variant':variant,'te_variant':'02','de_variant':'01','ka_variant':ka,'shorti_variant':shorti,'ttf':str((dest/f'ereversed-{variant}.ttf').relative_to(out))})
    gs=fonts[variant].getGlyphSet();tt_ring,tt_poly=topology(gs[target],gs);assert not tt_ring.is_ccw
    integer_join_indices=integer_joins(fonts[variant]['glyf'][target])
    distance=ring.hausdorff_distance(tt_ring);assert distance<1.25
    metrics[variant]={'name':spec['name'],'character':'э','unicode':'U+044D','glyph':target,'status':'unselected proposal','advance':layer.width,
        'bbox_cubic':bp.bounds,'bbox_ttf':[fonts[variant]['glyf'][target].xMin,fonts[variant]['glyf'][target].yMin,fonts[variant]['glyf'][target].xMax,fonts[variant]['glyf'][target].yMax],
        'cubic_nodes':sum(len(p.nodes) for p in layer.paths),'ttf_points':len(fonts[variant]['glyf'][target].coordinates),'contours':1,
        'crossbar_y':[277,302],'crossbar_thickness':25,'crossbar_free_x':spec['crossbar_free_x'],'crossbar_straight_start_x':spec['crossbar_straight_start_x'],'native_relationship':spec['native_relationship'],
        'anchors':spec['anchors'],'kerning':'Outgoing native o pairs; incoming open edge unassigned, final Cyrillic spacing pending.'}
    checks[variant]={'sampled_source_and_ttf_topology_valid':True,'adjacent_source_duplicates':0,'source_smooth_join_max_error_degrees':tangent_error,
        'sampled_source_export_hausdorff_units':distance,'relative_area_difference':abs(tt_poly.area-poly.area)/poly.area,
        'integer_export_exact_g1_joins':len(integer_join_indices),'integer_export_max_join_angle_degrees':0.0,
        'integer_export_recipe':'data/ereversed-export.json','integer_export_max_coordinate_adjustment_units':1,
        'all_other_glyf_hmtx_and_gsub_preserved':True,'selected_de_and_te_preserved':True,'whole_glyph_mirror_used':False}

class PlotPen(BasePen):
    def __init__(self,gs):super().__init__(gs);self.v=[];self.c=[]
    def _moveTo(self,p):self.v.append(p);self.c.append(MP.MOVETO)
    def _lineTo(self,p):self.v.append(p);self.c.append(MP.LINETO)
    def _curveToOne(self,a,b,c):self.v.extend([a,b,c]);self.c.extend([MP.CURVE4]*3)
    def _closePath(self):self.v.append((0,0));self.c.append(MP.CLOSEPOLY)
def draw(ax,tt,name,x=0,y=0,scale=1,color='#282334'):
    gs=tt.getGlyphSet();p=PlotPen(gs);gs[name].draw(p)
    if p.v:ax.add_patch(PathPatch(MP(np.array(p.v)*scale+[x,y],p.c),facecolor=color,lw=0))
def word(ax,text,v,x,y,scale,color='#282334'):
    for n,adv,_,dx,dy in hb_shape(out/f'ereversed-{v}.ttf',text,{'liga':False}):
        draw(ax,fonts[v],n,x+dx*scale,y+dy*scale,scale,color);x+=adv*scale
fig=plt.figure(figsize=(16,14),facecolor='#f5f1e9')
fig.text(.055,.958,'э / открытая чаша и тонкая перекладина',fontsize=25,color='#282334')
fig.text(.055,.921,'Very Peri Serif · новые окончания на основе родной пластики',fontsize=12,color='#827b73')
for i,(v,spec) in enumerate(design['variants'].items()):
    x=.055+i*.49;fig.text(x,.86,f'{v} / {spec["name"]}',fontsize=19,color='#282334')
    ax=fig.add_axes([x+.035,.59,.355,.235]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,390);ax.set_ylim(-30,555);draw(ax,fonts[v],target)
    ax=fig.add_axes([x,.395,.425,.17]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,3400);ax.set_ylim(-260,900)
    pos=0
    for ch in ['э','o','c','e','г','т']:
        n=fonts[v].getBestCmap()[ord(ch)];draw(ax,fonts[v],n,pos,color='#8d8479' if ch in ['o','c','e'] else '#282334')
        ax.text(pos+fonts[v]['hmtx'][n][0]/2,840,ch,ha='center',fontsize=10,color='#827b73');pos+=fonts[v]['hmtx'][n][0]+85
    ax=fig.add_axes([x,.10,.425,.265]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,3650);ax.set_ylim(-220,2650)
    for text,y in [('это эра',1900),('эге эго',950),('дуэт эхо',0)]:word(ax,text,v,0,y,.74)
fig.text(.055,.05,'Серые o/c/e — исходник. Г с каплей, т02 и д01 сохранены. Все строки — настоящие глифы.',fontsize=10,color='#827b73')
fig.text(.055,.027,'Обе э — предложения к выбору. Наклон Italic не применяется; кернинг предварительный.',fontsize=10,color='#827b73')
fig.savefig(out/'comparison.png',dpi=160,facecolor=fig.get_facecolor());fig.savefig(out/'comparison.svg',facecolor=fig.get_facecolor());plt.close(fig)
fig=plt.figure(figsize=(9,7),facecolor='#f5f1e9');ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,648);ax.set_ylim(0,504);ax.axis('off');ax.add_patch(Rectangle((324,0),324,504,facecolor='#282334',lw=0))
for i,(v,spec) in enumerate(design['variants'].items()):
    top=475-i*245
    for x,color in [(20,'#282334'),(344,'#f5f1e9')]:
        ax.text(x,top,f'{v} / {spec["name"]}',fontsize=12,color=color)
        for size,dy in [(12,38),(24,87),(100,195)]:
            ax.text(x,top-dy+4,str(size)+' pt',fontsize=8,color=color);word(ax,'это',v,x+55,top-dy,size/1000,color)
fig.savefig(out/'sizes.png',dpi=180,facecolor=fig.get_facecolor());fig.savefig(out/'sizes.svg',facecolor=fig.get_facecolor());plt.close(fig)
(out/'metrics.json').write_text(json.dumps({'variants':metrics,'combinations':combinations},ensure_ascii=False,indent=2)+'\n')
(out/'outline-audit.json').write_text(json.dumps({'status':'passed','sample_points_per_cubic':600,'variants':checks,'limits':'Sampled topology/distance; optical acceptance remains open.','fontbakery':'not run','hyperglot':'not run'},ensure_ascii=False,indent=2)+'\n')
baseline=json.loads((base/'approved-baseline.json').read_text());baseline['fixed_glyphs'][pins[1]['glyph']]={'hmtx':pins[1]['hmtx'],'glyf_sha256':pins[1]['glyf_sha256']};baseline['source_file']='ereversed01/02: both unselected; te02/de01 selected'
(out/'approved-baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n');(out/'OFL.txt').write_bytes((base/'OFL.txt').read_bytes())
print(json.dumps({'variants':metrics,'checks':checks,'combinations':len(combinations)},ensure_ascii=False,indent=2))
