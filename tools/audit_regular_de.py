#!/usr/bin/env python3
"""Pinned, licensed outline comparison of lowercase Cyrillic de in real fonts.
Research material only. These outlines are never installed into Very Peri.
"""
import hashlib,json,re,sys,urllib.request,urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from html import escape
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.varLib.instancer import instantiateVariableFont
import uharfbuzz as hb
import io
COMMIT='47d54ca1ebb14fd864695f1d39dc734f39017c33'
FAMILIES=['prata','oranienbaum','oldstandardtt','cormorantgaramond','cormorantinfant','playfairdisplay','lora','literata','ptserif','forum','viaodalibre','yesevaone']
CACHE=Path('build/de-audit');LICENSE=Path('docs/research/de-references');OUT=Path('docs/img')

def fetch(family,file):
    dest=CACHE/family/file;dest.parent.mkdir(parents=True,exist_ok=True)
    url=f'https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/{family}/'+urllib.parse.quote(file)
    if not dest.exists():dest.write_bytes(urllib.request.urlopen(url,timeout=40).read())
    return dest,url

def load_family(family):
    meta,url=fetch(family,'METADATA.pb');license_path,_=fetch(family,'OFL.txt')
    LICENSE.mkdir(parents=True,exist_ok=True);(LICENSE/(family+'-OFL.txt')).write_bytes(license_path.read_bytes())
    blocks=re.findall(r'fonts \{(.*?)\n\}',meta.read_text(),re.S);rows=[]
    for style in ['normal','italic']:
        matches=[b for b in blocks if f'style: "{style}"' in b and 'weight: 400' in b]
        if not matches:continue
        filename=re.search(r'filename: "([^"]+)"',matches[0])[1]
        file,download=fetch(family,filename);font=TTFont(file);axes={}
        if 'fvar' in font:
            axes={a.axisTag:(400 if a.axisTag=='wght' else min(a.maxValue,max(a.minValue,48)) if a.axisTag=='opsz' else a.defaultValue) for a in font['fvar'].axes}
            font=instantiateVariableFont(font,axes,inplace=False)
        cm=font.getBestCmap()
        if 0x434 not in cm:continue
        gs=font.getGlyphSet();p=BoundsPen(gs);gs[cm[ord('x')]].draw(p);xh=p.bounds[3]
        data=io.BytesIO();font.save(data);data=data.getvalue();h=hb.Font(hb.Face(data));hb.ot_font_set_funcs(h);h.scale=(font['head'].unitsPerEm,)*2
        def shape(text,lang='ru',features=None,_font=font,_h=h):
            b=hb.Buffer();b.add_str(text);b.guess_segment_properties();b.language=lang;hb.shape(_h,b,features or {})
            return [(_font.getGlyphName(g.codepoint),p.x_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]
        base=dict(family=re.search(r'^name: "([^"]+)"',meta.read_text())[1],family_id=family,style=style,filename=filename,url=download,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),axes=axes,x_height=xh,upm=font['head'].unitsPerEm,license=str(LICENSE/(family+'-OFL.txt')),metadata_url=url)
        langs=['ru']
        if shape('д','bg')!=shape('д','ru'):langs.append('bg')
        variations=[(lang,{},'') for lang in langs]
        known={shape('д',lang)[0][0] for lang in langs}
        for tag in ['ss%02d'%i for i in range(1,21)]+['aalt']:
            result=shape('д','ru',{tag:1})[0][0]
            if result not in known:known.add(result);variations.append(('ru',{tag:1},tag))
        for lang,features,feature_label in variations:
            name=shape('д',lang,features)[0][0];p=BoundsPen(gs);gs[name].draw(p)
            record=dict(base,language=lang,features=features,glyph_name=name,glyph_bounds=list(p.bounds),advance=font['hmtx'][name][0],descender_per_x=max(0,-p.bounds[1]/xh),width_per_x=(p.bounds[2]-p.bounds[0])/xh)
            rows.append((record,font,lambda text,lang=lang,features=features,fn=shape:fn(text,lang,features)))
    return rows

def draw_plate(filename,rows,title,subtitle):
    W=1900;H=170+len(rows)*250
    from alphabet_sheet import canvas,text as mpltext,MplPen,PathPatch
    from matplotlib.transforms import Affine2D
    import matplotlib.pyplot as plt
    fig,ax=canvas(W,H)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="#f5f2ec"/>']
    def text(x,y,s,size=23,color='#272333'):
        mpltext(ax,x,y-size,s,size,color=color)
        svg.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,sans-serif" font-size="{size}" fill="{color}">{escape(s)}</text>')
    text(35,48,title,32);text(35,88,subtitle,21);text(350,132,'д · одинаковая x-height',18);text(620,132,'В окружении своих букв',18);text(1110,132,'В словах',18)
    for i,(r,font,shape) in enumerate(rows):
        top=160+i*250;baseline=top+170;gs=font.getGlyphSet();scale=85/r['x_height']
        svg.append(f'<path d="M 330 {baseline} H 1840 M 330 {baseline-85} H 1840" stroke="#ded8cf" fill="none"/>')
        text(35,top+32,r['family'],23);style='Regular' if r['style']=='normal' else 'Italic'
        text(35,top+64,style+' · '+r['language'].upper()+(' · '+','.join(r['features']) if r['features'] else ''),19,'#6f6676')
        text(35,top+95,'вынос / x: %.2f'%r['descender_per_x'],17,'#6f6676')
        def line(s,x,y,target):
            z=target/r['x_height']
            for n,a,dx,dy in shape(s):
                pen=SVGPathPen(gs);gs[n].draw(pen)
                m=MplPen(gs);gs[n].draw(m)
                if m.vertices:ax.add_patch(PathPatch(m.result(),facecolor='#272333',edgecolor='none',transform=Affine2D().scale(z,-z).translate(x+dx*z,y-dy*z)+ax.transData))
                if pen.getCommands():svg.append(f'<path d="{pen.getCommands()}" fill="#272333" transform="translate({x+dx*z:.3f} {y-dy*z:.3f}) scale({z:.6f} {-z:.6f})"/>')
                x+=a*z
        line('д',360,baseline,85);line('д а о у л',620,baseline,50)
        line('дело  дома  день',1140,top+95,35);line('город  одежда',1140,top+175,35)
        svg.append(f'<path d="M 35 {top+240} H 1860" stroke="#e4dfd7"/>')
    svg.append('</svg>');(OUT/filename).write_text('\n'.join(svg))
    fig.savefig(CACHE/(Path(filename).stem+'.png'),dpi=80,facecolor=fig.get_facecolor());plt.close(fig)

def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(load_family,FAMILIES))
    rows=[row for result in results for row in result]
    regular=[row for row in rows if row[0]['style']=='normal' and row[0]['language']=='ru' and not row[0]['features']]
    alternate=[row for row in rows if row not in regular]
    draw_plate('de_reference_regular.svg',regular,'Строчная д · 12 антикв · Regular / русский','Оригинальные контуры, набор HarfBuzz. Масштаб по x-height: одинаковая высота строчных, пропорции сохранены.')
    smallcaps=lambda row:bool(re.search(r'\.(?:sc|smcp)$',row[0]['glyph_name']))
    regional=[row for row in alternate if row[0]['style']=='normal' and not smallcaps(row)]
    italic=[row for row in alternate if row[0]['style']=='italic' and not smallcaps(row)]
    draw_plate('de_reference_alternates.svg',regional,'Строчная д · Regular · локальные формы и ss-наборы','Только прямые формы. BG — болгарская локализация; ss10/ss14 — стилистические наборы. Капитель исключена.')
    draw_plate('de_reference_italic.svg',italic,'Строчная д · Italic отдельно от Regular','Наклон, верхние выносные и локальные формы сохраняются. Капитель исключена из этого листа.')
    focused=[row for row in rows if (row[0]['family_id']=='cormorantinfant' and row[0]['style']=='normal' and row[0]['language']=='ru' and not row[0]['features']) or (row[0]['family_id']=='cormorantgaramond' and row[0]['style']=='normal' and row[0]['features']=={'ss10':1}) or (row[0]['family_id'] in ('lora','viaodalibre') and row[0]['style']=='normal' and row[0]['language']=='bg')]
    draft=Path('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf')
    if draft.exists():
        font=TTFont(draft);data=draft.read_bytes();h=hb.Font(hb.Face(data));hb.ot_font_set_funcs(h);h.scale=(1000,1000)
        for features,label in [({},'Very Peri · округлая д'),({'ss07':True},'Very Peri · печатная д')]:
            def shape(text,features=features):
                b=hb.Buffer();b.add_str(text);b.guess_segment_properties();b.language='ru';hb.shape(h,b,features)
                return [(font.getGlyphName(g.codepoint),p.x_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]
            name=shape('д')[0][0];p=BoundsPen(font.getGlyphSet());font.getGlyphSet()[name].draw(p)
            r=dict(family=label,style='normal',language='ru',features=features,x_height=510,descender_per_x=max(0,-p.bounds[1]/510))
            focused.append((r,font,shape))
    draw_plate('de_reference_shortlist.svg',focused,'Округлая д · варианты для нашего направления','Четыре реальных примера и две формы Very Peri. Сравнивайте чашу, переход в стойку и размах хвоста.')
    manifest={'date':'2026-10-17','google_fonts_commit':COMMIT,'normalization':'uniform scaling to Latin x outline top; each font retains width/height ratio; no outline edits','variable_instances':'wght400, opsz48 where available, other axes default','shaping':'HarfBuzz, cyrl; ru or explicitly labeled bg; GSUB applied','source_scope':'Google Fonts OFL families with U+0434; comparison sample, not a census','regular_ru_rows':len(regular),'other_rows':len(alternate),'regional_and_sets_rows':len(regional),'italic_rows':len(italic),'smallcaps_excluded_from_plates':sum(smallcaps(row) for row in alternate),'references':[r[0] for r in rows]}
    Path('data/de-reference-audit.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'regular':len(regular),'other':len(alternate),'references':[(r[0]['family'],r[0]['style'],r[0]['language'],r[0]['features'],r[0]['glyph_name']) for r in rows]},ensure_ascii=False))
if __name__=='__main__':main()
