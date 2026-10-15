# Extend the scratch report; no project files or outlines edited.
# Importing this file rebuilds deterministic source facts/atlases.
from native_curves import *

def inflections(p):
 # det of quadratic Bprime and linear Bdoubleprime, polynomial roots.
 c=coeffs(p);d=np.array([3*c[0],2*c[1],c[2]]);dd=np.array([6*c[0],2*c[1]])
 pol=np.polysub(np.polymul(d[:,0],dd[:,1]),np.polymul(d[:,1],dd[:,0]));pol=np.trim_zeros(pol,'f')
 if len(pol)<=1:return []
 return [float(t.real) for t in np.roots(pol) if abs(t.imag)<1e-7 and 0<t.real<1]

for name in NAMES:
 row=report['native_glyphs'][name];ss=segments(row['commands'])
 row['curvature_samples']=[{'command':s['command'],'samples':[{'t':float(t),**crv(s['points'],float(t))} for t in [0,.125,.25,.375,.5,.625,.75,.875,1]],'inflection_t':inflections(s['points']) if s['type']=='cubic' else []} for s in ss]

for key,row in DE.items():
 ss=segments(row['commands']);a=next(s for s in ss if s['command']==5);b=next(s for s in ss if s['command']==6);start=a['points'][0];end=b['points'][-1];mid=(start+end)/2;axis=(end-start)/np.linalg.norm(end-start);normal=np.array([-axis[1],axis[0]]);samples=np.vstack([bez(a['points'],np.linspace(0,1,10001)),bez(b['points'],np.linspace(0,1,10001))]);dep=(samples-mid)@normal
 report['rejected_de_comparison'][key]['upper_cap']={'commands':[5,6],'start':start.tolist(),'end':end.tolist(),'tip_join':a['points'][-1].tolist(),'chord_width_units':float(np.linalg.norm(end-start)),'maximum_cap_depth_from_chord_units':float(np.max(np.abs(dep))),'chord_angle_deg':math.degrees(math.atan2(*(end-start)[::-1])),'note':'Depth sampling matches native_caps. This comparison describes cap geometry, not a claim that all native caps share one shape.'}

report['native_bulb_normal_width']={}
for name,cmd in [('f',21),('r',24),('g',13),('a',11)]:
 ss=segments(DATA[name]['commands']);report['native_bulb_normal_width'][name]=[ray_width(ss,cmd,t) for t in [0,.125,.25,.375,.5,.625,.75,.875,1]]

# Verify original o nearly mirror-symmetric with differences explicit rather than assigning a mechanical ellipse.
report['o_exact_features']={
 'outer_bounds':[23,-9,383,516], 'inner_bounds':[99,16,307,491],
 'center_x':203,'side_extremum_y':254,'outer_vertical_center_from_bounds':253.5,
 'outer_crown_thickness_vertical':25,'outer_bottom_thickness_vertical':25,'horizontal_side_thickness':76,
 'outer_top_handle_x_length':101,'outer_bottom_handle_x_length':102,
 'outer_top_side_vertical_handle_length':147,'outer_bottom_side_vertical_handle_length':149,
 'inner_top_handle_x_length':70,'inner_bottom_handle_x_length':71,
 'inner_top_side_vertical_handle_length':157,'inner_bottom_side_vertical_handle_length':159,
 'interpretation':'Native o is left/right symmetric, but top/bottom handles differ by1-2units. Its counter and outside are separate cubic shapes, not offsets or scaled copies.'}
(OUT/'native-curve-facts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Extra curvature / inflection / bulb reports saved.')
for key,row in report['rejected_de_comparison'].items():print('de cap',key,row['upper_cap'])
for name,cmd in [('f',19),('r',22),('g',11)]:
 s=next(s for s in segments(DATA[name]['commands']) if s['command']==cmd)
 print('bulb inflection',name,cmd,inflections(s['points']))
print('o key radii')
for point in [[383,254],[203,516],[307,254],[203,491]]:
 for j in DATA['o']['joins']:
  if j['at']==point:print(point,j['incoming']['radius_units'],j['outgoing']['radius_units'])
