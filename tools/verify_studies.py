"""Check retained artifact hashes, exported fonts and optional portable rebuilds."""
from pathlib import Path
import argparse, hashlib, json
import xml.etree.ElementTree as ET
from glyphsLib import GSFont
from fontTools.ttLib import TTFont
from prepare_reference import verify_reference, COMMIT
from study_layout import hb_shape

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rebuilt-dir',type=Path)
parser.add_argument('--report',type=Path,default=ROOT/'build/study-verification.json')
args=parser.parse_args()
manifest=json.loads((ROOT/'data/study-manifest.json').read_text())
assert manifest['source_commit']==COMMIT
counts={'artifacts':0,'ttf':0,'woff2_pairs':0,'glyphs':0,'svg':0,'json':0}
paths=set()
for record in manifest['files']:
    relative=record['path'];assert relative not in paths;paths.add(relative)
    path=(ROOT/relative).resolve();assert path.is_relative_to(ROOT)
    data=path.read_bytes();assert len(data)==record['bytes'],relative
    assert hashlib.sha256(data).hexdigest()==record['sha256'],relative
    assert path.suffix.lower() not in {'.png','.zip','.rar','.pyc'},relative
    counts['artifacts']+=1
    if path.suffix=='.ttf':
        f=TTFont(path);assert f.getBestCmap(),relative
        assert any(0x400<=u<0x530 for u in f.getBestCmap()),relative
        counts['ttf']+=1
        woff=path.with_suffix('.woff2')
        if woff.exists():
            w=TTFont(woff)
            assert f.getBestCmap()==w.getBestCmap(),relative
            assert f['hmtx'].metrics==w['hmtx'].metrics,relative
            assert f.getGlyphOrder()==w.getGlyphOrder(),relative
            for n in f.getGlyphOrder():assert f['glyf'][n].compile(f['glyf'])==w['glyf'][n].compile(w['glyf']),(relative,n)
            counts['woff2_pairs']+=1
    elif path.suffix=='.glyphs':
        assert len(GSFont(str(path)).glyphs)>0,relative;counts['glyphs']+=1
    elif path.suffix=='.svg':
        tree=ET.fromstring(data)
        assert tree.tag.endswith('svg'),relative
        assert not any(n.tag.rsplit('}',1)[-1] in {'script','image'} for n in tree.iter()),relative
        counts['svg']+=1
    elif path.suffix=='.json':json.loads(data);counts['json']+=1

progress=json.loads((ROOT/'data/progress.json').read_text())
reference=verify_reference(ROOT/'reference/instrument-serif')
native=TTFont(reference/'fonts/ttf/InstrumentSerif-Regular.ttf')
baseline=json.loads((ROOT/'studies/regular/ka/approved-baseline.json').read_text())['fixed_glyphs']
latest=progress['latest_combinations']+progress.get('latest_de_combinations',[])
latin_tests=['AV','To','Ta','Yo','Wa','LT','Fo','Pa','oo','r.','fo','C)','C?','A/']
for combo in latest:
    path=ROOT/combo['ttf'];f=TTFont(path)
    for n in native.getGlyphOrder():
        assert native['glyf'][n].compile(native['glyf'])==f['glyf'][n].compile(f['glyf']),(path,n)
        assert native['hmtx'][n]==f['hmtx'][n],(path,n)
    for n,record in baseline.items():
        assert list(f['hmtx'][n])==record['hmtx'],(path,n)
        assert hashlib.sha256(f['glyf'][n].compile(f['glyf'])).hexdigest()==record['glyf_sha256'],(path,n)
    for text in latin_tests:
        assert hb_shape(path,text)==hb_shape(reference/'fonts/ttf/InstrumentSerif-Regular.ttf',text),(path,text)
    for text in ['дед беда','какао','крик','бгвдёжзийк']:
        hb_shape(path,text)
    assert hb_shape(path,'й')==hb_shape(path,'и\u0306'),path
    assert hb_shape(path,'й',{'ss07':True})==hb_shape(path,'и\u0306',{'ss07':True}),path
    for text,feature,target in [('и',{},'uni0438'),('и',{'ss07':True},'i.altDiagonal'),('б',{'ss02':True},'be.altFlag'),('г',{'ss05':True},'ghe.altBeak')]:
        assert hb_shape(path,text,feature)[0][0]==target,(path,text,feature)
    for tag in ['GSUB','GPOS']:
        scripts={r.ScriptTag for r in f[tag].table.ScriptList.ScriptRecord}
        assert {'latn','cyrl'}.issubset(scripts),(path,tag)

rebuilt_count=0
if args.rebuilt_dir:
    for stage in ['i-selected','shorti','ka','de-native']:
        saved=ROOT/'studies/regular'/stage
        rebuilt=args.rebuilt_dir.resolve()/stage
        for expected in saved.rglob('*.ttf'):
            candidate=rebuilt/expected.relative_to(saved)
            a=TTFont(expected);b=TTFont(candidate)
            assert a.getBestCmap()==b.getBestCmap(),candidate
            assert a.getGlyphOrder()==b.getGlyphOrder(),candidate
            assert a['hmtx'].metrics==b['hmtx'].metrics,candidate
            for n in a.getGlyphOrder():assert a['glyf'][n].compile(a['glyf'])==b['glyf'][n].compile(b['glyf']),(candidate,n)
            for tag in ['GSUB','GPOS','GDEF']:
                assert a[tag].compile(a)==b[tag].compile(b),(candidate,tag)
            rebuilt_count+=1
report={'status':'passed','source_commit':COMMIT,'retained':counts,'latest_combinations_checked':len(latest),'baseline_glyphs_checked':len(baseline),'original_glyphs_preserved':len(native.getGlyphOrder()),'latin_pair_samples_preserved':len(latin_tests),'precomposed_decomposed_shorti_and_features_checked':True,'portable_rebuilt_fonts_semantically_identical':rebuilt_count,'fontbakery':'not run','hyperglot':'not run','final_cyrillic_kerning':'not completed','fresh_dependency_install':'not repeated; current pinned environment used'}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
