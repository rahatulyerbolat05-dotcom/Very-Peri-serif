"""The approved El Arch 2 drawing as a late, additive ss10 extension.

Existing outline masters and layout lookups are never regenerated. Historical
curve regressions use a reversible base-font view; check_italic_el_alternate
independently checks this projection against the actual frozen 1.113 tables.
"""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import readGlyphFromString
from build_draft_font import merge_layout
from family_finish import base_tables

NAME = 'uni043B.ss10'
SOURCE = Path('data/italic-el-arch-2/uni043B.glif')
RECORD = Path('data/italic-el-arch-2/opentype.json')
FEA = '''languagesystem DFLT dflt;
languagesystem latn dflt;
languagesystem cyrl dflt;
feature aalt {
  sub uni043B from [uni043B.ss10];
} aalt;
feature ss10 {
  featureNames {
    name "Cyrillic el: rounded arch and exit";
    name 3 1 0x0419 "л: округлая арка и хвост";
  };
  script cyrl;
  sub uni043B by uni043B.ss10;
} ss10;
'''


def apply(font):
    from build_el_arch_variant import kern_lookup
    record = json.loads(RECORD.read_text())
    assert NAME not in font.getGlyphOrder(), 'Do not apply ss10 twice'
    assert font['GSUB'].table.LookupList.LookupCount == record['base_gsub_lookups']
    assert font['GPOS'].table.LookupList.LookupCount == record['base_gpos_lookups']
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record['source_sha256']
    pen = TTGlyphPointPen(None); meta = SimpleNamespace()
    readGlyphFromString(raw.decode(), meta, pen)
    order = font.getGlyphOrder()+[NAME]
    glyph = pen.glyph(); glyph.recalcBounds(font['glyf'])
    font['glyf'][NAME] = glyph; font['hmtx'][NAME] = (round(meta.width), glyph.xMin)
    font.setGlyphOrder(order)
    font['GDEF'].table.GlyphClassDef.classDefs[NAME] = 1
    for sub in base_tables(font):
        i = sub.BaseCoverage.glyphs.index('uni043B')
        base = copy.deepcopy(sub.BaseArray.BaseRecord[i])
        for anchor in base.BaseAnchor:
            if anchor:
                anchor.XCoordinate = 259 if anchor.YCoordinate > 0 else 220
        sub.BaseCoverage.glyphs.append(NAME)
        sub.BaseArray.BaseRecord.append(base)
        sub.BaseArray.BaseCount += 1
    extra = copy.deepcopy(font)
    for tag in ('GSUB', 'GPOS', 'GDEF'):
        del extra[tag]
    addOpenTypeFeaturesFromString(extra, FEA)
    fresh = [n for n in extra['name'].names if n.nameID > record['base_max_name_id']]
    assert {n.nameID for n in fresh} == {record['feature_name_id']}
    font['name'].names.extend(fresh)
    merge_layout(font, extra, 'GSUB')
    table = font['GSUB'].table
    index = next(i for i,r in enumerate(table.FeatureList.FeatureRecord) if r.FeatureTag == 'ss10')
    cyrl = next(s.Script for s in table.ScriptList.ScriptRecord if s.ScriptTag == 'cyrl')
    for lang in [cyrl.DefaultLangSys]+[r.LangSys for r in cyrl.LangSysRecord]:
        if lang:
            lang.FeatureIndex = sorted(set(lang.FeatureIndex+[index]))
            lang.FeatureCount = len(lang.FeatureIndex)
    rows, pairs, offset = kern_lookup(font, NAME)
    assert offset == record['base_gpos_lookups']
    return {'glyph': NAME, 'feature': 'ss10', 'source': str(SOURCE),
            'pairs_checked': len(rows), 'pairs': {a+' '+b: v for (a,b),v in pairs.items()},
            'pair_rows': rows, 'default_el_preserved': True}


def legacy_view(font):
    """Undo only the explicit additions, without reading baseline font tables.

    Used by older frozen-outline regression gates that intentionally address
    the old glyph inventory. The extension has an independent full-font gate.
    """
    if NAME not in font.getGlyphOrder():
        return font
    record = json.loads(RECORD.read_text())
    f = copy.deepcopy(font)
    f.ensureDecompiled()  # load lazy glyph-indexed tables before shortening order
    assert f.getGlyphOrder()[-1] == NAME
    f.setGlyphOrder(f.getGlyphOrder()[:-1])
    if 'glyf' in f:
        del f['glyf'].glyphs[NAME]
    del f['hmtx'].metrics[NAME]
    f['maxp'].numGlyphs -= 1
    if f['post'].formatType == 2:
        f['post'].extraNames = [n for n in f['post'].extraNames if n != NAME]
        f['post'].mapping.pop(NAME, None)
    f['OS/2'].recalcAvgCharWidth(f)
    f.getTableData('hmtx')  # recompute numberOfHMetrics before hhea comparisons
    del f['GDEF'].table.GlyphClassDef.classDefs[NAME]
    for sub in base_tables(f):
        i = sub.BaseCoverage.glyphs.index(NAME)
        assert i == len(sub.BaseCoverage.glyphs)-1
        sub.BaseCoverage.glyphs.pop(); sub.BaseArray.BaseRecord.pop()
        sub.BaseArray.BaseCount -= 1
    gpos = f['GPOS'].table.LookupList
    gpos.Lookup = gpos.Lookup[:record['base_gpos_lookups']]
    gpos.LookupCount = len(gpos.Lookup)
    for r in f['GPOS'].table.FeatureList.FeatureRecord:
        if r.FeatureTag == 'kern':
            r.Feature.LookupListIndex = [i for i in r.Feature.LookupListIndex if i < gpos.LookupCount]
            r.Feature.LookupCount = len(r.Feature.LookupListIndex)
    gsub = f['GSUB'].table
    gsub.LookupList.Lookup = gsub.LookupList.Lookup[:record['base_gsub_lookups']]
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    kept = [(i,r) for i,r in enumerate(gsub.FeatureList.FeatureRecord) if r.FeatureTag != 'ss10']
    mapping = {before: after for after,(before,r) in enumerate(kept)}
    for i,r in kept:
        r.Feature.LookupListIndex = [j for j in r.Feature.LookupListIndex if j < record['base_gsub_lookups']]
        r.Feature.LookupCount = len(r.Feature.LookupListIndex)
    gsub.FeatureList.FeatureRecord = [r for i,r in kept]
    gsub.FeatureList.FeatureCount = len(kept)
    for script in gsub.ScriptList.ScriptRecord:
        for lang in [script.Script.DefaultLangSys]+[r.LangSys for r in script.Script.LangSysRecord]:
            if lang:
                lang.FeatureIndex = [mapping[i] for i in lang.FeatureIndex if i in mapping]
                lang.FeatureCount = len(lang.FeatureIndex)
                if lang.ReqFeatureIndex != 65535:
                    lang.ReqFeatureIndex = mapping[lang.ReqFeatureIndex]
    f['name'].names = [n for n in f['name'].names if n.nameID != record['feature_name_id']]
    return f


def legacy_font(*args, **kwargs):
    return legacy_view(TTFont(*args, **kwargs))
