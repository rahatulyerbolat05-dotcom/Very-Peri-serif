import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
for path in sys.argv[1:]:
    f = TTFont(path)
    print("=====", path)
    n = f['name']
    for i in (1,2,4,5,13,14):
        r = n.getName(i,3,1,0x409)
        print(i, r.toUnicode() if r else None)
    head, hhea, os2 = f['head'], f['hhea'], f['OS/2']
    print("UPM", head.unitsPerEm, "hhea asc/desc/gap", hhea.ascent, hhea.descent, hhea.lineGap)
    print("typo asc/desc/gap", os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap, "win", os2.usWinAscent, os2.usWinDescent)
    print("xHeight", getattr(os2,'sxHeight',None), "capHeight", getattr(os2,'sCapHeight',None), "weight", os2.usWeightClass, "width", os2.usWidthClass)
    print("italicAngle", f['post'].italicAngle)
    cmap = f.getBestCmap()
    print("glyphs", len(f.getGlyphOrder()), "cmap", len(cmap))
    gs = f.getGlyphSet()
    def b(ch):
        g = cmap.get(ord(ch))
        if not g: return None
        p = BoundsPen(gs); gs[g].draw(p)
        return p.bounds, f['hmtx'][g]
    for ch in "HxnoOpdgaeyzf":
        print(ch, b(ch))
    cyr = [c for c in cmap if 0x400 <= c <= 0x52F]
    print("cyrillic cps:", len(cyr))
    blocks = {}
    for c in cmap:
        blocks.setdefault(c>>8, 0); blocks[c>>8]+=1
    print("blocks (hi byte):", {hex(k):v for k,v in sorted(blocks.items())})
    if 'GSUB' in f:
        print("GSUB", sorted({fr.FeatureTag for fr in f['GSUB'].table.FeatureList.FeatureRecord}))
    if 'GPOS' in f:
        print("GPOS", sorted({fr.FeatureTag for fr in f['GPOS'].table.FeatureList.FeatureRecord}))
    print("tables", sorted(f.keys()))
