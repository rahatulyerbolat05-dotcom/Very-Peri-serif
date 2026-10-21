#!/usr/bin/env python3
"""Very Peri Serif as one family: the Regular and the reviewed Italic linked as Regular and Italic (author: "merge them").
1. Italic completed with the 27 characters only the Regular had: spaces and invisible controls (Regular advances), hyphen/bar/apostrophe
   mapped to the native Italic hyphen, em dash and right quote, the others (figure dash, daggers, primes, currency, numero, schwa) as
   the Regular outlines sheared by 13 degrees about y=255 (the method of the capitals, docs/italic-rules.md 6.0), tidied and faired;
   the mathematical and technical signs (approximately equal, dotted circle, replacement character) stay upright, as in the native Italic.
2. One family: name IDs 1/2/4/6 (Very Peri Serif / Regular, Italic; VeryPeriSerif-Regular, VeryPeriSerif-Italic), the Regular's copyright,
   manufacturer, designer, URLs and licence on both, vendor VPER, the same vertical metrics, style linking (fsSelection REGULAR/ITALIC,
   macStyle, italicAngle -13), meta table, STAT (wght 400; ital 1 Italic, the Regular has ital 0 elidable linked to 1), Windows names only. Both styles share the release version; data/italic-version.json records the separate drawing revision.
3. build/release/VeryPeriSerif-Italic.ttf/.woff2 (regular_release.directory), a test pair under the family of the test Regular (dist/test,
   tools/make_test_copy.py), build/release/family-validation.json (OpenType Sanitizer, linking, coverage, shaping). The published fonts/,
   docs/qa/ and the release archive in dist/ are written from these by tools/package_release.py.
Usage: python3 -I tools/build_family.py [italic.ttf]   (default: the latest build/italic-lower/VeryPeriSerifItalicI*.ttf)
"""
import glob,hashlib,json,math,os,shutil,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
import ots
from family_finish import extend_italic_anchors, remove_experiments, tabular_figures, mark_ascent, stressed_i
from italic_tidy import tidy
from italic_fair import fair

S=math.tan(math.radians(13));Y0=255
CONFIG=json.loads(Path('data/params.json').read_text())['regular_release']
OUT=Path(CONFIG['directory']);REG=OUT/'VeryPeriSerif-Regular.ttf';TEST=Path('dist/test')
SPACES=(0x2002,0x2003,0x2007,0x2009,0x200A,0x200B,0x202F,0x2060,0xFEFF)
NATIVE_MAP={0x2010:'hyphen',0x2011:'hyphen',0x2015:'emdash',0x02BC:'quoteright'}
UPRIGHT=(0x2248,0x25CC,0xFFFD)
SHEAR=(0x2012,0x2020,0x2021,0x2032,0x2033,0x20B4,0x20B8,0x20BD,0x2116,0x018F,0x0259)
LINK_IDS=(0,7,8,9,10,11,12,13,14)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def complete(ita,reg):
    rcm=reg.getBestCmap();glyf=ita['glyf'];hmtx=ita['hmtx'];added={}
    curve_manifest=Path('data/curve-finish/manifest.json')
    retained_spacing=json.loads(curve_manifest.read_text()).get('derived_from_regular',{}).get('Italic',{}) if curve_manifest.exists() else {}
    def put(cp,name,glyph,adv):
        if name not in glyf.glyphOrder:glyf[name]=glyph
        hmtx[name]=(adv,getattr(glyph,'xMin',0) if glyph.numberOfContours else 0)
        for t in ita['cmap'].tables:
            if t.isUnicode() and (cp<=0xFFFF or t.format in (12,13)):t.cmap[cp]=name
    for cp in SPACES:
        name=rcm[cp];g=Glyph();g.numberOfContours=0;put(cp,name,g,reg['hmtx'][name][0]);added[hex(cp)]='space'
    for cp,donor in NATIVE_MAP.items():
        for t in ita['cmap'].tables:
            if t.isUnicode():t.cmap[cp]=donor
        added[hex(cp)]='native '+donor
    gs=reg.getGlyphSet()
    for cp in UPRIGHT+SHEAR:
        name=rcm[cp];pen=TTGlyphPen(None)
        gs[name].draw(TransformPen(pen,(1,0,0,1,0,0) if cp in UPRIGHT else (1,0,S,1,-S*Y0,0)));g=pen.glyph();g.recalcBounds(glyf)
        if cp in SHEAR:g,_=tidy(g,glyf);g,_=fair(g,glyf);g.recalcBounds(glyf)
        if name in retained_spacing:
            metrics=retained_spacing[name]
            assert reg['hmtx'][name][0]==metrics['advance']
            g.coordinates.translate((metrics['left_side_bearing']-g.xMin,0));g.recalcBounds(glyf)
        put(cp,name,g,reg['hmtx'][name][0]);added[hex(cp)]='upright Regular' if cp in UPRIGHT else 'Regular sheared'
    ita.setGlyphOrder(glyf.glyphOrder)
    gdef=ita['GDEF'].table.GlyphClassDef.classDefs
    for name in glyf.glyphOrder:
        if name not in gdef and glyf[name].numberOfContours:gdef[name]=1
    return added


def set_names(font,reg,family,style,ps,version,keep_feature_names=True):
    name=font['name'];kept=[r for r in name.names if r.nameID>=256] if keep_feature_names else []
    name.names=[r for r in reg['name'].names if r.nameID in LINK_IDS]+kept
    uid=hashlib.sha256(b''.join(font['glyf'][n].compile(font['glyf']) for n in font.getGlyphOrder())).hexdigest()[:12]
    values={1:family,2:style,3:f'{version};{CONFIG["vendor_id"]};{ps};{uid}',4:f'{family} {style}' if style!='Regular' else f'{family} Regular',5:f'Version {version}',6:ps}
    if style=='Italic':                                                       # no Cormorant outline in the Italic (docs/legal-review.md)
        values[0]=CONFIG['copyright']
        values[10]='Italic. Latin, Russian and Kazakh. Based on Instrument Serif Italic. '+CONFIG['ai_note']
    for nid,v in values.items():
        name.setName(v,nid,3,1,0x409)
    name.names=[r for r in name.names if r.platformID!=1]                     # Windows names only, as the Regular 1.016


def link(ita,reg,version):
    o=ita['OS/2'];r=reg['OS/2']
    o.achVendID=r.achVendID;o.usWinAscent=r.usWinAscent;o.usWinDescent=r.usWinDescent
    o.sTypoAscender,o.sTypoDescender,o.sTypoLineGap=r.sTypoAscender,r.sTypoDescender,r.sTypoLineGap
    ita['hhea'].ascent,ita['hhea'].descent,ita['hhea'].lineGap=reg['hhea'].ascent,reg['hhea'].descent,reg['hhea'].lineGap
    o.usWeightClass=r.usWeightClass;o.usWidthClass=r.usWidthClass
    o.fsSelection=(o.fsSelection|0x01|0x80)&~0x40&~0x20                     # ITALIC, USE_TYPO_METRICS; not REGULAR, not BOLD
    o.fsType=r.fsType
    cps=sorted(ita.getBestCmap());o.usFirstCharIndex=min(cps);o.usLastCharIndex=min(max(cps),0xFFFF)
    o.recalcUnicodeRanges(ita);o.ulCodePageRange1,o.ulCodePageRange2=r.ulCodePageRange1,r.ulCodePageRange2
    ita['head'].macStyle=2;ita['head'].fontRevision=float(version);ita['post'].italicAngle=-13.0
    ita['meta']=reg['meta'];o.recalcAvgCharWidth(ita)
    from build_regular_release import stat
    stat(ita,italic=True)


def validate(regp,itap):
    reg=TTFont(regp);ita=TTFont(itap);checks={}
    def ck(label,ok):checks[label]=bool(ok);assert ok,label
    ck('same family name',reg['name'].getDebugName(1)==ita['name'].getDebugName(1))
    ck('styles Regular / Italic',(reg['name'].getDebugName(2),ita['name'].getDebugName(2))==('Regular','Italic'))
    ck('Regular flags',reg['OS/2'].fsSelection&0x40 and not reg['OS/2'].fsSelection&1 and reg['head'].macStyle&3==0 and reg['post'].italicAngle==0)
    ck('Italic flags',ita['OS/2'].fsSelection&1 and not ita['OS/2'].fsSelection&0x40 and ita['head'].macStyle&3==2 and ita['post'].italicAngle<0)
    ck('same weight and width',(reg['OS/2'].usWeightClass,reg['OS/2'].usWidthClass)==(ita['OS/2'].usWeightClass,ita['OS/2'].usWidthClass))
    ck('same vertical metrics',all(getattr(reg['OS/2'],a)==getattr(ita['OS/2'],a) for a in ('sTypoAscender','sTypoDescender','sTypoLineGap','usWinAscent','usWinDescent')) and (reg['hhea'].ascent,reg['hhea'].descent)==(ita['hhea'].ascent,ita['hhea'].descent))
    ck('same upm and vendor',reg['head'].unitsPerEm==ita['head'].unitsPerEm and reg['OS/2'].achVendID==ita['OS/2'].achVendID)
    ck('Italic yMax within winAscent',ita['head'].yMax<=ita['OS/2'].usWinAscent and -ita['head'].yMin<=ita['OS/2'].usWinDescent)
    missing=sorted(set(reg.getBestCmap())-set(ita.getBestCmap()));ck('Italic covers every Regular character',not missing)
    for p in (regp,itap):
        r=ots.sanitize(str(p),os.devnull,capture_output=True);ck('OpenType Sanitizer '+Path(p).name,r.returncode==0)
    import uharfbuzz as hb
    for p in (regp,itap):
        f=hb.Font(hb.Face(Path(p).read_bytes()));b=hb.Buffer();b.add_str('Съешь же ещё этих мягких французских булок, да выпей чаю. № 5 ₸ ₽');b.guess_segment_properties();hb.shape(f,b,{})
        ck('no .notdef in sample '+Path(p).name,all(g.codepoint!=0 for g in b.glyph_infos))
    return checks


def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    src=Path(args[0]) if args else Path(sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1])
    version=CONFIG['version']
    reg=TTFont(REG);ita=TTFont(src)
    added=complete(ita,reg);link(ita,reg,version)
    anchors,native_aliases=extend_italic_anchors(ita)
    removed=remove_experiments(ita)
    from curve_finish import apply as finish_curves
    curve_sources=finish_curves(ita,'Italic')
    stressed_i(ita)
    from italic_kern import apply as kern_italic
    kerning=kern_italic(ita,native_aliases=native_aliases)
    figures=tabular_figures(ita)
    ita['OS/2'].recalcUnicodeRanges(ita)
    ita['OS/2'].recalcAvgCharWidth(ita)
    # A stacked accent on a tall Cyrillic base must not be clipped in legacy
    # Windows renderers. Preserve the common typographic line spacing.
    ascent=max(mark_ascent(ita),reg['OS/2'].usWinAscent)
    assert ascent<=reg['OS/2'].usWinAscent, 'Regular build must reserve the family mark ascent'
    set_names(ita,reg,'Very Peri Serif','Italic','VeryPeriSerif-Italic',version)
    ita.recalcTimestamp=False
    ita['head'].created=reg['head'].created;ita['head'].modified=reg['head'].modified
    ttf=OUT/'VeryPeriSerif-Italic.ttf';ita.save(ttf)
    woff=OUT/'VeryPeriSerif-Italic.woff2';w=TTFont(ttf);w.recalcTimestamp=False;w.flavor='woff2';w.save(woff)
    # test pair: the Italic under the family of the test Regular (tools/make_test_copy.py)
    tag='T'+CONFIG['version'].replace('.','');test=TEST/f'VeryPeriSerif{tag}-Italic.ttf'
    t=TTFont(ttf);fam=f'Very Peri Serif {tag}'
    for r in t['name'].names:
        if r.nameID==1:r.string=fam
        elif r.nameID==3:r.string=f'{version};{CONFIG["vendor_id"]};VeryPeriSerif{tag}-Italic'
        elif r.nameID==4:r.string=f'{fam} Italic'
        elif r.nameID==6:r.string=f'VeryPeriSerif{tag}-Italic'
    t.save(test)
    checks=validate(REG,ttf);tchecks=validate(TEST/f'VeryPeriSerif{tag}-Regular.ttf',test)
    report=dict(regular=dict(file=REG.name,version=CONFIG['version'],sha256=sha(REG)),italic=dict(file=ttf.name,version=version,source=str(src),sha256=sha(ttf),woff2_sha256=sha(woff)),
                added_to_italic=added,mark_anchors=anchors,native_cyrillic_clones=native_aliases,removed_experimental_glyphs=removed,tabular_figures=figures,kerning=kerning,curve_finish=curve_sources,
                checks=checks,test_pair=dict(family=fam,files=[f'VeryPeriSerif{tag}-Regular.ttf',test.name],checks=tchecks))
    (OUT/'family-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile('font/README-family.md',OUT/'README-family.md')
    members=['VeryPeriSerif-Regular.ttf','VeryPeriSerif-Regular.woff2','VeryPeriSerif-Italic.ttf','VeryPeriSerif-Italic.woff2','README-family.md','OFL.txt','AUTHORS.txt','FONTLOG.txt','Cormorant-OFL.txt','Cormorant-NOTICE.txt','family-validation.json']
    sums=''.join(sha(OUT/m)+'  '+m+'\n' for m in sorted(members))
    archive=OUT/'VeryPeriSerif-Family.zip';date=tuple(map(int,CONFIG['date'].split('-')))+(0,0,0)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for m in sorted(members):
            info=zipfile.ZipInfo('VeryPeriSerif/'+m,date_time=date);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,(OUT/m).read_bytes())
        info=zipfile.ZipInfo('VeryPeriSerif/SHA256SUMS-family.txt',date_time=date);info.external_attr=0o100644<<16;z.writestr(info,sums)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps(dict(italic=str(ttf),test=str(test),archive=str(archive),added=len(added),checks=sum(checks.values())),ensure_ascii=False))


if __name__=='__main__':main()
