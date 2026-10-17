#!/usr/bin/env python3
"""Vector proof of source width edits and HarfBuzz-shaped text comparisons."""
import io,json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from alphabet_sheet import canvas,text,glyph,plt,MplPen,PathPatch,BG
from matplotlib.transforms import Affine2D
from fontTools.ttLib import TTFont
import uharfbuzz as hb


def source_proof():
    rows=[r for r in json.loads(Path('data/width-refinement/manifest.json').read_text()) if r['role']=='primary']
    fig,ax=canvas(3000,1770);text(ax,35,25,'Пропорции и вес · Regular 1.011 / 1.012',35)
    text(ax,35,80,'В каждой паре слева — было, справа — после правки. Одинаковые кегль и цвет.',23)
    for i,r in enumerate(rows):
        x=i%5*600;y=145+i//5*530
        text(ax,x+35,y,r['character'],27)
        glyph(ax,r['source'],x+160,y+295,.29,color='#272333');glyph(ax,r['path'],x+435,y+295,.29)
        text(ax,x+160,y+400,str(r['advance_before']),21,ha='center');text(ax,x+435,y+400,str(r['advance_after']),21,ha='center')
    fig.savefig('docs/img/width_refinement.svg');Path('build/width-review').mkdir(exist_ok=True);fig.savefig('build/width-review/changes.png');plt.close(fig)


def text_proof():
    olddata=subprocess.check_output(['git','show','f3614aa:dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf']);newdata=Path('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf').read_bytes()
    fig,ax=canvas(2600,1800);text(ax,40,30,'Ритм строки · слева 1.011, справа 1.012',33)
    samples=['ЖИЗНЬ  ШИРОТА  ЧАША','ШЫҒЫС  ШАҢ  ҚЫЗЫЛ','ФОРМА  ЮНОСТЬ  МЫШЬ','тишина  ширина  шёпот','мощь  щука  мышь  июнь','дело  дома  день  дядя','дождь  одежда  двадцать','зима  звезда  зелёный','фраза  юла  физика  мысль','Ә Ғ Қ Ң Ө Ұ Ү Һ І','ә ғ қ ң ө ұ ү һ і']
    for data,x,color in [(olddata,40,'#272333'),(newdata,1350,'#272333')]:
        font=TTFont(io.BytesIO(data));gs=font.getGlyphSet();h=hb.Font(hb.Face(data));hb.ot_font_set_funcs(h);h.scale=(1000,1000)
        for k,s in enumerate(samples):
            b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(h,b,{});cursor=x;y=220+k*138;z=.09
            for g,pos in zip(b.glyph_infos,b.glyph_positions):
                pen=MplPen(gs);gs[font.getGlyphName(g.codepoint)].draw(pen)
                if pen.vertices:ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none',transform=Affine2D().scale(z,-z).translate(cursor+pos.x_offset*z,y-pos.y_offset*z)+ax.transData))
                cursor+=pos.x_advance*z
    text(ax,40,1740,'Родная латиница и неизменённые буквы сохранены. Кернинг пересчитан для новых пропорций.',23)
    fig.savefig('docs/img/width_text_comparison.svg');fig.savefig('build/width-review/text.png');plt.close(fig)
if __name__=='__main__':
    source_proof()
    if '--text' in sys.argv:text_proof()
