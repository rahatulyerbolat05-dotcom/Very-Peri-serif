"""Capital И: exact native H stems/serifs, new ascending hairline and local joins."""
from pathlib import Path
from types import SimpleNamespace
import json,hashlib,math
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ufoLib.glifLib import writeGlyphToString
from fontTools.ttLib import TTFont
from study_layout import add_order,mark_base,inherit_native_kern,names,save_font,hb_shape
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capital-i';OUT.mkdir(parents=True,exist_ok=True)
f=GSFont(str(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'));r=RecordingPen();f.glyphs['H'].layers[0].draw(r);h=r.value
ops=h[:6]+[
 ('lineTo',((160,90),)),('curveTo',((160,98),(165,106),(174,124))),
 ('lineTo',((372,527),)),('curveTo',((382,547),(386,547),(386,531)))]+h[10:30]+[
 ('lineTo',((386,630),)),('curveTo',((386,620),(380,612),(372,596))),
 ('lineTo',((174,193),)),('curveTo',((164,173),(160,173),(160,189)))]+h[34:]
p=RecordingPen();p.value=ops;name='uni0418';width=546
(OUT/'uni0418.glif').write_text(writeGlyphToString(name,SimpleNamespace(width=width,unicodes=[0x418]),lambda pp:p.replay(SegmentToPointPen(pp)),formatVersion=2))
# Numerical topology check of source and exported curves.
import numpy as np
from shapely.geometry import LinearRing
from fontTools.pens.basePen import BasePen
class Sample(BasePen):
 def __init__(self,gs=None):super().__init__(gs);self.points=[]
 def _moveTo(self,p):self.points.append(p)
 def _lineTo(self,p):self.points.append(p)
 def _curveToOne(self,a,b,c):
  p=np.array(self._getCurrentPoint());t=np.linspace(0,1,201)[1:,None];self.points.extend(map(tuple,(1-t)**3*p+3*(1-t)**2*t*np.array(a)+3*(1-t)*t*t*np.array(b)+t**3*np.array(c)))
 def _closePath(self):pass
s=Sample();p.replay(s);assert LinearRing(s.points).is_simple
reports=[]
for v in ['01','02']:
 base=ROOT/f'studies/regular/che-ya/che-ya-shorti{v}.ttf';tt=TTFont(base);old=TTFont(base);add_order(tt,[name])
 pen=TTGlyphPen(None);p.replay(Cu2QuPen(pen,.5,reverse_direction=True));g=pen.glyph();tt['glyf'][name]=g;g.recalcBounds(tt['glyf']);tt['hmtx'][name]=(width,g.xMin)
 assert (g.xMin,g.yMin,g.xMax,g.yMax)==(19,0,527,720)
 for t in tt['cmap'].tables:
  if t.isUnicode():t.cmap[0x418]=name
 tt['GDEF'].table.GlyphClassDef.classDefs[name]=1
 mark_base(tt,name,'H',top=(273,720),bottom=(273,0),active_classes={0,2});inherit_native_kern(tt,{name:'H'});names(tt,'CapitalIShortI'+v)
 dest=OUT/f'capital-i-shorti{v}.ttf';save_font(tt,dest);new=TTFont(dest)
 for n in old.getGlyphOrder():
  assert old['glyf'][n].compile(old['glyf'])==new['glyf'][n].compile(new['glyf']),n
  assert old['hmtx'][n]==new['hmtx'][n],n
 assert old['GSUB'].compile(old)==new['GSUB'].compile(new)
 sample=Sample(new.getGlyphSet());new.getGlyphSet()[name].draw(sample);assert LinearRing(sample.points).is_simple
 for text in ['Ива','Ира','Игоря','HИH','OИO','И\u0301']:hb_shape(dest,text)
 for text in ['AVATAR','office','HTo','кч','кт','чая','якоря']:assert hb_shape(dest,text)==hb_shape(base,text)
 reports.append({'file':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'existing_glyphs_preserved':len(old.getGlyphOrder()),'GSUB_preserved':True,'topology_and_shaping':'passed'})
metrics={'character':'И','status':'single proposal, not user-approved','advance':546,'bounds':[19,0,527,720],'stems':71,'diagonal_normal_thickness':69*198/math.hypot(198,403),'diagonal_angle_degrees':math.degrees(math.atan2(403,198)),'donors':'native H stems and all four serifs exactly retained in cubic source; new ascending hairline and four local joins','native_N':'comparison only; no reflected N or assumption that historical D8 was approved','kerning':'H edge classes inherited as starting values, Cyrillic pairs not final','builds':reports}
(OUT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n');(OUT/'design.json').write_text(json.dumps(ops,indent=2)+'\n');(OUT/'OFL.txt').write_bytes((ROOT/'OFL.txt').read_bytes());print(json.dumps(metrics,ensure_ascii=False))
