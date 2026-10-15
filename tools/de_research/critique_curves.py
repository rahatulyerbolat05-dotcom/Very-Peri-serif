from pathlib import Path
import json, math
import numpy as np
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen,replayRecording
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import nearest_points
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'build/research-deep/critique';OUT.mkdir(parents=True,exist_ok=True)
FONT=GSFont(ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'); MID=FONT.masters[0].id
CURRENT=json.loads((ROOT/'studies/reference-analysis/de-curves-deep/critique/rejected-outlines.json').read_text())['variants']
def native(name):
 p=RecordingPen();FONT.glyphs[name].layers[MID].draw(p);return p.value

def segments(commands):
 result=[];p=start=None;ci=-1
 for op,ps in commands:
  if op=='moveTo':p=start=np.array(ps[0],float);ci+=1
  elif op=='curveTo':
   q=np.array(ps,float);result.append({'i':len(result),'ci':ci,'kind':'cubic','p':np.vstack([p,q])});p=q[-1]
  elif op=='lineTo':
   q=np.array(ps[0],float);result.append({'i':len(result),'ci':ci,'kind':'line','p':np.vstack([p,q])});p=q
  elif op=='closePath' and np.linalg.norm(p-start)>1e-9:result.append({'i':len(result),'ci':ci,'kind':'line','p':np.vstack([p,start])});p=start
 return result

def sample(s,n=601):
 p=s['p'];t=np.linspace(0,1,n)[:,None]
 return (1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3] if len(p)==4 else (1-t)*p[0]+t*p[1]
def derivative(s,t):
 p=s['p']
 if len(p)==2:return p[1]-p[0]
 return 3*((1-t)**2*(p[1]-p[0])+2*(1-t)*t*(p[2]-p[1])+t*t*(p[3]-p[2]))
def curvature(s,t):
 p=s['p']
 if len(p)==2:return 0.
 d=derivative(s,t);dd=6*((1-t)*(p[2]-2*p[1]+p[0])+t*(p[3]-2*p[2]+p[1]));return float((d[0]*dd[1]-d[1]*dd[0])/np.linalg.norm(d)**3)
def joinstats(cmds):
 ss=segments(cmds);out=[]
 for ci in set(s['ci'] for s in ss):
  rr=[s for s in ss if s['ci']==ci]
  for a,b in zip(rr,rr[1:]+rr[:1]):
   da=derivative(a,1);db=derivative(b,0);ang=math.degrees(math.acos(np.clip(da@db/np.linalg.norm(da)/np.linalg.norm(db),-1,1)))
   ka,kb=curvature(a,1),curvature(b,0)
   out.append({'contour':ci,'point':a['p'][-1].tolist(),'angle_deg':ang,'signed_curvature_in':ka,'signed_curvature_out':kb,'radius_in':None if ka==0 else abs(1/ka),'radius_out':None if kb==0 else abs(1/kb),'ratio_abs':None if ka*kb==0 else max(abs(ka),abs(kb))/min(abs(ka),abs(kb))})
 return out

def polygon(cmd):
 ss=segments(cmd);rings=[]
 for ci in set(s['ci'] for s in ss):rings.append(np.vstack([sample(s)[1:] for s in ss if s['ci']==ci]))
 return Polygon(rings[0],rings[1:])

class PlotPen(BasePen):
 def __init__(self):super().__init__(None);self.v=[];self.c=[]
 def _moveTo(self,p):self.v.append(p);self.c.append(MP.MOVETO)
 def _lineTo(self,p):self.v.append(p);self.c.append(MP.LINETO)
 def _curveToOne(self,a,b,c):self.v.extend([a,b,c]);self.c.extend([MP.CURVE4]*3)
 def _closePath(self):self.v.append((0,0));self.c.append(MP.CLOSEPOLY)
def patch(ax,cmds,color='#272431',alpha=1,transform=None,outline=False):
 p=PlotPen();replayRecording(cmds,p);v=np.array(p.v,float)
 if transform:v=transform(v)
 ax.add_patch(PathPatch(MP(v,p.c),facecolor='none' if outline else color,edgecolor=color if outline else 'none',lw=1.3,alpha=alpha))
def curve(ax,s,color='#db6842',lw=1.8,alpha=1,comb=False):
 pts=sample(s);ax.plot(*pts.T,color=color,lw=lw,alpha=alpha)
 if comb and len(s['p'])==4:
  for t in np.linspace(.05,.95,14):
   p=sample(s,101)[int(round(t*100))];d=derivative(s,t);nn=np.array([-d[1],d[0]])/np.linalg.norm(d);k=curvature(s,t)
   ax.plot(*np.array([p,p+nn*k*650]).T,color=color,lw=.7,alpha=.7)
def setup(ax,xlim,ylim):ax.set_aspect('equal');ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.axis('off')

metrics={'source':'Instrument/instrument-serif 65c0ef225f386a3c7e87570a4aa9cc0262c2fd81 Regular cubic master; current retained de-cursive source.','method':'Cubic derivatives analytic at joins; filled area / comparison uses 600 chords per cubic, approximation. Curvature is kappa=(xprime*ysecond-yprime*xsecond)/speed^3. R=1/abs(kappa). G2 is diagnostic, not imposed rule.','current':{k:{'area_sampled':polygon(v['commands']).area,'joins':joinstats(v['commands'])} for k,v in CURRENT.items()},'native':{n:{'area_sampled':polygon(native(n)).area,'joins':joinstats(native(n))} for n in ['o','d','a','b','p','g','u','t','f','r','c']}}
p1,p2=map(lambda k:polygon(CURRENT[k]['commands']),['01','02']);metrics['two_variant_similarity']={'area_union':p1.union(p2).area,'area_intersection':p1.intersection(p2).area,'intersection_over_union':p1.intersection(p2).area/p1.union(p2).area,'symmetric_difference_area':p1.symmetric_difference(p2).area,'same_counter':CURRENT['01']['commands'][-6:]==CURRENT['02']['commands'][-6:]}
# Cap resemblance, similarity alignment (explicitly not testing a construction recipe).
cap1=segments(CURRENT['01']['commands'])[4:6]
# d native cap two cubics: outer tip reaches (452,129), then cap at (440,146), ends (427,130).
dss=segments(native('d'));capd=dss[4:6]
a,b=capd[0]['p'][0],capd[-1]['p'][-1];A,B=cap1[0]['p'][0],cap1[-1]['p'][-1]
z=complex(*(B-A))/complex(*(b-a))
def align(v):
 v=np.array(v);q=(v[...,0]-a[0])+1j*(v[...,1]-a[1]);q=q*z+(A[0]+1j*A[1]);return np.stack([q.real,q.imag],axis=-1)
l1=LineString(np.vstack([sample(s) for s in cap1]));ld=LineString(align(np.vstack([sample(s) for s in capd])))
metrics['terminal_comparison']={'native_d_cap_endpoints':[a.tolist(),b.tolist()],'current_01_cap_endpoints':[A.tolist(),B.tolist()],'scale_for_endpoint_match':abs(z),'rotation_degrees':math.degrees(math.atan2(z.imag,z.real)),'hausdorff_after_similarity_alignment_sampled':l1.hausdorff_distance(ld),'interpretation':'The rounded thin cap is already present in native d/a/t/c. Rejecting every rounded cap as foreign is unsupported. Full lead-in curvature and taper must be assessed separately.'}
(OUT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))

fig=plt.figure(figsize=(16,15),facecolor='#f5f2ec');grid=fig.add_gridspec(3,4,height_ratios=[1.25,1,.85],hspace=.28,wspace=.3)
fig.text(.04,.97,'д: разбор кривых и окончаний, а не новый рисунок',fontsize=22,color='#272431')
fig.text(.04,.943,'Факты геометрии отделены от гипотез о стиле. Верхневыносной письменный скелет остаётся допустимым.',fontsize=12,color='#736b62')
for c,k in enumerate(['01','02']):
 ax=fig.add_subplot(grid[0,c]);cmd=CURRENT[k]['commands'];patch(ax,cmd,color='#db6842',alpha=.9)
 for s in segments(cmd):
  if s['ci']==1 or (s['ci']==0 and s['i'] in [0,11,12]):curve(ax,s,color='#147c75',lw=2.1)
 for yy in [0,510,740]:ax.axhline(yy,color='#bdb5a8',lw=.6,ls='--');ax.text(2,yy+8,str(yy),fontsize=8,color='#81796e')
 ax.annotate('узел возврата',xy=(269,498),xytext=(10,590),fontsize=9,arrowprops={'arrowstyle':'->','color':'#736b62'})
 if k=='02':
  ax.plot([245],[715],'o',color='#a3422b',ms=4)
  ax.text(0,-83,'Внутренний верх: R 135 → 12,4',fontsize=9,color='#a3422b')
 setup(ax,(0,420),(-95,790));ax.set_title(f'д{k}: родная o / новый верх',loc='left',fontsize=13)
ax=fig.add_subplot(grid[0,2:]);
for i,n in enumerate(['o','d','b','a','u','g']):
 patch(ax,native(n),color='#77716a',transform=lambda v,i=i:v*.43+[i*225,0]);ax.text(i*225+80,-58,n,ha='center',fontsize=16)
setup(ax,(-15,1345),(-210,410));ax.set_title('Родные Regular: чаша и контакт со стойкой',loc='left',fontsize=13)
ax.text(0,-170,'Зелёный — точные фрагменты o; оранжевый — новый верх.\nЦелая контрформа o сохраняет симметрию; d/b используют иной контакт со стойкой.',fontsize=10,color='#736b62')

ax=fig.add_subplot(grid[1,:2]);cmd=CURRENT['01']['commands'];patch(ax,cmd,color='#d3ccc2')
ss=segments(cmd)
for i in [7,8,9,10]:curve(ax,ss[i],comb=True)
for i in [7,8,9,10]:
 s=ss[i];ax.plot(*s['p'].T,'o--',color='#aa614a',lw=.6,ms=3,alpha=.7)
ax.annotate('54 ед. прямого участка (допустимо)',xy=(280,546),xytext=(110,575),fontsize=9,arrowprops={'arrowstyle':'->'})
ax.annotate('R ≈ 22 → 611\nкасательная общая, кривизна меняется ×27',xy=(266,495),xytext=(95,425),fontsize=10,arrowprops={'arrowstyle':'->'})
setup(ax,(85,375),(405,655));ax.set_title('Шейка д01/02: локальный резкий поворот',loc='left',fontsize=14)
ax=fig.add_subplot(grid[1,2:]);patch(ax,native('d'),color='#d3ccc2')
for s in segments(native('d')):
 if s['ci']==0 and (s['p'][:,1].min()<520 and s['p'][:,1].max()>480) and s['p'][:,0].min()>230:curve(ax,s,color='#147c75',comb=True)
setup(ax,(180,405),(385,635));ax.set_title('Родная d: малая шейка тоже допустима',loc='left',fontsize=14)
ax.text(185,392,'У оригинала есть и малые радиусы, и неидеальные стыки.\nИз них нельзя вывести универсальный запрет на выемку или угол.',fontsize=9,color='#736b62')

ax=fig.add_subplot(grid[2,0]);
for s in cap1:curve(ax,s,color='#db6842',lw=4)
for s in capd:ax.plot(*align(sample(s)).T,color='#147c75',lw=1.5,ls='--')
setup(ax,(130,179),(670,713));ax.set_title('Тонкий круглый cap',loc='left',fontsize=13)
ax.text(130,663,'Оранжевый: текущая д01\nПунктир: родная d, поворот/масштаб\nРазница ≈ %.2f ед.'%l1.hausdorff_distance(ld),fontsize=9,color='#736b62')
ax=fig.add_subplot(grid[2,1:]);
for i,n in enumerate(['a','d','t','c','f','g','r']):
 patch(ax,native(n),color='#77716a',transform=lambda v,i=i:v*.36+[i*185,0]);ax.text(i*185+65,-52,n,ha='center',fontsize=13)
setup(ax,(-10,1300),(-100,310));ax.set_title('Реестр окончаний шире одной капли: функция и подводка важнее названия',loc='left',fontsize=13)
fig.text(.04,.035,'Диагностика: симметричная неизменная o + новая спина ≠ доказательство родства. G1 ≠ оптическая доводка.\nЗелёный/оранжевый не означают «хорошо/плохо». Малые радиусы и круглые caps не запрещены: оценивать весь штрих и контраст.',fontsize=11,color='#736b62')
fig.savefig(OUT/'curves-terminals-forensic.svg',bbox_inches='tight');fig.savefig(OUT/'curves-terminals-forensic.png',dpi=160,bbox_inches='tight');plt.close(fig)
print(json.dumps({'similarity':metrics['two_variant_similarity'],'terminal':metrics['terminal_comparison'],'neck_joins':[r for r in metrics['current']['01']['joins'] if r['point']==[266.,495.]]},ensure_ascii=False,indent=2))
