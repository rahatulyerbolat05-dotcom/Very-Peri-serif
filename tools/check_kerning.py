#!/usr/bin/env python3
"""Exhaustive HarfBuzz checks for all ordered Cyrillic pairs and feature modes."""
import hashlib,io,json,re,subprocess
from pathlib import Path
import uharfbuzz as hb
from fontTools.ttLib import TTFont


def check(data,font,native,chars,native_kern,report_path=None):
    rules={(a,b):int(v) for a,b,v in re.findall(r'^pos (\S+) (\S+) (-?\d+);$',Path('font/draft-features.fea').read_text(),re.M)}
    hf=hb.Font(hb.Face(data));hb.ot_font_set_funcs(hf);hf.scale=(1000,1000)
    def run(text,features):
        b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(hf,b,features)
        return [font.getGlyphName(x.codepoint) for x in b.glyph_infos],sum(p.x_advance for p in b.glyph_positions)
    from contour_contacts import Auditor
    contour_audit=Auditor(font)
    counts={};checks=0
    from itertools import product
    tags=('ss01','ss07','ss08','ss09')
    modes={'+'.join(t for t,on in zip(tags,flags) if on) or 'default':
           {t:True for t,on in zip(tags,flags) if on} for flags in product((False,True),repeat=4)}
    modes.update({'aalt':{'aalt':1},'aalt+ss09':{'aalt':1,'ss09':True}})
    for label,features in modes.items():
        for a in chars:
            for b in chars:
                names,on=run(a+b,features);offnames,off=run(a+b,dict(features,kern=False))
                assert names==offnames and len(names)==2 and '.notdef' not in names,(label,a+b,names)
                expected=rules.get(tuple(names),0)+native_kern(native,*names)
                assert on-off==expected,(label,a+b,names,on-off,expected)
                contour_audit.check(*names,font['hmtx'][names[0]][0]+expected,(label,a+b))
                checks+=1
        counts[label]=len(chars)**2
    # Both directions with Latin, digits, punctuation and currency symbols.
    mixed='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?«»“”()[]—–-ʼ‑₸₽₴№′″†‡≈�Əə‐‒―'
    mixed_count=0
    for a in chars:
        for b in mixed:
            for text in (a+b,b+a):
                names,on=run(text,{});offnames,off=run(text,{'kern':False})
                assert names==offnames and len(names)==2 and '.notdef' not in names,text
                expected=rules.get(tuple(names),0)+native_kern(native,*names)
                assert on-off==expected,(text,names,on-off)
                contour_audit.check(*names,font['hmtx'][names[0]][0]+expected,text)
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
    # Only the recorded width/weight refinements (incl. 1.001 weight balance of ж ф ю) may change from Regular 1.011.
    old=TTFont(io.BytesIO(subprocess.check_output(['git','show','f3614aa:dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf'])))
    assert set(old.getGlyphOrder()).issubset(font.getGlyphOrder())
    changed={f'uni{ord(ch):04X}' for ch in 'ЖШЩЫЮюФЧтшщыфдзжЪя'}|{'uni0429.tail_old','uni0449.tail_old'}
    finish=Path('data/curve-finish/manifest.json')
    if finish.exists():changed.update(json.loads(finish.read_text())['glyphs']['Regular'])
    assert changed.issubset(font.getGlyphOrder())
    spacing=json.loads(Path('data/spacing.json').read_text())['glyphs'] if Path('data/spacing.json').exists() else {}
    from polish_outlines import STRAIGHT_DEV
    manifest=Path('build/regular-release/source/build-manifest.json')
    STRAIGHTENED={n:min(STRAIGHT_DEV,r['polish']['deviation']) for n,r in json.loads(manifest.read_text())['glyph_records'].items()
                  if 'straight' in r.get('polish',{})} if manifest.exists() else {}
    def same_shape(name_new,name_old):
        # Outline hygiene (1.003) changes node structure, never the shape: two-sided deviation under 2.0 units.
        # Re-spacing (1.010) only translates a glyph by its recorded dx.
        from outline_clean import GlyphShape,max_deviation
        dx=spacing.get(name_new,{}).get('dx',0)
        if not dx and font['glyf'][name_new].compile(font['glyf'])==old['glyf'][name_old].compile(old['glyf']):return True
        # Straightened edges (1.016, polish_outlines.straighten: bellies and broken lines made straight, author: "crooked lines") may move
        # by the deviation the build recorded for that glyph, at most STRAIGHT_DEV.
        limit=2.0+STRAIGHTENED.get(name_new,0)          # the 1.003-1.015 hygiene allowance plus the recorded straightening
        return max_deviation(GlyphShape(font.getGlyphSet(),name_new,-dx),GlyphShape(old.getGlyphSet(),name_old))<=limit
    def same_metrics(name_new,name_old):
        sp=spacing.get(name_new)
        if sp:return font['hmtx'][name_new][0]==old['hmtx'][name_old][0]+sp['dadv']
        return font['hmtx'][name_new][0]==old['hmtx'][name_old][0] and abs(font['hmtx'][name_new][1]-old['hmtx'][name_old][1])<=2
    source_records=json.loads(manifest.read_text())['glyph_records']
    for name in old.getGlyphOrder():
        native_copy=source_records.get(name,{}).get('native_copy')
        if native_copy:
            assert font['glyf'][name].compile(font['glyf'])==native['glyf'][native_copy].compile(native['glyf']),('native copy',name)
            assert font['hmtx'][name]==native['hmtx'][native_copy],('native metrics',name)
            continue
        if name in changed:continue
        assert same_shape(name,name),name
        assert same_metrics(name,name),name
    # Printed alternate stays identical to its existing 1.007 outline and metrics.
    alt='uni0434.ss07';primary=alt
    if alt not in changed:assert same_shape(alt,primary)
    assert same_metrics(alt,primary)
    geometry=json.loads(Path('build/kerning/pairs.json').read_text())
    for r in geometry:
        if not r.get('identical_to_native'):   # identical homoglyph pairs equal the native Latin pair by rule
            assert r['final_min_gap']>=r['minimum_allowed']-1e-8,r
            assert r['protected_gap']>=8,r
        assert rules.get((r['left'],r['right']),0)==r['additional'],r
    result={'ttf_sha256':hashlib.sha256(data).hexdigest(),'failed':0,
        'cyrillic_pairs_per_mode':len(chars)**2,'feature_modes':counts,
        'mixed_pairs_checked':mixed_count,'harfbuzz_pairs_checked':checks+native_count,'cyrillic_and_mixed_pairs_checked':checks,
        'native_unicode_pairs_preserved':native_count,
        'geometric_pairs_checked':len(geometry),'unchanged_outlines_and_advances':len(old.getGlyphOrder())-len(changed.intersection(old.getGlyphOrder())),'intentional_outline_changes':sorted(changed),
        'native_native_pairs_changed':0,'vector_pairs_without_body_overlap':len(contour_audit.checked),
        'scope':'All 84×84 ordered pairs in all 16 stylistic-set combinations plus two alternate modes, mixed pairs in both directions, every geometric result and unchanged source shapes/metrics.'}
    Path(report_path or 'dist/VeryPeriSerifDraft/kerning-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result
