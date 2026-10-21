#!/usr/bin/env python3
"""Author-reported ya defects: compare the published 1.108 with final outputs."""
import datetime, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from curve_finish_proof import crop, BG
from family_proof import Proof, page
from check_ya_revision import BASELINE


def main():
    cfg = json.loads(Path('data/params.json').read_text())['regular_release']; version = cfg['version']
    out = Path('build/ya-recheck'); out.mkdir(exist_ok=True)
    date = datetime.datetime.fromisoformat(cfg['date']).replace(tzinfo=datetime.timezone.utc)
    pdfpath = Path(f'docs/specimen/VeryPeriSerif-Ya-{version}.pdf')
    with PdfPages(pdfpath, metadata={'Title': 'Very Peri Serif ya '+version, 'CreationDate': date, 'ModDate': date}) as pdf:
        for style in ('Regular', 'Italic'):
            previous = out/f'{style}-1.108.ttf'
            previous.write_bytes(subprocess.check_output(['git', 'show', f'{BASELINE}:fonts/ttf/VeryPeriSerif-{style}.ttf']))
            paths = [previous, Path(f'build/release/VeryPeriSerif-{style}.ttf')]
            fonts = [TTFont(p) for p in paths]
            regions = [((210, 260), 330, 'full'), ((230, 490), 100, 'upper bowl')] if style == 'Regular' else [((210, 260), 330, 'full'), ((276, 95), 45, 'stem/foot'), ((391, 176), 24, 'terminal')]
            fig, axs = plt.subplots(len(regions), 2, figsize=(10, 5*len(regions)), facecolor=BG)
            for row, (xy, radius, label) in enumerate(regions):
                for k in (0, 1): crop(axs[row, k], fonts[k], 'uni044F', xy, f'{style} {label} · '+('1.108' if k == 0 else version), radius)
            fig.tight_layout(); pdf.savefig(fig)
            fig.savefig(f'docs/img/ya-{style.lower()}-{version}.svg', metadata={'Date': cfg['date']})
            fig.savefig(out/f'{style}-final.png', dpi=110); plt.close(fig)
            fig, ax = page(style+' · я · 1.108 / '+version, 1200, 1100)
            for k in (0, 1):
                proof = Proof(paths[k]); y = 180+k*470
                ax.text(45, y-45, '1.108' if k == 0 else version, fontsize=16)
                for j, text in enumerate(('я · моя · яркая · земля', 'семья · друзья · история', 'яна · Яна · қиял')):
                    end = proof.line(ax, text, 45, y+80+j*112, 105)
                    assert end < 1155, ('proof overflow', style, text, end)
            pdf.savefig(fig); fig.savefig(out/f'{style}-words.png', dpi=100); plt.close(fig)
    print(pdfpath)


if __name__ == '__main__': main()
