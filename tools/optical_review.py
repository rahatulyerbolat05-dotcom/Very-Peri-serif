#!/usr/bin/env python3
"""Measured inventory for visual acceptance; never equates geometry with taste.

All 84 letters in each style are rendered in family_proof.py. This companion
records width/height/density/curve diagnostics against the pinned baseline and
native Latin, so a reviewer can tell an intentional corner from a new defect.
"""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
import pathops
import polish_audit
from family_proof import UP,LOW


def glyph(font,ch):
    name=font.getBestCmap()[ord(ch)];g=font['glyf'][name];g.recalcBounds(font['glyf'])
    p=pathops.Path();font.getGlyphSet()[name].draw(p.getPen(glyphSet=font.getGlyphSet()))
    diagnostics=polish_audit.check(font,name)
    return {'glyph':name,'advance':font['hmtx'][name][0],'bounds':[g.xMin,g.yMin,g.xMax,g.yMax],
            'density':round(abs(p.area)/((g.xMax-g.xMin)*(g.yMax-g.yMin)),4),
            'points':len(g.getCoordinates(font['glyf'])[0]),'diagnostics':{k:len(v) for k,v in diagnostics.items()}}


def main():
    out=Path('build/release');report={'method':__doc__,'styles':{},'automated_diagnostics_are_not_visual_approval':True}
    for style in ('Regular','Italic'):
        f=TTFont(out/f'VeryPeriSerif-{style}.ttf');before=TTFont(f'build/premium/before/{style}.ttf')
        rows={ch:{'before':glyph(before,ch),'after':glyph(f,ch)} for ch in UP+LOW}
        native={ch:glyph(f,ch) for ch in 'HNOAonumcpxyz'}
        report['styles'][style]={'letters':rows,'native_controls':native,
                                'sha256':hashlib.sha256((out/f'VeryPeriSerif-{style}.ttf').read_bytes()).hexdigest(),
                                'baseline_sha256':hashlib.sha256(Path(f'build/premium/before/{style}.ttf').read_bytes()).hexdigest(),
                                'zhe_to_en':round(rows['ж']['after']['advance']/rows['н']['after']['advance'],3),
                                'de_depth':rows['д']['after']['bounds'][1]}
    (out/'optical-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({s:{k:v for k,v in r.items() if k not in ('letters','native_controls')} for s,r in report['styles'].items()}))


if __name__=='__main__':main()
