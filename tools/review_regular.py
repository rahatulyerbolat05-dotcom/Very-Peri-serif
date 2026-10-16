#!/usr/bin/env python3
"""Review all installed Cyrillic forms and alternatives, with raster diagnostics.
The scanline statistic is a warning aid, not a universal optical-weight score.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_draft_font import CHARS,TTF,OUT
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from alphabet_sheet import canvas,text,PathPatch,MplPen
from matplotlib.transforms import Affine2D
import matplotlib.pyplot as plt
from audit_author_glyphs import inspect

BUILD=Path('build/optical-review')
BASELINE='66f1909'

def weight(ch,font,height):
    im=Image.new('L',(1800,1600));ImageDraw.Draw(im).text((400,1100),ch,font=font,fill=255,anchor='ls')
    arr=np.asarray(im)>127;rows=[]
    for y in np.linspace(height*.25,height*.75,51):
        edges=np.diff(np.r_[False,arr[1100-round(y)],False].astype(int))
        widths=np.where(edges==-1)[0]-np.where(edges==1)[0];widths=widths[(widths>=10)&(widths<=130)]
        if len(widths):rows.append(float(max(widths)))
    return float(np.median(rows))

def main():
    BUILD.mkdir(exist_ok=True,parents=True)
    old=BUILD/'before.ttf';old.write_bytes(subprocess.check_output(['git','show',BASELINE+':'+str(TTF)]))
    before=ImageFont.truetype(str(old),1000);after=ImageFont.truetype(str(TTF),1000)
    font=TTFont(TTF);gs=font.getGlyphSet();manifest=json.loads((OUT/'build-manifest.json').read_text());records=manifest['glyph_records']
    rows=[];audits=[]
    for ch in CHARS:
        h=720 if ch.isupper() else 510
        rows.append({'character':ch,'scanline_main_run_before':weight(ch,before,h),'scanline_main_run_after':weight(ch,after,h)})
    for name,r in records.items():
        if not r['path'].endswith('.glif'):continue
        audit=inspect(r['character'],dict(path=r['path'],role='installed',glif_sha256=r['sha256']))
        assert audit['matches_registered_hash'] and audit['open_contours']==0
        audits.append({'name':name,'path':r['path'],'open_contours':audit['open_contours'],
                       'non_simple_sampled_rings':[x['contour'] for x in audit['ring_diagnostics'] if not x['simple_approx']],
                       'contours':audit['normalized_contours']})
    def draw(ax,name,x,y,size,fontgs=gs,color='#272333'):
        b=BoundsPen(fontgs);fontgs[name].draw(b)
        if not b.bounds:return
        pen=MplPen(fontgs);fontgs[name].draw(pen);xmin,_,xmax,_=b.bounds
        ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none',transform=Affine2D().scale(size/1000,-size/1000).translate(x-(xmin+xmax)*size/2000,y)+ax.transData))
    fig,ax=canvas(2200,2800);text(ax,40,30,'Оптическая проверка · все 84 буквы и устанавливаемые альтернативы',30)
    for i,ch in enumerate(CHARS):
        x=85+(i%14)*155;y=235+(i//14)*210
        draw(ax,f'uni{ord(ch):04X}',x,y,145);text(ax,x,y+40,ch,18,ha='center')
    alts=[n for n,r in records.items() if r['character'] in CHARS and n!=f'uni{ord(r["character"]):04X}']
    text(ax,40,1450,'Контекстные и стилистические формы, включая прежние хвосты',26)
    for i,n in enumerate(alts):
        x=85+(i%14)*155;y=1665+(i//14)*225
        draw(ax,n,x,y,140);text(ax,x,y+35,n.replace('uni',''),11,ha='center')
    text(ax,40,2140,'Новые текстовые знаки · пробелы U+2009 / U+202F имеют ширину200',25)
    for i,ch in enumerate('№₽₴ʼ‑◌'):
        draw(ax,f'uni{ord(ch):04X}',180+i*330,2430,225);text(ax,180+i*330,2480,f'U+{ord(ch):04X}',18,ha='center')
    text(ax,40,2620,'Срезы толщины — диагностика; форма, контраст и число штрихов влияют на оптический вес.',22)
    text(ax,40,2670,'Кернинг сохранён без изменений. Окончательное утверждение форм — после просмотра в макете.',22)
    fig.savefig('docs/img/optical_review.svg');fig.savefig(BUILD/'all-forms.png',dpi=90);plt.close(fig)
    # Compare changed forms at identical scale, then the PDF's text at text sizes.
    fig,ax=canvas(2000,1650);text(ax,40,30,'Уточнение развилки и веса · сверху 1.002, снизу 1.003',28)
    oldgs=TTFont(old).getGlyphSet()
    for i,ch in enumerate('үұЗзч'):
        x=200+i*380
        draw(ax,f'uni{ord(ch):04X}',x,425,340,oldgs,'#98918d');draw(ax,f'uni{ord(ch):04X}',x,880,340)
    from matplotlib.font_manager import FontProperties
    prop=FontProperties(fname=str(TTF))
    for i,size in enumerate((18,30,48)):
        ax.text(40,1040+i*160,'Өзгерте алмайтын заттарға алаңдаудың қажеті жоқ. Күн, гүл, үміт; ұлт, ұлы, құс.',fontproperties=prop,fontsize=size*72/100,color='#272333',va='top')
    ax.text(40,1530,'1\u2009000\u202f₸ · 2\u202f500 ₽ · 500 ₴ · № 12 · lʼart · по‑русски · ◌́',fontproperties=prop,fontsize=42*72/100,va='top')
    fig.savefig('docs/img/optical_changes.svg');fig.savefig(BUILD/'changes.png',dpi=90);plt.close(fig)
    result={'baseline_commit':BASELINE,'current_ttf_sha256':hashlib.sha256(TTF.read_bytes()).hexdigest(),
        'primary_forms_reviewed':len(CHARS),'installed_alternatives_reviewed':len(alts),'source_checks':audits,
        'weight_statistic':'Median of largest 10..130-unit horizontal ink runs at 51 body heights (25..75%); diagnostic only, not normal stroke thickness.',
        'primary_weight_scan':rows}
    Path('data/regular-refinement/optical-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Reviewed',len(CHARS),'primary forms,',len(alts),'alternatives,',len(audits),'GLIF sources; ring candidates:',[(x['name'],x['non_simple_sampled_rings']) for x in audits if x['non_simple_sampled_rings']])

if __name__=='__main__':main()
