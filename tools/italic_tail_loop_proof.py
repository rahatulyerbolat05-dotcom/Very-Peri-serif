#!/usr/bin/env python3
"""First contour-repair batch: final glyphs, actual CFF, exact crossings and words."""
import datetime
import io
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from fontTools.ttLib import TTFont
import numpy as np
from contour_geometry import read_outline
from tail_join_geometry import NAMES, TIPS, join_pair, nonendpoint_intersections
from fix_italic_tail_joins import BASELINE
from curve_finish_proof import crop, BG
from family_proof import Proof, page


def main():
    cfg = json.loads(Path('data/params.json').read_text())['regular_release']; version = cfg['version']
    out = Path('build/tail-joins'); out.mkdir(exist_ok=True)
    old_path = out/'Italic-1.110.ttf'
    old_path.write_bytes(subprocess.check_output(['git', 'show', BASELINE+':fonts/ttf/VeryPeriSerif-Italic.ttf']))
    paths = [old_path, Path('build/release/VeryPeriSerif-Italic.ttf')]
    fonts = [TTFont(p) for p in paths]
    date = datetime.datetime.fromisoformat(cfg['date']).replace(tzinfo=datetime.timezone.utc)
    pdf_path = Path(f'docs/specimen/VeryPeriSerif-Tail-Joins-{version}.pdf')
    with PdfPages(pdf_path, metadata={'Title': 'Very Peri Serif '+version+' — exact tail-join loop repairs',
                                     'CreationDate': date, 'ModDate': date}) as pdf:
        fig, axs = plt.subplots(3, 4, figsize=(15, 12), facecolor=BG)
        for row, name in enumerate(NAMES):
            px = TIPS[name]
            for k in (0, 1):
                crop(axs[row, 2*k], fonts[k], name, (px-12, -35), name+' · '+('1.110' if k == 0 else version), 130)
                crop(axs[row, 2*k+1], fonts[k], name, (px-1, -1), 'join · '+('1.110' if k == 0 else version), 5)
        fig.suptitle('Pointed tail style retained; only the crossing loop is removed', fontsize=15)
        fig.tight_layout(rect=(0, 0, 1, .97)); pdf.savefig(fig)
        fig.savefig(f'docs/img/tail-joins-{version}.svg', metadata={'Date': cfg['date']})
        fig.savefig(out/'final-joins.png', dpi=110); plt.close(fig)
        fig, axs = plt.subplots(3, 4, figsize=(15, 11), facecolor=BG)
        for row, name in enumerate(NAMES):
            for k, f in enumerate(fonts):
                contour = read_outline(f, name)[0][0]; i, j = join_pair(contour, name, bool(k))
                ax = axs[row, 2*k]; ax.set_facecolor(BG)
                for index, color in ((i, '#326fac'), (j, '#d18426')):
                    s = contour[index]; points = s.evaluate(np.linspace(0, 1, 250))
                    ax.plot(points[:, 0], points[:, 1], color=color, lw=1.2)
                hits = nonendpoint_intersections(contour[i], contour[j])
                for hit in hits: ax.plot(*hit['xy'], 'o', color='#c33e3e', ms=4)
                px = TIPS[name]; ax.set_xlim(px-3, px+1); ax.set_ylim(-2, 1)
                ax.set_aspect('equal'); ax.set_title(('1.110: crossing' if k == 0 else version+': separate branches'), fontsize=10)
                ax.tick_params(labelsize=7)
                crop(axs[row, 2*k+1], f, name, (px-1, -1), name+' · full glyph', 600)
                g = f['glyf'][name]; axs[row, 2*k+1].set_xlim(g.xMin-20, g.xMax+20); axs[row, 2*k+1].set_ylim(g.yMin-20, g.yMax+20)
        fig.tight_layout(); pdf.savefig(fig); fig.savefig(out/'final-crossings.png', dpi=110); plt.close(fig)
        fig, ax = page('Italic · 1.110 / '+version+' · Russian and Kazakh words', 1450, 1500)
        for k, p in enumerate(paths):
            proof = Proof(p); y = 160+k*670
            ax.text(45, y-45, '1.110' if k == 0 else version, fontsize=16, color='#69656a')
            for j, text in enumerate(('улица · птица · площадь', 'помощь · щука · вещица',
                                      'жаңбыр · теңіз · көңіл', 'кеңістік · жаңа · аң', 'ц · щ · ң · ц́ · щ́ · ң́')):
                end = proof.line(ax, text, 45, y+90+j*105, 94)
                assert end < 1405, ('Word proof overflow', text, end)
        pdf.savefig(fig); fig.savefig(out/'final-words.png', dpi=100); plt.close(fig)
        # Optional CFF comparison when run after package_release or a preview export.
        candidates = (Path('build/release/VeryPeriSerif-Italic.otf'), Path('fonts/otf/VeryPeriSerif-Italic.otf'))
        cff = [TTFont(p) for p in candidates if p.exists()]
        cff = [f for f in cff if f['name'].getDebugName(5) == 'Version '+version]
        if cff:
            f = cff[0]
            fig, axs = plt.subplots(3, 2, figsize=(10, 12), facecolor=BG)
            for row, name in enumerate(NAMES):
                for col, font in enumerate((fonts[1], f)):
                    crop(axs[row, col], font, name, (TIPS[name]-1, -1), name+' · '+('TTF' if col == 0 else 'serialized CFF'), 5)
            fig.tight_layout(); pdf.savefig(fig); fig.savefig(out/'final-formats.png', dpi=110); plt.close(fig)
    print(pdf_path)


if __name__ == '__main__': main()
