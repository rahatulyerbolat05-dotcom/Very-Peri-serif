#!/usr/bin/env python3
"""Italic lowercase pilot: Cyrillic letters assembled from native Instrument Serif Italic parts.
Everything is cut and joined along the slant axis: ud = x - tan13 * y (the native stems are vertical in ud, so a cut
along ud keeps a stem whole). Parts are never scaled; they are moved whole (CLAUDE.md, lesson of Regular 1.015).
Letters built here (docs/italic-rules.md 6.3): ш щ ц н д (native n/u/q/j parts), г (native r), л (native arch + leg).
Writes build/italic-lower/VeryPeriSerifItalicT0-lower.ttf (the caps test font plus these letters).
"""
import json,math,sys
from pathlib import Path
import pathops
from pathops import PathOp
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
sys.path.insert(0,str(Path(__file__).resolve().parent))
from italic_tidy import tidy
from italic_round import round_glyph

S=math.tan(math.radians(13))
TAIL_KIND='pen'                                      # descender tail of ц щ ң қ: 'pen' (the exit turns into a downstroke below the line, as written), 'comma' (tail of the native comma under the stroke, which keeps its exit), 'n' (exit stroke of n at descender depth), 'ball', 'wedge', 'reg' (Regular drop), 'j' (native hook), 'q' (native flat foot)
ITA=Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Italic.ttf')
REG=Path('dist/VeryPeriSerif/VeryPeriSerif-Regular.ttf')
CAPS=Path('build/italic-caps/VeryPeriSerifItalicT0-caps.ttf')

# measured on the native u/n (tools/italic_rules_measure.py scans, de-slanted ud): stem edges
STEM_W=63.4                      # u second stem 274.1..337.5
U_L,U_R=274.1,337.5              # u right stem
N_L,N_R=52.0,116.2               # n first stem
U_PITCH=233.                     # u stem1 centre 72.5 -> stem2 centre 305.8


def polys_ud(font,name):
    from italic_rules_measure import polys
    return polys(font,name,S)


def outer_ud(P,y):
    from italic_rules_measure import runs
    r=runs(P,y);return r[0][0],r[-1][1]


def native(font,name):
    p=pathops.Path();gs=font.getGlyphSet();gs[name].draw(p.getPen(glyphSet=gs));return p


def transformed(path,dx=0.,dy=0.,shear=0.,about=0.):
    out=pathops.Path();pen=TransformPen(out.getPen(),(1,0,shear,1,dx-shear*about,dy));path.draw(pen);return out


def poly(points):
    p=pathops.Path();pen=p.getPen();pen.moveTo(points[0])
    for q in points[1:]:pen.lineTo(q)
    pen.closePath();return p


def disc(cx,cy,r,ry=None):
    """Ellipse (semi-axes r, ry) from four cubic arcs; a round terminal for a stroke end."""
    ry=r if ry is None else ry;k=0.5522847498
    p=pathops.Path();pen=p.getPen();pen.moveTo((cx+r,cy))
    pen.curveTo((cx+r,cy+k*ry),(cx+k*r,cy+ry),(cx,cy+ry));pen.curveTo((cx-k*r,cy+ry),(cx-r,cy+k*ry),(cx-r,cy))
    pen.curveTo((cx-r,cy-k*ry),(cx-k*r,cy-ry),(cx,cy-ry));pen.curveTo((cx+k*r,cy-ry),(cx+r,cy-k*ry),(cx+r,cy));pen.closePath();return p


def sweep(P,w0,w1):
    """Stroke of widening w0 -> w1 along the cubic centre line P (4 points): each edge is the cubic with its control points moved by the end normals."""
    def unit(a,b):
        dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);return dx/l,dy/l
    t0=unit(P[0],P[1]);t1=unit(P[2],P[3]);n0=(-t0[1],t0[0]);n1=(-t1[1],t1[0])
    def edge(sign):
        o=[(P[0][0]+sign*n0[0]*w0/2,P[0][1]+sign*n0[1]*w0/2),(P[1][0]+sign*n0[0]*(w0*.75+w1*.25)/2,P[1][1]+sign*n0[1]*(w0*.75+w1*.25)/2),
           (P[2][0]+sign*n1[0]*(w0*.25+w1*.75)/2,P[2][1]+sign*n1[1]*(w0*.25+w1*.75)/2),(P[3][0]+sign*n1[0]*w1/2,P[3][1]+sign*n1[1]*w1/2)];return o
    A=edge(1);B=edge(-1)
    p=pathops.Path();pen=p.getPen();pen.moveTo(A[0]);pen.curveTo(A[1],A[2],A[3]);pen.lineTo(B[3]);pen.curveTo(B[2],B[1],B[0]);pen.closePath();return p


def band(ud0,ud1,y0,y1):
    """Slanted rectangle: ud in [ud0,ud1], y in [y0,y1]."""
    return poly([(ud0+S*y0,y0),(ud1+S*y0,y0),(ud1+S*y1,y1),(ud0+S*y1,y1)])


def right_of(c):return band(c,c+4000,-1500,2000)
def left_of(c):return band(c-4000,c,-1500,2000)
def above(y):return band(-4000,4000,y,2000)
def below(y):return band(-4000,4000,-1500,y)


def AND(a,b):return pathops.op(a,b,PathOp.INTERSECTION,fix_winding=True)
def OR(*ps):
    r=ps[0]
    for q in ps[1:]:r=pathops.op(r,q,PathOp.UNION,fix_winding=True)
    return r
def SUB(a,b):return pathops.op(a,b,PathOp.DIFFERENCE,fix_winding=True)


def to_glyph(path,glyf):
    path=pathops.simplify(path,fix_winding=True)
    pen=TTGlyphPen(None);path.draw(Cu2QuPen(pen,0.5,reverse_direction=False));g=pen.glyph();g.recalcBounds(glyf);return g


def slices(path,y,eps=0.3):
    """(ud_min, ud_max) of each piece of the outline in a thin band at height y (pathops, nonzero fill), left to right."""
    from fontTools.pens.recordingPen import RecordingPen
    rec=RecordingPen();AND(path,poly([(-5000,y-eps),(5000,y-eps),(5000,y+eps),(-5000,y+eps)])).draw(rec);out=[];cur=[]
    for op,args in rec.value:
        if op=='moveTo':cur=[args[0]]
        elif op in ('lineTo','curveTo','qCurveTo'):cur+=list(args)
        elif cur:out.append((min(q[0] for q in cur)-S*y,max(q[0] for q in cur)-S*y));cur=[]
    return sorted(out)


def pen_tail(comma_ext,base,y_top=110.,y_v=16.,depth=-160.,top_width=None):
    """Descender tail as the pen writes it (Russian cursive, Marck Script, Caveat, Alegreya, Piazzolla): the last stroke keeps its exit up to the right,
    the pen turns at the exit and makes a downstroke parallel to the slant below the line, which ends turning left (the native comma tip).
    The downstroke leaves the outer edge of the exit tangentially at y_top (the turning point stays the exit tip), its left edge comes out of the foot
    at y_v (an open pocket remains between foot and tail), it swells below the baseline and its tip stops at `depth` (у goes to -215: ц stays shorter).
    top_width: start width when the exit is not a separate piece at y_top (capitals: the flag of the stem foot)."""
    def edge(y,side):return slices(base,y)[-1][side]
    rt=edge(y_top,1);sr=(edge(y_top-5,1)-edge(y_top+5,1))/10.
    if top_width is None:lt=edge(y_top,0);sl=(edge(y_top-5,0)-edge(y_top+5,0))/10.
    else:lt=rt-top_width;sl=sr                     # capitals: the flag at the foot of the stem is merged with the stem, the downstroke starts as a hairline at its tip
    return OR(base,comma_ext(lt,y_top,sl,rt,sr,edge(y_v,1),depth))


def make_comma_ext(ita):
    """Descender tail 'comma': the lower part of the native comma (below its waist) hung under the last stroke, which keeps its own exit.
    Returns comma_ext(l_top,y_top,sl,r_top,sr,l_j,depth): the tail of the native comma below y=-40, moved (no scaling) so that its waist
    sits at ud=l_j and its tip at `depth`, plus the bridge from the stroke above: left edge from (l_top,y_top) with slope sl (ud per unit
    downward) to the waist, vertical there; right edge from (r_top,y_top) with slope sr to the waist with the comma's own lean. Both edges
    are cubics in the de-slanted plane, so the joints are tangent-continuous. Used by the lowercase (here) and the capitals (italic_caps)."""
    from italic_rules_measure import runs
    name=ita.getBestCmap()[ord(',')];comma_g=native(ita,name)
    P=polys_ud(ita,name);CL,CR=runs(P,-40)[0]                        # waist of the comma: left edge stationary (57.4), width 41.9
    CM=(runs(P,-35)[0][1]-runs(P,-45)[0][1])/10.                       # its right edge leans in by 0.34 per unit downward
    bottom=ita['glyf'][name].yMin
    def comma_ext(l_top,y_top,sl,r_top,sr,l_j,depth=-200.):
        dy=depth-bottom;dx=l_j-CL+S*dy;yj=-40.+dy;r_j=l_j+(CR-CL);h=(y_top-yj)/3.
        X=lambda u,y:(u+S*y,y)
        p=pathops.Path();pen=p.getPen()
        pen.moveTo(X(l_top,y_top));pen.curveTo(X(l_top+sl*h,y_top-h),X(l_j,yj+h),X(l_j,yj))
        pen.lineTo(X(r_j,yj));pen.curveTo(X(r_j+CM*h,yj+h),X(r_top+sr*h,y_top-h),X(r_top,y_top));pen.closePath()
        return OR(p,transformed(AND(comma_g,below(-40.)),dx=dx,dy=dy))
    return comma_ext


def build(ita,reg):
    u=native(ita,'u');n=native(ita,'n');q=native(ita,'q');j=native(ita,'j');r=native(ita,'r')
    out={}
    # ---- stems cleaned from the bowl/arch joints so that they can be reused
    def u_stem2(left=U_L,right=U_R):
        return OR(band(left,right,100,485),AND(u,AND(right_of(262),below(192))),AND(u,AND(right_of(262),above(480))))
    def n_stem1():
        trap=poly([(50.4+S*55,55),(117.0+S*55,55),(116.1+S*340,340),(52.4+S*340,340)])
        return OR(trap,AND(n,AND(left_of(126),below(60))),AND(n,AND(left_of(126),above(300))))
    # ---- ш: u + u with a shared middle stem
    A=AND(u,left_of(338))                                       # u without its exit foot (the foot is covered by the next stem)
    shift=U_PITCH
    B=transformed(u,dx=shift)
    Bclip=AND(B,OR(below(150),right_of(400)))
    sha=OR(A,Bclip)
    out['ш']=(sha,508+int(shift))
    # ---- ц, щ: tail from the Regular ц (stalk + drop, sheared) under the last stem, in place of the exit foot
    rcm=reg.getBestCmap();rc=native(reg,rcm[ord('ц')])
    tail_reg=AND(rc,poly([(290,-400),(520,-400),(520,-8),(290,-8)]))
    # Regular stem left edge x=305 at y=-10; Italic stem left edge ud=U_L
    def tail_at(stem_left):
        t=transformed(tail_reg,shear=S,about=0.)        # slant about the baseline
        return transformed(t,dx=stem_left-305.0)
    def stem_to_tail(stem_left,stem_right):
        # straight stem down to y=20, narrowing into the stalk (46 wide) by y=-2
        return poly([(stem_left+S*60,60),(stem_right+S*60,60),(stem_right+S*60-(stem_right-stem_left-46)*0.0,60)])
    def foot_cut(base,l=262):return SUB(AND(base,left_of(l+76)),AND(right_of(l),below(58)))
    ts=U_L
    TAIL=TAIL_KIND
    def descender_tail(cx,y0,w0,flick=None):
        """'ball': the stem bends right at depth and ends in the round terminal of the family (as the ear of g and the tail of y); 'wedge': straight descender narrowing to a thin end.
        The stroke starts inside the stem along its slant, its width is the perpendicular one (horizontal width times cos 13), so the edges continue the stem edges."""
        xa=lambda y:cx+S*y;x0=xa(y0);wp=w0*math.cos(math.radians(13))
        if TAIL=='ball':
            P=[(x0,y0),(x0-S*(y0+60),-60),(xa(-200)+30,-218),(xa(-200)+88,-196)]
            return OR(sweep(P,wp,33.),disc(P[3][0],P[3][1]+1,18))
        P=[(x0,y0),(x0-S*(y0+50),-50),(xa(-120)+6,-120),(xa(-215)+34,-214)]
        return OR(sweep(P,wp,18.),disc(P[3][0],P[3][1]+8,9))
    comma_ext=make_comma_ext(ita)
    def n_foot(cx,depth=-200.):
        """The native exit stroke of n (stem foot curving into the thin flick) moved down by `depth`, no scaling: the same gesture as every stem end of the
        family, at descender depth. Returns (piece, half stem width, y of the stem cut after the move)."""
        from italic_rules_measure import runs
        a,b_=runs(polys_ud(ita,'n'),192)[-1]
        return transformed(AND(n,AND(right_of(250),below(192))),dx=cx-(a+b_)/2+S*depth,dy=depth),(b_-a)/2,192+depth
    def with_tail(base,l,lo):
        """base: glyph whose last stem has left edge ud=l+(U_L-262) and an exit foot on the right; swap the foot for the tail.
        The stem narrows on both sides, 8.5 each (right from y=260, left from y=170: the bowl is close above that), to y=-10 (edge lean 11.2 and 14.8 degrees, both native values)
        into the 46 wide stalk of the Regular tail."""
        left=l+(U_L-262);right=left+(U_R-U_L);k=8.5
        if TAIL=='pen':return pen_tail(comma_ext,base)
        if TAIL=='comma':
            return OR(base,comma_ext(left,100.,0.,right,0.,left))
        if TAIL in ('ball','wedge'):
            cx=(left+right)/2;wu=(U_R-U_L)/2;y0=110.     # the stroke starts inside the stem and keeps its slant: the cut at y=58 is covered
            flick=AND(base,AND(right_of(right-3),AND(below(95),above(24))))      # the native exit tip above the cut: the spur right of the stem
            return OR(SUB(AND(base,left_of(right+1)),AND(right_of(l),below(58))),descender_tail(cx,y0,2*wu,flick if TAIL=='comma' else None))
        if TAIL=='n':
            cx=(left+right)/2;wu=(U_R-U_L)/2;foot,wn,ytop=n_foot(cx)
            taper=poly([(cx-wu+S*150,150),(cx-wn+S*ytop,ytop),(cx+wn+S*ytop,ytop),(cx+wu+S*150,150)])
            return OR(SUB(AND(base,left_of(right+1)),AND(right_of(l),below(58))),taper,foot)
        if TAIL in ('j','q'):
            cx=(left+right)/2;ys=6. if TAIL=='j' else 58.;wj=66.9/2;wu=(U_R-U_L)/2
            taper=poly([(cx-wu+S*140,140),(cx-wj+S*ys,ys),(cx+wj+S*ys,ys),(cx+wu+S*140,140)])
            if TAIL=='j':piece=transformed(AND(j,below(ys)),dx=cx-85.2)          # native hook of j, curls left
            else:piece=transformed(AND(q,AND(right_of(200),below(ys))),dx=cx-270.5) # native descender of q with its flat serif
            return OR(SUB(AND(base,left_of(right+1)),AND(right_of(l),below(58))),taper,piece)
        wr=poly([(right+S*260,260),(right-k+S*-10,-10),(right-k+S*-10+300,-10),(right+S*260+300,260)])
        wl=poly([(left+S*170,170),(left+k+S*-10,-10),(left+k+S*-10-14-k,-10),(left+S*170-14,170)])
        cut=lambda g:SUB(SUB(g,wr),wl)
        stem=cut(band(left,right+4,-10,70))
        body=cut(SUB(AND(base,left_of(right+1)),AND(right_of(l),below(58))))
        return OR(body,stem,tail_at(left+k))
    out['ц']=(with_tail(u,262,0),508+8)
    shift2=shift
    out['щ']=(with_tail(sha,262+shift2,shift2),508+int(shift2)+8)
    # ---- н: first stem of n, last stem of u, crossbar
    gapL=N_R+146.0                                    # counter 0.80 of Regular (182) = 146
    d=gapL-U_L
    st2=transformed(u_stem2(),dx=d)
    bar=band(N_R-6,U_L+d+6,252,282)
    en=OR(n_stem1(),st2,bar)
    out['н']=(en,int(14+ (U_R+d)+ 87+ 4))
    # ---- д: bowl and stem of q down to the baseline, descender and hook of j
    dsh=237.0-51.6
    jd=transformed(j,dx=dsh)
    a_=native(ita,'a')
    de=OR(AND(AND(a_,above(125)),left_of(338)),AND(AND(q,above(0)),below(126)),AND(jd,below(6)))
    out['д']=(de,430)
    # ---- л: right half of n (arch from its thin side, stem, exit) + a straight thin leg along the Regular leg slope
    arch=OR(AND(n,right_of(262)),AND(n,AND(right_of(122),above(305))))
    LEG_W=41.0;LEG_SLOPE=0.2493                    # perpendicular 37 (thin diagonals 24-37), tan 14 degrees measured in ud; I007 had 28.2 and the lightest colour of the set
    c305=142.05                                    # centre of the native arch thin side at y=305 (n: 128.0..156.1)
    def leg_edge(y,off):return c305+LEG_SLOPE*(y-305)+off
    # the leg ends in a round terminal: a disc of the leg's perpendicular half-width, tangent to the baseline (overshoot LEG_DIP), the leg starts at its centre
    LEG_DIP=3.0;LEG_FULL=120.;LEG_JOIN=330.;LEG_TOP=30.;r_=LEG_W/2*math.cos(math.atan(LEG_SLOPE+S));cy_=r_-LEG_DIP
    cx_=leg_edge(cy_,0)+S*cy_                      # leg axis at the disc centre (ud axis + slant)
    def half(y):return LEG_W/2 if y<=LEG_FULL else LEG_W/2+(LEG_TOP/2-LEG_W/2)*min(1.,(y-LEG_FULL)/(LEG_JOIN-LEG_FULL))   # taper to the arch thin side (30 at y=330, native 28-31)
    ys=[cy_,LEG_FULL,LEG_JOIN+10]
    leg=poly([(leg_edge(y,-half(y))+S*y,y) for y in ys]+[(leg_edge(y,half(y))+S*y,y) for y in reversed(ys)])
    out['л']=(OR(arch,leg,disc(cx_,cy_,r_)),521)
    # ---- к ж ь ъ ы: stem with the entry hook of n (or a flat top), arms and bowl of native k and b
    k=native(ita,'k');b=native(ita,'b')
    hook=AND(transformed(n_stem1(),dx=-47.8),above(330))         # n stem (52.4..116.1) onto the k/b stem (4.6..69.4)
    cut_asc=AND(left_of(77),above(345))                          # ascender of k and b above the arm joint
    ka=OR(SUB(k,cut_asc),hook)
    out['к']=(ka,447)
    zh_stem=AND(SUB(k,cut_asc),below(510))                       # k without ascender, flat top at the x-height
    zh_stem=OR(SUB(zh_stem,AND(left_of(77),above(345))),AND(k,AND(left_of(77),AND(above(344),below(510)))))
    mirror_arms=transformed(AND(k,right_of(70)),dx=0.)
    mp=pathops.Path();k_arms=SUB(AND(AND(k,right_of(55)),below(520)),AND(left_of(72),above(500)));k_arms.draw(TransformPen(mp.getPen(),(-1,0,2*S,1,2*37.0,0)))
    out['ж']=(OR(zh_stem,mp),447)
    soft=OR(SUB(b,cut_asc),hook)
    out['\uf102']=(soft,431)                                    # ь variant A: native b bowl (reads as upsilon)
    hard_stem=AND(SUB(b,cut_asc),below(510))
    hard_stem=OR(hard_stem,AND(b,AND(left_of(77),AND(above(344),below(510)))))
    head=OR(band(-110,10,478,510),band(-110,-80,440,510))
    out['\uf103']=(OR(hard_stem,head),431)                      # ъ variant A
    gap=44.0                                                     # bowl to stem, 1.015: clearance 34-57
    bowl_right=337.6
    dy=(bowl_right+gap)-U_L
    out['\uf104']=(OR(soft,transformed(u_stem2(),dx=dy)),431)  # ы variant A
    # ---- ө ғ: o and r with the crossbar
    o=native(ita,'o')
    P=polys_ud(ita,'o');lo,hi=outer_ud(P,255)
    out['ө']=(OR(o,band(lo+1,hi-1,243,268)),414)
    out['ғ']=(OR(r,band(-10,116,236,266)),368)
    # ---- й: native u with the breve
    out['й']=(native(ita,'ubreve'),508)
    # ---- letters without a native analogue: Regular shape sheared about y=255 (the capital method)
    rcm=reg.getBestCmap();rgl=reg['glyf']
    def sheared(ch,kind=None,rects=()):
        gname=rcm[ord(ch)]
        if kind:g=round_glyph(rgl[gname],rgl,kind,rects,255,255)
        else:
            pen=TTGlyphPen(None);reg.getGlyphSet()[gname].draw(TransformPen(pen,(1,0,S,1,-S*255,0)));g=pen.glyph()
        path=pathops.Path();g.draw(path.getPen(glyphSet=None),rgl) if False else None
        gs=reg.getGlyphSet()
        pth=pathops.Path();pen2=TransformPen(pth.getPen(),(1,0,S,1,-S*255,0)) if not kind else pth.getPen()
        if kind:
            from fontTools.pens.ttGlyphPen import TTGlyphPen as _P
            g.draw(pth.getPen(),rgl) if hasattr(g,'draw') else None
        else:gs[gname].draw(pen2)
        return pth
    # ь ъ ы, default: Regular shape (bowl only 57 percent of the x-height, not the full b bowl), sheared; the head of the
    # stems is replaced by the entry hook of n; the right stem of ы is the clean u stem
    # the stem is the native n stem (entry hook, flat base, 65 wide), its right edge on the Regular stem edge (ud 87.1);
    # only the bowl (and the head of ъ) is taken from the sheared Regular letter
    n_stem=transformed(n_stem1(),dx=87.1-116.1)
    ь_=sheared('ь');out['ь']=(OR(n_stem,AND(AND(ь_,right_of(80)),below(430))),367+14)
    ъ_=sheared('ъ');ъ_stem=band(37.1,105.1,0,440)
    out['ъ']=(OR(AND(ъ_,above(430)),ъ_stem,AND(AND(ъ_,right_of(98)),below(430))),385)
    ы_=sheared('ы')
    bowl_r=366.5-58.9
    ыdx=(bowl_r+40.0)-U_L
    out['ы']=(OR(n_stem,AND(AND(AND(ы_,right_of(80)),left_of(330)),below(430)),transformed(u_stem2(),dx=ыdx)),552)
    out['\uf101']=(sheared('л'),425)                              # л, variant 2: plain shear of the Regular л (for comparison)
    # ---- ю ф: only native parts (n stem, o, p and b stems)
    p_=native(ita,'p')
    o_lo,o_hi=outer_ud(polys_ud(ita,'o'),255)
    gap_yu=57.0                                                  # stem to oval, as in the Regular 1.015
    dxo=116.1+gap_yu-o_lo
    out['ю']=(OR(n_stem1(),band(110,116.1+gap_yu+22,243,268),transformed(o,dx=dxo)),600)
    c_f=(o_lo+o_hi)/2
    def f_stem():                                  # 54 wide through the bowl, widening to the native b (66) and p (67) stems over 120 units: no step at the joints
        W=[(-60,33.5),(0,27.0),(440,27.0),(560,33.0)]
        return poly([(c_f-w+S*y,y) for y,w in W]+[(c_f+w+S*y,y) for y,w in reversed(W)])
    out['ф']=(OR(o,f_stem(),transformed(AND(b,above(560)),dx=c_f-37.9),transformed(AND(p_,below(-60)),dx=c_f-50.2)),560)
    # ---- в ч я: stem swap, bowls and legs from the sheared Regular
    v_fill=poly([(150,500),(165,511),(205,510),(222,509),(229,491),(195,468),(188,467),(160,440)])    # the Regular bowl starts right of the n arch: fills the notch between arch and bowl top
    out['в']=(OR(n_stem,AND(AND(sheared('в'),right_of(80)),below(530)),v_fill),435)
    ч_=sheared('ч')
    ч_stem=transformed(n_stem1(),dx=14.1-84.25)                 # left stem: n stem centred on the Regular stem (ud -19.9..48.1)
    ч_right=transformed(u_stem2(),dx=222.1-U_L)                   # right stem: clean u stem with its exit
    out['ч']=(OR(AND(ч_stem,above(300)),OR(AND(AND(ч_,left_of(130)),below(300)),AND(AND(ч_,right_of(130)),left_of(240))),ч_right),433)
    я_=sheared('я')
    я_right=transformed(u_stem2(),dx=191.1-U_L)
    yaleg=poly([(74.4+0.32*(0-100)-14+S*0,0),(74.4+0.32*(0-100)+14,0),(74.4+0.32*(105-100)+14+S*105,105),(74.4+0.32*(105-100)-14+S*105,105)])
    out['я']=(OR(AND(AND(я_,left_of(196)),above(100)),yaleg,я_right),428)
    # ---- м: Regular shape without serifs; the right stem is the clean u stem with its exit (roles as the capital М: thin left stem 30,
    # thick "\\" 69, thin "/" 30, thick right stem)
    м_=sheared('м')
    lstem=poly([(3.5+0.0344*(0-100),0),(3.5+0.0344*(0-100)+30.4,0),(3.5+0.0344*(510-100)+30.4+S*510,510),(3.5+0.0344*(510-100)+S*510,510)])
    м_body=SUB(AND(м_,left_of(306)),OR(AND(left_of(100),below(72)),AND(right_of(235),below(60)),AND(left_of(15),above(465)),AND(AND(right_of(225),above(468)),left_of(275.0))))
    vtip=poly([(163.0+S*50,50),(183.5+S*50,50),(173.5-S*9,-9)])   # the Regular V ends 35 units above the baseline: bring the tip down
    out['м']=(OR(м_body,lstem,vtip,transformed(u_stem2(),dx=303.5-U_L)),510)
    # ---- Kazakh letters: қ ң (tail of ц in place of the exit), ү ұ (u with a straight descender from p), ә (sheared Regular)
    Pk=polys_ud(ita,'k')
    from italic_rules_measure import runs as _runs
    leg_l,leg_r=_runs(Pk,62)[1]                                  # the k leg at y=62 (ud)
    st_right=leg_r;st_left=st_right-46.0
    l2,r2=leg_l2r2=_runs(Pk,95)[1]
    ycut=95 if TAIL in ('ball','wedge') else 62
    leg_cut=OR(AND(right_of(200),below(ycut)),AND(right_of(r2+1.5 if TAIL in ('ball','wedge') else 335),below(230)))
    bridge=poly([(leg_l+S*62,62),(leg_r+S*62,62),(st_right+S*-10,-10),(st_left+S*-10,-10)])
    if TAIL=='pen':
        out['қ']=(pen_tail(comma_ext,ka),470)
    elif TAIL=='comma':
        kl=_runs(Pk,40)[1][0];ksl=(_runs(Pk,38)[1][0]-_runs(Pk,42)[1][0])/4.   # leg left edge at y=40 and its lean (0.8 per unit downward): the bridge leaves it tangentially
        out['қ']=(OR(ka,comma_ext(kl,40.,ksl,340.,0.,298.)),470)   # waist under the foot of the leg: the knee stays as heavy as the stem (67 across)
    elif TAIL in ('ball','wedge'):
        cxk=(leg_l+leg_r)/2;wu=(U_R-U_L)/2
        # leg edges higher up (l2,r2): the taper follows them, no notch at the cut
        taper=poly([(l2+S*95,95),(r2+S*95,95),(cxk+wu+S*28,28),(cxk-wu+S*28,28)])   # ends below the start of the stroke: its slanted cap is covered
        out['қ']=(OR(SUB(ka,leg_cut),taper,descender_tail(cxk,40.,2*wu)),470)
    elif TAIL=='n':
        cxk=(leg_l+leg_r)/2;foot,wn,ytop=n_foot(cxk)
        taper=poly([(leg_l+S*62,62),(leg_r+S*62,62),(cxk+wn+S*ytop,ytop),(cxk-wn+S*ytop,ytop)])
        out['қ']=(OR(SUB(ka,leg_cut),taper,foot),470)
    else:out['қ']=(OR(SUB(ka,leg_cut),bridge,tail_at(st_left)),470)
    out['ң']=(with_tail(en,d+262,0),500)
    c_u=(U_L+U_R)/2
    u_body=SUB(AND(u,left_of(338)),AND(right_of(262),below(58)))
    descender=OR(band(c_u-32,c_u+32,-100,70),transformed(AND(p_,below(-100)),dx=c_u-50.2))
    out['ү']=(OR(u_body,descender),508)
    out['ұ']=(OR(u_body,descender,band(c_u-89,c_u+89,-78,-52)),508)
    out['ә']=(sheared('ә','closed'),int(round(reg['hmtx'][rcm[ord('ә')]][0]*1.002)))
    for ch,kind in (('з','open'),('э','open'),('б','closed')):
        out[ch]=(sheared(ch,kind,((-999,999,430,800),) if ch=='б' else ()),int(round(reg['hmtx'][rcm[ord(ch)]][0]*1.002)))
    # ---- г: native r (stem with entry, arm)
    out['г']=(r,368)
    return out


# side bearings of the native family each letter belongs to (docs/italic-rules.md 5): left, right
BEARINGS={'қ':(6,15),'ң':(19,15),'ү':(21,20),'ұ':(21,20),'ә':(None,None),'к':(6,22),'ж':(19,22),'ь':(14,22),'ъ':(14,22),'ы':(14,22),'ө':(20,21),'ғ':(19,-36),'й':(21,20),'в':(20,22),'м':(20,22),'з':(None,None),'э':(None,None),'ч':(20,22),'я':(20,22),'ю':(19,21),'ф':(20,22),'б':(None,None),'ш':(21,20),'ц':(21,15),'щ':(21,15),'н':(19,22),'д':(13,10),'л':(20,22),'г':(19,-36),'\uf101':(20,22),'\uf102':(13,22),'\uf103':(13,22),'\uf104':(13,22)}


SPACING=json.loads(Path('data/italic-spacing.json').read_text())['glyphs'] if Path('data/italic-spacing.json').exists() else {}


def main():
    ita=TTFont(ITA);reg=TTFont(REG);font=TTFont(CAPS)
    built=build(ita,reg);rep=[]
    for ch,(path,adv) in built.items():
        glyf=font['glyf'];g=to_glyph(path,glyf)
        g,st=tidy(g,glyf)
        lsb,rsb=BEARINGS[ch];g.recalcBounds(glyf)
        if lsb is not None:g.coordinates.translate((lsb-g.xMin,0));g.recalcBounds(glyf);adv=int(round(g.xMax+rsb))
        sp=SPACING.get(ch)
        if sp:g.coordinates.translate((sp['dx'],0));g.recalcBounds(glyf);adv+=sp['dadv']
        name=f'uni{ord(ch):04X}';glyf[name]=g
        font['hmtx'][name]=(adv,getattr(g,'xMin',0))
        for t in font['cmap'].tables:
            if t.isUnicode():t.cmap[ord(ch)]=name
        rep.append(dict(character=ch,advance=adv,nodes=len(g.coordinates)))
    font.setGlyphOrder(font['glyf'].glyphOrder)
    out=Path('build/italic-lower');out.mkdir(parents=True,exist_ok=True)
    ver=json.loads(Path('data/italic-version.json').read_text())['version'];tag='I'+ver.replace('.','').zfill(3)
    family=f'Very Peri Serif Italic {tag}';ps=f'VeryPeriSerifItalic{tag}-Italic'
    for r in font['name'].names:
        if r.nameID==1:r.string=family
        elif r.nameID==3:r.string=f'{ver};italic test;'+ps
        elif r.nameID==4:r.string=family+' Italic'
        elif r.nameID==6:r.string=ps
    target=out/f'VeryPeriSerifItalic{tag}.ttf';font.save(target)
    print(target,rep)


if __name__=='__main__':main()
