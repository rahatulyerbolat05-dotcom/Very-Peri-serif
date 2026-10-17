#!/usr/bin/env python3
"""Actual outlines and HarfBuzz words: old loop, new hook, printed ss07."""
import io,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from alphabet_sheet import canvas,text,glyph,MplPen,PathPatch
from matplotlib.transforms import Affine2D
from fontTools.ttLib import TTFont
import uharfbuzz as hb
import matplotlib.pyplot as plt

def main():
    fig,ax=canvas(1800,1450);text(ax,35,25,'Regular · д с нижним хвостиком',32)
    old=subprocess.check_output(['git','show','fa52875:dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf'])
    new=Path('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf').read_bytes()
    columns=[('Прежняя петлевая','data/codex/uni0434-01.glif',old,{},'#928993'),
             ('Новая · округлая чаша','data/regular-de-tail/uni0434.glif',new,{},'#272333'),
             ('Печатная альтернатива · ss07','data/regular-de-refinement/uni0434.glif',new,{'ss07':True},'#675177')]
    words=['дело  дома  день','город  дядя  дождь','детали  одежда','дл  лд  ад  да  дд','двадцать  подъезд','дно  дуга  долг  друзья']
    for i,(label,path,data,features,color) in enumerate(columns):
        x=30+i*600;text(ax,x,105,label,23)
        for y in (225,560,700):ax.plot([x,x+540],[y,y],color='#ded8cf',lw=.6)
        glyph(ax,path,x+270,560,.65,color=color)
        font=TTFont(io.BytesIO(data));gs=font.getGlyphSet();h=hb.Font(hb.Face(data));hb.ot_font_set_funcs(h);h.scale=(1000,1000)
        for row,s in enumerate(words):
            cursor=x;y=845+row*90;scale=.065
            b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(h,b,features)
            for g,p in zip(b.glyph_infos,b.glyph_positions):
                pen=MplPen(gs);gs[font.getGlyphName(g.codepoint)].draw(pen)
                if pen.vertices:ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none',transform=Affine2D().scale(scale,-scale).translate(cursor+p.x_offset*scale,y-p.y_offset*scale)+ax.transData))
                cursor+=p.x_advance*scale
    text(ax,35,1400,'Округлая чаша q и крючок j: родные контуры без масштаба. Печатная форма сохранена в шрифте через ss07.',19)
    fig.savefig('docs/img/regular_de_tail.svg',facecolor=fig.get_facecolor());Path('build/regular-de').mkdir(parents=True,exist_ok=True)
    fig.savefig('build/regular-de/tail-comparison.png',dpi=100,facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':main()
