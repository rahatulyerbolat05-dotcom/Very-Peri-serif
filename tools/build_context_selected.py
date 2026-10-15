#!/usr/bin/env python3
"""Build selected forms with Claude's contextual к and stylistic т.
Existing studies and their native layout tables are retained unchanged.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib, json
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.ufoLib.glifLib import readGlyphFromString
from study_layout import add_order, mark_base, names, save_font, hb_shape
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/context-selected'
OUT=ROOT/'studies/regular/context-selected'

def add_layout(font,fea):
    extra=TTFont();extra.setGlyphOrder(font.getGlyphOrder());addOpenTypeFeaturesFromString(extra,fea)
    old=font['GSUB'].table;new=extra['GSUB'].table;offset=len(old.LookupList.Lookup)
    def shift(obj):
        if isinstance(obj,list):
            for v in obj:shift(v)
        elif hasattr(obj,'__dict__'):
            if hasattr(obj,'LookupListIndex'):obj.LookupListIndex+=offset
            for k,v in obj.__dict__.items():
                if k!='LookupListIndex':shift(v)
    for lookup in new.LookupList.Lookup:shift(lookup)
    old.LookupList.Lookup.extend(new.LookupList.Lookup);old.LookupList.LookupCount=len(old.LookupList.Lookup)
    added=[]
    for rec in new.FeatureList.FeatureRecord:
        rec.Feature.LookupListIndex=[i+offset for i in rec.Feature.LookupListIndex]
        added.append(len(old.FeatureList.FeatureRecord));old.FeatureList.FeatureRecord.append(rec)
    for script in old.ScriptList.ScriptRecord:
        if script.ScriptTag not in ('DFLT','cyrl'):continue
        langs=[script.Script.DefaultLangSys]+[r.LangSys for r in script.Script.LangSysRecord]
        for lang in langs:
            if lang is not None:lang.FeatureIndex+=added
    records=old.FeatureList.FeatureRecord;order=sorted(range(len(records)),key=lambda i:records[i].FeatureTag);remap={i:j for j,i in enumerate(order)}
    old.FeatureList.FeatureRecord=[records[i] for i in order];old.FeatureList.FeatureCount=len(records)
    for script in old.ScriptList.ScriptRecord:
        for lang in [script.Script.DefaultLangSys]+[r.LangSys for r in script.Script.LangSysRecord]:
            if lang is None:continue
            lang.FeatureIndex=sorted(remap[i] for i in lang.FeatureIndex);lang.FeatureCount=len(lang.FeatureIndex)
            if lang.ReqFeatureIndex!=65535:lang.ReqFeatureIndex=remap[lang.ReqFeatureIndex]

def build(base,label):
    f=TTFont(base);original=TTFont(base);cmap=f.getBestCmap();ka=cmap[ord('к')];te=cmap[ord('т')]
    short='uni043A.short';talt='uni0442.claude';add_order(f,[short,talt])
    for name,file,donor in [(short,'ka-short.glif',ka),(talt,'te-claude.glif',te)]:
        pen=TTGlyphPen(None);meta=SimpleNamespace();readGlyphFromString((DATA/file).read_text(),meta,PointToSegmentPen(Cu2QuPen(pen,1.0,reverse_direction=False)))
        g=pen.glyph();f['glyf'][name]=g;g.recalcBounds(f['glyf']);f['hmtx'][name]=(round(meta.width),g.xMin);mark_base(f,name,donor,top=(round(meta.width/2),510),bottom=(round(meta.width/2),0))
    head=json.loads((DATA/'head-class.json').read_text())['verified_characters']
    members=sorted({cmap[ord(ch)] for ch in head if ord(ch) in cmap}|{short,talt})
    # Include retained Cyrillic stylistic forms with the same top-left stem.
    members += [n for n in json.loads((DATA/'head-class.json').read_text())['verified_alternate_glyphs'] if n in f.getGlyphOrder() and n not in members]
    fea='languagesystem DFLT dflt;\nlanguagesystem cyrl dflt;\n@HEAD_TL = ['+' '.join(members)+'];\nfeature calt { lookupflag IgnoreMarks; sub '+ka+"' @HEAD_TL by "+short+'; } calt;\nfeature ss08 { sub '+te+' by '+talt+'; } ss08;\n'
    add_layout(f,fea);names(f,'Selected'+label);path=OUT/('selected-'+label+'.ttf');save_font(f,path);(OUT/('selected-'+label+'.fea')).write_text(fea)
    # Existing glyph geometry/metrics and original Latin shaping must not drift.
    check=TTFont(path)
    for name in original.getGlyphOrder():
        assert original['glyf'][name].compile(original['glyf'])==check['glyf'][name].compile(check['glyf']),name
        assert original['hmtx'][name]==check['hmtx'][name],name
    tests=[]
    for ch,n in cmap.items():
        if not 0x400<=ch<=0x4ff:continue
        word='к'+chr(ch);expected=short if chr(ch) in head else ka
        got=hb_shape(path,word);assert got[0][0]==expected,(word,got,expected)
        assert hb_shape(path,word,{'calt':False})[0][0]==ka
        tests.append(word)
    for word in ['к','ик','к и','ко','ка']:
        assert all(g[0]!=short for g in hb_shape(path,word)),word
    assert [r[0] for r in hb_shape(path,'ккк')]==[short,short,ka]
    assert hb_shape(path,'к\u0301и')[0][0]==short
    assert hb_shape(path,'т',{'ss08':True})[0][0]==talt
    for feature,word in [('ss02','кб'),('ss03','кб'),('ss04','кв'),('ss05','кг'),('ss07','ки'),('ss08','кт')]:
        result=hb_shape(path,word,{feature:True})
        assert result[0][0]==short,(feature,result)
    for word in ['AVATAR','office','minimum','Typography','a\u0301','Toyo']:
        assert hb_shape(path,word)==hb_shape(base,word),word
    return {'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tested_cyrillic_pairs':tests,'head_glyphs':members,'existing_glyphs_preserved':len(original.getGlyphOrder()),'cyrillic_codepoints':19}

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    reports=[build(ROOT/'studies/regular/ereversed-refined'/sub/'ereversed-02.ttf',label) for sub,label in [('with-ka02-shorti01', 'shorti01'),('with-ka02-shorti02','shorti02')]]
    (OUT/'verification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n');print(json.dumps(reports,ensure_ascii=False))
