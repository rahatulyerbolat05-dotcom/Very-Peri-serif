"""Capital soft sign from native B bowl and I head."""
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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capital-soft-sign';OUT.mkdir(parents=True,exist_ok=True)
f=GSFont(str(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'))
def src(n):
 p=RecordingPen();f.glyphs[n].layers[0].draw(p);return p.value
def c(op,*pts):return op,pts
def shift(ops,dx,dy):return [(op,tuple((x+dx,y+dy) for x,y in pts)) for op,pts in ops]
b,i=map(src,['B','I'])
soft=b[:4]+[c('curveTo',(275,410),(220,412),(174,412)),c('curveTo',(165,412),(160,417),(160,426))]+i[6:22]+b[18:25]
specs=[('Ь','uni042C',478,soft,'H')]
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
 base=ROOT/f'studies/regular/capitals-jfya/capitals-shorti{v}.ttf';tt=TTFont(base);old=TTFont(base);add_order(tt,[s[1] for s in specs])
 for ch,n,w,ops,donor in specs:
  pen=TTGlyphPen(None);records[n].replay(Cu2QuPen(pen,.5,reverse_direction=True));g=pen.glyph();tt['glyf'][n]=g;g.recalcBounds(tt['glyf']);tt['hmtx'][n]=(w,g.xMin)
  for table in tt['cmap'].tables:
   if table.isUnicode():table.cmap[ord(ch)]=n
  tt['GDEF'].table.GlyphClassDef.classDefs[n]=1;mark_base(tt,n,donor,top=(125,720),bottom=(w//2,0),active_classes={0,2})
  validate(tt.getGlyphSet()[n],tt.getGlyphSet())
 names(tt,'CapitalSoftSignShortI'+v);dest=OUT/f'capitals-shorti{v}.ttf';save_font(tt,dest);new=TTFont(dest)
 for n in old.getGlyphOrder():
  assert old['glyf'][n].compile(old['glyf'])==new['glyf'][n].compile(new['glyf']),n
  assert old['hmtx'][n]==new['hmtx'][n],n
 assert old['GSUB'].compile(old)==new['GSUB'].compile(new)
 for text in ['Ь','ЯЗЬ','ЗЯБЬ','Ь\u0301']:hb_shape(dest,text)
 for text in ['AVATAR','office','HИH','кч','кт','чая','якоря']:assert hb_shape(dest,text)==hb_shape(base,text)
 reports.append({'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'existing_glyphs_preserved':len(old.getGlyphOrder()),'capital_I_preserved':True,'shaping':'passed'})
(OUT/'metrics.json').write_text(json.dumps({'glyphs':metrics,'builds':reports},ensure_ascii=False,indent=2)+'\n');(OUT/'design.json').write_text(json.dumps({ch:ops for ch,n,w,ops,d in specs},ensure_ascii=False,indent=2)+'\n');(OUT/'OFL.txt').write_bytes((ROOT/'OFL.txt').read_bytes());print(json.dumps(metrics,ensure_ascii=False))
