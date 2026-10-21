#!/usr/bin/env python3
"""Before/after enlargements of every reviewed suspect, from final font files."""
import datetime,json,math,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.backends.backend_pdf import PdfPages
from fontTools.ttLib import TTFont
from alphabet_sheet import MplPen
from family_proof import Proof,page

BG='#f5f2ec';INK='#272333'


def crop(ax,font,name,xy,label,radius=65):
    gs=font.getGlyphSet();pen=MplPen(gs);gs[name].draw(pen)
    ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none'))
    x,y=xy;ax.set_xlim(x-radius,x+radius);ax.set_ylim(y-radius,y+radius)
    ax.set_aspect('equal');ax.axis('off');ax.set_facecolor(BG)
    ax.set_title(label,fontsize=9,color='#69656a')


def main():
    config=json.loads(Path('data/params.json').read_text())['regular_release']
    ver=config['version'];manifest=json.loads(Path('data/curve-finish/manifest.json').read_text())
    base=manifest['baseline_commit'];out=Path('build/curve-audit');out.mkdir(parents=True,exist_ok=True)
    fonts={};paths={}
    for style in ('Regular','Italic'):
        previous=out/f'{style}-1.107.ttf'
        previous.write_bytes(subprocess.check_output(['git','show',f'{base}:fonts/ttf/VeryPeriSerif-{style}.ttf']))
        paths[style,0]=previous;paths[style,1]=Path(f'build/release/VeryPeriSerif-{style}.ttf')
        for k in (0,1):fonts[style,k]=TTFont(paths[style,k])
    spots=json.loads(Path('data/curve-finish/review-spots.json').read_text())
    date=datetime.datetime.fromisoformat(config['date']).replace(tzinfo=datetime.timezone.utc)
    target=Path(f'docs/specimen/VeryPeriSerif-Curve-Review-{ver}.pdf')
    with PdfPages(target,metadata={'Title':'Very Peri Serif '+ver+' curve review','Author':'Very Peri Serif project','CreationDate':date,'ModDate':date}) as pdf:
        selected={'Regular':[(19, 'м · foot'),(22,'м · foot'),(25,'т · right foot'),(8,'ж · shoulder'),(33,'ы · serif'),(38,'Қ · foot'),(56,'к · contextual head'),(44,'prime · end')],
                  'Italic':[(119,'м · upper join'),(120,'м · upper join'),(86,'И · foot'),(104,'ш · counter'),(123,'ү · stem'),(126,'б · shoulder'),(130,'т ss03 · terminal'),(142,'dagger · bar')]}
        for style,items in selected.items():
            fig,axs=plt.subplots(4,4,figsize=(14,14),facecolor=BG)
            for j,(index,label) in enumerate(items):
                r=next(x for x in spots if x['id']==index)
                for k in (0,1):crop(axs[j//2,(j%2)*2+k],fonts[style,k],r['glyph'],r['xy'],label+' · '+('1.107' if k==0 else ver))
            fig.tight_layout();pdf.savefig(fig)
            fig.savefig(f'docs/img/curve-review-{style.lower()}-{ver}.svg',metadata={'Date':config['date']})
            fig.savefig(out/f'featured-{style}.png',dpi=120);plt.close(fig)
        for pg in range(math.ceil(len(spots)/8)):
            fig,axs=plt.subplots(4,4,figsize=(14,14),facecolor=BG)
            for j,r in enumerate(spots[pg*8:(pg+1)*8]):
                for k in (0,1):crop(axs[j//2,(j%2)*2+k],fonts[r['style'],k],r['glyph'],r['xy'],f"#{r['id']} {r['style']} {r['glyph']} · "+('1.107' if k==0 else ver))
            for ax in axs.flat:
                if not ax.has_data():ax.axis('off')
            fig.tight_layout();pdf.savefig(fig);fig.savefig(out/f'final-comparison-{pg+1:02}.png',dpi=90);plt.close(fig)
        for style in ('Regular','Italic'):
            fig,ax=page(style+' · 1.107 / '+ver+' · curves in words',1500,1300)
            for k in (0,1):
                p=Proof(paths[style,k]);y=170+k*600;ax.text(45,y-40,'1.107' if k==0 else ver,fontsize=15,color='#69656a')
                for j,text in enumerate(['мир · тишина · жизнь · улыбка','Иллюзия · Шёпот · Жаңбыр','үкі · ұлт · қазақ · ғылым','«Слова» · 12 500 ₸ · † ‡ ≈ ′ ″']):
                    end=p.line(ax,text,45,y+90+j*112,78)
                    assert end<1455,(style,text,'proof overflow',end)
            pdf.savefig(fig);fig.savefig(out/f'words-{style}.png',dpi=110);plt.close(fig)
    print(target)


if __name__=='__main__':main()
