#!/usr/bin/env python3
"""Outline proof of head separation, complete typography and spacing widths."""
import io,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_draft_font import shape
from build_draft_font import TTF
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from PIL import Image,ImageDraw,ImageFont

def main():
    now=TTF.read_bytes();old=subprocess.check_output(['git','show','68fc03e:'+str(TTF)])
    font=TTFont(io.BytesIO(now));before=TTFont(io.BytesIO(old))
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="2100" height="1550" viewBox="0 0 2100 1550">','<rect width="100%" height="100%" fill="#f5f2ec"/>']
    def label(x,y,s):svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="28" fill="#69656a">{s}</text>')
    def line(s,x,y,size,isold=False):
        data,f=(old,before) if isold else (now,font);gs=f.getGlyphSet();scale=size/1000
        for n,advance,_,dx,dy in shape(data,f,s):
            pen=SVGPathPen(gs);gs[n].draw(pen)
            color='#aaa19b' if isold else '#272333'
            svg.append(f'<path fill="{color}" transform="translate({x+dx*scale} {y-dy*scale}) scale({scale} {-scale})" d="{pen.getCommands()}"/>');x+=advance*scale
    label(40,50,'1.005 · верхние засечки разделены, новые типографские знаки')
    label(40,115,'1.004');line('КУ УУ УХ ХУ · уу ух ху',40,270,150,True)
    label(40,355,'1.005');line('КУ УУ УХ ХУ · уу ух ху',40,510,150)
    line('ҚАЗАҚСТАН · Күн, гүл, үміт; ұлт, ұлы, құс.',40,700,95)
    label(40,810,'Штрихи, знаки, тире, акценты')
    line('12′ 30″ · † ‡ · ≈ · � · Ə́ ə́',40,970,155)
    line('2020‒2026 · слово‐слово · слово―слово',40,1120,100)
    label(40,1220,'En / Em / Figure / Hair: ширина показана между вертикалями')
    line('|\u2002|\u2003|\u2007|\u200a|',40,1370,120)
    label(40,1490,'Основные формы букв и их ширины сохранены. Пробелы и соединители поддерживают Unicode.')
    svg.append('</svg>');Path('docs/img/regular_polish.svg').write_text('\n'.join(svg))
    image=Image.new('RGB',(2000,1050),'#f5f2ec');d=ImageDraw.Draw(image)
    bf=ImageFont.truetype(io.BytesIO(old),160);nf=ImageFont.truetype(io.BytesIO(now),160)
    d.text((30,220),'КУ УУ УХ ХУ · уу ух ху',font=bf,fill='#aaa19b',anchor='ls')
    d.text((30,450),'КУ УУ УХ ХУ · уу ух ху',font=nf,fill='#272333',anchor='ls')
    d.text((30,710),'12′ 30″ · † ‡ · ≈ · � · Ə́ ə́',font=nf,fill='#272333',anchor='ls')
    d.text((30,950),'2020‒2026 · слово‐слово',font=ImageFont.truetype(io.BytesIO(now),110),fill='#272333',anchor='ls')
    image.save('build/kerning/polish.png')

if __name__=='__main__':main()
