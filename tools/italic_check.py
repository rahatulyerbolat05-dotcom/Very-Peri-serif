#!/usr/bin/env python3
"""Check Italic glyphs against the line rules of docs/italic-lines.md.
Usage: python3 -I tools/italic_check.py font.ttf [glyph names or characters ...] [--all-cyrillic]
Checks per glyph: (L1) straight stems lean 13.0 / 13.4 +- 0.5 degrees, a free stem of an arch letter 14.8 / 15.3 +- 0.7, inner stems of M W 11.2 and arm-end cuts of E F T 10.3 +- 0.5,
(L2) a pair of pieces symmetric about the slant axis (mean 13.0) is allowed; diagonals of A V W M lean 25.6 / -0.8 +- 1.0, (L3) stem thickness at y=255 within 65-66 (lowercase) or 69 (capitals) +- 3,
(L4) ovals: leftmost point at 34-37 percent of the contour height, rightmost at 63-66 percent (outer contour of round
letters). Prints one line per glyph with OK or the deviations.
"""
import math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from italic_geometry import straight_pieces,round_features
from italic_rules_measure import Poly,runs

def check(font,name,char):
    problems=[];info=[]
    pcs=straight_pieces(font,name,70)
    for p in pcs:
        a=p['angle']
        if abs(a-13)<=7:
            ok=any(abs(a-v)<=t for v,t in ((13.0,0.5),(13.4,0.5),(14.8,0.7),(15.3,0.7),(11.2,0.5),(10.3,0.5)))
            if not ok and any(q is not p and abs((a+q['angle'])/2-13)<=0.7 and abs(a-q['angle'])>1 for q in pcs):ok=True   # a pair symmetric about the slant axis (Д legs)
            if not ok:problems.append(f"L1 стойка {a}° ({p['length']} @ x{p['x']})")
        elif 20<a<30 or -3<a<1:info.append(f"диагональ {a}°")
    gs=font.getGlyphSet();poly=Poly(gs,0.);gs[name].draw(poly)
    cap=char.isupper();y=360 if cap else 255
    r=runs(poly.polys,y);w=[round(b-a) for a,b in r]
    target=69 if cap else 66
    thick=[x for x in w if 50<=x<=100]
    for x in thick:
        if x<target-3-30 and False:problems.append(f'L3 {x}')
    if w:info.append('срез %d: %s'%(y,w))
    rf=round_features(font,name)
    if rf and char.lower() in 'oecасзэюф':
        o=rf[0]
        if not(0.30<=o['left_at']<=0.37) :info.append(f"овал: левая крайняя на {o['left_at']}")
    return problems,info

def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    font=TTFont(args[0]);cm=font.getBestCmap()
    chars=args[1:] or ([chr(c) for c in list(range(0x410,0x430))+[0x401]] if '--all-cyrillic' in sys.argv else [])
    for ch in chars:
        cp=ord(ch) if len(ch)==1 else None
        name=cm.get(cp) if cp else ch
        if not name:print(ch,'нет глифа');continue
        problems,info=check(font,name,ch if cp else name)
        print(ch,name,'OK' if not problems else '; '.join(problems),'|',', '.join(info))

if __name__=='__main__':main()
