"""Local contour repairs requested by the author, after integer-grid fairing."""
from polish_outlines import contours_of,to_glyph,hausdorff


def smooth_ya(glyph,glyf):
    """Fair both donor seams of я without changing its bowl, stem or metrics.

    The g bowl used three nodes to descend into the q stem, leaving a visible
    notch at the top.  At the lower join, the link and stem made a pointed
    triangular spur.  Replace only those two short runs with tangent-matched
    quadratic splines; all endpoints and the counter stay in place.
    """
    contours=contours_of(glyph,glyf);top=lower=0
    for points in contours:
        n=len(points)
        for i,p in list(enumerate(points)):
            if i+6<n and p[2] and p[1]==513 and points[i+1][2] and points[i+1][1]==497 and points[i+3][2] and points[i+3][1]==510 and points[i+6][2] and points[i+6][1]==516:
                end=points[i+6]
                points[i+1:i+6]=[[p[0]-15,513,False],[end[0]+31,516,False]]
                top+=1;break
        n=len(points)
        for i,p in list(enumerate(points)):
            if i+4<n and p[2] and p[1]==205 and not points[i+1][2] and points[i+2][2] and points[i+2][1]==217 and points[i+4][2] and points[i+4][1]==196:
                end=points[i+4]
                points[i+1:i+4]=[[p[0]+3,p[1]+11,False],[end[0]+3,end[1]+11,False]]
                lower+=1;break
    assert (top,lower)==(1,1),('The я joins changed; review the contour repair',top,lower)
    result=to_glyph(contours);result.recalcBounds(glyf)
    deviation=float(hausdorff(glyph,result,glyf))
    assert deviation<=16.5,('я join displacement',deviation)
    return result,{'regions':['top bowl/stem shoulder','lower link/stem shoulder'],
                   'repairs':['tangent-matched top spline','rounded lower spline'],
                   'outline_deviation':round(deviation,3)}


def smooth_zhe(glyph,glyf):
    """Vertical tangent at the left bowl/connector shoulder, after the redraw."""
    contours=contours_of(glyph,glyf);fixed=0
    for points in contours:
        for i,p in enumerate(points):
            a=points[i-1];b=points[(i+1)%len(points)]
            if p[2] and not a[2] and not b[2] and p[1]==334 and a[1]==278 and b[0]==p[0] and a[0]==p[0]-3:
                a[0]=p[0];fixed+=1
    assert fixed==1,('The ж shoulder changed; review the contour repair',fixed)
    result=to_glyph(contours);result.recalcBounds(glyf)
    deviation=float(hausdorff(glyph,result,glyf))
    assert deviation<=2.,('ж shoulder displacement',deviation)
    return result,{'region':'left bowl/connector shoulder','handle_dx':3,
                   'tangent_break_before_degrees':3.1,'tangent_break_after_degrees':0,
                   'outline_deviation':round(deviation,3)}


def smooth_ze(glyph,glyf):
    """The inner shoulder of з: horizontal tangent at y=489, not a 4.6° kink.

    The outgoing off-curve point was at y=487 while the incoming tangent is
    horizontal at 489. Raising that handle by 2 units moves the contour by at
    most one unit. Keep the extremum and the drop's weight/position intact.
    """
    contours=contours_of(glyph,glyf);fixed=0
    for points in contours:
        for i,p in enumerate(points):
            a=points[i-1];b=points[(i+1)%len(points)]
            if p[2] and not a[2] and not b[2] and p[1]==489 and a[1]==489 and b[1]==487 and a[0]<p[0]<b[0]:
                b[1]=489;fixed+=1
    assert fixed==1,('The з shoulder changed; review the contour repair',fixed)
    result=to_glyph(contours);result.recalcBounds(glyf)
    deviation=float(hausdorff(glyph,result,glyf))
    assert deviation<=1.2,('з shoulder displacement',deviation)
    return result,{'region':'upper inner shoulder','handle_y':[487,489],
                   'tangent_break_before_degrees':4.6,'tangent_break_after_degrees':0,
                   'outline_deviation':round(deviation,3)}
