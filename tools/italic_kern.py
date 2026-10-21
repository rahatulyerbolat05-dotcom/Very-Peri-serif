#!/usr/bin/env python3
"""Native-calibrated Italic kerning, all case orders and mixed-script partners.

Native/native pairs remain untouched. Letter/letter pairs use the existing
curated native rhythm; punctuation, digits and symbols inherit the gap and
kerning of an edge donor. This avoids forcing a full stop or a quote to the
mean inter-letter gap. Run once on a fresh build, after character completion.
"""
import copy
import glob
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import optical_kerning as OK
from build_draft_font import DONORS, merge_layout, native_kern

LETTERS = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһі'
CAPS = LETTERS.upper()
TARGET = 'аеёиопрстух'
CAP_TARGET = 'АВЕЁКМНОРСТХ'
BAR_LIMIT = {'uni0442.ss03': 24, 'uni0433.ss04': 24}
OUT = Path('data/italic-kerning.json')
REF = Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Italic.ttf')


def apply(font,native_aliases=None):
    native_aliases=native_aliases or {}
    native = TTFont(REF)
    native_names = set(native.getGlyphOrder())|set(native_aliases)
    cm = font.getBestCmap()
    prof = OK.profiles(font)
    ref = OK.profiles(native)
    char_of = {n: chr(cp) for cp, n in cm.items() if not 0xE000 <= cp <= 0xF8FF}
    extra = json.loads(Path('data/italic-features.json').read_text())['kern_glyphs']
    for n, (ch, _) in extra.items():
        char_of[n] = ch
    own = {n for n in prof if n not in native_names and n in char_of
           and char_of[n] != '◌' and not n.endswith('.tnum')}
    partners = [n for n in prof if n in char_of and char_of[n] != '◌'
                and not 0xF101 <= ord(char_of[n]) <= 0xF108]
    # Include native unencoded variants which GSUB can select next to Cyrillic.
    partners += [n for n in prof if n in native_names and n!='.notdef' and n not in partners]
    for n in partners:
        if n not in char_of:
            root=n.split('.')[0]
            char_of[n] = char_of.get(root,char_of.get(root.split('_')[0],'a'))
    def gap(a, b, high, profiles=prof):
        g, valid = OK.gap_profile(profiles[a], profiles[b])
        return OK.optical(g, valid, high), g, valid
    targets = {}
    for label, left, right, high in [('ll', TARGET, TARGET, 510), ('Ul', CAP_TARGET, TARGET, 510),
                                      ('lU', TARGET, CAP_TARGET, 510), ('UU', CAP_TARGET, CAP_TARGET, 720)]:
        values = []
        for a in left:
            for b in right:
                na, nb = cm[ord(a)], cm[ord(b)]
                v, g, valid = gap(na, nb, high)
                if v is not None:
                    values.append(v + native_kern(font, na, nb))
        targets[label] = float(np.mean(values))
    def donor(n, side):
        if n in native_names:
            return native_aliases.get(n,n)
        ch = char_of[n]
        d = DONORS.get(ch, ('E', 'E') if ch.isupper() else ('e', 'e'))[side]
        # The repeated-stem letters in this Italic are native n/u/m, and use
        # native italic edge logic, rather than Regular's diagonal donors.
        special = {'н': 'n', 'ш': 'm', 'щ': 'm', 'ц': 'u', 'ң': 'n', 'қ': 'k',
                   'д': 'g', 'ж': 'c', 'в': 'b', 'я': 'a', 'ю': 'o', 'ф': 'o',
                   'ы': 'b' if side == 0 else 'n', 'ү': 'y', 'ұ': 'y', 'ғ': 'dotlessi'}
        return special.get(ch, d)
    nk_cache = {}
    def nk(a, b):
        if (a, b) not in nk_cache:
            nk_cache[a, b] = native_kern(font, a, b)
        return nk_cache[a, b]
    pairs, rows, categories = {}, [], {}
    for a in partners:
        for b in partners:
            if a not in own and b not in own:
                continue
            ca, cb = char_of[a], char_of[b]
            letters = ca.isalpha() and cb.isalpha()
            high = 510 if ca.islower() or cb.islower() else 720
            v, g, valid = gap(a, b, high)
            if not valid.any():
                # Disjoint vertical bands (e.g. a low dot and an upper quote)
                # need no contour-based correction.
                continue
            current = nk(a, b)
            if letters:
                label = ('l' if ca.islower() else 'U') + ('l' if cb.islower() else 'U')
                target = targets[label]
                delta = target - (v + current) if v is not None else 0
                limit = min(70, BAR_LIMIT.get(a, 70), BAR_LIMIT.get(b, 70))
                correction = max(-limit, min(40, delta * .8)) if abs(delta) >= 24 else 0
            else:
                label = 'punctuation/digits/symbols'
                da, db = donor(a, 1), donor(b, 0)
                if da not in ref or db not in ref:
                    continue
                rv, _, _ = gap(da, db, high, ref)
                target = (rv + native_kern(native,da,db)) if rv is not None else None
                delta = target - (v + current) if target is not None and v is not None else 0
                correction = max(-90, min(60, delta)) if abs(delta) >= 12 else 0
            # The stricter 20-unit letter clearance of I023, including tails.
            # Punctuation has closer native contacts; retain at least 5 units.
            clearance = 20 if letters else 5
            total = current + round(correction / 2) * 2
            total = max(total, math.ceil(clearance - float(g[valid].min())))
            additional = int(total - current)
            if additional:
                pairs[a, b] = additional
            categories[label] = categories.get(label, 0) + 1
            rows.append({'left': a, 'right': b, 'category': label, 'kern': total,
                         'gap': float(g[valid].min()) + total,
                         'optical_before': round(v + current, 2) if v is not None else None,
                         'optical_after': round(v + total, 2) if v is not None else None})
    fea = ['languagesystem DFLT dflt;', 'languagesystem latn dflt;', 'languagesystem cyrl dflt;', 'feature kern { lookupflag IgnoreMarks;']
    fea += [f'pos {a} {b} {v};' for (a, b), v in sorted(pairs.items())]
    fea += ['} kern;']
    extra_font = copy.deepcopy(font)
    for tag in ('GSUB', 'GPOS', 'GDEF'):
        if tag in extra_font:
            del extra_font[tag]
    addOpenTypeFeaturesFromString(extra_font, '\n'.join(fea))
    merge_layout(font, extra_font, 'GPOS')
    report = {'method': __doc__, 'target_gaps': targets, 'pairs_evaluated': len(rows),
              'categories': categories, 'native_native_pairs_changed': 0,
              'minimum_clearance': min(r['gap'] for r in rows),
              'pairs': {a + ' ' + b: v for (a, b), v in sorted(pairs.items())}}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    Path('build/premium').mkdir(parents=True, exist_ok=True)
    Path('build/premium/italic-pairs.json').write_text(json.dumps(rows, ensure_ascii=False) + '\n')
    return {k: v for k, v in report.items() if k not in ('pairs', 'method')}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1]
    font = TTFont(path)
    print(json.dumps(apply(font), ensure_ascii=False))
    if '--report' not in sys.argv:
        font.save(path)


if __name__ == '__main__':
    main()
