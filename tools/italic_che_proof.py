#!/usr/bin/env python3
"""Author-reported che step: final glyphs, enlarged transition, CFF and words."""
import datetime
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from fontTools.ttLib import TTFont
from fix_italic_che import BASELINE
from curve_finish_proof import crop,BG
from family_proof import Proof,page


def main():
    cfg=json.loads(Path('data/params.json').read_text())['regular_release'];version=cfg['version']
    out=Path('build/che-fix');out.mkdir(exist_ok=True);old=out/'Italic-1.111.ttf'
    old.write_bytes(subprocess.check_output(['git','show',BASELINE+':fonts/ttf/VeryPeriSerif-Italic.ttf']))
    paths=[old,Path('build/release/VeryPeriSerif-Italic.ttf')];fonts=[TTFont(p) for p in paths]
    date=datetime.datetime.fromisoformat(cfg['date']).replace(tzinfo=datetime.timezone.utc)
    dest=Path(f'docs/specimen/VeryPeriSerif-Che-{version}.pdf')
    with PdfPages(dest,metadata={'Title':'Very Peri Serif '+version+' — Italic che seam repair','CreationDate':date,'ModDate':date}) as pdf:
        fig,axs=plt.subplots(1,4,figsize=(15,6),facecolor=BG)
        for k,font in enumerate(fonts):
            crop(axs[2*k],font,'uni0447',(230,255),'1.111' if not k else version,350)
            crop(axs[2*k+1],font,'uni0447',(165,300),'1.111: step' if not k else version+': convex arc',65)
        fig.tight_layout();pdf.savefig(fig);fig.savefig(f'docs/img/che-{version}.svg',metadata={'Date':cfg['date']})
        fig.savefig(out/'final-che.png',dpi=115);plt.close(fig)
        fig,ax=page('Italic · ч · 1.111 / '+version,1400,1380)
        for k,p in enumerate(paths):
            proof=Proof(p);y=170+k*610;ax.text(45,y-45,'1.111' if not k else version,fontsize=16,color='#69656a')
            for j,text in enumerate(('чаша · чистота · вечер','ночь · мяч · чувство','ча · че · чи · чо · чу','ч · ч́ · Чч')):
                end=proof.line(ax,text,45,y+90+j*115,104)
                assert end<1355,('Word proof overflow',text,end)
        pdf.savefig(fig);fig.savefig(out/'final-words.png',dpi=100);plt.close(fig)
        choices=[Path('build/release/VeryPeriSerif-Italic.otf'),Path('fonts/otf/VeryPeriSerif-Italic.otf')]
        candidates=[TTFont(p) for p in choices if p.exists()]
        candidates=[f for f in candidates if f['name'].getDebugName(5)=='Version '+version]
        if candidates:
            fig,axs=plt.subplots(1,2,figsize=(11,6),facecolor=BG)
            for j,f in enumerate((fonts[1],candidates[0])):crop(axs[j],f,'uni0447',(165,300),'TTF' if not j else 'Serialized CFF',65)
            fig.tight_layout();pdf.savefig(fig);fig.savefig(out/'final-formats.png',dpi=110);plt.close(fig)
    print(dest)


if __name__=='__main__':main()
