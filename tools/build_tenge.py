#!/usr/bin/env python3
"""[РЕШЕНИЕ] Build U+20B8: native T foot/stem, two numeral-height bars."""
import json
from pathlib import Path
from types import SimpleNamespace
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.pointPen import SegmentToPointPen
from fontTools.ufoLib.glifLib import writeGlyphToString
import pathops


def main():
    font=TTFont('reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf')
    rec=RecordingPen();font.getGlyphSet()['T'].draw(rec)
    # Keep the original foot and its transition into the unscaled 71-unit stem.
    a=next(i for i,op in enumerate(rec.value) if op[1] and op[1][-1]==(195,69))
    b=next(i for i,op in enumerate(rec.value) if op==('lineTo',((266,69),)))
    body=RecordingPen();body.value=rec.value[:a+1]+[
        ('lineTo',((195,630),)),('lineTo',((266,630),)),
        ('lineTo',((266,69),))]+rec.value[b+1:]
    path=pathops.Path();body.replay(path.getPen())
    bars=pathops.Path();pen=bars.getPen()
    for bottom in [600,690]:
        # [РЕШЕНИЕ] 30-unit bars, 60-unit clear gap, softly rounded ends.
        x0,x1,r=25,436,10;top=bottom+30
        pen.moveTo((x0+r,bottom));pen.lineTo((x1-r,bottom))
        pen.qCurveTo((x1,bottom),(x1,bottom+r));pen.lineTo((x1,top-r))
        pen.qCurveTo((x1,top),(x1-r,top));pen.lineTo((x0+r,top))
        pen.qCurveTo((x0,top),(x0,top-r));pen.lineTo((x0,bottom+r))
        pen.qCurveTo((x0,bottom),(x0+r,bottom));pen.closePath()
    path=pathops.op(path,bars,pathops.PathOp.UNION,fix_winding=True,clockwise=True)
    assert len(list(path.contours))==2 and path.bounds==(25.,0.,436.,720.)
    meta=SimpleNamespace(width=font['hmtx']['T'][0],unicodes=[0x20B8],
        note='[РЕШЕНИЕ] Знак тенге: стойка71 и нижняя засечка родной T без масштаба; две перекладины30 на высоте цифр720. Интервалы черновые.')
    folder=Path('data/currency');folder.mkdir(exist_ok=True)
    (folder/'uni20B8.glif').write_text(writeGlyphToString('uni20B8',meta,lambda p:path.draw(SegmentToPointPen(p))))
    (folder/'tenge.json').write_text(json.dumps({'character':'₸','unicode':'U+20B8',
        'path':str(folder/'uni20B8.glif'),'advance':meta.width,'bounds':list(path.bounds),
        'stem_width':71,'bar_thickness':30,'bar_bottoms':[600,690],
        'bar_gap':60,'source':'Instrument Serif Regular T foot; new horizontal bars',
        'status':'draft design requested by user'},ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
