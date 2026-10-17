#!/usr/bin/env python3
"""Lines and slants inside the glyphs of the native Instrument Serif Italic (docs/italic-lines.md).
Measured, per glyph: angles of every straight piece 70+ units long (from the vertical, positive = leaning right
going up), extremes of round contours (heights of the leftmost / rightmost points as a share of the contour height, tilt
of the top-bottom axis), thickness of horizontal hairlines. Writes data/italic-geometry.json.
Needs the reference fonts (tools/fetch_reference.sh).
"""
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from italic_rules_measure import REF,Poly

LATIN='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


def straight_pieces(font,name,min_len=70):
    g=font['glyf'][name]
    if g.numberOfContours<=0:return []
    c,e,fl=g.getCoordinates(font['glyf']);out=[];s=0
    for en in e:
        P=[(c[i][0],c[i][1],bool(fl[i]&1)) for i in range(s,en+1)];s=en+1;n=len(P)
        for i in range(n):
            a,b=P[i],P[(i+1)%n]
            if a[2] and b[2]:
                dx,dy=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dy)
                if L>=min_len:
                    if dy<0:dx,dy=-dx,-dy
                    out.append(dict(x=round((a[0]+b[0])/2),y=round((a[1]+b[1])/2),length=round(L),angle=round(math.degrees(math.atan2(dx,dy)),1)))
    return sorted(out,key=lambda r:r['x'])


def round_features(font,name):
    gs=font.getGlyphSet();p=Poly(gs,0.);gs[name].draw(p);out=[]
    for poly in p.polys:
        xs=[q[0] for q in poly];ys=[q[1] for q in poly];x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
        top=max(poly,key=lambda q:q[1]);bot=min(poly,key=lambda q:q[1]);lef=min(poly,key=lambda q:q[0]);rig=max(poly,key=lambda q:q[0])
        h=y1-y0;w=x1-x0
        out.append(dict(w=round(w),h=round(h),axis_tilt=round(math.degrees(math.atan2(top[0]-bot[0],h)),1),left_at=round((lef[1]-y0)/h,3),right_at=round((rig[1]-y0)/h,3),top_x=round((top[0]-x0)/w,3),bottom_x=round((bot[0]-x0)/w,3)))
    return out


def main():
    it=TTFont(REF/'InstrumentSerif-Italic.ttf');cm=it.getBestCmap()
    data={'straight':{ch:straight_pieces(it,cm[ord(ch)]) for ch in LATIN},'round':{ch:round_features(it,cm[ord(ch)]) for ch in 'oOcCeadbpqgG'}}
    Path('data/italic-geometry.json').write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n');print('written')

if __name__=='__main__':main()
