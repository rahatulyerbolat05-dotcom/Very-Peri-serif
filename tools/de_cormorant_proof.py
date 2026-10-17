#!/usr/bin/env python3
"""The two selected Cormorant references beside the actual Very Peri builds."""
import io,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
import uharfbuzz as hb
from audit_regular_de import load_family,draw_plate,CACHE

def own_row(data,label,features=None):
    font=TTFont(io.BytesIO(data));h=hb.Font(hb.Face(data));hb.ot_font_set_funcs(h);h.scale=(1000,1000)
    def shape(text):
        b=hb.Buffer();b.add_str(text);b.guess_segment_properties();b.language='ru';hb.shape(h,b,features or {})
        return [(font.getGlyphName(g.codepoint),p.x_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]
    name=shape('д')[0][0];p=BoundsPen(font.getGlyphSet());font.getGlyphSet()[name].draw(p)
    return (dict(family=label,style='normal',language='ru',features=features or {},x_height=510,descender_per_x=max(0,-p.bounds[1]/510)),font,shape)

def main():
    rows=[]
    for family in ('cormorantgaramond','cormorantinfant'):
        for row in load_family(family):
            r=row[0]
            if r['style']=='normal' and r['language']=='ru' and r['features']==({'ss10':1} if family=='cormorantgaramond' else {}):rows.append(row)
    new=Path('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf').read_bytes()
    old=subprocess.check_output(['git','show','767ffe0:dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf'])
    rows += [own_row(new,'Very Peri · новая д 1.008'),own_row(old,'Very Peri · прежняя 1.007'),own_row(new,'Very Peri · печатная ss07',{'ss07':True})]
    draw_plate('de_cormorant_style.svg',rows,'Строчная д · выбранное направление Cormorant → Very Peri','Одинаковая видимая высота строчных. У Very Peri собственный рисунок чаши и хвоста, родные окончания q/j.')
if __name__=='__main__':main()
