from pathlib import Path
import json,math
import numpy as np
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'build/research-deep/native';OUT.mkdir(parents=True,exist_ok=True)
F=GSFont(str(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'))
rows=[]
for g in F.glyphs:
 l=g.layers['m01']
 if l is None:continue
 p=RecordingPen();l.draw(p);ss=[];current=None;contour=-1
 for i,(op,ps) in enumerate(p.value):
  if op=='moveTo':current=np.array(ps[0],float);contour+=1
  elif op=='curveTo':
   pts=np.array([current,*ps],float);ss.append((i,contour,pts));current=pts[-1]
  elif op=='lineTo':current=np.array(ps[0],float)
 for a,b in zip(ss,ss[1:]):
  if a[1]!=b[1] or b[0]!=a[0]+1:continue
  if not np.array_equal(a[2][-1],b[2][0]):continue
  p0=a[2][0];p3=b[2][-1];chord=p3-p0;w=np.linalg.norm(chord)
  if not 20<=w<=30:continue
  allpts=np.vstack([a[2],b[2]])
  if np.max(np.linalg.norm(allpts-p0,axis=1))>40:continue
  v=a[2][1]-p0;u=p3-b[2][-2];ang=math.degrees(math.acos(np.clip(np.dot(v,u)/np.linalg.norm(v)/np.linalg.norm(u),-1,1)))
  if ang<140:continue
  rows.append({'glyph':g.name,'commands':[a[0],b[0]],'points':[a[2].tolist(),b[2].tolist()],'chord_length':float(w),'chord_angle_deg':math.degrees(math.atan2(chord[1],chord[0])),'terminal_tangent_rotation_deg':ang})
(OUT/'all-master-cap-candidates.json').write_text(json.dumps({'method':'Geometric candidate scan only, not semantic classification: consecutive cubics with same contour and shared join, endpoint chord20..30units, all controlpoints within40units of starting point, endpoint tangent direction difference>=140degrees. Includes non-letter/mark/interior fillet candidates.','candidates':rows},ensure_ascii=False,indent=2)+'\n')
print('candidates',len(rows))
print([(r['glyph'],round(r['chord_angle_deg'],1),r['commands']) for r in rows if 20<abs(r['chord_angle_deg'])<70][:80])
