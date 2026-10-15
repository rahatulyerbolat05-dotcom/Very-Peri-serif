from pathlib import Path
import hashlib,json,math,itertools
import numpy as np
from glyphsLib import GSFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'build/research-deep/native';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'reference/instrument-serif/sources/Instrument_Serif.glyphs'
assert hashlib.sha256(SRC.read_bytes()).hexdigest()=='e7dd989a8d17b7cdc13130b79597d44bdd4b9dd043c801639468ef38d58a706f'
F=GSFont(str(SRC))
PIN='65c0ef225f386a3c7e87570a4aa9cc0262c2fd81'
NAMES=['a','d','u','t','f','g','r','c','e','o']

def commands(layer):
 p=RecordingPen();layer.draw(p);return p.value

def segments(cmds):
 result=[];current=None;start=None;contour=-1
 for ci,(op,pts) in enumerate(cmds):
  if op=='moveTo':current=np.array(pts[0],float);start=current.copy();contour+=1
  elif op=='lineTo':
   end=np.array(pts[0],float);result.append({'command':ci,'contour':contour,'type':'line','points':np.array([current,end])});current=end
  elif op=='curveTo':
   ps=np.array([current,*pts],float);result.append({'command':ci,'contour':contour,'type':'cubic','points':ps});current=ps[-1]
  elif op=='closePath' and not np.allclose(current,start):
   result.append({'command':ci,'contour':contour,'type':'line','points':np.array([current,start])});current=start
 return result

def bez(p,t):
 t=np.asarray(t);p=np.asarray(p)
 if len(p)==2:return (1-t[...,None])*p[0]+t[...,None]*p[1]
 return (1-t[...,None])**3*p[0]+3*(1-t[...,None])**2*t[...,None]*p[1]+3*(1-t[...,None])*t[...,None]**2*p[2]+t[...,None]**3*p[3]

def deriv(p,t):
 if len(p)==2:return p[1]-p[0],np.array([0.,0.])
 q=np.diff(p,axis=0);d=3*((1-t)**2*q[0]+2*(1-t)*t*q[1]+t*t*q[2]);dd=6*((1-t)*(q[1]-q[0])+t*(q[2]-q[1]));return d,dd

def crv(p,t):
 d,dd=deriv(p,t);speed=np.linalg.norm(d);k=(d[0]*dd[1]-d[1]*dd[0])/speed**3 if speed>1e-12 else None
 return {'tangent_deg':math.degrees(math.atan2(d[1],d[0])),'signed_curvature_per_unit':k,'radius_units':abs(1/k) if k and abs(k)>1e-12 else None}

def joins(ss):
 rows=[]
 for contour in sorted(set(s['contour'] for s in ss)):
  cs=[s for s in ss if s['contour']==contour]
  for a,b in zip(cs,cs[1:]+cs[:1]):
   ai=crv(a['points'],1);bo=crv(b['points'],0);di=deriv(a['points'],1)[0];do=deriv(b['points'],0)[0]
   angle=math.degrees(math.acos(np.clip(np.dot(di,do)/(np.linalg.norm(di)*np.linalg.norm(do)),-1,1)))
   rows.append({'contour':contour,'at':a['points'][-1].tolist(),'incoming_command':a['command'],'outgoing_command':b['command'],'tangent_mismatch_deg':angle,'incoming':ai,'outgoing':bo,'curvature_ratio_abs':max(abs(ai['signed_curvature_per_unit']),abs(bo['signed_curvature_per_unit']))/min(abs(ai['signed_curvature_per_unit']),abs(bo['signed_curvature_per_unit'])) if ai['signed_curvature_per_unit'] and bo['signed_curvature_per_unit'] else None})
 return rows

def coeffs(p):
 if len(p)==2:return np.array([p[1]-p[0],p[0]])
 return np.array([-p[0]+3*p[1]-3*p[2]+p[3],3*p[0]-6*p[1]+3*p[2],-3*p[0]+3*p[1],p[0]])

def ray_width(ss,selected,t,side=1):
 a=next(s for s in ss if s['command']==selected);point=bez(a['points'],t);d=deriv(a['points'],t)[0];normal=side*np.array([-d[1],d[0]])/np.linalg.norm(d)
 hits=[]
 for b in ss:
  if b is a:continue
  c=coeffs(b['points']).copy();c[-1]-=point
  poly=c[:,0]*normal[1]-c[:,1]*normal[0];poly=np.trim_zeros(poly,'f')
  if len(poly)<=1:continue
  for rt in np.roots(poly):
   if abs(rt.imag)>1e-7 or not(-1e-8<=rt.real<=1+1e-8):continue
   tb=float(np.clip(rt.real,0,1));end=bez(b['points'],tb);dist=float(np.dot(end-point,normal))
   if dist>1e-5:hits.append((dist,b['command'],tb,end.tolist()))
 if not hits:return None
 dist,cmd,tb,end=min(hits)
 return {'at_command':selected,'t':t,'point':point.tolist(),'normal':normal.tolist(),'width_units':dist,'opposite_command':cmd,'opposite_t':tb,'opposite_point':end,'curve':crv(a['points'],t)}

def jsonsegment(s):return {**s,'points':s['points'].tolist()}

DATA={}
for name in NAMES:
 layer=F.glyphs[name].layers['m01'];cmds=commands(layer);ss=segments(cmds);bp=BoundsPen(None);layer.draw(bp)
 DATA[name]={'advance':layer.width,'bounds':bp.bounds,'commands':cmds,'segments':[jsonsegment(s) for s in ss],'joins':joins(ss)}

# Exact segment reuse under translation: signatures preserve all control vectors.
reuses=[]
for a,b in itertools.combinations(NAMES,2):
 for sa in segments(DATA[a]['commands']):
  if sa['type']!='cubic':continue
  for sb in segments(DATA[b]['commands']):
   if sb['type']!='cubic':continue
   pa,pb=sa['points'],sb['points']
   if np.array_equal(pa-pa[0],pb-pb[0]):
    reuses.append({'a':a,'a_command':sa['command'],'b':b,'b_command':sb['command'],'translation':(pb[0]-pa[0]).tolist(),'same_direction':True})

# Native o normal thickness, source polynomial ray intersections (no raster).
o=segments(DATA['o']['commands']);o_widths=[]
for cmd in [1,2,3,4]:
 for t in [0,.125,.25,.375,.5,.625,.75,.875,1]:o_widths.append(ray_width(o,cmd,t))
# Native a/d/t/c/e lower outer exits through their corresponding inner outlines.
exit_samples={}
for name,cmd in [('a',4),('d',4),('t',1),('c',1),('e',1)]:
 ss=segments(DATA[name]['commands']);exit_samples[name]=[ray_width(ss,cmd,t) for t in [.15,.3,.45,.6,.75,.9]]

# New de is compared numerically; no new outline is drawn/generated.
DE=json.loads((ROOT/'studies/reference-analysis/de-curves-deep/critique/rejected-outlines.json').read_text())['variants'];de_report={}
for key,row in DE.items():
 ss=segments(row['commands']);upper=[]
 for s in ss:
  if s['contour']==0 and s['points'].max(axis=0)[1]>=640:
   upper.append({'command':s['command'],'points':s['points'].tolist(),'samples':[{'t':t,**crv(s['points'],t)} for t in [0,.25,.5,.75,1]]})
 de_report[key]={'name':row['name'],'joins':joins(ss),'upper_segments':upper,'outer_spine_normal_width':[ray_width(ss,2,t) for t in [.1,.25,.5,.75,.9]],'upper_outer_normal_width':[ray_width(ss,3,t) for t in [.1,.25,.5,.75,.9]],'neck_normal_width':[ray_width(ss,11,t) for t in [.1,.25,.5,.75,.9]]}

# Native cap metrics: start and end are the points where tip rounding starts.
cap_defs=[('a','exit',5,6),('d','exit',5,6),('t','exit',2,3),('c','lower_exit',2,3),('c','upper_spur_cap',8,9),('e','lower_exit',2,3),('u','head',24,25),('d','ascender_flag_tip',13,14),('f','left_crossbar',25,26)]
caps=[]
for name,label,c1,c2 in cap_defs:
 ss=segments(DATA[name]['commands']);a=next(s for s in ss if s['command']==c1);b=next(s for s in ss if s['command']==c2);start=a['points'][0];end=b['points'][-1];mid=(start+end)/2;axis=(end-start)/np.linalg.norm(end-start);normal=np.array([-axis[1],axis[0]]);samples=np.vstack([bez(a['points'],np.linspace(0,1,10001)),bez(b['points'],np.linspace(0,1,10001))]);dep=(samples-mid)@normal
 caps.append({'glyph':name,'label':label,'commands':[c1,c2],'start':start.tolist(),'end':end.tolist(),'tip_join':a['points'][-1].tolist(),'chord_width_units':float(np.linalg.norm(end-start)),'chord_angle_deg':math.degrees(math.atan2(*(end-start)[::-1])),'maximum_cap_depth_from_chord_units':float(np.max(np.abs(dep))),'join':next(j for j in DATA[name]['joins'] if j['incoming_command']==c1),'sampled_tangent_rotation_deg':[crv(s['points'],t)['tangent_deg'] for s in [a,b] for t in [0,.5,1]]})

# Mathematical shape limits have exact source coefficients and explicit tolerances.
report={'source':{'repository':'https://github.com/Instrument/instrument-serif','commit':PIN,'file':'sources/Instrument_Serif.glyphs','master_id':'m01','master_name':str(F.masters['m01'].name),'sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'units_per_em':F.upm},'method':{'coordinates':'Exact cubic Glyphs master, not quadratics/raster. Segment indices are zero-based RecordingPen command indices, include moveTo/closePath.','curvature':'signed det(Bprime,Bdoubleprime)/norm(Bprime)^3; units inverse font-unit. Radius = abs(1/k), null for line/zero curvature.','normal_width':'At selected outer cubic t, intersect ray in the left tangent-normal direction with every other source segment by solving cubic line-crossing polynomials; nearest positive hit. Numeric root tolerance1e-7 imaginary/1e-8 parameter; near own join hits below1e-5 rejected.','t_parameter_warning':'t is Bezier parameter, not normalized arclength; samples establish behavior at listed stations, not extrema.','cap_depth':'Sample 10001t/segment, projection from chord midpoint normal to start-end cap chord; approximate maximum, source coordinates exact.','reuses':'Exact equality of all four cubic control vectors after translation; no optical near-match threshold.','limits':'No claim these sampled glyphs prove universal designer intent. Ray width is local stroke thickness at that contour station; complex intersections may hit another branch and are recorded for inspection.'},'native_glyphs':DATA,'exact_translated_cubic_reuses':reuses,'o_normal_width':o_widths,'exit_normal_width':exit_samples,'native_caps':caps,'rejected_de_comparison':de_report}
(OUT/'native-curve-facts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

# Native-only atlas. All outlines original, no manufactured de proof shown here.
def path_for(cmds):
 v=[];c=[]
 for op,pts in cmds:
  if op=='moveTo':v.append(pts[0]);c.append(MP.MOVETO)
  elif op=='lineTo':v.append(pts[0]);c.append(MP.LINETO)
  elif op=='curveTo':v.extend(pts);c.extend([MP.CURVE4]*3)
  elif op=='closePath':v.append((0,0));c.append(MP.CLOSEPOLY)
 return MP(v,c)

def plot(ax,name,limits=None,indices=(),annotate=True):
 row=DATA[name];ax.add_patch(PathPatch(path_for(row['commands']),fc='#25242a',ec='none'))
 for y in [0,510,740]:ax.axhline(y,color='#d3cec4',lw=.5,zorder=-1)
 for seg in segments(row['commands']):
  if seg['command'] not in indices:continue
  pts=seg['points'];sam=bez(pts,np.linspace(0,1,150));ax.plot(sam[:,0],sam[:,1],color='#d04d3b',lw=2)
  ax.plot(pts[:,0],pts[:,1],color='#da988b',lw=.6,marker='o',ms=2)
  if annotate:
   p=pts[-1];ax.annotate(f"{seg['command']}:({p[0]:g},{p[1]:g})",p,xytext=(5,6),textcoords='offset points',fontsize=6,color='#a72f23')
 ax.set_aspect('equal');ax.set_axis_off()
 if limits:ax.set_xlim(*limits[:2]);ax.set_ylim(*limits[2:])
 else:ax.set_xlim(-10,row['advance']+25);ax.set_ylim(min(-30,row['bounds'][1]-20),790)

fig=plt.figure(figsize=(16,16),facecolor='#f6f2e9');fig.suptitle('Instrument Serif Regular: native curves and terminal families',fontsize=19,x=.05,ha='left',y=.985)
fig.text(.05,.96,'Exact cubic master m01 / UPM 1000 / red = measured source segments; labels = command : endpoint',fontsize=10,color='#6b655c')
gs=fig.add_gridspec(3,5,left=.045,right=.98,top=.93,bottom=.07,hspace=.45,wspace=.36)
for i,name in enumerate(NAMES):
 ax=fig.add_subplot(gs[i//5,i%5]);inds={'a':[5,6,12,13,14],'d':[5,6,13,14],'u':[4,5,6,7,8,24,25],'t':[2,3],'f':[18,19,20,21],'g':[10,11,12,13,14],'r':[21,22,23,24],'c':[2,3,8,9],'e':[2,3],'o':[1,2,7,8]}.get(name,[])
 plot(ax,name,indices=inds,annotate=False);ax.set_title(f'{name} / advance {DATA[name]["advance"]:g}',fontsize=14,loc='left')
 ax.text(0,-.10,{'a':'Bulb and exit are distinct families','d':'Exact translated a exit cap','u':'Pointed lower flag; flat upper head','t':'Exit cap, wider shoulder turn','f':'Asymmetric bulb into thin crown','g':'Bulb ear and concave neck','r':'Bulb below crown, concave return','c':'Lower exit cap / upper tall spur','e':'25-unit crossbar; lower exit cap','o':'76 side / 25 crown, normal widths vary'}[name],transform=ax.transAxes,fontsize=8,color='#6b655c',wrap=True)
for col,(name,lim,inds,title) in enumerate([
 ('a',(345,410,95,160),[5,6],'a exit: 25-unit mouth'),
 ('d',(225,290,660,715),[13,14,15],'d head: 24-unit mouth'),
 ('u',(4,67,470,522),[24,25,26],'u head: 26.1-unit mouth'),
 ('c',(280,330,145,200),[2,3],'c lower: diagonal cap'),
 ('o',(10,398,-20,530),[1,2,7,8],'o: outer and inner handles')]):
 ax=fig.add_subplot(gs[2,col]);plot(ax,name,lim,inds,annotate=True);ax.set_title(title,fontsize=10,loc='left')
fig.text(.05,.025,f'Pinned Instrument/instrument-serif {PIN[:12]} | master SHA-256 {report["source"]["sha256"][:20]}…',fontsize=9,color='#6b655c')
for ext in ['svg','png']:fig.savefig(OUT/f'native-terminal-atlas.{ext}',dpi=180,facecolor=fig.get_facecolor())
plt.close(fig)

fig,axs=plt.subplots(2,4,figsize=(16,10),facecolor='#f6f2e9');fig.suptitle('Native detail: rounded caps coexist with asymmetric bulbs and pointed flags',fontsize=18)
for ax,(name,lim,inds,title) in zip(axs.flat,[
 ('a',(340,410,85,165),[4,5,6,7],'a exit cap'),('t',(198,260,95,165),[1,2,3,4],'t exit cap'),('c',(270,334,135,200),[1,2,3,4],'c lower cap'),('e',(285,345,125,185),[1,2,3,4],'e lower cap'),('f',(145,325,600,765),[18,19,20,21],'f bulb & crown'),('r',(165,330,390,530),[21,22,23,24],'r asymmetric bulb'),('g',(245,407,470,610),[9,10,11,12,13,14,15],'g bulb & narrow neck'),('u',(304,450,-16,120),[4,5,6,7,8,9,10],'u lower pointed flag')]):
 plot(ax,name,lim,inds,annotate=True);ax.set_title(title,loc='left',fontsize=12)
fig.tight_layout(rect=(0,.02,1,.95))
for ext in ['svg','png']:fig.savefig(OUT/f'native-detail-magnifications.{ext}',dpi=180,facecolor=fig.get_facecolor())
plt.close(fig)
print('Saved native curve facts and two SVG/PNG atlases')
print('source',report['source'])
print('exact reuse',len(reuses))
for row in caps:print('cap',row['glyph'],row['label'],'chord',round(row['chord_width_units'],3),'depth',round(row['maximum_cap_depth_from_chord_units'],3),'join radii',row['join']['incoming']['radius_units'],row['join']['outgoing']['radius_units'])
for key,row in de_report.items():
 print('de',key,'upperjoins')
 for j in row['joins']:
  if j['at'][1]>490: print(j['at'], 'G1',round(j['tangent_mismatch_deg'],6),'radii',j['incoming']['radius_units'],j['outgoing']['radius_units'],'ratio',j['curvature_ratio_abs'])
