#!/usr/bin/env python3
"""Full ordered-pair PDF, offline comparison UI and a compact outline proof."""
import base64,csv,hashlib,io,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from build_draft_font import TTF,OUT,CHARS,native_kern,REF
from alphabet_sheet import canvas,text,MplPen,PathPatch
from matplotlib.transforms import Affine2D
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

BASE='f732cb2'

def main():
    data=TTF.read_bytes();font=TTFont(TTF);gs=font.getGlyphSet();native=TTFont(REF)
    olddata=subprocess.check_output(['git','show',BASE+':'+str(TTF)]);oldfont=TTFont(io.BytesIO(olddata));oldgs=oldfont.getGlyphSet()
    hf=hb.Font(hb.Face(data));hb.ot_font_set_funcs(hf);hf.scale=(1000,1000)
    oldhf=hb.Font(hb.Face(olddata));hb.ot_font_set_funcs(oldhf);oldhf.scale=(1000,1000)
    def shaped(s,old=False,features=None):
        b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(oldhf if old else hf,b,features or {})
        f=oldfont if old else font
        return [(f.getGlyphName(n.codepoint),p.x_advance,p.x_offset,p.y_offset) for n,p in zip(b.glyph_infos,b.glyph_positions)]
    # Reusable embedded glyph font keeps the exhaustive PDF compact. Draw one
    # glyph at each HarfBuzz position; no renderer-specific pair shaping.
    import copy
    from matplotlib.font_manager import FontProperties
    private=copy.deepcopy(font);order=private.getGlyphOrder();glyph_index={n:i for i,n in enumerate(order)}
    for table in private['cmap'].tables:
        if table.isUnicode():table.cmap.update({0xE000+i:n for i,n in enumerate(order)})
    private.save('build/kerning/proof-private.ttf')
    prop=FontProperties(fname='build/kerning/proof-private.ttf')
    def draw(ax,items,x,y,size,color='#272333'):
        for n,advance,dx,dy in items:
            ax.text(x+dx*size/1000,y-dy*size/1000,chr(0xE000+glyph_index[n]),fontproperties=prop,
                    fontsize=size*.72,color=color,va='baseline')
            x+=advance*size/1000
    # Each primary letter gets a complete page of all 84 following letters.
    # Alternatives are shown explicitly in both positions, not hidden by calt.
    rules={(a,b):int(v) for a,b,v in re.findall(r'^pos (\S+) (\S+) (-?\d+);$',Path('font/draft-features.fea').read_text(),re.M)}
    records=json.loads((OUT/'build-manifest.json').read_text())['glyph_records']
    alts=[n for n,r in records.items() if r['character'] in CHARS and n!=f'uni{ord(r["character"]):04X}']
    def fixed(a,b):
        kern=rules.get((a,b),0)+native_kern(native,a,b)
        return [(a,font['hmtx'][a][0]+kern,0,0),(b,font['hmtx'][b][0],0,0)]
    pages=0
    with PdfPages(OUT/'kerning-all-pairs.pdf') as pdf:
        for label,items in [(ch,[(ch+r,shaped(ch+r)) for r in CHARS]) for ch in CHARS]+[
            (n+' / left',[(records[n]['character']+r,fixed(n,f'uni{ord(r):04X}')) for r in CHARS]) for n in alts]+[
            (n+' / right',[(r+records[n]['character'],fixed(f'uni{ord(r):04X}',n)) for r in CHARS]) for n in alts]:
            fig,ax=canvas(1200,1400);text(ax,30,20,'Very Peri Serif Draft 1.010 · '+label,26)
            for i,(caption,pair) in enumerate(items):
                x=30+(i%7)*165;y=155+(i//7)*100
                draw(ax,pair,x,y,66);text(ax,x,y+18,caption,12,color='#8a8580')
            text(ax,30,1360,'kern + calt; explicit glyph forms on alternative pages · all ordered pairs',16)
            pdf.savefig(fig);plt.close(fig);pages+=1
            if pages in (1,4,13,20,70,78,80,85):
                # Separate review raster of the same page.
                fig,ax=canvas(1200,1400);text(ax,30,20,label,26)
                for i,(_,pair) in enumerate(items):draw(ax,pair,30+(i%7)*165,155+(i//7)*100,66)
                fig.savefig(f'build/kerning/page-{pages}.png',dpi=100);plt.close(fig)
    # Compact before/after proof, all paths shaped through HarfBuzz.
    rows=['КУ УУ УХ ХУ · уу ух ху','АЛЛА ЛАЛА ЛЛ лл АА АУ','ҚАЗАҚСТАН ҮЛГІ ӨМІР',
          'күн гүл үміт ұлт ұлы құс','Съешь ещё мягких булок.','ЦЩҢҚ цщңқ ҢҢ ЦЦ',
          'КНИГА книга нн оо фф','1\u2009000\u202f₸ · № 12 · 500 ₽','ТАТАРСТАН ГАЛАКТИКА']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="2200" height="1550" viewBox="0 0 2200 1550">','<rect width="100%" height="100%" fill="#f5f2ec"/>','<text x="35" y="45" font-family="sans-serif" font-size="30">Кернинг: слева 1.009, справа 1.010</text>']
    for col in (0,1):
        for i,row in enumerate(rows):
            x=30+1100*col;y=175+150*i;scale=.095
            for n,advance,dx,dy in shaped(row,old=col==0):
                pen=SVGPathPen(oldgs if col==0 else gs);(oldgs if col==0 else gs)[n].draw(pen)
                svg.append(f'<path fill="{"#99918c" if col==0 else "#272333"}" transform="translate({x+dx*scale} {y-dy*scale}) scale({scale} {-scale})" d="{pen.getCommands()}"/>');x+=advance*scale
    svg.append('</svg>');Path('docs/img/kerning_comparison.svg').write_text('\n'.join(svg))
    current=base64.b64encode((OUT/'VeryPeriSerifDraft-Regular.woff2').read_bytes()).decode()
    old=base64.b64encode(subprocess.check_output(['git','show',BASE+':dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.woff2'])).decode()
    html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Very Peri Serif · кернинг</title>
<style>@font-face{font-family:Now;src:url(data:font/woff2;base64,CURRENT)}@font-face{font-family:Before;src:url(data:font/woff2;base64,OLD)}*{box-sizing:border-box}body{margin:0;background:#f5f2ec;color:#272333;font:16px system-ui}header{padding:20px;position:sticky;top:0;background:#f5f2ec;border-bottom:1px solid #ccc;z-index:2}h1{font-size:24px;margin:0 0 12px}label{display:inline-block;margin:6px}select,input,button{font:inherit;padding:6px}main{padding:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:10px}.cell{border:1px solid #d8d2cc;border-radius:8px;padding:14px;overflow:visible}.now{font-family:Now;font-size:66px;line-height:1.35}.before{font-family:Before;font-size:48px;color:#aaa19b;line-height:1.35}textarea{width:100%;min-height:90px;font:18px system-ui}.sample{font-size:44px;overflow-wrap:anywhere}small{color:#6e6561}section{margin-bottom:25px}</style>
<header><h1>Кернинг · 1.010 / 1.009</h1><label>Буква <select id="left"></select></label><label>Своя <input id="custom" size="3" maxlength="2"></label><label><select id="direction"><option value="left">Слева</option><option value="right">Справа</option></select></label><label>Сочетания <select id="group"><option value="cyrl">Русские + казахские</option><option value="latin">Латиница</option><option value="digits">Цифры и знаки</option></select></label><label><input type="checkbox" id="kern" checked>kern</label><label><input type="checkbox" id="ss01">ss01</label><label><input type="checkbox" id="ss07">ss07</label><label><input type="checkbox" id="ss08">ss08</label><label><input type="checkbox" id="ss09">ss09</label><p><small>Чёрный — новая сборка, серый — предыдущая. calt включён. Оба шрифта встроены: файл работает без сети.</small></p></header>
<main><section><textarea id="sample">Қазақ тілі — әдемі тіл. Күн, гүл, үміт; ұлт, ұлы, құс.\nСъешь ещё этих мягких французских булок. 1 000 ₸ · № 12 · 500 ₽</textarea><div class="sample before" id="sampleBefore"></div><div class="sample now" id="sampleNow"></div></section><div id="grid" class="grid"></div></main>
<script>const alphabet=ALPHABET;const groups={cyrl:alphabet,latin:'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',digits:'0123456789.,:;!?«»“”()[]—–-ʼ‑₸₽₴№'};const el=id=>document.getElementById(id);for(const c of alphabet){const o=document.createElement('option');o.value=c;o.textContent=c;el('left').append(o)}function render(){const c=el('custom').value||el('left').value;const feat=['kern','ss01','ss07','ss08','ss09'].map(x=>"'"+x+"' "+(el(x).checked?1:0)).join(',');el('grid').replaceChildren();for(const r of groups[el('group').value]){const p=el('direction').value==='left'?c+r:r+c;const cell=document.createElement('div');cell.className='cell';for(const style of ['before','now']){const d=document.createElement('div');d.className=style;d.textContent=p;d.style.fontFeatureSettings=feat;cell.append(d)}el('grid').append(cell)}for(const id of ['sampleBefore','sampleNow']){el(id).textContent=el('sample').value;el(id).style.fontFeatureSettings=feat}}for(const n of document.querySelectorAll('select,input,textarea'))n.addEventListener('input',render);render();</script></html>'''
    html=html.replace('CURRENT',current).replace('OLD',old).replace('ALPHABET',json.dumps(CHARS,ensure_ascii=False))
    (OUT/'kerning-proof.html').write_text(html)
    with (OUT/'kerning-matrix.csv').open('w',newline='') as matrix:
        writer=csv.writer(matrix,lineterminator="\n");writer.writerow(['left/right']+list(CHARS))
        for a in CHARS:
            row=[a]
            for b in CHARS:
                row.append(sum(x[1] for x in shaped(a+b))-sum(x[1] for x in shaped(a+b,features={'kern':False})))
            writer.writerow(row)
    (OUT/'kerning-proof-info.json').write_text(json.dumps({'ttf_sha256':hashlib.sha256(data).hexdigest(),'pdf_sha256':hashlib.sha256((OUT/'kerning-all-pairs.pdf').read_bytes()).hexdigest(),'html_sha256':hashlib.sha256((OUT/'kerning-proof.html').read_bytes()).hexdigest(),'pdf_pages':pages,'primary_ordered_pairs':len(CHARS)**2,'alternative_forms':len(alts),'offline_html':True},indent=2)+'\n')
    print('PDF pages',pages,'primary pairs',len(CHARS)**2)

if __name__=='__main__':main()
