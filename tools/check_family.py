#!/usr/bin/env python3
"""Independent acceptance of final fonts, using HarfBuzz and vector intersections.

Exercises actual output files. Expected kerning is read from their GPOS, not
from the generator's JSON. Native shaping is compared with the pinned source.
"""
import hashlib
import io
import itertools
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont, ImageChops
from build_draft_font import native_kern
from contour_contacts import Auditor

CHARS = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӘҒҚҢӨҰҮҺІ'
CHARS += CHARS.lower()
MIXED = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?«»“”()[]—–-ʼ‑₸₽₴№′″†‡≈Əə'


def check(path, exhaustive=True):
    data = Path(path).read_bytes()
    f = TTFont(io.BytesIO(data))
    style = f['name'].getDebugName(2)
    native = TTFont('reference/instrument-serif/fonts/ttf/InstrumentSerif-' + style + '.ttf')
    native_names=set(native.getGlyphOrder())
    if style=='Italic':
        aliases=json.loads(Path('build/release/family-validation.json').read_text()).get('native_cyrillic_clones',{})
        for new,old in aliases.items():
            assert f['glyf'][new].compile(f['glyf'])==native['glyf'][old].compile(native['glyf']),('Native clone outline',new)
            assert f['hmtx'][new]==native['hmtx'][old],('Native clone metrics',new)
            for partner in native_names:
                assert native_kern(f,new,partner)==native_kern(native,old,partner),('Native clone kern',new,partner)
                assert native_kern(f,partner,new)==native_kern(native,partner,old),('Native clone kern',partner,new)
        native_names.update(aliases)
    hf = hb.Font(hb.Face(data))
    hb.ot_font_set_funcs(hf)
    def shape(text, features=None, language='ru', hfont=hf, font=f):
        b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); b.language = language
        hb.shape(hfont, b, features or {})
        return [(font.getGlyphName(g.codepoint), p.x_advance, p.x_offset, p.y_offset)
                for g, p in zip(b.glyph_infos, b.glyph_positions)]
    checks = []
    def ck(ok, label):
        if not ok:
            raise AssertionError((style, label))
        checks.append(label)
    ck(all(ord(c) in f.getBestCmap() for c in CHARS), 'Russian and Kazakh coverage')
    if style=='Italic':
        from polish_audit import check as curve_check
        for ch in 'жз':
            ck(not curve_check(f,f.getBestCmap()[ord(ch)])['kink'],'No residual curve kinks in '+ch)
        # Author request: default г is exactly locl SRB г minus its top line.
        body=[c for c in native['glyf']['imacron'].components if c.glyphName!='uni0304']
        ck(len(body)==1 and body[0].glyphName=='dotlessi' and (body[0].x,body[0].y)==(0,0), 'Serbian ghe body is native dotlessi')
        ghe=f.getBestCmap()[ord('г')]
        width_cfg=json.loads(Path('data/params.json').read_text())['premium_review'].get('italic_ghe_width')
        if width_cfg:
            from italic_rules_measure import polys,runs
            actual=polys(f,ghe,0);original=polys(native,'dotlessi',0)
            ck(f['hmtx'][ghe][0]==width_cfg['advance'], 'Wider ghe advance')
            for y in (205.1,230.1,255.1,280.1,305.1):
                a,b=runs(actual,y),runs(original,y)
                ck(len(a)==len(b)==1 and all(abs(x-z-width_cfg['anchor_dx'])<.1 for x,z in zip(a[0],b[0])), 'Wider ghe preserves diagonal stem at y='+str(y))
        else:
            ck(f['glyf'][ghe].compile(f['glyf'])==native['glyf'][body[0].glyphName].compile(native['glyf'])
               and f['hmtx'][ghe]==native['hmtx']['imacron'], 'Default ghe exactly matches Serbian body without macron')
        ck(shape('г',language='sr')[0][0]=='imacron' and shape('г',language='mk')[0][0]=='imacron', 'Serbian and Macedonian ghe retain macron')
        ck(shape('г',{'ss04':1})[0][0]=='uni0433.ss04', 'Printed ghe alternative retained')
        ck(shape('л',{'ss10':1})[0][0]=='uni043B.ss10', 'Previous el form available through ss10')
        ck(shape('л')[0][0]=='uni043B' and f['hmtx']['uni043B']==(392,10), 'Arched el is the default')
        # Compare independent flattened profiles of the actual exported outlines.
        from italic_rules_measure import polys, runs
        barred=f.getBestCmap()[ord('ғ')]
        body,with_bar=[polys(f,n,0) for n in (ghe,barred)]
        ck(f['hmtx'][barred][0]==f['hmtx'][ghe][0], 'Barred ghe shares default ghe advance')
        ck(f['glyf'][barred].numberOfContours==1, 'Barred ghe crossbar is merged into the body')
        profiles=[(runs(body,y+.1),runs(with_bar,y+.1)) for y in range(0,511,5) if not 230<=y<=272]
        ck(all(len(a)==len(b) and all(abs(x-z)<1.25 for ar,br in zip(a,b) for x,z in zip(ar,br))
               for a,b in profiles), 'Barred ghe preserves default body outside crossbar')
        a,b=runs(body,251.1)[0],runs(with_bar,251.1)[0]
        ck(a[0]-b[0]>30 and b[1]-a[1]>25, 'Barred ghe crossbar projects on both sides')
        ck(shape('г\u0301')[-1][1:]==shape('ғ\u0301')[-1][1:], 'Ghe and barred ghe share stress anchors')
        de=f.getBestCmap()[ord('д')]
        ck(f['hmtx'][de][0]==432, 'De preserves accepted advance after bowl repair')
        bowl,donor=polys(f,de,0),polys(native,'q',0)
        dx=f['glyf'][de].xMin-native['glyf']['q'].xMin
        for y in (-8.5,-4.5,.5,5.5):
            actual,expected=runs(bowl,y)[0],runs(donor,y)[0]
            ck(all(abs(x-z-dx)<1 for x,z in zip(actual,expected)), 'De retains rounded native bowl at y='+str(y))
        # Actual ink across the lower arc of я; the 1.102 ellipse left a
        # 9-unit hairline at the bottom of the bowl.
        ya=f.getBestCmap()[ord('я')]
        outline=polys(f,ya,0)
        upright=[[(-y,x) for x,y in contour] for contour in outline]
        widths=[]
        for x in (140.1,145.1,150.1,155.1,160.1,165.1):
            arc=[b-a for a,b in runs(upright,x) if 180<-b<235 and -a<270]
            ck(len(arc)==1, 'Ya lower bowl is continuous at x='+str(x))
            widths.extend(arc)
        ck(all(14<=w<=16.5 for w in widths), 'Ya lower arc holds the reviewed 14-16 unit hairline')
        ya_quality=curve_check(f,ya)
        ck(not ya_quality['kink'], 'Ya has no contour kink')
        ck(not ya_quality['micro'], 'Ya has no micro-segment at either repaired join')
        ck(not ya_quality['wobble'], 'Ya has no curvature wobble at either repaired join')
        yg=f['glyf'][ya];coords,ends,flags=yg.getCoordinates(f['glyf'])
        points=[(coords[i][0],coords[i][1],bool(flags[i]&1)) for i in range(len(coords))]
        ck(yg.numberOfContours==2, 'Ya has exactly body and counter contours')
        ck([(x,y,on) for x,y,on in points if 220<=x<=310 and 510<=y<=516]==
           [(305,513,True),(290,513,False),(260,516,False),(229,516,True)],
           'Ya top bowl/stem seam is one tangent-matched spline')
        ck([(x,y,on) for x,y,on in points if 211<=x<=240 and 190<=y<=220]==
           [(213,205,True),(216,216,False),(235,207,False),(232,196,True)],
           'Ya lower link/stem seam is one rounded spline')
    else:
        # Regular 1.105/1.106: round the two leg-to-bowl corners, then remove
        # the remaining kink on the inner edge of the right foot.
        from polish_audit import check as curve_check
        ya=f.getBestCmap()[ord('я')]
        yg=f['glyf'][ya];coords,ends,flags=yg.getCoordinates(f['glyf'])
        points=[(coords[i][0],coords[i][1],bool(flags[i]&1)) for i in range(len(coords))]
        ck(f['hmtx'][ya]==(428,-6), 'Regular ya preserves accepted advance and bearing')
        ck((yg.xMin,yg.yMin,yg.xMax,yg.yMax)==(-6,-9,399,516), 'Regular ya preserves accepted bounds')
        ck(yg.numberOfContours==2, 'Regular ya has exactly body and counter contours')
        ck([(x,y,on) for x,y,on in points if 145<=x<=160 and 220<=y<=246]==
           [(155,222,False),(158,234,True),(159,238,False),(156,244,False),(148,245,True)],
           'Regular ya outer leg shoulder is a rounded spline')
        ck([(x,y,on) for x,y,on in points if 185<=x<=220 and 235<=y<=250]==
           [(218,248,False),(193,247,False),(190,237,True)],
           'Regular ya inner leg shoulder is a rounded spline')
        # Collinearity at one node missed the multi-segment wave in 1.106.
        # Measure the complete exported edge: a convex foot has a monotone
        # slope from the bottom bowl to the straight stem.
        from italic_rules_measure import polys, runs
        outline=polys(f,ya,0)
        foot=[min(a for a,b in runs(outline,y+.1) if a>220) for y in range(0,101,5)]
        ck(all(foot[i+1]-2*foot[i]+foot[i-1]>=-.05 for i in range(1,len(foot)-1)),
           'Regular ya complete right-foot edge is convex without a wave')
        ya_quality=curve_check(f,ya)
        ck(not ya_quality['kink'], 'Regular ya has no contour kink')
        ck(not ya_quality['micro'], 'Regular ya has no micro-segment at either repaired join')
        ck(not ya_quality['wobble'], 'Regular ya has no curvature wobble at either repaired join')
    ck(not any(0xF101 <= cp <= 0xF108 for cp in f.getBestCmap()), 'No experimental PUA characters')
    ck(all(f['glyf'][n].compile(f['glyf']) == native['glyf'][n].compile(native['glyf'])
           and f['hmtx'][n] == native['hmtx'][n] for n in native.getGlyphOrder()), 'Native outlines, hints and metrics preserved')
    # Upper marks can follow any alphabetic base, including feature variants.
    features = [{}, {'ss01':1}, {'ss02':1,'ss03':1,'ss04':1,'ss05':1,'ss06':1}] if style == 'Italic' else [{}, {'ss01':1,'ss07':1,'ss08':1,'ss09':1}]
    if style == 'Italic':
        features.append({'ss10':1})
    mark_count = 0
    for mode,language in itertools.product(features,('ru','kk','sr','mk')):
        for ch in CHARS + 'Əə':
            on = shape(ch+'\u0301', mode, language)
            off = shape(ch+'\u0301', dict(mode,mark=False,mkmk=False), language)
            ck(on != off and on[-1][1] == 0, f'Attached stress {ch} {mode} {language}')
            ck(shape(unicodedata.normalize('NFC',ch+'\u0301'),mode,language) ==
               shape(unicodedata.normalize('NFD',ch+'\u0301'),mode,language),f'NFC/NFD stress {ch} {mode}')
            mark_count += 1
    ck(shape('і\u0301')[0][0] in ('dotlessi','uni0456.dotless'), 'Dot removed below acute on Cyrillic i')
    for text in ('Ѝ','ѝ'):
        ck(ord(text) in f.getBestCmap(), 'Stressed Bulgarian i encoded '+text)
        ck(shape(text)==shape(unicodedata.normalize('NFD',text)), 'Stressed i NFC/NFD '+text)
    for text in ('жа','дж','яд','ыж','эж','юн','әп','үк','нк','пн','кн','қн','гл','нг','гТ','Тг','гү','ға','ағ','ғұ','ғТ','Тғ','дд','нд'):
        accented=text[0]+'\u0301'+text[1]
        ck(sum(x[1] for x in shape(text))==sum(x[1] for x in shape(accented)), 'Accents preserve contextual forms and kerning '+text)
    for ch in 'яыэюәүЯЫЭЮӘҮ':
        single=shape(ch+'\u0308\u0301', {'mkmk':True})
        off=shape(ch+'\u0308\u0301', {'mkmk':False})
        ck(single != off, 'Stacked marks '+ch)
        # Highest actual ink, not only the base glyph's head.yMax.
        high=max(f['glyf'][n].yMax+dy for n,adv,dx,dy in single)
        ck(high<=f['OS/2'].usWinAscent, 'Stacked marks within Windows ascent '+ch)
    widths=[]
    for c in '0123456789':
        r=shape(c,{'tnum':True})
        ck(r[0][0].endswith('.tnum'),'tnum substitutes '+c)
        widths.append(r[0][1])
    ck(len(set(widths))==1,'Tabular figures have equal advances')
    for lang in ('ru','kk','sr','mk'):
        ck(sum(x[1] for x in shape('0123456789',{'tnum':True},lang))==10*widths[0], 'Tabular total, with kerning '+lang)
    ck(len(shape('office'))<len(shape('office',{'liga':False})), 'Standard ligatures active')
    ck(shape('qj',{'dlig':True})==shape('qj',{'dlig':True},hfont=hb.Font(hb.Face(Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-'+style+'.ttf').read_bytes())),font=native), 'Native discretionary ligature')
    # Every native Unicode pair must retain its complete shaping signature.
    nhf=hb.Font(hb.Face(Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-'+style+'.ttf').read_bytes()))
    native_chars=[chr(cp) for cp in native.getBestCmap() if cp>=32]
    for a in native_chars:
        for b in native_chars:
            if shape(a+b)!=shape(a+b,hfont=nhf,font=native):
                raise AssertionError(('Native regression',style,repr(a+b)))
    # Italic all 64 set combinations, plus SRB/MKD with and without all sets.
    # Regular already has its full 18-mode matrix in check_kerning.py.
    if style=='Italic' and exhaustive:
        tags=['ss%02d'%i for i in range(1,7)]
        modes=[({t:1 for t,v in zip(tags,flags) if v},'ru') for flags in itertools.product((0,1),repeat=6)]
        modes += [(mode,lang) for lang in ('sr','mk') for mode in ({},{t:1 for t in tags})]
    else:
        modes=[({},'ru')]
    audit=Auditor(f)
    expected={}
    pairs=0
    modes_report={}
    def pair(text,mode,lang):
        nonlocal pairs
        on=shape(text,mode,lang);off=shape(text,dict(mode,kern=False),lang)
        names=tuple(x[0] for x in on)
        if '.notdef' in names or names!=tuple(x[0] for x in off):
            raise AssertionError(('Pair substitution',style,text,mode,lang,on))
        if len(names)==1:
            # Native f + Cyrillic і can form the inherited f_i ligature in a
            # mixed HarfBuzz run. There is no remaining pair to kern/intersect.
            assert sum(x[1] for x in on)==sum(x[1] for x in off),(style,text,on,off)
            pairs+=1
            return
        assert len(names)==2,('Unexpected glyph count',style,text,on)
        if names not in expected:
            expected[names]=native_kern(f,*names)
        delta=sum(x[1] for x in on)-sum(x[1] for x in off)
        if delta!=expected[names]:
            raise AssertionError(('Kerning mismatch',style,text,mode,lang,delta,expected[names]))
        if any(n not in native_names for n in names):
            audit.check(*names,f['hmtx'][names[0]][0]+delta,(style,text,mode,lang))
        pairs+=1
    for mode,lang in modes:
        for a in CHARS:
            for b in CHARS:
                pair(a+b,mode,lang)
        modes_report[lang+':'+','.join(mode)]=len(CHARS)**2
    for a in CHARS:
        for b in MIXED:
            pair(a+b,{},'ru');pair(b+a,{},'ru')
    ligature_texts=['fiЖ','ffiж','Жfi','жffi','flд','дfl']
    if style=='Italic':ligature_texts.append('fіЖ')
    for text in ligature_texts:
        pair(text,{},'ru')
    # True pixel parity of the glyph itself (no string-pair kerning involved).
    raster_pairs=[]
    if style=='Regular':
        records=json.loads(Path('build/regular-release/source/build-manifest.json').read_text())['glyph_records']
        meta={r['character']:{'latin':r['native_copy']} for n,r in records.items() if 'native_copy' in r and '.' not in n}
        cmap=f.getBestCmap()
        reverse={n:chr(cp) for cp,n in native.getBestCmap().items()}
        for ch,r in meta.items():
            if len(ch)!=1 or 'latin' not in r or r['latin'] not in reverse or ord(ch) not in cmap:
                continue
            for size in (16,24,36,48,72,133):
                raster=ImageFont.truetype(io.BytesIO(data),size,layout_engine=ImageFont.Layout.BASIC)
                def draw(c):
                    im=Image.new('L',(300,300));ImageDraw.Draw(im).text((70,200),c,font=raster,fill=255,anchor='ls');return im
                ck(ImageChops.difference(draw(ch),draw(reverse[r['latin']])).getbbox() is None,f'Raster homoglyph {ch} {size}px')
            raster_pairs.append(ch)
    return {'file':str(path),'sha256':hashlib.sha256(data).hexdigest(),'style':style,
            'version':f['name'].getDebugName(5),'passed':len(checks),'failed':0,'checks':checks,
            'stress_sequences':mark_count,'feature_modes':modes_report,'harfbuzz_pairs_checked':pairs,
            'native_unicode_pairs_preserved':len(native_chars)**2,'vector_pairs_checked':len(audit.checked),
            'raster_homoglyphs':raster_pairs}


def main():
    root=Path('build/release')
    results=[check(root/f'VeryPeriSerif-{s}.ttf') for s in ('Regular','Italic')]
    report={'fonts':results,'passed':sum(r['passed'] for r in results),'failed':0}
    (root/'family-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='fonts'}))


if __name__=='__main__':
    main()
