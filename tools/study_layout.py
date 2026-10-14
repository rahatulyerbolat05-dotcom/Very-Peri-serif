"""Layout helpers preserving existing glyphs/features while adding studies."""

from pathlib import Path

import copy

from fontTools.ttLib import TTFont

import uharfbuzz as hb

def add_order(tt, names):
    # Decode tables while the original glyph and metric counts still match.
    _ = tt['glyf'];_ = tt['hmtx'];_ = tt['loca']
    tt.setGlyphOrder(tt.getGlyphOrder() + list(names))
    tt['hhea'].numberOfHMetrics = len(tt.getGlyphOrder())
    tt['maxp'].numGlyphs = len(tt.getGlyphOrder())

def mark_base(tt, name, donor, top=None, bottom=None):
    gid = tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for sub in lookup.SubTable:
            if donor not in sub.BaseCoverage.glyphs:
                continue
            records = dict(zip(sub.BaseCoverage.glyphs, sub.BaseArray.BaseRecord))
            record = copy.deepcopy(records[donor])
            if top is not None:
                # Original top mark class is 0, as verified on u/breve.
                record.BaseAnchor[0].XCoordinate, record.BaseAnchor[0].YCoordinate = top
            if bottom is not None:
                # Native bottom marks use class 2; short de feet need a new anchor.
                assert record.BaseAnchor[2] is not None
                record.BaseAnchor[2].XCoordinate, record.BaseAnchor[2].YCoordinate = bottom
            records[name] = record
            sub.BaseCoverage.glyphs = sorted(records, key=gid.get)
            sub.BaseArray.BaseRecord = [records[n] for n in sub.BaseCoverage.glyphs]
            sub.BaseArray.BaseCount = len(records)

def inherit_native_kern(tt, aliases):
    """Transfer existing pairs/classes only to exact native-u bodies."""
    gid = tt.getReverseGlyphMap()
    for lookup in tt['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType != 2:
            continue
        for sub in lookup.SubTable:
            if sub.Format == 2:
                coverage = set(sub.Coverage.glyphs)
                for target, donor in aliases.items():
                    if donor in coverage:
                        coverage.add(target)
                    for cd in [sub.ClassDef1, sub.ClassDef2]:
                        if donor in cd.classDefs:
                            cd.classDefs[target] = cd.classDefs[donor]
                sub.Coverage.glyphs = sorted(coverage, key=gid.get)
            elif sub.Format == 1:
                records = dict(zip(sub.Coverage.glyphs, sub.PairSet))
                original = copy.deepcopy(records)
                for target, donor in aliases.items():
                    if donor in original:
                        records[target] = copy.deepcopy(original[donor])
                for record in records.values():
                    pairs = {r.SecondGlyph:r for r in record.PairValueRecord}
                    oldpairs = dict(pairs)
                    for target, donor in aliases.items():
                        if donor in oldpairs:
                            r = copy.deepcopy(oldpairs[donor]);r.SecondGlyph = target
                            pairs[target] = r
                    record.PairValueRecord = [pairs[n] for n in sorted(pairs,key=gid.get)]
                    record.PairValueCount = len(record.PairValueRecord)
                sub.Coverage.glyphs = sorted(records, key=gid.get)
                sub.PairSet = [records[n] for n in sub.Coverage.glyphs]
                sub.PairSetCount = len(records)

def names(tt, suffix):
    family = 'Very Peri Regular Study ' + suffix
    values = {1:family,2:'Regular',3:family+';2026;study',4:family+' Regular',6:'VeryPeriRegularStudy'+suffix+'-Regular',16:family,17:'Regular'}
    for r in tt['name'].names:
        if r.nameID in values:
            r.string = values[r.nameID].encode(r.getEncoding())

def save_font(tt, path):
    tt.flavor = None;tt.save(path.with_suffix('.ttf'))
    tt = TTFont(path.with_suffix('.ttf'))
    tt.flavor = 'woff2';tt.save(path.with_suffix('.woff2'));tt.flavor = None
    return tt

def hb_shape(path, text, features=None):
    tt = TTFont(path);f = hb.Font(hb.Face(path.read_bytes()));f.scale = (1000,1000)
    b = hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(f,b,features or {})
    result = [(tt.getGlyphOrder()[g.codepoint],p.x_advance,p.y_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]
    assert all(g.codepoint for g in b.glyph_infos), text
    return result
