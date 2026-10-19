#!/usr/bin/env python3
"""Build installable Very Peri Serif Draft Regular with original OT retained.

Run from repository root with fonttools, uharfbuzz, brotli, pillow, skia-pathops.
Outputs: dist/VeryPeriSerifDraft/. Original and authored outlines are not edited.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
from alphabet_sheet import source_items
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ufoLib.glifLib import readGlyphFromString
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import pathops
from audit_author_glyphs import rectangle
from outline_clean import clean_path
from polish_outlines import polish
CLEAN_QUAD_TOLERANCE=.9   # cubic->quadratic error for cleaned outlines, font units

REF=Path('reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf')
OUT=Path('dist/VeryPeriSerifDraft')
TTF=OUT/'VeryPeriSerifDraft-Regular.ttf'
RU='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
KZ='ӘҒҚҢӨҰҮҺІ'
CHARS=RU+RU.lower()+KZ+KZ.lower()
# Edge-donor choices are draft design decisions; they never replace outlines.
UP=[('A','A'),('H','B'),('B','B'),('F','F'),('A','A'),('E','E'),('Edieresis','Edieresis'),('X','X'),('S','S'),('H','H'),('H','H'),('K','K'),('A','H'),('M','M'),('H','H'),('O','O'),('H','H'),('P','P'),('C','C'),('T','T'),('Y','Y'),('O','O'),('X','X'),('H','H'),('U','H'),('H','H'),('H','H'),('T','B'),('B','I'),('B','B'),('C','C'),('H','O'),('R','R')]
LOW=[('a','a'),('o','b'),('h','b'),('r','r'),('o','o'),('e','e'),('edieresis','edieresis'),('x','x'),('c','s'),('u','u'),('ubreve','ubreve'),('k','k'),('n','n'),('n','n'),('h','u'),('o','o'),('n','n'),('p','p'),('c','c'),('m','m'),('y','y'),('o','o'),('x','x'),('u','u'),('u','h'),('u','u'),('u','u'),('r','b'),('h','n'),('h','b'),('c','c'),('h','o'),('o','n')]
KUP=[('O','O'),('F','F'),('K','K'),('H','H'),('O','O'),('Y','Y'),('Y','Y'),('H','h'),('I','I')]
KLOW=[('o','o'),('r','r'),('k','k'),('h','u'),('o','o'),('y','y'),('y','y'),('h','h'),('i','i')]
DONORS=dict(zip(CHARS,UP+LOW+KUP+KLOW))
DONORS['₸']=('T','T')
DONORS['У']=('y','y')
SYMBOLS={'₸':'data/currency/uni20B8.glif'}
SYMBOL_DONORS={'₽':'P','₴':'S','№':'N','ʼ':'quoteright','‑':'hyphen','\u2009':'space','\u202f':'space','◌':'o'}
for ch,donor in SYMBOL_DONORS.items():
    SYMBOLS[ch]=f'data/text-symbols/uni{ord(ch):04X}.glif';DONORS[ch]=(donor,donor)

for ch,item in json.loads(Path('data/typographic-completion/manifest.json').read_text()).items():
    SYMBOLS[ch]=item['path'];DONORS[ch]=(item['donor'],item['donor'])


SPACING_FILE=Path('data/spacing.json')
SPACING=json.loads(SPACING_FILE.read_text())['glyphs'] if SPACING_FILE.exists() else {}


def load(filename):
    meta=SimpleNamespace();p=pathops.Path()
    readGlyphFromString(Path(filename).read_text(),meta,PointToSegmentPen(p.getPen()))
    return p,round(getattr(meta,"width",0))


def name_for(ch):return f'uni{ord(ch):04X}'


def native_kern(font,left,right):
    table=font['GPOS'].table
    indices=next(r.Feature.LookupListIndex for r in table.FeatureList.FeatureRecord if r.FeatureTag=='kern')
    total=0
    for idx in indices:
        for s in table.LookupList.Lookup[idx].SubTable:
            if left not in s.Coverage.glyphs:continue
            assert s.ValueFormat1==4 and s.ValueFormat2==0
            if s.Format==1:
                i=s.Coverage.glyphs.index(left)
                rec=next((r for r in s.PairSet[i].PairValueRecord if r.SecondGlyph==right),None)
                if rec is None:continue
                total+=rec.Value1.XAdvance;break
            if s.Format==2:
                a=s.ClassDef1.classDefs.get(left,0);b=s.ClassDef2.classDefs.get(right,0)
                total+=s.Class1Record[a].Class2Record[b].Value1.XAdvance;break
    return total


def glyph_profile(path):
    result=[]
    for y in range(-204,733,12):
        cut=pathops.op(path,rectangle(-1000,y,3000,y+.05),pathops.PathOp.INTERSECTION)
        result.append((cut.bounds[0],cut.bounds[2]) if list(cut.contours) else None)
    return result


def extend_anchors(font,records):
    table=font['GPOS'].table.LookupList.Lookup[1].SubTable[0]
    bases=dict(zip(table.BaseCoverage.glyphs,table.BaseArray.BaseRecord))
    original=dict(bases)
    for name,r in records.items():
        if r['character'] in SYMBOLS and r['character'] not in '◌Əə':continue
        donor=r['donors'][0]
        if r['character']=='і':donor='dotlessi'
        if donor not in original:donor='E' if r['character'].isupper() else 'e'
        anchors=copy.deepcopy(original[donor])
        dx=(r.get('advance_unspaced',r['advance'])-font['hmtx'][donor][0])/2+r.get('spacing_dx',0)
        for anchor in anchors.BaseAnchor:
            if anchor:anchor.XCoordinate=round(anchor.XCoordinate+dx)
        if r['character'] in 'ЙЁйё' and anchors.BaseAnchor[0]:
            anchors.BaseAnchor[0].YCoordinate=max(anchors.BaseAnchor[0].YCoordinate,font['glyf'][name].yMax)
        if r['character']=='◌':
            for i,anchor in enumerate(anchors.BaseAnchor):
                if anchor:
                    anchor.XCoordinate=285
                    if i in (0,1):anchor.YCoordinate=510
        if r['character'] in 'Əə':
            anchors=copy.deepcopy(bases['uni04D8' if r['character']=='Ə' else 'uni04D9'])
        bases[name]=anchors
        font['GDEF'].table.GlyphClassDef.classDefs[name]=1
    order=font.getReverseGlyphMap();names=sorted(bases,key=order.get)
    table.BaseCoverage.glyphs=names;table.BaseArray.BaseRecord=[bases[n] for n in names]
    table.BaseArray.BaseCount=len(names)
    mark_top=max(font['glyf'][g].yMax-r.MarkAnchor.YCoordinate
                 for g,r in zip(table.MarkCoverage.glyphs,table.MarkArray.MarkRecord) if r.Class in (0,1))
    max_anchor=max(bases[n].BaseAnchor[0].YCoordinate for n in records if n in bases and bases[n].BaseAnchor[0])
    # Keep hhea/typo line spacing; allow legacy Windows clipping bounds to cover
    # an acute above precomposed Ё/Й as well as the simple capital vowels.
    font['OS/2'].usWinAscent=max(font['OS/2'].usWinAscent,max_anchor+mark_top+2)


def offset_lookup_records(obj,offset,seen=None):
    if seen is None:seen=set()
    if id(obj) in seen:return
    seen.add(id(obj))
    if type(obj).__name__ in ('SubstLookupRecord','PosLookupRecord'):
        obj.LookupListIndex+=offset
    if isinstance(obj,list):
        for value in obj:offset_lookup_records(value,offset,seen)
    elif hasattr(obj,'__dict__'):
        for value in obj.__dict__.values():offset_lookup_records(value,offset,seen)


def merge_layout(font,extra,tag):
    old=font[tag].table;new=extra[tag].table;offset=len(old.LookupList.Lookup)
    for lookup in new.LookupList.Lookup:offset_lookup_records(lookup,offset)
    old.LookupList.Lookup.extend(new.LookupList.Lookup);old.LookupList.LookupCount=len(old.LookupList.Lookup)
    remap={}
    for i,record in enumerate(new.FeatureList.FeatureRecord):
        record.Feature.LookupListIndex=[j+offset for j in record.Feature.LookupListIndex]
        same=next((j for j,r in enumerate(old.FeatureList.FeatureRecord) if r.FeatureTag==record.FeatureTag),None)
        if same is None:
            same=len(old.FeatureList.FeatureRecord);old.FeatureList.FeatureRecord.append(record)
        else:
            feature=old.FeatureList.FeatureRecord[same].Feature
            feature.LookupListIndex.extend(record.Feature.LookupListIndex)
            feature.LookupCount=len(feature.LookupListIndex)
            if record.Feature.FeatureParams:feature.FeatureParams=record.Feature.FeatureParams
        remap[i]=same
    scripts={r.ScriptTag:r for r in old.ScriptList.ScriptRecord}
    for script in new.ScriptList.ScriptRecord:
        for lang in [script.Script.DefaultLangSys]+[r.LangSys for r in script.Script.LangSysRecord]:
            if lang:lang.FeatureIndex=[remap[i] for i in lang.FeatureIndex];lang.FeatureCount=len(lang.FeatureIndex)
        if script.ScriptTag not in scripts:
            scripts[script.ScriptTag]=script
        else:
            assert not script.Script.LangSysRecord
            target=scripts[script.ScriptTag].Script.DefaultLangSys
            source=script.Script.DefaultLangSys
            if source:
                target.FeatureIndex=sorted(set(target.FeatureIndex+source.FeatureIndex));target.FeatureCount=len(target.FeatureIndex)
    # Cyrillic inherits mark/mkmk, ccmp and native liga/dlig as well as additions.
    cyrl=scripts['cyrl'].Script.DefaultLangSys
    allowed={'kern','mark','mkmk'} if tag=='GPOS' else {'aalt','case','ccmp','dlig','liga','ordn','ss01','calt','ss07','ss08','ss09'}
    cyrl.FeatureIndex=sorted(set(cyrl.FeatureIndex+[i for i,r in enumerate(old.FeatureList.FeatureRecord) if r.FeatureTag in allowed]))
    cyrl.FeatureCount=len(cyrl.FeatureIndex)
    # Feature records must be sorted; update every language's indices afterwards.
    ordered=sorted(enumerate(old.FeatureList.FeatureRecord),key=lambda p:p[1].FeatureTag)
    mapping={oldidx:newidx for newidx,(oldidx,_) in enumerate(ordered)}
    old.FeatureList.FeatureRecord=[r for _,r in ordered];old.FeatureList.FeatureCount=len(ordered)
    for record in scripts.values():
        for lang in [record.Script.DefaultLangSys]+[r.LangSys for r in record.Script.LangSysRecord]:
            if lang:
                lang.FeatureIndex=sorted(mapping[i] for i in lang.FeatureIndex)
                if lang.ReqFeatureIndex!=65535:lang.ReqFeatureIndex=mapping[lang.ReqFeatureIndex]
    old.ScriptList.ScriptRecord=sorted(scripts.values(),key=lambda r:r.ScriptTag)
    old.ScriptList.ScriptCount=len(scripts)


def main(output_dir=OUT,ttf_path=TTF):
    output_dir=Path(output_dir);ttf_path=Path(ttf_path)
    import subprocess
    import re
    keep_kerning='--keep-kerning' in sys.argv
    kept_pairs={(a,b):int(v) for a,b,v in re.findall(r'^pos (\S+) (\S+) (-?\d+);$',Path('font/draft-features.fea').read_text(),re.M)} if keep_kerning else None
    subprocess.run([sys.executable,'-I','tools/check_context_classes.py'],check=True,stdout=subprocess.DEVNULL)
    output_dir.mkdir(parents=True,exist_ok=True);Path('font').mkdir(exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());context=json.loads(Path('data/context/serif_bl.json').read_text())
    font=TTFont(REF);native=TTFont(REF);order=list(font.getGlyphOrder());records={};paths={};chosen={};tail_pairs={}
    def install(ch,filename,name,native_donor=None):
        if native_donor:
            path=pathops.Path();native.getGlyphSet()[native_donor].draw(path.getPen())
            advance=native['hmtx'][native_donor][0]
            checksum=hashlib.sha256(native['glyf'][native_donor].compile(native['glyf'])).hexdigest()
        else:
            path,advance=load(filename);checksum=hashlib.sha256(Path(filename).read_bytes()).hexdigest()
        spaced=SPACING.get(name) if not native_donor else None
        advance_unspaced=advance
        if spaced:
            moved=pathops.Path();path.draw(TransformPen(moved.getPen(),(1,0,0,1,spaced['dx'],0)));path=moved;advance=advance+spaced['dadv']
        path=pathops.simplify(path,fix_winding=True,clockwise=True)
        # Added glyphs only: merge redundant nodes, exact extrema/smooth joins. Verbatim
        # Instrument homoglyphs keep their native structure.
        tolerance=.1
        if not native_donor and 'data/homoglyph/' not in str(filename):path=clean_path(path);tolerance=CLEAN_QUAD_TOLERANCE
        pen=TTGlyphPen(None);path.draw(Cu2QuPen(pen,tolerance,reverse_direction=False))
        glyph=pen.glyph()
        # Integer rounding can create zero-length export fragments. Clean the
        # compiled copy; never rewrite the source GLIF or a native Latin glyph.
        rounded=pathops.Path();glyph.draw(rounded.getPen(),font['glyf'])
        rounded=pathops.simplify(rounded,fix_winding=True,clockwise=True)
        pen=TTGlyphPen(None);rounded.draw(Cu2QuPen(pen,.1,reverse_direction=False));glyph=pen.glyph()
        polish_stats={}
        if not native_donor and 'data/homoglyph/' not in str(filename):
            font['glyf'][name]=glyph;glyph,polish_stats=polish(glyph,font['glyf'],name)
            # 1.016: tangent breaks at seams and short handles faired on the integer grid (tools/italic_fair.py, Regular tolerances:
            # points within 1.2, glyph within 1.5); kinks of the added letters 223 -> 24, curvature wobble 15 -> 1
            from italic_fair import fair_regular
            glyph.recalcBounds(font['glyf']);glyph,fair_stats=fair_regular(glyph,font['glyf'])
            if len(fair_stats)>1:polish_stats=dict(polish_stats,fair={k:v for k,v in fair_stats.items()})
            from polish_outlines import straight_edges
            glyph,again=straight_edges(glyph,font['glyf'],glyph,{})   # a faired handle can bend a straightened edge again
            if again.get('straight'):polish_stats=dict(polish_stats,straight_after_fair=again['straight'])
        font['glyf'][name]=glyph;order.append(name);glyph.recalcBounds(font['glyf'])
        font['hmtx'][name]=(advance,getattr(glyph,'xMin',0))
        paths[name]=path;records[name]={'character':ch,'path':filename,'advance':advance,'donors':DONORS[ch],
            'sha256':checksum}
        if polish_stats:records[name]['polish']=polish_stats
        if spaced:records[name].update(spacing_dx=spaced['dx'],advance_unspaced=advance_unspaced)
        if native_donor:records[name]['donors']=(native_donor,native_donor)
    for ch in CHARS:
        items=source_items(ch,cfg);assert items,ch
        chosen[ch]=items[0]['path'];install(ch,items[0]['path'],name_for(ch))
        for table in font['cmap'].tables:
            if table.isUnicode():table.cmap[ord(ch)]=name_for(ch)
    for ch,filename in SYMBOLS.items():
        chosen[ch]=filename;install(ch,filename,name_for(ch))
        for table in font['cmap'].tables:
            if table.isUnicode():table.cmap[ord(ch)]=name_for(ch)
    for ch,filename,suffix in [('п','data/pe/pe_flag.glif','flag'),('к','data/ka/ka_short.glif','short'),('к','data/ka-flag/uni043A.flag.glif','flag'),('к','data/ka-flag/uni043A.short.flag.glif','short.flag'),('К','data/ka-flag/uni041A.flag.glif','flag'),('н','data/en-flat/uni043D.flat.glif','flat'),('т','data/te/t1.glif','ss08'),('д','data/regular-de-refinement/uni0434.glif','ss07')]:
        install(ch,filename,name_for(ch)+'.'+suffix)
    for ch,basename in [('а','a-cy'),('с','es-cy'),('е','ie-cy'),('ё','io-cy')]:
        install(ch,'data/homoglyph/'+basename+'.ss01.glif',name_for(ch)+'.ss01')
    install('і',str(REF)+'#dotlessi','uni0456.dotless','dotlessi')
    for ch,entry in cfg['user'].items():
        if ch not in CHARS:continue
        current={v['role']:v for v in entry['variants']}
        for role,item in current.items():
            if role!='primary':install(ch,item['path'],name_for(ch)+'.'+role)
        for item in entry.get('tail_alternatives',[]):
            role=item['role'];base=name_for(ch)+('' if role=='primary' else '.'+role)
            old=base+'.tail_old';install(ch,item['path'],old);tail_pairs[base]=old
    font.setGlyphOrder(order);font['maxp'].numGlyphs=len(order)
    extend_anchors(font,records)
    # Pair generation: native donor values plus explicitly reviewed draft pairs.
    pairs={};overrides=json.loads(Path('font/kerning-overrides.json').read_text())['pairs']
    original_names=native.getGlyphOrder()
    right=lambda n:records[n]['donors'][1] if n in records else n
    left=lambda n:records[n]['donors'][0] if n in records else n
    cache={}
    def donor_value(a,b):
        key=(right(a),left(b))
        if key not in cache:cache[key]=native_kern(native,*key)
        return cache[key]
    for a in order:
        for b in order:
            if a not in records and b not in records:continue
            value=donor_value(a,b)
            if a not in records:
                value-=native_kern(native,a,b)
            if a in records and b in records:
                text=records[a]['character']+records[b]['character']
                value=overrides.get(text,value)
            if value:pairs[a,b]=value
    # Collision protection on every Cyrillic pair, including after substitutions.
    profiles={n:glyph_profile(p) for n,p in paths.items()};clamped=[]
    donor_profiles={}
    def native_clearance(a,b):
        da,db=right(a),left(b)
        for donor in (da,db):
            if donor not in donor_profiles:
                path=pathops.Path();glyphset=native.getGlyphSet();glyphset[donor].draw(path.getPen(glyphSet=glyphset))
                donor_profiles[donor]=glyph_profile(path)
        gap=min((native['hmtx'][da][0]+pb[0]-pa[1] for pa,pb in zip(donor_profiles[da],donor_profiles[db]) if pa and pb),default=1000)
        # Native serifs can deliberately touch; do not turn AA/KA into loose pairs.
        return min(6,gap+native_kern(native,da,db))
    for a in records:
        for b in records:
            gap=min((records[a]['advance']+pb[0]-pa[1] for pa,pb in zip(profiles[a],profiles[b]) if pa and pb),default=1000)
            value=pairs.get((a,b),0);minimum=native_clearance(a,b)
            safe=max(value,round(minimum-gap+.499))
            if safe!=value:clamped.append({'left':a,'right':b,'requested':value,'actual':safe})
            if safe:pairs[a,b]=safe
            else:pairs.pop((a,b),None)
    if not keep_kerning:
        from optical_kerning import refine
        pairs,clamped=refine(font,native,records,native_kern,overrides)
    if keep_kerning:
        assert kept_pairs and all(a in order and b in order for a,b in kept_pairs)
        pairs=kept_pairs;clamped=[]
    serif=[name_for(ch) for ch in context['declared_class']['lower']+context['declared_class']['upper'] if ch in CHARS]
    head=[name_for(ch) for ch in context['ka_short']['declared_class']['lower'] if ch in CHARS]
    # Add all shape variants of members so feature ordering cannot disable context.
    for name,r in records.items():
        if name==name_for(r['character']):continue
        if name=='uni0434.ss07':
            from check_context_classes import test,test_top
            if test(paths[name])[0]:serif.append(name)
            if test_top(paths[name])[0]:head.append(name)
            continue
        if name_for(r['character']) in serif:serif.append(name)
        if name_for(r['character']) in head:head.append(name)
    # Letters without a lower-left serif: before them н gets the ordinary flat foot (tools/en_flat.py).
    plain=[name_for(ch) for ch in CHARS if name_for(ch) not in serif]
    for name,r in records.items():
        if name!=name_for(r['character']) and name not in serif and name_for(r['character']) in plain:plain.append(name)
    marktable=native['GPOS'].table.LookupList.Lookup[1].SubTable[0]
    above=[g for g,r in zip(marktable.MarkCoverage.glyphs,marktable.MarkArray.MarkRecord) if r.Class in (0,1)]
    fea=['languagesystem DFLT dflt;','languagesystem latn dflt;','languagesystem cyrl dflt;',
         '@serif_bl = ['+' '.join(serif)+'];','@head_tl = ['+' '.join(head)+'];','@no_serif_bl = ['+' '.join(plain)+'];',
         '@above_marks = ['+' '.join(above)+'];',
         "feature ccmp { sub uni0456' @above_marks by uni0456.dotless; } ccmp;",
         'feature ss07 { featureNames { name "Printed Cyrillic de"; }; sub uni0434 by uni0434.ss07; } ss07;',
         'feature calt { script cyrl;',
         'lookup calt_forms {',
         "sub uni043F' @serif_bl by uni043F.flag;",
         "sub uni043A' @head_tl by uni043A.short;",
         "sub uni049B' @head_tl by uni049B.context;",'} calt_forms;',
         '# к, к.short and К get the exit foot of н (tools/ka_flag.py) before a letter with a lower-left serif; қ keeps its tail',
         'lookup calt_feet {',
         "sub uni043A.short' @serif_bl by uni043A.short.flag;",
         "sub uni043A' @serif_bl by uni043A.flag;",
         "sub uni041A' @serif_bl by uni041A.flag;",
         "sub uni043D' @no_serif_bl by uni043D.flat;",'} calt_feet;','} calt;',
         'feature ss01 {']
    fea += [f'sub {name_for(ch)} by {name_for(ch)}.ss01;' for ch in 'асеё']
    fea += ['} ss01;','feature ss08 { featureNames { name "Alternate Cyrillic te"; }; sub uni0442 by uni0442.ss08; } ss08;',
            'feature ss09 { featureNames { name "Previous tail style"; };']
    fea += [f'sub {a} by {b};' for a,b in tail_pairs.items()]
    fea += ['} ss09;','feature aalt { sub uni049B from [uni049B.alternate]; sub uni0434 from [uni0434.ss07]; } aalt;',
            'feature kern {']
    fea += [f'pos {a} {b} {value};' for (a,b),value in sorted(pairs.items())]
    fea += ['} kern;']
    features='\n'.join(fea)+'\n';Path('font/draft-features.fea').write_text(features)
    # Compile additions in a separate font, then append lookups to existing OT.
    extra=copy.deepcopy(font)
    for tag in ('GSUB','GPOS','GDEF'):
        if tag in extra:del extra[tag]
    addOpenTypeFeaturesFromString(extra,features)
    merge_layout(font,extra,'GSUB');merge_layout(font,extra,'GPOS');font['name']=extra['name']
    digest=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()
    values={0:native['name'].getDebugName(0)+'; Cyrillic extension 2026 Very Peri Serif project contributors; Modified de Copyright 2015 the Cormorant Project Authors (github.com/CatharsisFonts/Cormorant).',
            1:'Very Peri Serif Draft',2:'Regular',3:'1.012;VPER;VeryPeriSerifDraft-Regular;'+digest[:12],
            4:'Very Peri Serif Draft Regular',5:'Version 1.012',6:'VeryPeriSerifDraft-Regular'}
    for nid in (16,17):font['name'].removeNames(nameID=nid)
    for nid,value in values.items():
        font['name'].removeNames(nameID=nid)
        font['name'].setName(value,nid,3,1,0x409);font['name'].setName(value,nid,1,0,0)
    font['head'].fontRevision=1.012;font.recalcTimestamp=False;font['OS/2'].recalcUnicodeRanges(font)
    font['OS/2'].recalcAvgCharWidth(font)
    font.save(ttf_path)
    web=TTFont(ttf_path);web.recalcTimestamp=False;web.flavor='woff2';web.save(ttf_path.with_suffix('.woff2'))
    manifest={'family':'Very Peri Serif Draft','version':'1.012','unicode_letters':len(CHARS),'unicode_symbols_added':list(SYMBOLS),'kerning_preserved':keep_kerning,
              'glyphs_added':len(records),'kerning_pairs_added':len(pairs),'collision_adjustments':clamped,
              'chosen_sources':chosen,'glyph_records':records,
              'tail_feature':'ss09','te_feature':'ss08','de_feature':'ss07','default_context':'calt',
              'note':'Unapproved designs use first currently displayed proposal; draft spacing and kerning.'}
    (output_dir/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    for filename in ('OFL.txt','AUTHORS.txt'):
        shutil.copyfile(Path('reference/instrument-serif')/filename,output_dir/filename)
    shutil.copyfile('data/cormorant-de/OFL.txt',output_dir/'Cormorant-OFL.txt')
    shutil.copyfile('data/cormorant-de/NOTICE.txt',output_dir/'Cormorant-NOTICE.txt')
    print(json.dumps({'ttf':str(ttf_path),'added_glyphs':len(records),'kerning_pairs':len(pairs),'clamped_pairs':len(clamped)},ensure_ascii=False))


if __name__=='__main__':main()
