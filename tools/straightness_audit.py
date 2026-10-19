#!/usr/bin/env python3
"""Lines that should be straight and are not (author: "vectors where the lines are unfinished and crooked").
  a chain of consecutive segments (lines and curves) that turns less than TURN (6) degrees in all over 80+ units is a stroke edge meant
  straight; its largest distance from the chord (0.4+ reported) is a belly, a dent or a broken line
Calibrated on the native Latin of the same font (printed for comparison). Usage: python3 -I tools/straightness_audit.py font.ttf [--json out]
"""
import json,math,sys
from fontTools.ttLib import TTFont
sys.path.insert(0,__import__('os').path.dirname(__file__))
from polish_audit import contours,segments
TURN=6.
LATIN='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
CYR='абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһіАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӘҒҚҢӨҰҮҺІ'


def flat(seg,n=16):
    if seg[0]=='L':return [seg[1],seg[2]]
    p0,c,p1=seg[1],seg[2],seg[3];return [((1-t)**2*p0[0]+2*t*(1-t)*c[0]+t*t*p1[0],(1-t)**2*p0[1]+2*t*(1-t)*c[1]+t*t*p1[1]) for t in [i/n for i in range(n+1)]]


def direction(seg,end):
    a,b=(seg[-2],seg[-1]) if end else (seg[1],seg[2])
    if seg[0]=='L':a,b=seg[1],seg[2]
    return math.atan2(b[1]-a[1],b[0]-a[0])


def check(font,name):
    """Chains of consecutive segments (lines and curves) that turn less than TURN degrees in all and run 80+ units: a stroke edge meant
    straight. sag = their largest distance from the chord, if 0.4 units or more (a belly or a broken line)."""
    out=[]
    for C in contours(font,name):
        segs=segments(C);n=len(segs)
        if n<2:continue
        pts=[flat(s) for s in segs]
        def turn(i):                                     # total direction change inside segment i
            P=pts[i];a=math.atan2(P[1][1]-P[0][1],P[1][0]-P[0][0]);b=math.atan2(P[-1][1]-P[-2][1],P[-1][0]-P[-2][0])
            return abs(math.degrees((b-a+math.pi)%(2*math.pi)-math.pi))
        def joint(i):                                    # break between segment i and i+1
            P=pts[i];Q=pts[(i+1)%n];a=math.atan2(P[-1][1]-P[-2][1],P[-1][0]-P[-2][0]);b=math.atan2(Q[1][1]-Q[0][1],Q[1][0]-Q[0][0])
            return abs(math.degrees((b-a+math.pi)%(2*math.pi)-math.pi))
        used=set()
        for i in range(n):
            if i in used or turn(i)>TURN:continue
            # grow a chain forward while the total turn stays small
            chain=[i];tot=turn(i);j=i
            while len(chain)<n:
                k=(j+1)%n;t=tot+joint(j)+turn(k)
                if t>TURN or k in chain:break
                chain.append(k);tot=t;j=k
            P=[p for c in chain for p in pts[c]];L=math.dist(P[0],P[-1])
            if L<80 or len(chain)<1:continue
            dx,dy=P[-1][0]-P[0][0],P[-1][1]-P[0][1];d=max(abs((q[0]-P[0][0])*dy-(q[1]-P[0][1])*dx)/L for q in P)
            if d>=0.4:out.append((round(d,2),round(L),len(chain),tuple(map(round,P[0])),tuple(map(round,P[-1]))));used.update(chain)
    return out,[]


def run(font,chars,skip=()):
    cm=font.getBestCmap();out={}
    for ch in chars:
        n=cm.get(ord(ch))
        if not n or n in skip or font['glyf'][n].numberOfContours<=0:continue
        s,b=check(font,n)
        if s or b:out[ch]=dict(glyph=n,sag=s,bend=b)
    return out


def main():
    f=TTFont(sys.argv[1]);cm=f.getBestCmap();lat={cm.get(ord(c)) for c in LATIN}
    L=run(f,LATIN);C=run(f,CYR,skip=lat)
    ns=lambda R,k:sum(len(v[k]) for v in R.values())
    print(f'native Latin: sag {ns(L,"sag")} bend {ns(L,"bend")} in {len(L)} letters; own Cyrillic: sag {ns(C,"sag")} bend {ns(C,"bend")} in {len(C)} letters')
    for ch,v in sorted(L.items()):print(' L',ch,'sag',v['sag'][:3],'bend',v['bend'][:3])
    for ch,v in sorted(C.items(),key=lambda kv:-(len(kv[1]['sag'])+len(kv[1]['bend']))):print(' C',ch,v['glyph'],'sag',v['sag'][:4],'bend',v['bend'][:4])
    if '--json' in sys.argv:json.dump(dict(latin=L,cyrillic=C),open(sys.argv[sys.argv.index('--json')+1],'w'),ensure_ascii=False,indent=1)


if __name__=='__main__':main()
