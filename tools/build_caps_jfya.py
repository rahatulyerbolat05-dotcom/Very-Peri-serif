"""Capital Й Ф Я proposals, retaining earlier selected glyphs."""
from pathlib import Path
from types import SimpleNamespace
import json,hashlib,copy
import pathops
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.pointPen import SegmentToPointPen,PointToSegmentPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ufoLib.glifLib import writeGlyphToString,readGlyphFromString
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from study_layout import add_order,mark_base,names,save_font,hb_shape
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capitals-jfya';OUT.mkdir(parents=True,exist_ok=True)
f=GSFont(str(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'))
def src(n):
 p=RecordingPen();f.glyphs[n].layers[0].draw(p);return p

def transformed(p,t):
 r=RecordingPen();p.replay(TransformPen(r,t));return r

def c(op,*pts):return op,pts

def union(a,b):
 pa=pathops.Path();pb=pathops.Path();a.replay(pa.getPen());b.replay(pb.getPen());result=pathops.op(pa,pb,pathops.PathOp.UNION);rec=RecordingPen();result.draw(rec);return rec
ishort=RecordingPen();readGlyphFromString((ROOT/'studies/regular/capital-i/uni0418.glif').read_text(),SimpleNamespace(),PointToSegmentPen(ishort));ishort.value+=transformed(src('brevecomb'),(1,0,0,1,69,210)).value
oval=RecordingPen();oval.value=[c('moveTo',(325,90)),c('curveTo',(485,90),(615,210),(615,360)),c('curveTo',(615,510),(485,630),(325,630)),c('curveTo',(165,630),(35,510),(35,360)),c('curveTo',(35,210),(165,90),(325,90)),c('closePath'),c('moveTo',(325,117)),c('curveTo',(204,117),(114,185),(114,360)),c('curveTo',(114,535),(204,603),(325,603)),c('curveTo',(446,603),(536,535),(536,360)),c('curveTo',(536,185),(446,117),(325,117)),c('closePath')]
ef=union(oval,transformed(src('I'),(1,0,0,1,200.5,0)))
# Reflection is limited to the P bowl/stem skeleton: a new thin diagonal and A foot
# establish the ascending stroke weight; this is not a reflected R.
pr=transformed(src('P'),(-1,0,0,1,500,0));aa=transformed(src('A'),(1,0,0,1,10,0));leg=RecordingPen();leg.value=aa.value[:6]+[c('lineTo',(243,351)),c('lineTo',(214,357)),c('lineTo',(68,89))]+aa.value[24:29]
# Align the new diagonal with the two inherited foot curves (local handle edits).
leg.value[5]=c('curveTo',(98,29),(99-144/263*20,68),(99,88))
leg.value[9]=c('curveTo',(68-146/268*20,69),(47,31),(21,26))
ya=union(pr,leg)
specs=[('Й','uni0419',546,ishort,'H',940),('Ф','uni0424',650,ef,'O',720),('Я','uni042F',519,ya,'H',720)]
# Numerical source/export contour checks.
import numpy as np
from shapely.geometry import LinearRing,Polygon
from fontTools.pens.basePen import BasePen
class Sample(BasePen):
 def __init__(self,gs=None):super().__init__(gs);self.rings=[]
 def _moveTo(self,p):self.pts=[p]
 def _lineTo(self,p):self.pts.append(p)
 def _curveToOne(self,a,b,c):
  p=np.array(self._getCurrentPoint());t=np.linspace(0,1,201)[1:,None];self.pts.extend(map(tuple,(1-t)**3*p+3*(1-t)**2*t*np.array(a)+3*(1-t)*t*t*np.array(b)+t**3*np.array(c)))
 def _closePath(self):self.rings.append(self.pts)
def audit(rec,gs=None):
 s=Sample(gs);rec.draw(s) if gs is not None else rec.replay(s);assert all(LinearRing(r).is_simple for r in s.rings)
 for i,a in enumerate(s.rings):
  for b in s.rings[i+1:]:assert not LinearRing(a).intersects(LinearRing(b))
 return len(s.rings)
metrics=[]
for ch,n,w,p,donor,top in specs:
 count=audit(p);bp=BoundsPen(None);p.replay(bp)
 (OUT/(n+'.glif')).write_text(writeGlyphToString(n,SimpleNamespace(width=w,unicodes=[ord(ch)]),lambda pp:p.replay(SegmentToPointPen(pp)),formatVersion=2))
 metrics.append({'character':ch,'advance':w,'bounds':bp.bounds,'contours':count,'status':'proposal awaiting user approval','sampled_topology':'passed'})
reports=[]
for v in ['01','02']:
 base=ROOT/f'studies/regular/capitals-bdzei/capitals-shorti{v}.ttf';tt=TTFont(base);old=TTFont(base);add_order(tt,[s[1] for s in specs])
 for ch,n,w,p,donor,top in specs:
  pen=TTGlyphPen(tt.getGlyphSet())
  if ch=='Й':
   pen.addComponent('uni0418',(1,0,0,1,0,0));pen.addComponent('uni0306',(1,0,0,1,69,210))
  else:p.replay(Cu2QuPen(pen,.5,reverse_direction=True))
  g=pen.glyph();tt['glyf'][n]=g;g.recalcBounds(tt['glyf']);tt['hmtx'][n]=(w,g.xMin)
  for table in tt['cmap'].tables:
   if table.isUnicode():table.cmap[ord(ch)]=n
  tt['GDEF'].table.GlyphClassDef.classDefs[n]=1;mark_base(tt,n,donor,top=(w//2,top),bottom=(w//2,0),active_classes={0,2})
  audit(tt.getGlyphSet()[n],tt.getGlyphSet())
 # Canonical И + breve composition, preserving original ccmp lookups.
 sub=ot.LigatureSubst();lig=ot.Ligature();lig.LigGlyph='uni0419';lig.CompCount=2;lig.Component=['uni0306'];sub.ligatures={'uni0418':[lig]}
 lookup=ot.Lookup();lookup.LookupType=4;lookup.LookupFlag=0;lookup.SubTable=[sub];lookup.SubTableCount=1
 gsub=tt['GSUB'].table;idx=len(gsub.LookupList.Lookup);gsub.LookupList.Lookup.append(lookup);gsub.LookupList.LookupCount+=1
 for fr in gsub.FeatureList.FeatureRecord:
  if fr.FeatureTag=='ccmp':fr.Feature.LookupListIndex.append(idx);fr.Feature.LookupCount+=1
 names(tt,'CapsJFYaShortI'+v);dest=OUT/f'capitals-shorti{v}.ttf';save_font(tt,dest);new=TTFont(dest)
 for n in old.getGlyphOrder():
  assert old['glyf'][n].compile(old['glyf'])==new['glyf'][n].compile(new['glyf']),n
  assert old['hmtx'][n]==new['hmtx'][n],n
 for text in ['Йод','Фора','Яра','Й\u0301','Ф\u0301Я\u0301']:hb_shape(dest,text)
 assert hb_shape(dest,'Й')==hb_shape(dest,'И\u0306')
 assert hb_shape(dest,'Й\u0301')==hb_shape(dest,'И\u0306\u0301')
 for text in ['AVATAR','office','HИH','кч','кт','Боря','Дора','Зоя']:assert hb_shape(dest,text)==hb_shape(base,text)
 reports.append({'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'existing_glyphs_preserved':len(old.getGlyphOrder()),'canonical_ishort_composition':'passed','shaping':'passed'})
(OUT/'metrics.json').write_text(json.dumps({'glyphs':metrics,'builds':reports},ensure_ascii=False,indent=2)+'\n');(OUT/'design.json').write_text(json.dumps({ch:p.value for ch,n,w,p,d,t in specs},ensure_ascii=False,indent=2)+'\n');(OUT/'OFL.txt').write_bytes((ROOT/'OFL.txt').read_bytes());print(json.dumps(metrics,ensure_ascii=False))
