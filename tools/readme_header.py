#!/usr/bin/env python3
"""Header picture of the README (docs/img/header.svg), set in the published fonts and written as outlines, so it needs no font to show.
Text is shaped by HarfBuzz with the default features (kerning, contextual forms). Colours: Very Peri (#6667AB) and a light lilac.
Usage: python3 -I tools/readme_header.py [fonts/ttf]
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb

W,H=1600,640;BG='#6667AB';INK='#F4F1FF';SOFT='#D9D3FF'
LINES=[('Regular','Very Peri Serif',190,70,230,INK),
       ('Italic','Съешь же ещё этих мягких',96,74,380,INK),
       ('Regular','французских булок, да выпей чаю',96,74,500,INK),
       ('Italic','Қазақ тілі · Ұлы дала · Өнер және ғылым',72,74,600,SOFT)]


def run(font,blob,text,size,x,y):
    f=hb.Font(hb.Face(blob));b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(f,b,{})
    gs=font.getGlyphSet();z=size/font['head'].unitsPerEm;parts=[]
    for info,pos in zip(b.glyph_infos,b.glyph_positions):
        pen=SVGPathPen(gs);name=font.getGlyphName(info.codepoint)
        gs[name].draw(TransformPen(pen,(z,0,0,-z,x+pos.x_offset*z,y-pos.y_offset*z)))
        d=pen.getCommands()
        if d:parts.append(d)
        x+=pos.x_advance*z
    return ' '.join(parts),x


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else 'fonts/ttf');fonts={}
    for s in ('Regular','Italic'):
        p=root/f'VeryPeriSerif-{s}.ttf';fonts[s]=(TTFont(p),p.read_bytes())
    body=[]
    for style,text,size,x,y,color in LINES:
        d,end=run(*fonts[style],text,size,x,y);assert end<W-40,(text,end)
        body.append(f'<path fill="{color}" d="{d}"/>')
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">'
         f'<title>Very Peri Serif: Regular and Italic, Russian and Kazakh</title><rect width="{W}" height="{H}" fill="{BG}"/>'+''.join(body)+'</svg>\n')
    out=Path('docs/img/header.svg');out.write_text(svg);print(out,len(svg)//1024,'KB')


if __name__=='__main__':main()
