#!/usr/bin/env python3
"""Outline comparison of the old and printed Regular д, including shaped words."""
import io,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from alphabet_sheet import canvas,text,glyph,load_glif,MplPen,PathPatch
from matplotlib.transforms import Affine2D
from fontTools.ttLib import TTFont
import uharfbuzz as hb
import matplotlib.pyplot as plt

def main():
    fig,ax=canvas(1500,1400)
    text(ax,45,35,'Regular · строчная д',32)
    text(ax,160,100,'Прежняя',23);text(ax,900,100,'Печатная',23)
    for x in (0,750):
        for y in (185,593,665):ax.plot([45+x,700+x],[y,y],color='#dfd8ce',linewidth=1)
    glyph(ax,'data/codex/uni0434-01.glif',350,593,.8,color='#8d8790')
    glyph(ax,'data/regular-de-refinement/uni0434.glif',1100,593,.8)
    before=subprocess.check_output(['git','show','fa52875:dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf'])
    after=Path('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf').read_bytes()
    def word(s,x,y,data,color):
        font=TTFont(io.BytesIO(data));gs=font.getGlyphSet();h=hb.Font(hb.Face(data));hb.ot_font_set_funcs(h);h.scale=(1000,1000)
        b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(h,b,{})
        for g,p in zip(b.glyph_infos,b.glyph_positions):
            pen=MplPen(gs);gs[font.getGlyphName(g.codepoint)].draw(pen)
            if not pen.vertices:x+=p.x_advance*.085;continue
            ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none',transform=Affine2D().scale(.085,-.085).translate(x+p.x_offset*.085,y-p.y_offset*.085)+ax.transData));x+=p.x_advance*.085
    for i,s in enumerate(['дело  дома  день','город  дядя  дождь','детали  одежда','дл  лд  ад  да  дд','двадцать  подъезд']):
        y=850+i*105;word(s,55,y,before,'#8d8790');word(s,805,y,after,'#25222b')
    Path('docs/img/regular_de_refinement.svg').parent.mkdir(exist_ok=True)
    fig.savefig('docs/img/regular_de_refinement.svg',facecolor=fig.get_facecolor())
    Path('build/regular-de').mkdir(parents=True,exist_ok=True);fig.savefig('build/regular-de/comparison.png',dpi=100,facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':main()
