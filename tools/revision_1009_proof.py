#!/usr/bin/env python3
"""Actual imported de proportions, author tails and distinct uppercase U shapes."""
import copy,io,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from alphabet_sheet import canvas,text,glyph,MplPen,PathPatch,source_items
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from matplotlib.transforms import Affine2D
from finish_regular import load
import uharfbuzz as hb
import matplotlib.pyplot as plt

OUT=Path('build/revision-1009')
def main():
    OUT.mkdir(parents=True,exist_ok=True);cfg=json.loads(Path('data/alphabet.json').read_text())
    variants=json.loads(Path('data/cormorant-de/manifest.json').read_text())['variants']
    font=TTFont('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf')
    fig,ax=canvas(2200,1550);text(ax,35,25,'д · реальный контур Cormorant · четыре варианта пропорций',34)
    text(ax,35,80,'01 — исходные пропорции; 02/03 — сужение и хвост −280; 04 — более короткий хвост −240.',22)
    for i,v in enumerate(variants):
        x=i*550;text(ax,x+35,145,v['variant']+' · '+v['label'],22)
        glyph(ax,v['path'],x+275,590,.72)
        for y in (590,590-516*.72):ax.plot([x+35,x+510],[y,y],color='#ded8d0',lw=.7)
        trial=copy.deepcopy(font);p,advance=load(v['path']);pen=TTGlyphPen(None);p.draw(Cu2QuPen(pen,.1,reverse_direction=False));g=pen.glyph();g.recalcBounds(trial['glyf']);trial['glyf']['uni0434']=g;trial['hmtx']['uni0434']=(advance,g.xMin)
        data=io.BytesIO();trial.save(data);h=hb.Font(hb.Face(data.getvalue()));hb.ot_font_set_funcs(h);h.scale=(1000,1000);gs=trial.getGlyphSet()
        for row,s in enumerate(['дело  дома  день','город  одежда','дл  лд  ад  да  дд','дядя  дождь','двадцать  подъезд']):
            cursor=x+35;y=995+row*95;z=.065;b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(h,b,{'kern':False})
            for n,pos in zip(b.glyph_infos,b.glyph_positions):
                pen=MplPen(gs);gs[trial.getGlyphName(n.codepoint)].draw(pen)
                if pen.vertices:ax.add_patch(PathPatch(pen.result(),facecolor='#272333',edgecolor='none',transform=Affine2D().scale(z,-z).translate(cursor+pos.x_offset*z,y-pos.y_offset*z)+ax.transData))
                cursor+=pos.x_advance*z
    text(ax,35,1500,'Кривые Cormorant сохранены. В словах — наши остальные буквы; кернинг отключён одинаково для всех четырёх строк.',20)
    fig.savefig('docs/img/de_cormorant_proportions.svg');fig.savefig(OUT/'de-proportions.png');plt.close(fig)
    fig,ax=canvas(1800,1150);text(ax,35,25,'Прописные У · Ү · Ұ',35)
    for i,(ch,label) in enumerate([('У','Диагональ и нижний крючок'),('Ү','Прямая вертикальная стойка'),('Ұ','Та же стойка с перекладиной')]):
        x=300+i*600;text(ax,x,100,label,23,ha='center');glyph(ax,source_items(ch,cfg)[0]['path'],x,930,.95)
    fig.savefig('docs/img/capital_u_revision.svg');fig.savefig(OUT/'capital-u.png');plt.close(fig)
    fig,ax=canvas(2200,1650);text(ax,35,25,'Хвостики · полный контур из авторского SVG',33)
    for i,ch in enumerate('цщқңЦЩҚҢ'):
        x=275+i%4*550;y=120+i//4*740;text(ax,x,y,ch,30,ha='center');glyph(ax,source_items(ch,cfg)[0]['path'],x,y+560,.52)
    text(ax,35,1600,'Перенесены вход, капля, внутренняя дуга и выступ. Верхняя часть каждой буквы сохранена; ss09 — прежние угловые хвосты.',21)
    fig.savefig('docs/img/author_tail_revision.svg');fig.savefig(OUT/'tails.png');plt.close(fig)
if __name__=='__main__':main()
