#!/usr/bin/env python3
"""Release-only character/anchor finishing, shared by both styles.

Native glyphs and their hint programs stay untouched. The added mark anchors
follow the native four-class mark system; above/below anchors are shifted by
half the advance difference, with an italic correction when raising an anchor.
"""
import copy
import json
import math
from pathlib import Path

from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphComponent

CYRILLIC = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӘҒҚҢӨҰҮҺІ'


def base_tables(font):
    for lookup in font['GPOS'].table.LookupList.Lookup:
        if lookup.LookupType == 4:
            yield from lookup.SubTable


def extend_italic_anchors(font):
    """Cover every newly built letter/alternate, retaining native anchors verbatim."""
    cm = font.getBestCmap()
    existing={n for t in base_tables(font) for n in t.BaseCoverage.glyphs}
    aliases={}
    # Some native Latin consonants have no mark anchors. Their Cyrillic
    # aliases need separate bases: adding an anchor to the shared Latin name
    # would change inherited Latin shaping. Copy their native kern classes too.
    for ch in CYRILLIC+CYRILLIC.lower():
        name=cm.get(ord(ch))
        if name and (name not in existing or name in ('a','e')) and not name.startswith('uni'):
            new=f'uni{ord(ch):04X}'
            font['glyf'][new]=copy.deepcopy(font['glyf'][name])
            font['hmtx'][new]=font['hmtx'][name]
            aliases[new]=name
            for sub in font['cmap'].tables:
                if sub.isUnicode():sub.cmap[ord(ch)]=new
    variants=json.loads(Path('data/italic-features.json').read_text()).get('native_cyrillic_variants',{})
    aliases.update({n:orig for n,orig in variants.items() if n in font['glyf']})
    font.setGlyphOrder(font['glyf'].glyphOrder)
    inherit_kern_classes(font,aliases)
    # Shared m was the source of Cyrillic т's ss03/locl substitutions. Its new
    # Cyrillic copy must keep those substitutions, while Latin m stays intact.
    for lookup in font['GSUB'].table.LookupList.Lookup:
        for raw in lookup.SubTable:
            sub=raw.ExtSubTable if hasattr(raw,'ExtSubTable') else raw
            if hasattr(sub,'mapping'):
                for new,old in aliases.items():
                    if old in sub.mapping:
                        value=copy.deepcopy(sub.mapping[old])
                        if value==old+'.ss01' and new+'.ss01' in font['glyf']:value=new+'.ss01'
                        sub.mapping[new]=value
            if hasattr(sub,'alternates'):
                for new,old in aliases.items():
                    if old in sub.alternates:
                        sub.alternates[new]=[new+'.ss01' if n==old+'.ss01' and new+'.ss01' in font['glyf'] else n
                                             for n in sub.alternates[old]]
    cm=font.getBestCmap()
    reverse = font.getReverseGlyphMap()
    glyphs = font['glyf']
    slope = math.tan(math.radians(-font['post'].italicAngle))
    letters = {cm[ord(ch)]: ch for ch in CYRILLIC + CYRILLIC.lower() + 'Əə' if ord(ch) in cm}
    # Unencoded stylistic/localized forms can receive marks after GSUB too.
    for name in font.getGlyphOrder():
        if name.startswith('uni') and '.' in name:
            try:
                ch = chr(int(name[3:7], 16))
            except ValueError:
                continue
            if ch in CYRILLIC + CYRILLIC.lower():
                letters[name] = ch
    added = {}
    for table in base_tables(font):
        bases = dict(zip(table.BaseCoverage.glyphs, table.BaseArray.BaseRecord))
        for name, ch in letters.items():
            if name in bases:
                continue
            g = glyphs[name]
            g.recalcBounds(glyphs)
            original=aliases.get(name)
            if original in bases:
                bases[name]=copy.deepcopy(bases[original])
                font['GDEF'].table.GlyphClassDef.classDefs[name]=1
                added[name]={'donor':original,'native_anchor_copy':True}
                continue
            if original and original.split('.')[0] in bases:
                root=original.split('.')[0];anchors=copy.deepcopy(bases[root])
                dx=g.xMin-glyphs[root].xMin
                target=510 if g.yMax<=535 else g.yMax
                for i,a in enumerate(anchors.BaseAnchor):
                    if a:
                        dy=target-a.YCoordinate if i==0 else 0
                        a.XCoordinate=round(a.XCoordinate+dx+slope*dy);a.YCoordinate+=dy
                bases[name]=anchors;font['GDEF'].table.GlyphClassDef.classDefs[name]=1
                added[name]={'donor':root,'alternate_anchor':True}
                continue
            donor = 'E' if ch.isupper() else 'n'
            if ch in 'ӘӨОЭЗФЮәөоэзфюƏə':
                donor = 'O' if ch.isupper() else 'o'
            if ch == 'й':
                donor = 'ubreve'
            elif ch == 'ё':
                donor = 'edieresis'
            elif ch == 'Ё':
                donor = 'Edieresis'
            anchors = copy.deepcopy(bases[donor])
            dx = (font['hmtx'][name][0] - font['hmtx'][donor][0]) / 2
            # Accents clear ascenders and existing diacritics. Round overshoots
            # (516/730) use the flat alignment height, as in native o/O.
            height = 720 if ch.isupper() else 510
            if g.yMax > height + 25:
                height = g.yMax
            for i, a in enumerate(anchors.BaseAnchor):
                if a is None:
                    continue
                dy = max(0, height - a.YCoordinate) if i == 0 else 0
                a.XCoordinate = round(a.XCoordinate + dx + slope * dy)
                a.YCoordinate += dy
            bases[name] = anchors
            font['GDEF'].table.GlyphClassDef.classDefs[name] = 1
            added[name] = {'donor': donor, 'top': [anchors.BaseAnchor[0].XCoordinate,
                                                 anchors.BaseAnchor[0].YCoordinate]}
        names = sorted(bases, key=reverse.get)
        table.BaseCoverage.glyphs = names
        table.BaseArray.BaseRecord = [bases[n] for n in names]
        table.BaseArray.BaseCount = len(names)
    return added,aliases


def inherit_kern_classes(font,aliases):
    """Exact native kerning for encoded copies of a shared native glyph."""
    order=font.getReverseGlyphMap();table=font['GPOS'].table
    indices={i for r in table.FeatureList.FeatureRecord if r.FeatureTag=='kern' for i in r.Feature.LookupListIndex}
    for index in indices:
        for raw in table.LookupList.Lookup[index].SubTable:
            sub=raw.ExtSubTable if hasattr(raw,'ExtSubTable') else raw
            if sub.Format==2:
                for new,old in aliases.items():
                    if old in sub.Coverage.glyphs:
                        sub.Coverage.glyphs.append(new)
                        sub.ClassDef1.classDefs[new]=sub.ClassDef1.classDefs.get(old,0)
                    sub.ClassDef2.classDefs[new]=sub.ClassDef2.classDefs.get(old,0)
                sub.Coverage.glyphs.sort(key=order.get)
            else:
                rows=dict(zip(sub.Coverage.glyphs,sub.PairSet))
                for row in rows.values():
                    values={r.SecondGlyph:r for r in row.PairValueRecord}
                    for new,old in aliases.items():
                        if old in values:
                            value=copy.deepcopy(values[old]);value.SecondGlyph=new
                            row.PairValueRecord.append(value)
                    row.PairValueRecord.sort(key=lambda r:order[r.SecondGlyph]);row.PairValueCount=len(row.PairValueRecord)
                for new,old in aliases.items():
                    if old in rows:rows[new]=copy.deepcopy(rows[old])
                names=sorted(rows,key=order.get)
                sub.Coverage.glyphs=names;sub.PairSet=[rows[n] for n in names];sub.PairSetCount=len(names)


def remove_experiments(font):
    """Rejected sketches are source material, not undocumented release characters."""
    removed = set()
    for table in font['cmap'].tables:
        if table.isUnicode():
            for cp in list(table.cmap):
                if 0xF101 <= cp <= 0xF108:
                    removed.add(table.cmap.pop(cp))
    # None is referenced by a release feature or component. Keep this assertion
    # explicit, so adding a real alternate cannot silently delete its outline.
    for name in font.getGlyphOrder():
        g = font['glyf'][name]
        if g.isComposite():
            assert not removed.intersection(c.glyphName for c in g.components)
    for name in removed:
        del font['glyf'][name]
        del font['hmtx'][name]
        font['GDEF'].table.GlyphClassDef.classDefs.pop(name, None)
    font.setGlyphOrder([n for n in font.getGlyphOrder() if n not in removed])
    return sorted(removed)


def tabular_figures(font):
    """Centred native lining figures, a shared cell, opt-in via tnum."""
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from build_draft_font import merge_layout
    cm = font.getBestCmap()
    digits = [cm[ord(ch)] for ch in '0123456789']
    width = max(font['hmtx'][n][0] for n in digits)
    pairs = []
    for name in digits:
        new = name + '.tnum'
        dx = round((width - font['hmtx'][name][0]) / 2)
        g = Glyph()
        g.numberOfContours = -1
        c = GlyphComponent()
        c.glyphName, c.x, c.y, c.flags = name, dx, 0, 0x4
        g.components = [c]
        font['glyf'][new] = g
        g.recalcBounds(font['glyf'])
        font['hmtx'][new] = width, g.xMin
        font['GDEF'].table.GlyphClassDef.classDefs[new] = 1
        pairs.append((name, new))
    font.setGlyphOrder(font['glyf'].glyphOrder)
    extra = copy.deepcopy(font)
    for tag in ('GSUB', 'GPOS', 'GDEF'):
        if tag in extra:
            del extra[tag]
    fea = 'languagesystem DFLT dflt; languagesystem latn dflt; languagesystem cyrl dflt;\n'
    fea += 'feature tnum {\n' + '\n'.join(f'sub {a} by {b};' for a, b in pairs) + '\n} tnum;'
    addOpenTypeFeaturesFromString(extra, fea)
    merge_layout(font, extra, 'GSUB')
    table=font['GSUB'].table
    index=next(i for i,r in enumerate(table.FeatureList.FeatureRecord) if r.FeatureTag=='tnum')
    for script in table.ScriptList.ScriptRecord:
        for lang in [script.Script.DefaultLangSys]+[r.LangSys for r in script.Script.LangSysRecord]:
            if lang is not None:
                lang.FeatureIndex=sorted(set(lang.FeatureIndex+[index]))
                lang.FeatureCount=len(lang.FeatureIndex)
    # Inherited proportional-digit kerning would destroy the tabular cells.
    # Both styles' native pair lookup only covers the original digit names.
    return {'cell': width, 'glyphs': [b for _, b in pairs]}


def stressed_i(font):
    """Bulgarian stressed i: encoded composites and canonical ccmp decomposition.

    Decomposing at shaping time retains the base letter's contextual forms and
    kerning, including next to a combining mark. This adds the two characters;
    it is not a claim of Bulgarian local-form editorial review.
    """
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from build_draft_font import merge_layout
    cm=font.getBestCmap();table=next(base_tables(font))
    bases=dict(zip(table.BaseCoverage.glyphs,table.BaseArray.BaseRecord))
    marks=dict(zip(table.MarkCoverage.glyphs,table.MarkArray.MarkRecord))
    mark=marks['gravecomb'];rules=[];new_anchors={}
    for ch,base_ch in [('Ѝ','И'),('ѝ','и')]:
        name=f'uni{ord(ch):04X}';base=cm[ord(base_ch)]
        anchor=bases[base].BaseAnchor[mark.Class]
        dx=anchor.XCoordinate-mark.MarkAnchor.XCoordinate
        dy=anchor.YCoordinate-mark.MarkAnchor.YCoordinate
        g=Glyph();g.numberOfContours=-1;g.components=[]
        for part,x,y in [(base,0,0),('gravecomb',dx,dy)]:
            c=GlyphComponent();c.glyphName,c.x,c.y,c.flags=part,x,y,0x4;g.components.append(c)
        font['glyf'][name]=g;g.recalcBounds(font['glyf'])
        font['hmtx'][name]=font['hmtx'][base][0],g.xMin
        font['GDEF'].table.GlyphClassDef.classDefs[name]=1
        for sub in font['cmap'].tables:
            if sub.isUnicode():sub.cmap[ord(ch)]=name
        new_anchors[name]=copy.deepcopy(bases[base])
        top=new_anchors[name].BaseAnchor[0]
        raise_by=max(0,g.yMax-top.YCoordinate)
        top.XCoordinate+=round(math.tan(math.radians(-font['post'].italicAngle))*raise_by)
        top.YCoordinate+=raise_by
        rules.append(f'sub {name} by {base} gravecomb;')
    font.setGlyphOrder(font['glyf'].glyphOrder)
    bases.update(new_anchors);order=font.getReverseGlyphMap();names=sorted(bases,key=order.get)
    table.BaseCoverage.glyphs=names;table.BaseArray.BaseRecord=[bases[n] for n in names];table.BaseArray.BaseCount=len(names)
    extra=copy.deepcopy(font)
    for tag in ('GSUB','GPOS','GDEF'):
        if tag in extra:del extra[tag]
    addOpenTypeFeaturesFromString(extra,'languagesystem DFLT dflt; languagesystem latn dflt; languagesystem cyrl dflt;\nfeature ccmp {\n'+'\n'.join(rules)+'\n} ccmp;')
    merge_layout(font,extra,'GSUB')
    font['OS/2'].recalcUnicodeRanges(font)
    return ['Ѝ','ѝ']


def mark_ascent(font):
    highest = font['OS/2'].usWinAscent
    for table in base_tables(font):
        for record in table.BaseArray.BaseRecord:
            for mark, mr in zip(table.MarkCoverage.glyphs, table.MarkArray.MarkRecord):
                anchor = record.BaseAnchor[mr.Class]
                if anchor:
                    g = font['glyf'][mark]
                    g.recalcBounds(font['glyf'])
                    highest = max(highest, anchor.YCoordinate + g.yMax - mr.MarkAnchor.YCoordinate + 2)
    return highest
