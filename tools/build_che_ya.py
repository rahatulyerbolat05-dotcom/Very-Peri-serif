"""One upright handwritten study each for ч and я, with native donor fragments."""
from pathlib import Path
from types import SimpleNamespace
import copy,json,hashlib,sys
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.ttLib import TTFont
from study_layout import add_order,mark_base,names,save_font,hb_shape
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/che-ya';OUT.mkdir(parents=True,exist_ok=True)
f=GSFont(str(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'))
def commands(n):
 p=RecordingPen();f.glyphs[n].layers[0].draw(p);return p.value
u,a,y=map(commands,['u','a','y'])
def shift(cmds,dx=0,dy=0):return [(op,tuple((x+dx,yy+dy) for x,yy in pts)) for op,pts in cmds]
def cmd(op,*pts):return (op,pts)
che=[cmd('moveTo',(171,221))]+shift(u[1:3],dy=230)+u[3:18]+[cmd('lineTo',(312,396))]+shift(u[19:21],dy=230)+u[21:28]+[cmd('lineTo',(70,331))]+shift(u[29:30],dy=230)+[cmd('closePath')]
ya=[cmd('moveTo',(83,-9))]+shift(y[1:2],dy=196)+[
 cmd('lineTo',(224,248)),cmd('curveTo',(245,248),(263,251),(280,260)),
 cmd('lineTo',(280,95)),cmd('curveTo',(280,75),(287,70),(289,57))]+shift(a[3:10],dx=35)+[
 cmd('curveTo',(348,479),(313,516),(245,516)),
 cmd('curveTo',(134,516),(52,455),(52,375)),
 cmd('curveTo',(52,291),(110,250),(191,244)),
 cmd('curveTo',(183,216),(170,161),(161,132))]+shift(y[26:30],dy=196)+[
 cmd('closePath'),cmd('moveTo',(224,277)),
 cmd('curveTo',(166,277),(129,311),(129,375)),
 cmd('curveTo',(129,451),(165,491),(224,491)),
 cmd('curveTo',(263,491),(280,464),(280,420)),cmd('lineTo',(280,314)),
 cmd('curveTo',(280,288),(261,277),(224,277)),cmd('closePath')]
specs=[('ч','uni0447',454,che),('я','uni044F',444,ya)]
records={};metrics=[]
# Sampled topology validation; exported curves remain Beziers.
import numpy as np
from fontTools.pens.basePen import BasePen
from shapely.geometry import LinearRing,Polygon
class Sample(BasePen):
 def __init__(self,gs=None):super().__init__(gs);self.rings=[]
 def _moveTo(self,p):self.pts=[p]
 def _lineTo(self,p):self.pts.append(p)
 def _curveToOne(self,a,b,c):
  p=np.array(self._getCurrentPoint());t=np.linspace(0,1,201)[1:,None];self.pts.extend(map(tuple,(1-t)**3*p+3*(1-t)**2*t*np.array(a)+3*(1-t)*t*t*np.array(b)+t**3*np.array(c)))
 def _closePath(self):self.rings.append(self.pts)
for ch,name,width,ops in specs:
 p=RecordingPen();p.value=ops;records[name]=p;b=BoundsPen(None);p.replay(b)
 sample=Sample();p.replay(sample)
 assert all(LinearRing(r).is_simple for r in sample.rings),ch
 if len(sample.rings)==2:assert Polygon(sample.rings[0]).contains(Polygon(sample.rings[1]))
 for op,pts in ops:
  if op=='curveTo':assert pts[0]!=pts[1] and pts[1]!=pts[2],(ch,pts)
 glif=writeGlyphToString(name,SimpleNamespace(width=width,unicodes=[ord(ch)]),lambda pp:p.replay(SegmentToPointPen(pp)),formatVersion=2)
 (OUT/(name+'.glif')).write_text(glif)
 metrics.append({'character':ch,'glyph':name,'advance':width,'bounds':b.bounds,'contours':len(sample.rings),'status':'single proposal, awaiting user selection','sampled_topology_valid':True})
reports=[]
for variant in ['01','02']:
 base=ROOT/f'studies/regular/context-selected/selected-shorti{variant}.ttf';tt=TTFont(base);old=TTFont(base);add_order(tt,[s[1] for s in specs])
 for ch,name,width,ops in specs:
  pen=TTGlyphPen(None);records[name].replay(Cu2QuPen(pen,.5,reverse_direction=True));g=pen.glyph();tt['glyf'][name]=g;g.recalcBounds(tt['glyf']);tt['hmtx'][name]=(width,g.xMin)
  for table in tt['cmap'].tables:
   if table.isUnicode():table.cmap[ord(ch)]=name
  tt['GDEF'].table.GlyphClassDef.classDefs[name]=1
  mark_base(tt,name,'u' if ch=='ч' else 'a',top=(width//2,510),bottom=(width//2,0),active_classes={0,2})
  sam=Sample(tt.getGlyphSet());tt.getGlyphSet()[name].draw(sam);assert all(LinearRing(r).is_simple for r in sam.rings),(ch,'TTF topology')
 # ч has the same upper-left head as u; extend only calt's following-head coverage.
 for lookup in tt['GSUB'].table.LookupList.Lookup:
  for sub in lookup.SubTable:
   if hasattr(sub,'LookAheadCoverage'):
    for coverage in sub.LookAheadCoverage:
     if 'uni043A.short' in coverage.glyphs:coverage.glyphs=sorted(set(coverage.glyphs)|{'uni0447'},key=tt.getReverseGlyphMap().get)
 names(tt,'CheYaShortI'+variant);path=OUT/f'che-ya-shorti{variant}.ttf';save_font(tt,path);new=TTFont(path)
 for name in old.getGlyphOrder():
  assert old['glyf'][name].compile(old['glyf'])==new['glyf'][name].compile(new['glyf']),name
  assert old['hmtx'][name]==new['hmtx'][name],name
 for text in ['чая','чача','якоря','я тебя','ч\u0301я\u0301','кч','кя']:hb_shape(path,text)
 assert hb_shape(path,'кч')[0][0]=='uni043A.short'
 assert hb_shape(path,'кя')[0][0]=='uni043A'
 for text in ['AVATAR','office','minimum','a\u0301','ккк','кт','ки']:
  assert hb_shape(path,text)==hb_shape(base,text)
 reports.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'existing_glyphs_preserved':len(old.getGlyphOrder()),'shape_and_context_checks':'passed'})
(OUT/'metrics.json').write_text(json.dumps({'glyphs':metrics,'builds':reports},ensure_ascii=False,indent=2)+'\n')
(OUT/'design.json').write_text(json.dumps({'che':che,'ya':ya},ensure_ascii=False,indent=2)+'\n')
(OUT/'OFL.txt').write_bytes((ROOT/'OFL.txt').read_bytes());print(json.dumps(metrics,ensure_ascii=False))
