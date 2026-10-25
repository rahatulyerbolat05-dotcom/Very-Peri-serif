#!/usr/bin/env python3
"""The actual released ss10 feature, with defaults and real shaped words."""
import datetime
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from family_proof import Proof,page


def main():
    cfg=json.loads(Path('data/params.json').read_text())['regular_release'];v=cfg['version']
    proof=Proof('build/release/VeryPeriSerif-Italic.ttf')
    fig,ax=page(f'Very Peri Serif {v} · Italic · ss10',1400,1200)
    ax.text(60,110,'Default',fontsize=15,color='#69656a')
    ax.text(700,110,'ss10',fontsize=15,color='#69656a')
    proof.line(ax,'л',60,450,560)
    proof.line(ax,'л',700,450,560,{'ss10':1})
    for k,mode in enumerate(({}, {'ss10':1})):
        y=630+k*275
        ax.text(60,y-70,'Default' if k==0 else 'ss10',fontsize=15,color='#69656a')
        for j,text in enumerate(('лилия · аллея · люблю · луна','гүл · әлем · ләззат · л́ · лл')):
            end=proof.line(ax,text,60,y+j*115,103,mode)
            assert end<1340,(text,end)
    fig.savefig(f'docs/img/el-alternate-{v}.svg',metadata={'Date':cfg['date']})
    fig.savefig('build/el-ss10-proof.png',dpi=110)
    moment=datetime.datetime.fromisoformat(cfg['date']).replace(tzinfo=datetime.timezone.utc)
    dest=Path(f'docs/specimen/VeryPeriSerif-El-Alternate-{v}.pdf')
    with PdfPages(dest,metadata={'Title':f'Very Peri Serif {v} — ss10', 'CreationDate':moment,'ModDate':moment}) as pdf:
        pdf.savefig(fig)
    plt.close(fig);print(dest)


if __name__=='__main__':main()
