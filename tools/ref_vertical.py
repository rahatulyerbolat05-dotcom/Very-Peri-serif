import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
f=TTFont(sys.argv[1]); cmap=f.getBestCmap(); gs=f.getGlyphSet()
def bounds(g):
    p=BoundsPen(gs); gs[g].draw(p); return p.bounds
allb=[(g,bounds(g)) for g in f.getGlyphOrder() if bounds(g)]
print("max ymax:", sorted(allb,key=lambda t:-t[1][3])[:4])
print("min ymin:", sorted(allb,key=lambda t:t[1][1])[:4])
for ch in "ËĔĂÉÝÿŭ":
    g=cmap.get(ord(ch)); print(ch,g,bounds(g) if g else None)
for cp,name in [(0x301,'acutecomb'),(0x300,'gravecomb'),(0x308,'dieresiscomb'),(0x306,'brevecomb'),(0x2BC,'apostrophe-mod'),(0x2116,'numero'),(0x20B8,'tenge'),(0x20BD,'ruble'),(0x20B4,'hryvnia'),(0xAB,'guillemotleft'),(0x2014,'emdash'),(0x2013,'endash'),(0xA0,'nbsp'),(0x2212,'minus'),(0x2009,'thinspace'),(0xA7,'section'),(0xB0,'degree'),(0x2030,'permille'),(0x201E,'quotedblbase'),(0x201C,'quotedblleft'),(0x2026,'ellipsis')]:
    g=cmap.get(cp); print(hex(cp),name,'->',g, bounds(g) if g and bounds(g) else '')
gpos=f['GPOS'].table
for i,lk in enumerate(gpos.LookupList.Lookup):
    print("GPOS lookup",i,"type",lk.LookupType)
# anchor names in mark lookups
names=set()
for lk in gpos.LookupList.Lookup:
    for st in lk.SubTable:
        if hasattr(st,'ExtSubTable'): st=st.ExtSubTable
        if hasattr(st,'MarkArray'):
            for mr in st.MarkArray.MarkRecord: names.add(mr.MarkAnchor.XCoordinate) if False else None
print("GDEF classes sample:", list(f['GDEF'].table.GlyphClassDef.classDefs.items())[:0])
