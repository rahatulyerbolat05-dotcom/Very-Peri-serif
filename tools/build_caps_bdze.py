"""One proposal each for Б Д З; preserve the existing capital И exactly."""
from pathlib import Path
from types import SimpleNamespace
import json,hashlib
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.ttLib import TTFont
from study_layout import add_order,mark_base,names,save_font,hb_shape
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capitals-bdzei';OUT.mkdir(parents=True,exist_ok=True)
f=GSFont(str(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'))
def src(n):
 p=RecordingPen();f.glyphs[n].layers[0].draw(p);return p.value
def c(op,*pts):return op,pts
def shift(ops,dx,dy):return [(op,tuple((x+dx,y+dy) for x,y in pts)) for op,pts in ops]
b,e,a,t=map(src,['B','E','a','three'])
be=b[:4]+[c('curveTo',(275,410),(220,412),(174,412)),c('curveTo',(165,412),(160,417),(160,426))]+e[23:42]+b[18:25]
de=[c('moveTo',(28,-110)),c('curveTo',(20,-110),(16,-104),(17,-94)),c('lineTo',(25,15)),c('curveTo',(26,28),(34,36),(46,37)),c('curveTo',(92,44),(112,66),(129,129)),c('lineTo',(260,651)),c('curveTo',(266,675),(260,687),(238,692)),c('lineTo',(211,697)),c('curveTo',(202,699),(198,703),(198,709)),c('curveTo',(198,716),(203,720),(213,720)),c('lineTo',(553,720)),c('curveTo',(563,720),(568,716),(568,709)),c('curveTo',(568,703),(564,699),(555,697)),c('lineTo',(532,693)),c('curveTo',(504,688),(498,682),(498,654)),c('lineTo',(498,80)),c('curveTo',(498,52),(506,39),(535,37)),c('curveTo',(548,35),(556,27),(556,15)),c('lineTo',(565,-94)),c('curveTo',(566,-104),(562,-110),(554,-110)),c('curveTo',(547,-110),(543,-105),(541,-97)),c('lineTo',(529,-44)),c('curveTo',(523,-14),(509,0),(480,0)),c('lineTo',(102,0)),c('curveTo',(73,0),(59,-14),(53,-44)),c('lineTo',(41,-97)),c('curveTo',(39,-105),(35,-110),(28,-110)),c('closePath'),c('moveTo',(170,30)),c('lineTo',(413,30)),c('curveTo',(423,30),(427,38),(427,54)),c('lineTo',(427,654)),c('curveTo',(427,682),(415,695),(389,695)),c('lineTo',(314,695)),c('curveTo',(306,695),(301,688),(299,679)),c('lineTo',(159,121)),c('curveTo',(148,74),(148,30),(170,30)),c('closePath')]
ze=t[:2]+[c('curveTo',(341,337),(294,408),(222,420)),c('curveTo',(214,422),(214,429),(223,433)),c('curveTo',(281,456),(314,520),(314,596)),c('curveTo',(314,676),(260,730),(188,730)),c('curveTo',(110,730),(36,681),(36,599))]+shift(a[12:14],5,244)+[c('curveTo',(129,691),(153,700),(180,700)),c('curveTo',(225,700),(246,661),(246,610)),c('curveTo',(246,508),(211,439),(159,429)),c('curveTo',(141,425),(119,422),(102,421)),c('curveTo',(91,420),(87,414),(87,407)),c('curveTo',(87,399),(92,394),(102,397)),c('curveTo',(121,403),(139,405),(159,405))]+t[18:24]
specs=[('Б','uni0411',478,be,'H'),('Д','uni0414',590,de,'H'),('З','uni0417',371,ze,'O')]
# Sample contours for topology; curve exports stay Beziers.
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
def validate(rec,gs=None):
 s=Sample(gs);rec.draw(s) if gs is not None else rec.replay(s)
 assert all(LinearRing(r).is_simple for r in s.rings)
 if len(s.rings)==2:assert Polygon(s.rings[0]).contains(Polygon(s.rings[1]))
 return len(s.rings)
records={};metrics=[]
for ch,n,w,ops,donor in specs:
 p=RecordingPen();p.value=ops;records[n]=p;count=validate(p);bp=BoundsPen(None);p.replay(bp)
 (OUT/(n+'.glif')).write_text(writeGlyphToString(n,SimpleNamespace(width=w,unicodes=[ord(ch)]),lambda pp:p.replay(SegmentToPointPen(pp)),formatVersion=2))
 metrics.append({'character':ch,'advance':w,'bounds':bp.bounds,'contours':count,'status':'single unapproved proposal','sampled_topology':'passed'})
reports=[]
for v in ['01','02']:
 base=ROOT/f'studies/regular/capital-i/capital-i-shorti{v}.ttf';tt=TTFont(base);old=TTFont(base);add_order(tt,[s[1] for s in specs])
 for ch,n,w,ops,donor in specs:
  pen=TTGlyphPen(None);records[n].replay(Cu2QuPen(pen,.5,reverse_direction=True));g=pen.glyph();tt['glyf'][n]=g;g.recalcBounds(tt['glyf']);tt['hmtx'][n]=(w,g.xMin)
  for table in tt['cmap'].tables:
   if table.isUnicode():table.cmap[ord(ch)]=n
  tt['GDEF'].table.GlyphClassDef.classDefs[n]=1;mark_base(tt,n,donor,top=(w//2,720),bottom=(w//2,-110 if ch=='Д' else 0),active_classes={0,2})
  validate(tt.getGlyphSet()[n],tt.getGlyphSet())
 names(tt,'CapsBDZeIShortI'+v);dest=OUT/f'capitals-shorti{v}.ttf';save_font(tt,dest);new=TTFont(dest)
 for n in old.getGlyphOrder():
  assert old['glyf'][n].compile(old['glyf'])==new['glyf'][n].compile(new['glyf']),n
  assert old['hmtx'][n]==new['hmtx'][n],n
 assert old['GSUB'].compile(old)==new['GSUB'].compile(new)
 for text in ['БДЗИ','Боря','Дора','Зоя','Ива','Б\u0301Д\u0301З\u0301']:hb_shape(dest,text)
 for text in ['AVATAR','office','HИH','кч','кт','чая','якоря']:assert hb_shape(dest,text)==hb_shape(base,text)
 reports.append({'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'existing_glyphs_preserved':len(old.getGlyphOrder()),'capital_I_preserved':True,'shaping':'passed'})
(OUT/'metrics.json').write_text(json.dumps({'glyphs':metrics,'builds':reports},ensure_ascii=False,indent=2)+'\n');(OUT/'design.json').write_text(json.dumps({ch:ops for ch,n,w,ops,d in specs},ensure_ascii=False,indent=2)+'\n');(OUT/'OFL.txt').write_bytes((ROOT/'OFL.txt').read_bytes());(OUT/'uni0418.glif').write_bytes((ROOT/'studies/regular/capital-i/uni0418.glif').read_bytes());print(json.dumps(metrics,ensure_ascii=False))
