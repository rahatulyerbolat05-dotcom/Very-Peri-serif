#!/usr/bin/env python3
"""Exhaustive HarfBuzz checks for all ordered Cyrillic pairs and feature modes."""
import hashlib,io,json,re,subprocess
from pathlib import Path
import uharfbuzz as hb
from fontTools.ttLib import TTFont


def check(data,font,native,chars,native_kern):
    rules={(a,b):int(v) for a,b,v in re.findall(r'^pos (\S+) (\S+) (-?\d+);$',Path('font/draft-features.fea').read_text(),re.M)}
    hf=hb.Font(hb.Face(data));hb.ot_font_set_funcs(hf);hf.scale=(1000,1000)
    def run(text,features):
        b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(hf,b,features)
        return [font.getGlyphName(x.codepoint) for x in b.glyph_infos],sum(p.x_advance for p in b.glyph_positions)
    counts={};checks=0
    modes={'default':{},'ss01':{'ss01':True},'ss08':{'ss08':True},'ss09':{'ss09':True},
           'combined':{'ss01':True,'ss08':True,'ss09':True},
           'ss01+ss08':{'ss01':True,'ss08':True},'ss01+ss09':{'ss01':True,'ss09':True},
           'ss08+ss09':{'ss08':True,'ss09':True},'aalt':{'aalt':1},'aalt+ss09':{'aalt':1,'ss09':True}}
    for label,features in modes.items():
        for a in chars:
            for b in chars:
                names,on=run(a+b,features);offnames,off=run(a+b,dict(features,kern=False))
                assert names==offnames and len(names)==2 and '.notdef' not in names,(label,a+b,names)
                expected=rules.get(tuple(names),0)+native_kern(native,*names)
                assert on-off==expected,(label,a+b,names,on-off,expected)
                checks+=1
        counts[label]=len(chars)**2
    # Both directions with Latin, digits, punctuation and currency symbols.
    mixed='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?«»“”()[]—–-ʼ‑₸₽₴№'
    mixed_count=0
    for a in chars:
        for b in mixed:
            for text in (a+b,b+a):
                names,on=run(text,{});offnames,off=run(text,{'kern':False})
                assert names==offnames and len(names)==2 and '.notdef' not in names,text
                assert on-off==rules.get(tuple(names),0)+native_kern(native,*names),(text,names,on-off)
                mixed_count+=1;checks+=1
    # Compare every native Unicode pair, including ligatures and marks.
    nhf=hb.Font(hb.Face(Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf').read_bytes()))
    hb.ot_font_set_funcs(nhf);nhf.scale=(1000,1000)
    def signature(hfont,ttfont,text):
        buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties();hb.shape(hfont,buf,{})
        return [(ttfont.getGlyphName(g.codepoint),p.x_advance,p.y_advance,p.x_offset,p.y_offset)
                for g,p in zip(buf.glyph_infos,buf.glyph_positions)]
    native_chars=[chr(c) for c in native.getBestCmap() if c>=32]
    native_count=0
    for a in native_chars:
        for b in native_chars:
            assert signature(hf,font,a+b)==signature(nhf,native,a+b),('native regression',repr(a+b))
            native_count+=1
    # Sources and all metrics must remain identical to 1.003.
    old=TTFont(io.BytesIO(subprocess.check_output(['git','show','6ccce10:dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf'])))
    assert font.getGlyphOrder()==old.getGlyphOrder()
    for name in old.getGlyphOrder():
        assert font['glyf'][name].compile(font['glyf'])==old['glyf'][name].compile(old['glyf']),name
        assert font['hmtx'][name]==old['hmtx'][name],name
    geometry=json.loads(Path('build/kerning/pairs.json').read_text())
    for r in geometry:
        assert r['final_min_gap']>=r['minimum_allowed']-1e-8,r
        assert rules.get((r['left'],r['right']),0)==r['additional'],r
    result={'ttf_sha256':hashlib.sha256(data).hexdigest(),'failed':0,
        'cyrillic_pairs_per_mode':len(chars)**2,'feature_modes':counts,
        'mixed_pairs_checked':mixed_count,'harfbuzz_pairs_checked':checks+native_count,'cyrillic_and_mixed_pairs_checked':checks,
        'native_unicode_pairs_preserved':native_count,
        'geometric_pairs_checked':len(geometry),'unchanged_outlines_and_advances':len(old.getGlyphOrder()),
        'native_native_pairs_changed':0,
        'scope':'All 84×84 ordered pairs in ten feature configurations, mixed pairs in both directions, every geometric result and unchanged source shapes/metrics.'}
    Path('dist/VeryPeriSerifDraft/kerning-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
