#!/usr/bin/env python3
"""Small printable sample of the queue, not a substitute for the complete atlas."""
import datetime
import hashlib
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import PathPatch
import numpy as np
from fontTools.ttLib import TTFont
from alphabet_sheet import MplPen
from contour_geometry import read_outline, sample_contour
from contour_audit import detector_hash, published_version

BG, INK = '#f5f2ec', '#272333'


def main():
    version = published_version()
    data = json.loads(gzip.decompress(Path(f'docs/qa/contour-audit-{version}.json.gz').read_bytes()))
    assert data['detector_sha256'] == detector_hash(), 'Audit detector changed: rerun the scan'
    fonts = {}
    for key, row in data['fonts'].items():
        p = Path(row['file'])
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256'], 'Stale audit: '+key
        fonts[key] = TTFont(p)
    selected = {}
    for style in ('Regular', 'Italic'):
        items = []; used = set()
        for case in data['cases']:
            if case['style'] != style: continue
            uses = data['shapes'][case['geometry_sha256']]['uses']
            match = [(key, name) for key, name in uses if key == style+'/TTF'
                     and any('\u0400' <= c <= '\u052f' for c in data['fonts'][key]['glyphs'][name]['characters'])]
            if not match: continue
            # Spread the compact overview across glyphs. The HTML keeps all sites.
            key, name = match[0]
            if name in used: continue
            used.add(name); items.append((case, key, name))
            if len(items) == 12: break
        selected[style] = items
    target = Path(f'docs/specimen/VeryPeriSerif-Contour-Audit-{version}.pdf')
    date = datetime.datetime.fromisoformat(json.loads(Path('data/params.json').read_text())['regular_release']['date']).replace(tzinfo=datetime.timezone.utc)
    with PdfPages(target, metadata={'Title': 'Very Peri Serif — diagnostic candidates, not accepted defects',
                                    'CreationDate': date, 'ModDate': date}) as pdf:
        for style, items in selected.items():
            for page in range(0, len(items), 4):
                fig, axs = plt.subplots(4, 3, figsize=(14, 15), facecolor=BG)
                fig.suptitle(style+' · '+version+' · candidates awaiting review', fontsize=17)
                for row, (case, key, name) in enumerate(items[page:page+4]):
                    f = fonts[key]; gs = f.getGlyphSet(); pen = MplPen(gs); gs[name].draw(pen)
                    contours, closed = read_outline(f, name)
                    allpts = np.vstack([s.points for c in contours for s in c]); origin = allpts.min(axis=0)
                    xy = np.asarray(case['xy'])+origin
                    wave = next((e for e in case['evidence'] if e['kind'] == 'curvature_wave'), None)
                    radius = max(24, min(100, wave['metrics']['span']*.7 if wave else 45))
                    for col in (0, 1):
                        ax = axs[row, col]; ax.set_facecolor(BG)
                        ax.add_patch(PathPatch(pen.result(), facecolor=INK, edgecolor='none'))
                        ax.plot(*xy, 'o', ms=4, mfc='none', mec='#c94e3b')
                        if col == 0:
                            lo, hi = allpts.min(axis=0)-20, allpts.max(axis=0)+20
                            ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1])
                        else:
                            ax.set_xlim(xy[0]-radius, xy[0]+radius); ax.set_ylim(xy[1]-radius, xy[1]+radius)
                            for seg in contours[case['contour']]:
                                p = seg.points
                                if np.min(np.linalg.norm(p-xy, axis=1)) > 3*radius: continue
                                ax.plot(p[:, 0], p[:, 1], '.-', color='#5283b0', lw=.5, ms=2)
                                ts = np.linspace(.02, .98, 20); q = seg.evaluate(ts); v = seg.evaluate(ts, 1); k = seg.curvature(ts)
                                speed = np.linalg.norm(v, axis=1)
                                for point, tangent, curvature, sp in zip(q, v, k, speed):
                                    if not np.isfinite(curvature) or sp < 1e-9: continue
                                    end = point+np.array([-tangent[1], tangent[0]])/sp*np.clip(curvature*400, -28, 28)
                                    ax.plot([point[0], end[0]], [point[1], end[1]], color='#479b76', lw=.5)
                        ax.set_aspect('equal'); ax.axis('off')
                        if col == 0:
                            chars = ''.join(data['fonts'][key]['glyphs'][name]['characters'])
                            ax.set_title(chars+' · '+name+' · '+case['id'][:8], fontsize=10)
                    ax = axs[row, 2]; ax.set_facecolor(BG)
                    sample = sample_contour(contours[case['contour']]); length = sample['length']
                    distance = (sample['s']-case['s']+length/2) % length-length/2
                    ids = np.argsort(distance); good = np.abs(distance[ids]) <= 80
                    ax.plot(distance[ids][good], sample['k'][ids][good], color='#479b76', lw=1)
                    ax.axhline(0, color='#bcb3a6', lw=.6); ax.axvline(0, color='#c94e3b', lw=.7)
                    ax.set_title(' / '.join(case['kinds']), fontsize=9, wrap=True)
                    ax.set_xlabel('arc distance from signal, units'); ax.set_ylabel('curvature'); ax.tick_params(labelsize=8)
                fig.tight_layout(rect=(0, 0, 1, .97)); pdf.savefig(fig)
                if page == 0:
                    fig.savefig(f'docs/img/contour-audit-{style.lower()}-{version}.svg', metadata={'Date': date.date().isoformat()})
                    out = Path('build/contour-audit'); out.mkdir(exist_ok=True)
                    fig.savefig(out/f'{style}-overview.png', dpi=100)
                plt.close(fig)
    print(target)


if __name__ == '__main__': main()
