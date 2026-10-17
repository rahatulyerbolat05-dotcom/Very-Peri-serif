#!/usr/bin/env python3
"""Cyrillic letters that already exist in the native Instrument Serif Italic (direct donors, data/italic-plan.json).
Writes data/italic-ready.json and an SVG/HTML sheet to the path given (default build/italic-ready/sheet.html).
"""
import json,sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen

REF=Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Italic.ttf')


def main():
    out=Path(sys.argv[1] if len(sys.argv)>1 else 'build/italic-ready/sheet.html');out.parent.mkdir(parents=True,exist_ok=True)
    plan=json.loads(Path('data/italic-plan.json').read_text());direct=plan['direct_donor_candidates']
    f=TTFont(REF);gs=f.getGlyphSet();cm=f.getBestCmap()
    rows=[]
    for ch,donor in direct.items():
        b=BoundsPen(gs);gs[donor].draw(b)
        rows.append(dict(character=ch,codepoint=f'U+{ord(ch):04X}',donor=donor,donor_codepoint=next((f'U+{c:04X}' for c,n in cm.items() if n==donor),None),advance=f['hmtx'][donor][0],bounds=[round(v) for v in b.bounds]))
    Path('data/italic-ready.json').write_text(json.dumps(rows,ensure_ascii=False,indent=1)+'\n')
    cells=''
    order=sorted(direct,key=lambda c:(c.islower(),c))
    cw=310;cols=6
    for i,ch in enumerate(order):
        donor=direct[ch];p=SVGPathPen(gs);gs[donor].draw(p);adv=f['hmtx'][donor][0]
        x=(i%cols)*cw+60;y=(i//cols)*500+400
        cells+=f'<g transform="translate({x},{y}) scale(0.38,-0.38)"><path d="{p.getCommands()}" fill="#111"/></g>'
        cells+=f'<line x1="{x-10}" x2="{x+cw-50}" y1="{y}" y2="{y}" stroke="#9cf" stroke-width="1"/>'
        cells+=f'<text x="{x}" y="{y+95}" font-family="sans-serif" font-size="40" fill="#a30">{ch}</text><text x="{x+55}" y="{y+95}" font-family="sans-serif" font-size="20" fill="#666">{donor}  adv {adv}</text>'
    h=(len(order)+cols-1)//cols*500+100
    out.write_text(f'<body style="margin:0;background:#f5f5f5"><svg xmlns="http://www.w3.org/2000/svg" width="{cols*cw+40}" height="{h}">{cells}</svg>')
    print(len(rows),'letters ->',out)

if __name__=='__main__':main()
