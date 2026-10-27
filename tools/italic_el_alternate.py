"""The approved El Arch 2 as the default, with the previous form in ss10.

The original additive 1.114 layout is built, then its two complete identities
are exchanged reversibly. Existing masters are never regenerated. Historical
curve regressions use a reversible base-font view; check_italic_el_alternate
independently checks this projection against the actual frozen 1.113 tables.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.reorderGlyphs import reorderGlyphs
from fontTools.ufoLib.glifLib import readGlyphFromString
from build_draft_font import merge_layout
from family_finish import base_tables

NAME = 'uni043B.ss10'
BASE = 'uni043B'
ARCH_LABEL = 'Cyrillic el: rounded arch and exit'
PREVIOUS_LABEL = 'Cyrillic el: previous diagonal form'
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


def is_promoted(font):
    return font['post'].italicAngle and font['name'].getDebugName(265) == PREVIOUS_LABEL


def swap_forms(font, promoting=True):
    """Exchange two complete glyph identities in GPOS, preserving their rhythm.

    Unicode and GSUB keep mapping л -> uni043B -> uni043B.ss10. Outlines,
    metrics, all kern classes/pairs and mark anchors travel with each drawing.
    Applying the inverse restores the exact 1.114 layout, not a fresh fit.
    """
    font.ensureDecompiled()
    if 'glyf' in font:
        glyf=font['glyf']
        glyf[BASE],glyf[NAME]=glyf[NAME],glyf[BASE]
    else:
        cs=font['CFF '].cff.topDictIndex[0].CharStrings
        cs[BASE],cs[NAME]=cs[NAME],cs[BASE]
    metrics=font['hmtx'].metrics
    metrics[BASE],metrics[NAME]=metrics[NAME],metrics[BASE]
    mapping={BASE:NAME,NAME:BASE};seen=set()
    def rename(value):
        if isinstance(value,str):return mapping.get(value,value)
        if isinstance(value,(int,float,bool,type(None))):return value
        if id(value) in seen:return value
        seen.add(id(value))
        if isinstance(value,list):
            value[:]=[rename(v) for v in value]
        elif isinstance(value,dict):
            renamed={mapping.get(k,k):rename(v) for k,v in value.items()}
            value.clear();value.update(renamed)
        elif isinstance(value,tuple):return tuple(rename(v) for v in value)
        elif hasattr(value,'__dict__'):
            for key,item in list(vars(value).items()):setattr(value,key,rename(item))
        return value
    rename(font['GPOS'].table)
    # Coverage arrays and their parallel records must be re-sorted by glyph ID.
    reorderGlyphs(font,list(font.getGlyphOrder()))
    for record in font['name'].names:
        if record.nameID==265:
            if record.langID==0x419:
                record.string='л: прежняя диагональная форма' if promoting else 'л: округлая арка и хвост'
            else:
                record.string=PREVIOUS_LABEL if promoting else ARCH_LABEL
    font['OS/2'].recalcAvgCharWidth(font)


def unpromoted_view(font):
    if not is_promoted(font):return font
    normalized=copy.deepcopy(font)
    swap_forms(normalized,promoting=False)
    return normalized


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
    promoted=record.get('default_form')=='arched'
    if promoted:
        # Freeze the existing binary subtable partitions before moving glyph
        # identities. Otherwise the first 64K overflow split would depend on
        # the new Coverage order, obscuring an exact inverse comparison.
        buffer=io.BytesIO();font.save(buffer)
        serialized=TTFont(io.BytesIO(buffer.getvalue()))
        serialized.ensureDecompiled()
        font['GPOS']=serialized['GPOS']
        swap_forms(font)
        exchange={BASE:NAME,NAME:BASE}
        pairs={(exchange.get(a,a),exchange.get(b,b)):v for (a,b),v in pairs.items()}
        rows=[dict(r,left=exchange.get(r['left'],r['left']),right=exchange.get(r['right'],r['right'])) for r in rows]
    return {'glyph': BASE if promoted else NAME,'alternate_glyph':NAME, 'feature': 'ss10', 'source': str(SOURCE),
            'pairs_checked': len(rows), 'pairs': {a+' '+b: v for (a,b),v in pairs.items()},
            'pair_rows': rows, 'default_el_preserved': not promoted,
            'arched_el_is_default':promoted,'ss10_is_previous_form':promoted}


def legacy_view(font):
    """Undo only the explicit additions, without reading baseline font tables.

    Used by older frozen-outline regression gates that intentionally address
    the old glyph inventory. The extension has an independent full-font gate.
    """
    if NAME not in font.getGlyphOrder():
        return font
    record = json.loads(RECORD.read_text())
    f = copy.deepcopy(unpromoted_view(font))
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
