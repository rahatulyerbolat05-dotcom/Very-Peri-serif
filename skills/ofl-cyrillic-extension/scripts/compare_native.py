#!/usr/bin/env python3
"""Protect every incoming glyph and sampled native shaping in same-format static fonts."""
import argparse
import json
from pathlib import Path
import sys
from fontTools.ttLib import TTFont
import uharfbuzz as hb
from font_support import glyph_signature,cff_hint_environment,sha,write_json,sfnt_bytes

TEXTS=['Hamburgefontsiv AVATAR Wa To fi ffi ff office affine','0123456789 € $ % «Hello» (A) – A.','café naïve façade Straße ÄÖÜ áàâãå āăą ıİ Œœ', 'a\u0301 e\u0308 o\u0302 i\u0301']


def compare(before,after,output):
    a,b=TTFont(before),TTFont(after)
    if any(tag in f for f in (a,b) for tag in ('fvar','gvar','CFF2')):raise ValueError('Static fonts only. Variable master/variation preservation needs its own checks.')
    kind=lambda f:'glyf' if 'glyf' in f else 'CFF ' if 'CFF ' in f else None
    if kind(a) is None or kind(a)!=kind(b):raise ValueError('Compare corresponding formats; TTF-to-CFF needs a separate geometric conversion check.')
    checks=[];errors=[]
    def ck(label,ok):
        checks.append(label)
        if not ok:errors.append(label)
    ck('same UPM',a['head'].unitsPerEm==b['head'].unitsPerEm)
    for n in a.getGlyphOrder():
        exists=n in b.getGlyphOrder();ck('native glyph exists: '+n,exists)
        if exists:ck('native outline, hints, advance and bearing: '+n,glyph_signature(a,n)==glyph_signature(b,n))
    cm_a=a.getBestCmap() or {};cm_b=b.getBestCmap() or {}
    ck('incoming cmap entries retained',all(cm_b.get(cp)==n for cp,n in cm_a.items()))
    for sub in a['cmap'].tables:
        key=(sub.platformID,sub.platEncID,sub.language,sub.format)
        matches=[t for t in b['cmap'].tables if (t.platformID,t.platEncID,t.language,t.format)==key]
        if sub.format==14:
            ok=any(all(set(values)<=set(t.uvsDict.get(selector,[])) for selector,values in sub.uvsDict.items()) for t in matches)
        else:
            ok=any(all(t.cmap.get(cp)==name for cp,name in sub.cmap.items()) for t in matches)
        ck('incoming cmap subtable retained: '+str(key),ok)
    for tag in ('cvt ','fpgm','prep','gasp'):
        ck('native global TrueType hint table '+tag,(tag in a)==(tag in b) and (tag not in a or a.getTableData(tag)==b.getTableData(tag)))
    ck('CFF native hint environment',cff_hint_environment(a)==cff_hint_environment(b))
    hbs=[]
    for f in (a,b):
        h=hb.Font(hb.Face(sfnt_bytes(f)));hb.ot_font_set_funcs(h);hbs.append(h)
    def shape(index,text,features):
        buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties();buf.language='en';hb.shape(hbs[index],buf,features)
        font=(a,b)[index]
        return [(font.getGlyphName(g.codepoint),p.x_advance,p.y_advance,p.x_offset,p.y_offset) for g,p in zip(buf.glyph_infos,buf.glyph_positions)]
    variants=[{}, {'kern':False},{'liga':False},{'dlig':True}]
    if 'GSUB' in a and a['GSUB'].table.FeatureList:
        variants += [{r.FeatureTag:True} for r in a['GSUB'].table.FeatureList.FeatureRecord if r.FeatureTag.startswith('ss')]
    singles=[chr(cp) for cp in cm_a if 0x20<=cp<=0x024F or 0x1E00<=cp<=0x1EFF]
    texts=[''.join(ch for ch in text if ord(ch) in cm_a or ch==' ') for text in TEXTS]
    # Every inherited Latin-range scalar is tested separately; contexts are a bounded sample.
    for i,features in enumerate(variants):
        for j,text in enumerate(texts+singles):ck(f'native HarfBuzz sample {i}:{j}',shape(0,text,features)==shape(1,text,features))
    report={'before':str(before),'after':str(after),'before_sha256':sha(before),'after_sha256':sha(after),
       'passed':len(checks)-len(errors),'failed':len(errors),'errors':errors,
       'scope':'All incoming glyphs/cmap and same-format hint data; sampled Latin shaping, not exhaustive pair/language/feature combinations.'}
    write_json(output,report);return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('before',type=Path);ap.add_argument('after',type=Path);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    try:r=compare(args.before,args.after,args.out)
    except ValueError as e:ap.error(str(e))
    print(json.dumps({k:v for k,v in r.items() if k!='errors'}));return bool(r['failed'])


if __name__=='__main__':sys.exit(main())
