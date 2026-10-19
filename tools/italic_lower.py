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
from italic_fair import fair
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


def pen_tail(comma_ext,base,y_top=72.,y_v=-5.,depth=-150.,top_width=None):
    """Descender tail as the pen writes it. Russian cursive (propisi): the last element of ц is a line with a rounding to the right that ends
    just above the bottom line, then a short stick goes down and rounds to the left (the 'claw'); the same in Marck Script, Caveat, Alegreya,
    Piazzolla. So: the native exit is cut low (y_top, it ends just above the baseline instead of rising to 145), the pen turns there over a round
    cap and makes a short downstroke parallel to the slant, its left edge leaves the foot at its bottom (y_v; a higher point leaves a crack), it swells below the
    line and ends in the native comma tip turned left at `depth` (у goes to -215: ц stays shorter).
    top_width: capitals, whose exit is the flag of the stem foot merged with the stem: the downstroke starts as a hairline at the flag tip."""
    def edge(y,side):return slices(base,y)[-1][side]
    if top_width is not None:
        rt=edge(y_top,1);sr=(edge(y_top-5,1)-edge(y_top+5,1))/10.;lt=rt-top_width
        return OR(base,comma_ext(lt,y_top,sr,rt,sr,edge(y_v,1),depth))
    fl,fr=slices(base,y_top)[-1]                    # the exit just above the bay between stem and exit
    body=SUB(base,AND(AND(right_of(fl-12.),above(y_top)),below(y_top+180.)))  # the rest of the exit (up to its tip near 145, 175 for k, whose tip turns left) goes
    cap=disc((fl+fr)/2+S*y_top,y_top,(fr-fl)/2)    # round turn of the pen over the whole end of the shortened exit (32 wide at y=72, as thin as the native tip)
    return OR(body,cap,comma_ext(fl,y_top,0.,fr,0.,edge(y_v,1),depth))


def stem_tail(base,y_top,sl=0.,sr=0.,depth=-150.,tip_r=12.,tip_off=-40.,tip_dir=(-1.0,-1.0),hand=(0.62,0.18,0.34,0.50)):
    """Capitals: the stem (or the leg of Қ) goes on below the line in one stroke and turns left into a round tip, as the pen does it.
    The Regular drop, its neck and the flag at the foot are removed below y_top (they made the joint crooked: a bent left edge and a knob on
    the right); the stroke is redrawn from its clean section at y_top (edges with slopes sl, sr in ud per unit downward). In the de-slanted
    plane: left edge stays straight long, then bends into the tip; right edge comes down, narrows and bends the same way; tip radius tip_r,
    its centre tip_off from the stroke's left edge (left of it: the bend needs room, a tip under the stem pulls the left edge inwards), lowest
    point at `depth`; hand: handle lengths (left top, left at the tip, right at the tip, right top) as fractions of the height."""
    l,r=slices(base,y_top)[-1]
    body=SUB(SUB(base,AND(right_of(l+1.),below(y_top))),below(-0.5))      # also every remnant of the drop below the line
    def unit(a,b):d=math.hypot(a,b);return a/d,b/d
    dt=unit(*tip_dir);no=(-dt[1],dt[0])
    if no[0]<0:no=(-no[0],-no[1])
    span=y_top-depth;lb=l+sl*span*0.6                                      # the left edge where it reaches the tip region
    C=(lb+tip_off,depth+tip_r);O=(C[0]+tip_r*no[0],C[1]+tip_r*no[1]);I=(C[0]-tip_r*no[0],C[1]-tip_r*no[1])
    bot=(C[0]+tip_r*dt[0],C[1]+tip_r*dt[1]);k=0.5523
    X=lambda q:(q[0]+S*q[1],q[1]);add=lambda a,b,t:(a[0]+b[0]*t,a[1]+b[1]*t)
    pth=pathops.Path();pen=pth.getPen()
    pen.moveTo(X((l,y_top)))
    h1,h2,h3,h4=hand
    pen.curveTo(X((l+sl*span*h1,y_top-span*h1)),X(add(I,dt,-span*h2)),X(I))               # left edge
    pen.curveTo(X(add(I,dt,tip_r*k)),X(add(bot,no,-tip_r*k)),X(bot))                      # round tip
    pen.curveTo(X(add(bot,no,tip_r*k)),X(add(O,dt,tip_r*k)),X(O))
    pen.curveTo(X(add(O,dt,-span*h3)),X((r+sr*span*h4,y_top-span*h4)),X((r,y_top)))      # right edge
    pen.closePath()
    return OR(body,pth)


def smooth_tail(base,y_c=60.,depth=-150.,tip_r=12.,reach=46.,lean=0.30,tip_dir=(-1.0,-1.0),fillet=18.,flag=None,y_b=0.):
    """The pen tail drawn as ONE stroke of smooth curves (the author: "make them smoother"; the composite of I015 had curvature jumps at the
    cap, the bridge and the grafted comma tip). In the de-slanted plane:
      outer contour: the inner edge of the exit at y_c rises, turns over the top (cap, tangent to the exit edge) and comes down as the right
                     edge of the downstroke, leaning out by `lean` (the swell of a pressed stroke), then bends down-left into the tip;
      tip:           round, radius tip_r, centre `reach` left of the foot's right extent at the baseline, `depth` at its lowest;
      inner contour: from the tip up to the foot, arriving tangent to the foot outline at the baseline: the foot flows into the tail, no crack.
    The native exit above y_c is removed (in cursive the exit ends just above the line)."""
    def piece(y):return slices(base,y)[-1]
    bx=piece(y_b)[1];b_s=(piece(y_b+4.)[1]-piece(y_b-4.)[1])/8.            # foot outline at the baseline and its lean
    if flag is None:
        fl,fr=piece(y_c);in_s=(piece(y_c+1.5)[0]-piece(y_c-1.5)[0])/3.     # exit inner edge: ud per unit upward, measured close (it is curved)
        body=SUB(base,AND(AND(right_of(fl-12.),above(y_c)),below(y_c+180.)))
    else:                                                                  # capitals: the flag of the stem foot is the exit, merged with the stem
        fr=piece(y_c)[1];fl=fr-flag;in_s=(piece(y_c+1.5)[1]-piece(y_c-1.5)[1])/3.;body=base
    def unit(a,b):l=math.hypot(a,b);return a/l,b/l
    dt=unit(*tip_dir)                                                      # direction of the stroke at the tip: down and to the left (45 degrees in the de-slanted plane)
    no=(-dt[1],dt[0])
    if no[0]<0:no=(-no[0],-no[1])                                          # normal to the outer side (it faces lower right)
    C=(bx-reach,depth+tip_r);O=(C[0]+tip_r*no[0],C[1]+tip_r*no[1]);I=(C[0]-tip_r*no[0],C[1]-tip_r*no[1])
    B=(bx,0.);E=(fl,y_c);D=(fr,y_c);ld=unit(lean,-1.);di=unit(in_s,1.);db=unit(b_s,1.)
    L=y_c-depth;k=0.5523
    X=lambda q:(q[0]+S*q[1],q[1])
    add=lambda a,b,t:(a[0]+b[0]*t,a[1]+b[1]*t)
    pth=pathops.Path();pen=pth.getPen()
    pen.moveTo(X(B))
    if flag is not None:pen.lineTo(X((bx-25.,(y_b+y_c)/2)))             # capitals: close through the stem, so no eye is left under the flag
    pen.lineTo(X(E))
    w=fr-fl;pen.curveTo(X(add(E,di,w*0.75)),X(add(D,ld,-w*0.75)),X(D))                       # turn of the pen
    pen.curveTo(X(add(D,ld,L*0.40)),X(add(O,dt,-L*0.36)),X(O))                               # outer edge of the downstroke: swells out, then bends left
    bot=(C[0]+tip_r*dt[0],C[1]+tip_r*dt[1])
    pen.curveTo(X(add(O,dt,tip_r*k)),X(add(bot,no,tip_r*k)),X(bot))                          # round tip
    pen.curveTo(X(add(bot,no,-tip_r*k)),X(add(I,dt,tip_r*k)),X(I))
    pen.curveTo(X(add(I,dt,-L*0.36)),X(add(B,db,-fillet)),X(B))                              # inner edge, tangent to the foot at the baseline (short handle: no wave)
    pen.closePath()
    return OR(body,pth)


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
        if TAIL=='pen':return smooth_tail(base)
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
    # ж as written (Cormorant, EB Garamond, PT Serif, Alegreya, Old Standard, Lora): a reversed c, the stem, a c, backs to the stem, a hairline
    # through them at the middle. The I006-I018 form (k arms mirrored) read as "ЖК" and is kept at U+F106.
    mp=pathops.Path();k_arms=SUB(AND(AND(k,right_of(55)),below(520)),AND(left_of(72),above(500)));k_arms.draw(TransformPen(mp.getPen(),(-1,0,2*S,1,2*37.0,0)))
    out['\uf106']=(OR(zh_stem,mp),447)
    c_=native(ita,'c');ZH_GAP=45.;ZH_SL,ZH_SR=4.2,68.4                          # k stem at mid height (ud)
    c_back=slices(c_,255)[0][0]                                                  # -31.1: outer edge of the back of c at mid height
    zh_c=transformed(c_,dx=ZH_SR+ZH_GAP-c_back)
    A2=ZH_SL-ZH_GAP+c_back                                                      # mirror about ud=A2/2: the back of the reversed c ends ZH_GAP left of the stem
    zh_rc=pathops.Path();c_.draw(TransformPen(zh_rc.getPen(),(-1,0,2*S,1,A2,0)))
    zh_stem2=AND(AND(k,left_of(72)),below(510))
    # the joins are the pen's upstrokes (author's sketch), not a level bar: from the back of the reversed c up to the top of the stem, and
    # from the foot of the stem up into the back of c; "/" strokes are hairlines in this face (x: 26)
    def hair(a,b,w=14.,bend=0.):                    # 14: the hairline of the pen model (o top); 24 made a dark knot (author)
        X=lambda q:(q[0]+S*q[1],q[1]);du,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(du,dy);nx,ny=-dy/l,du/l
        P=[a,(a[0]+du/3+nx*bend,a[1]+dy/3+ny*bend),(a[0]+2*du/3+nx*bend,a[1]+2*dy/3+ny*bend),b]
        return sweep([X(q) for q in P],w,w)
    rc_back=slices(zh_rc,195)[-1][1];c_back2=slices(zh_c,350)[0][0]          # outer edges of the two backs where the upstrokes meet them
    zh_h1=hair((rc_back-12,185),(ZH_SL+14,425),bend=-8)                         # reversed c -> top of the stem
    zh_h2=hair((ZH_SR-14,105),(c_back2+12,345),bend=-8)                         # foot of the stem -> back of c
    out['ж']=(OR(zh_rc,zh_stem2,zh_c,zh_h1,zh_h2),720)
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
    # ф by the usual method (author: not a crossed oval): two bowls on a shared stem, as the Regular ф. Left bowl, stem, ascender and flag:
    # the native d whole (its bowl joins its own stem, joints untouched); descender and serif: the native q (stem at the same place, 237..304);
    # right bowl: the native p bowl moved onto that stem, its counter tightened to the left one (d 174 at y=255; p 202). The crossed oval
    # (o + stem) of I008-I017 is kept as the PUA alternate U+F105.
    out['\uf105']=(OR(o,band((o_lo+o_hi)/2-27,(o_lo+o_hi)/2+27,-60,560),transformed(AND(b,above(560)),dx=(o_lo+o_hi)/2-37.9),transformed(AND(p_,below(-60)),dx=(o_lo+o_hi)/2-50.2)),560)
    d_=native(ita,'d')
    # ф (author: "frankly unfinished" for the d + p bowls of I018, which did not match): two equal native o, moved towards each other, the stem
    # between them takes the place of their inner walls, the arcs of each o run into the stem at the top and the bottom (Literata, Lora,
    # PT Serif); counters 158 each (Regular 143). Stem: ascender with flag of d, descender with serif of q, both moved onto it (no scaling).
    EF_SL=200.;EF_W=66.6;EF_DX=170.
    ef_bowls=OR(AND(o,left_of(EF_SL+1)),AND(transformed(o,dx=EF_DX),right_of(EF_SL+EF_W-1)))
    ef_up=OR(AND(d_,AND(AND(right_of(236),left_of(310)),AND(above(245),below(560)))),AND(d_,above(560)))   # stem, ascender, flag of d; not its exit
    ef_down=AND(q,OR(AND(AND(right_of(236),left_of(304.0)),below(255)),below(-60)))          # stem, descender, serif of q (equal to d at y=250; its right edge 0.3 wider is trimmed to d)
    ef_stem=OR(transformed(ef_up,dx=EF_SL-237.),transformed(ef_down,dx=EF_SL-237.))
    out['ф']=(OR(ef_bowls,ef_stem),600)
    # ---- в ч я: stem swap, bowls and legs from the sheared Regular
    v_fill=poly([(150,500),(165,511),(205,510),(222,509),(229,491),(195,468),(188,467),(160,440)])    # the Regular bowl starts right of the n arch: fills the notch between arch and bowl top
    out['\uf108']=(OR(n_stem,AND(AND(sheared('в'),right_of(80)),below(530)),v_fill),435)   # в of I006-I018 (stem with hook and the sheared Regular bowls)
    # в as written in italic (Cormorant, EB Garamond, Lora, PT Serif, Literata, Old Standard, Alegreya): no straight stem, one stroke: from the
    # waist down round the lower bowl, up the left spine, over the small upper loop, down into the waist and on to the left as the hairline that
    # parts the counters. No native donor has bowls of this size (6 and o are almost x-height tall), so it is drawn with the pen model fitted on
    # the native o (tools/italic_pen.py); skeleton in the de-slanted plane.
    import italic_pen as PEN
    # I022 (author: в still clumsy, no proper curves): 21 hand-placed points interpolated by Catmull-Rom gave uneven curvature, a narrow
    # beta-like letter (315 wide, both loops alike) and a bump at the lower left. Proportions measured on PT Serif, Lora, Source Serif and
    # Literata Italic (de-slanted, x-height 510, widths scaled to the native o, 356): в = 0.94 o, lower bowl widest at y 150 (centre line 286),
    # upper loop narrower (264 at y 400), convex spine that leans right and thins towards the top, hairline falling to the spine (262 -> 236),
    # lower bowl starting on the falling stroke of the upper loop (sharp inner notch at the right of the waist). Centre line = those points
    # smoothed by a least-squares cubic B-spline with a curvature penalty (28 control points, lambda 0.3, within 6 of the points), drawn by
    # the pen of the native o; 56 points (native b 58)
    VE_SKELETON=[(213,290),(240,268),(262,240),(276,210),(282,185),(286,160),(286,135),(283,110),(275,85),(261,60),(244,35),(212,12),(170,2),(125,10),(85,35),(62,70),(50,105),(44,140),(39,185),(37,230),(38,285),(45,335),(58,385),(83,435),(105,460),(135,490),(185,506),(228,492),(250,465),(260,435),(264,405),(262,375),(255,345),(244,320),(226,300),(200,280),(170,265),(130,253),(90,244),(52,236)]
    out['в']=(PEN.stroke_samples(PEN.smooth_skeleton(VE_SKELETON,28,0.3),taper=(30,0.5),tol=2.0),420)
    ч_=sheared('ч')
    ч_stem=transformed(n_stem1(),dx=14.1-84.25)                 # left stem: n stem centred on the Regular stem (ud -19.9..48.1)
    ч_right=transformed(u_stem2(),dx=222.1-U_L)                   # right stem: clean u stem with its exit
    out['ч']=(OR(AND(ч_stem,above(300)),OR(AND(AND(ч_,left_of(130)),below(300)),AND(AND(AND(ч_,right_of(130)),left_of(240)),above(150))),ч_right),433)   # I021: above 150, the Regular foot serif left a spur at the stem foot
    я_=sheared('я')
    я_right=transformed(u_stem2(),dx=191.1-U_L)
    yaleg=poly([(74.4+0.32*(0-100)-14+S*0,0),(74.4+0.32*(0-100)+14,0),(74.4+0.32*(105-100)+14+S*105,105),(74.4+0.32*(105-100)-14+S*105,105)])
    out['\uf107']=(OR(AND(AND(я_,left_of(196)),above(100)),yaleg,я_right),428)   # я of I008-I018 (sheared Regular bowl, straight leg)
    # я from native parts (author: redo): the closed upper bowl of g (200..516, its right wall 212..283 is where the stem goes), the u stem with
    # its exit on that wall, the leg: the lower half of the "/" of x with its ball at the baseline, carried up along its own direction to the
    # bowl bottom next to the stem (Old Standard, Cormorant, EB Garamond: the leg leaves the bowl at the stem and ends at the lower left).
    g_=native(ita,'g');x_=native(ita,'x')
    # g bowl without ear and link: the link is cut along an ellipse through the outer contour of the bowl (left -12.2 and right 288 at y=350,
    # top 516, bottom ~200), so the bowl closes in its own curve instead of a flat cut
    def ellipse_ud(cu,cy,a,b):
        k=0.5523;X=lambda u,y:(u+S*y,y);e=pathops.Path();pen=e.getPen();pen.moveTo(X(cu+a,cy))
        for (p1,p2,p3) in (((cu+a,cy+k*b),(cu+k*a,cy+b),(cu,cy+b)),((cu-k*a,cy+b),(cu-a,cy+k*b),(cu-a,cy)),((cu-a,cy-k*b),(cu-k*a,cy-b),(cu,cy-b)),((cu+k*a,cy-b),(cu+a,cy-k*b),(cu+a,cy))):
            pen.curveTo(X(*p1),X(*p2),X(*p3))
        pen.closePath();return e
    ya_bowl=AND(SUB(g_,AND(above(470),right_of(250))),ellipse_ud(138.,357.,151.5,160.))
    YA_SL=219.5
    q_top=OR(band(YA_SL,YA_SL+67.1,196,513),transformed(AND(q,AND(right_of(258),above(470))),dx=YA_SL-237.0))   # stem (67) and the ear of q; the V of q between bowl and ear is filled
    u_low=transformed(AND(u_stem2(),below(204)),dx=YA_SL-U_L)                  # stem foot and exit of u (63.4)
    ya_stem=OR(q_top,u_low,poly([(YA_SL+S*150,150),(YA_SL+63.4+S*150,150),(YA_SL+67.1+S*250,250),(YA_SL+S*250,250)]))
    YA_DX=45.                                                                  # leg moved right: it leaves the bowl bottom next to the stem
    ya_leg=transformed(AND(x_,AND(left_of(150),below(170))),dx=YA_DX)
    lean=(133.0-122.0)/50.                                                    # centre of the "/" of x: 133 at y=150, 122 at y=100 (ud)
    ya_link=poly([(120.0+YA_DX+S*150,150),(145.9+YA_DX+S*150,150),(145.9+YA_DX+lean*70+S*220,220),(120.0+YA_DX+lean*70+S*220,220)])
    out['я']=(OR(ya_bowl,ya_stem,ya_leg,ya_link),440)
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
        out['қ']=(smooth_tail(ka),470)
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
BEARINGS={'қ':(6,15),'ң':(19,15),'ү':(21,20),'ұ':(21,20),'ә':(None,None),'к':(6,22),'ж':(19,22),'\uf106':(19,22),'ь':(14,22),'ъ':(14,22),'ы':(14,22),'ө':(20,21),'ғ':(19,-36),'й':(21,20),'в':(20,22),'\uf108':(20,22),'м':(20,22),'з':(None,None),'э':(None,None),'ч':(20,22),'я':(20,22),'\uf107':(20,22),'ю':(19,21),'ф':(20,22),'\uf105':(20,22),'б':(None,None),'ш':(21,20),'ц':(21,15),'щ':(21,15),'н':(19,22),'д':(13,10),'л':(20,22),'г':(19,-36),'\uf101':(20,22),'\uf102':(13,22),'\uf103':(13,22),'\uf104':(13,22)}


SPACING=json.loads(Path('data/italic-spacing.json').read_text())['glyphs'] if Path('data/italic-spacing.json').exists() else {}


def main():
    ita=TTFont(ITA);reg=TTFont(REG);font=TTFont(CAPS)
    built=build(ita,reg);rep=[]
    for ch,(path,adv) in built.items():
        glyf=font['glyf'];g=to_glyph(path,glyf)
        g,st=tidy(g,glyf);g,_=fair(g,glyf)              # I021: seams and grid kinks faired (tools/italic_fair.py)
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
