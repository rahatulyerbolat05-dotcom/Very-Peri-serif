import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
f=TTFont(sys.argv[1]); cmap=f.getBestCmap(); gs=f.getGlyphSet()
def row(ch):
    g=cmap[ord(ch)]; p=BoundsPen(gs); gs[g].draw(p); adv=f['hmtx'][g][0]; x0,y0,x1,y1=p.bounds
    return adv, round(x0), round(adv-x1), round(y0), round(y1)
print("ch adv lsb rsb ymin ymax")
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ": print(ch,*row(ch))
for ch in "abcdefghijklmnopqrstuvwxyz": print(ch,*row(ch))
print("digits:", [ (c,)+row(c)[:1] for c in "0123456789"])
# locl languages and liga
gsub=f['GSUB'].table
for fr in gsub.FeatureList.FeatureRecord:
    if fr.FeatureTag in ("locl","liga","ccmp"):
        print(fr.FeatureTag, [gsub.LookupList.Lookup[i].LookupType for i in fr.Feature.LookupListIndex])
for sr in gsub.ScriptList.ScriptRecord:
    langs=[ls.LangSysTag for ls in sr.Script.LangSysRecord]
    print("script",sr.ScriptTag,"langs",langs)
print([g for g in f.getGlyphOrder() if '_' in g][:20])
print("kern pairs lookup count:", len(f['GPOS'].table.LookupList.Lookup))
