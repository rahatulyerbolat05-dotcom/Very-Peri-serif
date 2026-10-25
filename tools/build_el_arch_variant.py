#!/usr/bin/env python3
"""Build the author's arched lowercase л as a separately installable Italic.

The 1.113 release remains the baseline. Only uni043B, its metrics, mark
anchors and pairs are redesigned; the installable family has a unique name.
Run from the repository root: python3 -I tools/build_el_arch_variant.py --variant 2
"""
import argparse
import copy
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import ots
import uharfbuzz as hb
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import readGlyphFromString
import optical_kerning as OK
import ttf2otf
from build_draft_font import native_kern
from contour_geometry import read_outline, inspect_outline
from family_proof import Proof, page

NAME = 'uni043B'
BASELINE = 'v1.113'
FAMILY = 'Very Peri Serif El Arch 1'
PS_NAME = 'VeryPeriSerifElArch1-Italic'
DATE = '2026-10-26'
OUT = Path('build/el-arch')
SOURCE = Path('data/italic-el-arch/uni043B.glif')
MANIFEST = SOURCE.with_name('manifest.json')
QA = Path('docs/qa/el-arch-1.json')
ZIP = Path('dist/VeryPeriSerif-ElArch1.zip')
VARIANT = 1
LABEL = 'El Arch 1'
BOTTOM_ANCHOR = 190


def configure_variant(number):
    global VARIANT, LABEL, FAMILY, PS_NAME, OUT, SOURCE, MANIFEST, QA, ZIP, BOTTOM_ANCHOR
    VARIANT = number
    LABEL = f'El Arch {number}'
    FAMILY = 'Very Peri Serif '+LABEL
    PS_NAME = f'VeryPeriSerifElArch{number}-Italic'
    suffix = '' if number == 1 else f'-{number}'
    OUT = Path('build/el-arch'+suffix)
    SOURCE = Path('data/italic-el-arch'+suffix+'/uni043B.glif')
    MANIFEST = SOURCE.with_name('manifest.json')
    QA = Path(f'docs/qa/el-arch-{number}.json')
    ZIP = Path(f'dist/VeryPeriSerif-ElArch{number}.zip')
    BOTTOM_ANCHOR = 190 if number == 1 else 220


def baseline(fmt):
    folder = 'webfonts' if fmt == 'woff2' else fmt
    return subprocess.check_output(['git', 'show',
        f'{BASELINE}:fonts/{folder}/VeryPeriSerif-Italic.{fmt}'])


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def kern_lookup(font, name=NAME):
    """Append only л pairs; every existing lookup and script remains intact."""
    profiles = OK.profiles(font)
    cm = font.getBestCmap()
    lower = 'аеёиопрстух'
    targets = {}
    for label, a, b, high in (
            ('ll', lower, lower, 510),
            ('Ul', 'АВЕЁКМНОРСТХ', lower, 510),
            ('lU', lower, 'АВЕЁКМНОРСТХ', 510)):
        values = []
        for ca in a:
            for cb in b:
                na, nb = cm[ord(ca)], cm[ord(cb)]
                g, valid = OK.gap_profile(profiles[na], profiles[nb])
                v = OK.optical(g, valid, high)
                if v is not None:
                    values.append(v + native_kern(font, na, nb))
        targets[label] = float(np.mean(values))
    chars = {n: chr(cp) for cp, n in cm.items() if not 0xE000 <= cp <= 0xF8FF}
    for n in profiles:
        if n not in chars:
            chars[n] = chars.get(n.split('.')[0], 'a')
    rows, corrections = [], {}
    pairs = {(name, n) for n in profiles} | {(n, name) for n in profiles}
    for a, b in sorted(pairs):
        ca, cb = chars[a], chars[b]
        g, valid = OK.gap_profile(profiles[a], profiles[b])
        if not valid.any():
            continue
        current = native_kern(font, a, b)
        optical = OK.optical(g, valid, 510)
        clearance = 20 if ca.isalpha() and cb.isalpha() else 5
        label = ('l' if ca.islower() else 'U') + ('l' if cb.islower() else 'U')
        adjustment = 0
        if clearance == 20 and optical is not None:
            delta = targets[label] - (optical + current)
            adjustment = max(-70, min(40, delta * .8)) if abs(delta) >= 24 else 0
        total = max(current + round(adjustment / 2) * 2,
                    math.ceil(clearance - float(g[valid].min())))
        if total != current:
            corrections[a, b] = int(total - current)
        rows.append({'left': a, 'right': b, 'kern': total,
                     'minimum_clearance': float(g[valid].min()) + total,
                     'required_clearance': clearance})
    assert corrections
    fea = ('languagesystem DFLT dflt; languagesystem latn dflt; '
           'languagesystem cyrl dflt; feature kern { lookupflag IgnoreMarks;\n')
    fea += '\n'.join(f'pos {a} {b} {v};' for (a, b), v in corrections.items())
    fea += '\n} kern;'
    extra = copy.deepcopy(font)
    for tag in ('GSUB', 'GPOS', 'GDEF'):
        del extra[tag]
    addOpenTypeFeaturesFromString(extra, fea)
    table = font['GPOS'].table
    offset = len(table.LookupList.Lookup)
    table.LookupList.Lookup.extend(extra['GPOS'].table.LookupList.Lookup)
    table.LookupList.LookupCount = len(table.LookupList.Lookup)
    indices = list(range(offset, table.LookupList.LookupCount))
    # All existing language systems refer to these same kern feature records.
    for record in table.FeatureList.FeatureRecord:
        if record.FeatureTag == 'kern':
            record.Feature.LookupListIndex.extend(indices)
            record.Feature.LookupCount = len(record.Feature.LookupListIndex)
    return rows, corrections, offset


def anchors(font):
    """Centre marks on the new arch/stem, preserving their baseline heights."""
    changes = []
    for li, lookup in enumerate(font['GPOS'].table.LookupList.Lookup):
        if lookup.LookupType != 4:
            continue
        for si, sub in enumerate(lookup.SubTable):
            if NAME not in sub.BaseCoverage.glyphs:
                continue
            index = sub.BaseCoverage.glyphs.index(NAME)
            for ai, anchor in enumerate(sub.BaseArray.BaseRecord[index].BaseAnchor):
                if anchor is None:
                    continue
                old = anchor.XCoordinate
                # Top: halfway between the two crown extrema, with the native
                # italic offset to the accent baseline. Bottom: flat foot centre.
                new = 259 if anchor.YCoordinate > 0 else BOTTOM_ANCHOR
                anchor.XCoordinate = new
                changes.append([li, si, index, ai, old, new])
    return changes


def shape(raw, text):
    f = hb.Font(hb.Face(raw))
    b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); b.language = 'ru'
    hb.shape(f, b)
    return [(g.codepoint, p.x_advance, p.x_offset, p.y_offset)
            for g, p in zip(b.glyph_infos, b.glyph_positions)]


def close_cff_exactly(ttf_path, otf_path):
    """Quantize absolute controls to CFF 16.16 before computing relative deltas.

    Independently rounded relative thirds accumulated a 0.00006-unit closure
    segment. Absolute-grid controls telescope exactly at every on-curve point.
    This changes only the new el; all accepted 1.113 programs remain intact.
    """
    ttf = TTFont(ttf_path); otf = TTFont(otf_path); otf.recalcTimestamp = False
    gs = ttf.getGlyphSet()
    pen = T2CharStringPen(ttf['hmtx'][NAME][0], gs, roundTolerance=0)
    pen.round = lambda value: round(value * 65536) / 65536
    gs[NAME].draw(ReverseContourPen(pen))
    cs = otf['CFF '].cff.topDictIndex[0].CharStrings
    old = cs[NAME]
    cs[NAME] = pen.getCharString(private=old.private, globalSubrs=old.globalSubrs)
    otf.save(otf_path)


def verify(old_raw, paths, anchor_changes, offset, rows):
    old = TTFont(io.BytesIO(old_raw))
    checks = 0
    def ck(ok, label):
        nonlocal checks
        assert ok, label
        checks += 1
    raw = paths['ttf'].read_bytes(); new = TTFont(io.BytesIO(raw))
    ck(new.getGlyphOrder() == old.getGlyphOrder(), 'same glyph order')
    changed = []
    for name in old.getGlyphOrder():
        same = old['glyf'][name].compile(old['glyf']) == new['glyf'][name].compile(new['glyf'])
        if not same:
            changed.append(name)
        ck(same or name == NAME, ('unexpected outline/hint change', name))
        ck(name == NAME or old['hmtx'][name] == new['hmtx'][name], ('unexpected metric change', name))
    ck(changed == [NAME], 'only lowercase Cyrillic el redesigned')
    if VARIANT == 2:
        # Independently reconstruct the declared graft from both frozen donors.
        # No broad optical tolerance can hide a changed arch or mangled exit.
        from polish_outlines import contours_of
        pen = TTGlyphPointPen(None)
        readGlyphFromString(Path('data/italic-el-arch/uni043B.glif').read_text(), SimpleNamespace(), pen)
        arch = contours_of(pen.glyph(), new['glyf'])[0]
        foot = list(reversed(contours_of(old['glyf'][NAME], old['glyf'])[0]))
        start = next(i for i, p in enumerate(foot) if p[:2] == [377, 394])
        foot = foot[start:]+foot[:start]
        end = next(i for i, p in enumerate(foot) if p[:2] == [314, 404])
        foot = [[x-51, y, on] for x, y, on in foot[:end+1]]
        control = next(p for p in foot if p[:2] == [247, 91])
        control[1] = 93
        a = next(i for i, p in enumerate(arch) if p[:2] == [326, 394])
        b = next(i for i, p in enumerate(arch) if p[:2] == [263, 404])
        ck(contours_of(new['glyf'][NAME], new['glyf'])[0] == arch[:a]+foot+arch[b+1:],
           'exact arch and original exit graft, only declared control adjustment')
    for tag in ('cmap', 'GSUB', 'GDEF', 'cvt ', 'fpgm', 'prep', 'STAT', 'meta'):
        if tag in old:
            ck(old.getTableData(tag) == new.getTableData(tag), ('unchanged table', tag))
    restored = copy.deepcopy(new)
    table = restored['GPOS'].table
    ck(offset == len(old['GPOS'].table.LookupList.Lookup), 'lookup boundary')
    for lookup in table.LookupList.Lookup[offset:]:
        ck(lookup.LookupType == 2, 'pair-only additional lookup')
        for sub in lookup.SubTable:
            ck(sub.Format == 1, 'explicit additional pairs')
            for left, pairs in zip(sub.Coverage.glyphs, sub.PairSet):
                for pair in pairs.PairValueRecord:
                    ck(NAME in (left, pair.SecondGlyph), 'no unrelated new pair')
    table.LookupList.Lookup = table.LookupList.Lookup[:offset]
    table.LookupList.LookupCount = offset
    for record in table.FeatureList.FeatureRecord:
        if record.FeatureTag == 'kern':
            record.Feature.LookupListIndex = [i for i in record.Feature.LookupListIndex if i < offset]
            record.Feature.LookupCount = len(record.Feature.LookupListIndex)
    for li, si, index, ai, before, after in anchor_changes:
        table.LookupList.Lookup[li].SubTable[si].BaseArray.BaseRecord[index].BaseAnchor[ai].XCoordinate = before
    ck(restored.getTableData('GPOS') == old.getTableData('GPOS'), 'all other GPOS data preserved')
    for r in rows:
        ck(r['minimum_clearance'] >= r['required_clearance'], ('pair clearance', r))
        ck(native_kern(new, r['left'], r['right']) == r['kern'], ('serialized kerning', r))
    for text in ('office affine final AVATAR', 'я г ғ ч ң щ ү ұ', 'дождь · красота',
                 'Қазақ · керемет', 'Пп Тт Нн Ии', '0123456789 ₸ ₽'):
        ck(shape(old_raw, text) == shape(raw, text), ('unrelated shaping', text))
    for text in ('лилия аллея люблю платье', 'л́ л̀', 'гүл · әлем · ләззат'):
        ck(all(row[0] for row in shape(raw, text)), ('no missing glyphs', text))
    diagnostics = {}
    before_cs = TTFont(io.BytesIO(baseline('otf')))['CFF '].cff.topDictIndex[0].CharStrings
    for fmt, path in paths.items():
        f = TTFont(path)
        ck(ots.sanitize(str(path), '/dev/null', capture_output=True).returncode == 0, ('OTS', fmt))
        ck(f['name'].getDebugName(1) == FAMILY, ('test family name', fmt))
        ck(f['name'].getDebugName(6) == PS_NAME, ('unique PostScript name', fmt))
        for nid in (0, 8, 9, 13, 14):
            ck(f['name'].getDebugName(nid) == old['name'].getDebugName(nid), ('legal metadata', fmt, nid))
        ck(f['OS/2'].fsType == 0 and f['post'].italicAngle == -13, ('license and italic flags', fmt))
        findings, _ = inspect_outline(*read_outline(f, NAME))
        bad = {'self_intersection', 'zero_segment', 'stationary_point', 'transverse_step', 'short_segment'}
        ck(not any(r['kind'] in bad for r in findings), ('no topology defects or short steps', fmt))
        corners = [r for r in findings if r['kind'] == 'tangent_break']
        if VARIANT == 1:
            ck(all(r['xy'][1] == 0 for r in corners) and len(corners) == 2,
               ('only two intentional flat-foot corners', fmt))
        else:
            ck(not corners, ('no tangent break in the hybrid arch or exit', fmt))
        diagnostics[fmt] = findings
        if fmt == 'otf':
            cs = f['CFF '].cff.topDictIndex[0].CharStrings
            different = []
            for name in f.getGlyphOrder():
                before_cs[name].decompile(); cs[name].decompile()
                if before_cs[name].program != cs[name].program:
                    different.append(name)
            ck(different == [NAME], 'all other CFF programs preserved')
            ck(ttf2otf.exact_cubic_error(new, f, NAME) < .002, 'exact CFF el controls')
        elif fmt == 'woff2':
            for tag in ('glyf', 'hmtx', 'cmap', 'GSUB', 'GPOS', 'GDEF'):
                ck(new.getTableData(tag) == f.getTableData(tag), ('WOFF2 roundtrip', tag))
    return {'passed': checks, 'failed': 0, 'changed_glyphs': changed,
            'baseline': BASELINE, 'variant': FAMILY, 'date': DATE,
            'pairs_checked': len(rows), 'minimum_pair_clearance': min(r['minimum_clearance'] for r in rows),
            'font_sha256': {fmt: sha(path.read_bytes()) for fmt, path in paths.items()},
            'geometry_candidates': diagnostics,
            'optical_review': 'Arched el and word specimens reviewed separately; not whole-family optical acceptance.'}


def proof(ttf):
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    old_path = OUT/'baseline.ttf'; old_path.write_bytes(baseline('ttf'))
    old, new = Proof(old_path), Proof(ttf)
    fig, ax = page('Very Peri Serif · Italic · arched л', 1400, 1200)
    ax.text(60, 110, '1.113', fontsize=14, color='#69656a')
    if VARIANT == 1:
        ax.text(590, 110, LABEL, fontsize=14, color='#69656a')
        old.line(ax, 'л', 70, 465, 580); new.line(ax, 'л', 590, 465, 580)
    else:
        with zipfile.ZipFile('dist/VeryPeriSerif-ElArch1.zip') as archive:
            path = OUT/'arch1.ttf'
            path.write_bytes(archive.read('VeryPeriSerif-ElArch1/VeryPeriSerifElArch1-Italic.ttf'))
        ax.text(500, 110, 'El Arch 1', fontsize=14, color='#69656a')
        ax.text(920, 110, LABEL, fontsize=14, color='#69656a')
        old.line(ax, 'л', 60, 465, 550)
        Proof(path).line(ax, 'л', 500, 465, 550)
        new.line(ax, 'л', 920, 465, 550)
    for i, text in enumerate(('лилия · луна · аллея · люблю',
                              'платье · линия · молоко',
                              'лл · лп · пл · ли · ил · ла · ол',
                              'гүл · әлем · ләззат')):
        end = new.line(ax, text, 60, 680+i*120, 102)
        assert end < 1340, ('proof overflow', text)
    fig.savefig(f'docs/img/el-arch-{VARIANT}.svg', metadata={'Date': DATE})
    fig.savefig(OUT/f'el-arch-{VARIANT}.png', dpi=110)
    moment = datetime.datetime.fromisoformat(DATE).replace(tzinfo=datetime.timezone.utc)
    with PdfPages(f'docs/specimen/VeryPeriSerif-ElArch{VARIANT}.pdf',
                  metadata={'Title': FAMILY, 'CreationDate': moment, 'ModDate': moment}) as pdf:
        pdf.savefig(fig)
        fig2, ax2 = page(LABEL+' · text sizes and combining marks', 1400, 1050)
        y = 135
        for size in (24, 36, 48, 72, 110):
            new.line(ax2, 'лилия, аллея, люблю · гүл, әлем', 60, y, size)
            y += size*1.5+35
        new.line(ax2, 'л́ · л̀ · л̄ · л̆', 60, 950, 110)
        pdf.savefig(fig2); fig2.savefig(OUT/'el-arch-sizes.png', dpi=110)
        plt.close(fig2)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--variant', type=int, choices=(1, 2), default=1)
    configure_variant(ap.parse_args().variant)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    raw = baseline('ttf')
    assert sha(raw) == manifest['baseline_ttf_sha256']
    source = SOURCE.read_bytes()
    assert sha(source) == manifest['glif_sha256']
    font = TTFont(io.BytesIO(raw)); font.recalcTimestamp = False
    pen = TTGlyphPointPen(None); meta = SimpleNamespace()
    readGlyphFromString(source.decode(), meta, pen)
    glyph = pen.glyph(); glyph.recalcBounds(font['glyf'])
    font['glyf'][NAME] = glyph
    font['hmtx'][NAME] = (round(meta.width), glyph.xMin)
    anchor_changes = anchors(font)
    rows, corrections, offset = kern_lookup(font)
    for record in font['name'].names:
        values = {1: FAMILY, 2: 'Italic', 3: f'1.113;VPER;{PS_NAME};{sha(source)[:12]}',
                  4: FAMILY+' Italic', 5: 'Version 1.113; '+LABEL, 6: PS_NAME,
                  16: FAMILY, 17: 'Italic'}
        if record.nameID in values:
            record.string = values[record.nameID]
    font['OS/2'].recalcAvgCharWidth(font)
    paths = {fmt: OUT/(PS_NAME+'.'+fmt) for fmt in ('ttf', 'otf', 'woff2')}
    font.save(paths['ttf'])
    web = TTFont(paths['ttf']); web.recalcTimestamp = False; web.flavor = 'woff2'; web.save(paths['woff2'])
    ttf2otf.EXACT_ITALIC_CUBICS.add(NAME)
    ttf2otf.convert(paths['ttf'], paths['otf'])
    close_cff_exactly(paths['ttf'], paths['otf'])
    report = verify(raw, paths, anchor_changes, offset, rows)
    report['pair_corrections'] = {a+' '+b: v for (a, b), v in corrections.items()}
    report['anchor_changes'] = anchor_changes
    QA.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    proof(paths['ttf'])
    members = {path.name: path.read_bytes() for path in paths.values()}
    # The published baseline archive is the authoritative distribution notice.
    published = subprocess.check_output(['git', 'show', f'{BASELINE}:dist/VeryPeriSerif-1.113.zip'])
    with zipfile.ZipFile(io.BytesIO(published)) as archive:
        for name in ('OFL.txt', 'AUTHORS.txt', 'CONTRIBUTORS.txt', 'FONTLOG.txt'):
            matches = [n for n in archive.namelist() if n.endswith('/'+name)]
            assert len(matches) == 1, (name, matches)
            members[name] = archive.read(matches[0])
    for name, source in (('Cormorant-OFL.txt', 'data/cormorant-de/OFL.txt'),
                         ('Cormorant-NOTICE.txt', 'data/cormorant-de/NOTICE.txt')):
        members[name] = subprocess.check_output(['git', 'show', f'{BASELINE}:{source}'])
    command = 'python3 -I tools/build_el_arch_variant.py'
    if VARIANT != 1:
        command += f' --variant {VARIANT}'
    members['README.txt'] = (FAMILY+'\n\n'
        'Вариант строчной курсивной л по рисунку автора от 26.10.2026.\n'
        f'Установите {PS_NAME}.ttf и выберите семейство\n'
        f'{FAMILY}, начертание Italic. OTF — альтернативный формат\n'
        'установки, WOFF2 — для сайта. Достаточно установить один формат.\n'
        'Основной выпуск 1.113 сохранён отдельно.\n'
        'Изменены только л, её поля, пары и якоря знаков.\n'
        'Автор кириллицы: Yerbolat Rakhatuly (DEW). Лицензия: OFL 1.1.\n'
        'Остальные уведомления и исходная латиница сохранены.\n'
        f'Сборка: {command}\n').encode()
    members['FONTLOG.txt'] += (f'\n2026-10-26 — {LABEL}, optional Italic design study.\n'
        'Arched lowercase Cyrillic el by Yerbolat Rakhatuly (DEW),\n'
        'developed with OpenAI Codex. Other 1.113 glyphs retained.\n').encode()
    members[f'el-arch-{VARIANT}.svg'] = Path(f'docs/img/el-arch-{VARIANT}.svg').read_bytes()
    members[f'VeryPeriSerif-ElArch{VARIANT}.pdf'] = Path(f'docs/specimen/VeryPeriSerif-ElArch{VARIANT}.pdf').read_bytes()
    members['qa.json'] = QA.read_bytes()
    members['SHA256SUMS.txt'] = ''.join(sha(data)+'  '+name+'\n' for name, data in sorted(members.items())).encode()
    pending = io.BytesIO()
    with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(f'VeryPeriSerif-ElArch{VARIANT}/'+name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    candidate = pending.getvalue()
    if ZIP.exists():
        assert ZIP.read_bytes() == candidate, 'Versioned variants are immutable; choose a new variant number'
    else:
        ZIP.write_bytes(candidate)
    with zipfile.ZipFile(ZIP) as archive:
        assert archive.testzip() is None
    ZIP.with_suffix('.sha256').write_text(sha(ZIP.read_bytes())+'  '+ZIP.name+'\n')
    print(json.dumps({'archive': str(ZIP), 'checks': report['passed'], 'pairs': len(rows),
                      'points': len(glyph.coordinates), 'sha256': sha(ZIP.read_bytes())}))


if __name__ == '__main__':
    main()
