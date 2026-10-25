#!/usr/bin/env python3
"""Every reduced glyph: coincident before/after paths and stored points."""
import datetime,io,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import PathPatch
from fontTools.ttLib import TTFont
from alphabet_sheet import MplPen
from family_proof import Proof,page


def main():
    m=json.loads(Path('data/node-reduction/manifest.json').read_text())
    config=json.loads(Path('data/params.json').read_text())['regular_release']
    v=config['version']  # never overwrite the historical 1.113 specimen
    dest=Path('build/finalize');dest.mkdir(exist_ok=True)
    date=datetime.datetime.fromisoformat(config['date']).replace(tzinfo=datetime.timezone.utc)
    target=Path(f'docs/specimen/VeryPeriSerif-Node-Reduction-{v}.pdf')
    with PdfPages(target,metadata={'Title':'Very Peri Serif '+v+' lossless point reduction','Author':config['cyrillic_author'],'CreationDate':date,'ModDate':date}) as pdf:
        for style,row in m['styles'].items():
            raw=subprocess.check_output(['git','show',m['baseline_commit']+f':fonts/ttf/VeryPeriSerif-{style}.ttf'])
            old=TTFont(io.BytesIO(raw));new=TTFont(f'build/release/VeryPeriSerif-{style}.ttf')
            names=list(row['glyphs'])
            for pg in range((len(names)+7)//8):
                fig,axs=plt.subplots(2,4,figsize=(16,9),facecolor='#f5f2ec')
                for ax,name in zip(axs.flat,names[pg*8:(pg+1)*8]):
                    for f,color,alpha in ((old,'#dd5149',.6),(new,'#257b75',.65)):
                        gs=f.getGlyphSet();pen=MplPen(gs);gs[name].draw(pen)
                        ax.add_patch(PathPatch(pen.result(),facecolor=color,alpha=alpha,edgecolor='none'))
                        xy=f['glyf'][name].coordinates
                        ax.scatter([p[0] for p in xy],[p[1] for p in xy],s=3,color=color)
                    g=new['glyf'][name];pad=35
                    ax.set_xlim(g.xMin-pad,g.xMax+pad);ax.set_ylim(g.yMin-pad,g.yMax+pad)
                    counts=row['glyphs'][name];ax.set_title(f"{name} · {counts['points_before']} → {counts['points_after']}",fontsize=10)
                    ax.set_aspect('equal');ax.axis('off')
                for ax in axs.flat:
                    if not ax.has_data():ax.axis('off')
                fig.suptitle(f'{style} · 1.112 / {v} · exact coincident paths',fontsize=15)
                fig.subplots_adjust(left=.035,right=.965,bottom=.07,top=.87,wspace=.28,hspace=.38)
                pdf.savefig(fig);fig.savefig(dest/f'nodes-{style}-{pg+1}.png',dpi=110);plt.close(fig)
        fig,ax=page(v+' · frozen base glyphs · Russian and Kazakh',1500,1450)
        for k,style in enumerate(('Regular','Italic')):
            proof=Proof(f'build/release/VeryPeriSerif-{style}.ttf');y=140+k*650
            ax.text(45,y-40,style,fontsize=16,color='#69656a')
            for j,text in enumerate(('Жизнь · яркая · чаша · дождь','Қазақ тілі · үміт · ұлы · ғылым','Шёпот · ширина · тишина · № 57','Әә · Үү · Ұұ · Ңң · Өө · Ғғ · ₸','ff fi ffi · 12 500,00 ₸')):
                end=proof.line(ax,text,45,y+85+j*105,84)
                assert end<1455,(style,text,end)
        pdf.savefig(fig);fig.savefig(dest/'final-words.png',dpi=110);plt.close(fig)
    print(target)


if __name__=='__main__':main()
