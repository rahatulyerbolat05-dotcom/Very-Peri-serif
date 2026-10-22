#!/usr/bin/env python3
"""Before/after width and word proofs from the actual final Italic font."""
import datetime, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from curve_finish_proof import crop, BG
from family_proof import Proof, page
from check_ghe_width import BASELINE


def main():
    cfg = json.loads(Path('data/params.json').read_text())['regular_release']; version = cfg['version']
    out = Path('build/ghe-width'); out.mkdir(exist_ok=True)
    before = out/'Italic-1.109.ttf'
    before.write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:fonts/ttf/VeryPeriSerif-Italic.ttf']))
    paths = [before, Path('build/release/VeryPeriSerif-Italic.ttf')]; fonts = [TTFont(p) for p in paths]
    date = datetime.datetime.fromisoformat(cfg['date']).replace(tzinfo=datetime.timezone.utc)
    target = Path(f'docs/specimen/VeryPeriSerif-Ghe-{version}.pdf')
    with PdfPages(target, metadata={'Title': 'Very Peri Serif wider Italic ghe '+version, 'CreationDate': date, 'ModDate': date}) as pdf:
        fig, axs = plt.subplots(2, 4, figsize=(14, 10), facecolor=BG)
        regions = [('uni0433',(170,260),330,'г'),('uni0493',(170,260),330,'ғ'),
                   ('uni0433',(166,255),65,'stem'),('uni0433',(260,170),65,'exit')]
        for j, (name, xy, radius, label) in enumerate(regions):
            for k in (0,1): crop(axs[j//2, (j%2)*2+k], fonts[k], name, xy, label+' · '+('1.109' if k==0 else version), radius)
        fig.tight_layout(); pdf.savefig(fig)
        fig.savefig(f'docs/img/ghe-width-{version}.svg', metadata={'Date':cfg['date']})
        fig.savefig(out/'final-compare.png', dpi=110); plt.close(fig)
        for kind, texts in [('words',('глина · город · граница · книга','гора · дорога · игра · гроза','гүл · ертеңгі · ғылым · ағаш','ѓ · ғ́ · г · ғ')),
                            ('local',('глина · город','глина · город','глина · город'))]:
            fig, ax = page('Italic · г/ғ · 1.109 / '+version+' · '+kind, 1500, 1380)
            for k, path in enumerate(paths):
                proof = Proof(path); y = 150+k*640
                ax.text(45,y-45,'1.109' if k==0 else version,fontsize=16,color='#69656a')
                for j, text in enumerate(texts):
                    lang = ('ru','sr','ru')[j] if kind=='local' else 'ru'
                    features = {'ss04':True} if kind=='local' and j==2 else None
                    if kind=='local': ax.text(45,y+j*135,('Default','locl SRB','ss04')[j],fontsize=13,color='#69656a')
                    end = proof.line(ax,text,45,y+90+j*125,82,features=features,language=lang)
                    assert end<1455,('proof overflow',text,end)
            pdf.savefig(fig); fig.savefig(out/f'final-{kind}.png',dpi=100); plt.close(fig)
    print(target)


if __name__=='__main__': main()
