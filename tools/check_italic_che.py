#!/usr/bin/env python3
"""Author screenshot regression: che's short transverse donor seam must disappear."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import pathops
from fontTools.ttLib import TTFont
from contour_geometry import read_outline, inspect_outline, angle
from fix_italic_che import NAME, START, CONTROL, END, old_font
from polish_outlines import contours_of, hausdorff
from check_curve_finish import introduced_corners
from check_tail_joins import path_in, reduced_quadratics
from ttf2otf import exact_cubic_error
from revision_scope import later_outline_changes


def rotated(font):
    c = contours_of(font['glyf'][NAME],font['glyf'])[0]
    i = c.index([*START,True]); return c[i:]+c[:i]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('build/release'))
    ap.add_argument('--formats',default='ttf,otf,woff2');args=ap.parse_args()
    version=json.loads(Path('data/params.json').read_text())['regular_release']['version']
    report={'release':version,'baseline_version':'1.111','fonts':{}};count=0
    def ck(ok,label):
        nonlocal count
        assert ok,label
        count+=1
    for style in ('Regular','Italic'):
        before=old_font(style);ttf=TTFont(path_in(args.root,style,'ttf'))
        ck(before.getGlyphOrder()==ttf.getGlyphOrder(),(style,'glyph order'))
        changed=[n for n in ttf.getGlyphOrder() if before['glyf'][n].compile(before['glyf'])!=ttf['glyf'][n].compile(ttf['glyf'])]
        expected=({NAME} if style=='Italic' else set())|later_outline_changes('1.112',style)
        ck(set(changed)==expected,(style,'che and declared later representation changes',changed))
        ck(before['hmtx'].metrics==ttf['hmtx'].metrics,(style,'all advances and bearings retained'))
        for tag in ('cmap','GSUB','GPOS','GDEF'):
            ck(before.getTableData(tag)==ttf.getTableData(tag),(style,'unchanged shaping',tag))
        if style=='Italic':
            a,b=before['glyf'][NAME],ttf['glyf'][NAME]
            ck((a.xMin,a.yMin,a.xMax,a.yMax)==(b.xMin,b.yMin,b.xMax,b.yMax),'Che bounds')
            x,y=rotated(before),rotated(ttf);i=x.index([*END,True]);j=y.index([*END,True])
            ck(y[1:j]==[[*CONTROL,False]],'The entire transition is one quadratic')
            ck(x[i:]==y[j:],'All other stored points and flags retained')
            ck(len(x)-len(y)==4,'Four construction nodes removed')
            ck(not introduced_corners(before,ttf,NAME),'No new hard corner')
            ck(hausdorff(a,b,before['glyf'])<6,'Local displacement stays below six units')
            previous,_=inspect_outline(*read_outline(before,NAME))
            ck(any(r['kind']=='transverse_step' and 145<r['xy'][0]<170 and 290<r['xy'][1]<310 for r in previous),'Detector catches the author-reported old tooth')
        for fmt in args.formats.split(','):
            p=path_in(args.root,style,fmt);f=TTFont(p);row={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            if fmt=='otf':
                ref=old_font(style,'otf');old=ref['CFF '].cff.topDictIndex[0].CharStrings;new=f['CFF '].cff.topDictIndex[0].CharStrings
                changes=[]
                for n in f.getGlyphOrder():
                    old[n].decompile();new[n].decompile()
                    if old[n].program!=new[n].program:changes.append(n)
                ck(changes==([NAME] if style=='Italic' else []),(style,'only declared CFF glyph changes',changes))
                row['changed_charstrings']=changes
            if style=='Italic':
                c,closed=read_outline(f,NAME);diag,_=inspect_outline(c,closed)
                region=lambda r:130<=r['xy'][0]<=215 and 260<=r['xy'][1]<=345
                ck(not any(region(r) and r['kind'] in ('transverse_step','tangent_break','curvature_wave','short_segment') for r in diag),(fmt,'No tooth, kink, wave or micro-step in repaired region'))
                ck(not any(r['kind'] in ('self_intersection','zero_segment','disconnected') for r in diag),(fmt,'No new topology defect'))
                q=reduced_quadratics(c[0]) if fmt=='otf' else c[0]
                i=next(i for i,s in enumerate(q) if np.linalg.norm(s.points[0]-START)<.001)
                ck(np.allclose(q[i].points,[START,CONTROL,END],atol=.001,rtol=0),(fmt,'Exact final arc'))
                ck(all(q[i].curvature(t)<0 for t in np.linspace(0,1,33)),(fmt,'One convex arc, no inflection'))
                start_angle=angle(q[i-1].tangent(True),q[i].tangent(False));end_angle=angle(q[i].tangent(True),q[(i+1)%len(q)].tangent(False))
                ck(start_angle<.001 and end_angle<.5,(fmt,'Tangent continuity',start_angle,end_angle))
                start_curvature_jump=abs(float(q[i].curvature(0)/q[i-1].curvature(1)-1))
                ck(start_curvature_jump<.1,(fmt,'Bowl curvature transition',start_curvature_jump))
                error=exact_cubic_error(ttf,f,NAME) if fmt=='otf' else 0
                ck(error<.002,(fmt,'Exact serialized CFF',error))
                def area(font):
                    a=pathops.Path();font.getGlyphSet()[NAME].draw(a.getPen());return abs(a.area)
                drift=abs(area(f)-area(before))/area(before)
                ck(drift<.002,(fmt,'Ink area retained',drift))
                row.update(start_angle_degrees=start_angle,end_angle_degrees=end_angle,
                           start_curvature_relative_jump=start_curvature_jump,
                           end_curve_to_line_curvature_jump=abs(float(q[i].curvature(1))),
                           relative_ink_area_change=drift,exact_cubic_control_error=error)
            report['fonts'][style+'/'+fmt]=row
    report.update(passed=count,failed=0)
    dest=Path(f'docs/qa/che-{version}.json');dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':count,'failed':0,'report':str(dest)}))


if __name__=='__main__':main()
