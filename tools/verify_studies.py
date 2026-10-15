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
latest=progress['latest_combinations']+progress.get('latest_de_combinations',[])+progress.get('latest_te_combinations',[])+progress.get('latest_ereversed_combinations',[])
retained_rejected=progress.get('retained_rejected_de_combinations',[])
retained_alternatives=progress.get('retained_te_alternative_combinations',[])
retained_ereversed=progress.get('retained_initial_ereversed_combinations',[])
selected_de=json.loads((ROOT/'data/selected-de.json').read_text())
selected_te=json.loads((ROOT/'data/selected-te.json').read_text())
latin_tests=['AV','To','Ta','Yo','Wa','LT','Fo','Pa','oo','r.','fo','C)','C?','A/']
de_quadratic_checked=0
selected_de_checked=0
te_checked=0
selected_te_checked=0
alternative_te_checked=0
ereversed_checked=0
for combo in latest+retained_rejected+retained_alternatives+retained_ereversed:
    path=ROOT/combo['ttf'];f=TTFont(path)
    is_ereversed=any(path.is_relative_to(ROOT/'studies/regular'/stage) for stage in ['ereversed','ereversed-refined'])
    if is_ereversed or path.is_relative_to(ROOT/'studies/regular/te') or (path.is_relative_to(ROOT/'studies/regular/de-reimagined') and combo['de_variant']=='01'):
        assert list(f['hmtx']['uni0434'])==selected_de['hmtx'],path
        assert hashlib.sha256(f['glyf']['uni0434'].compile(f['glyf'])).hexdigest()==selected_de['glyf_sha256'],path
        fs=GSFont(str(ROOT/combo['glyphs']));layer=fs.glyphs['uni0434'].layers[0]
        outline=[[(tuple(n.position),n.type) for n in p.nodes] for p in layer.paths]
        assert hashlib.sha256(json.dumps(outline,separators=(',',':')).encode()).hexdigest()==selected_de['glyphs_outline_sha256'],path
        selected_de_checked+=1
    if is_ereversed or path.is_relative_to(ROOT/'studies/regular/te'):
        te_checked+=1
        record=selected_te if combo['te_variant']=='02' else selected_te['retained_alternative']
        assert list(f['hmtx']['uni0442'])==record['hmtx'],path
        assert hashlib.sha256(f['glyf']['uni0442'].compile(f['glyf'])).hexdigest()==record['glyf_sha256'],path
        layer=fs.glyphs['uni0442'].layers[0]
        outline=[[(tuple(n.position),n.type) for n in p.nodes] for p in layer.paths]
        assert hashlib.sha256(json.dumps(outline,separators=(',',':')).encode()).hexdigest()==record['glyphs_outline_sha256'],path
        if combo['te_variant']=='02':selected_te_checked+=1
        else:alternative_te_checked+=1
        assert f.getBestCmap()[0x442]=='uni0442',path
        for text in ['тигр тогда','будто три','дитё тити','т\u0301']:
            hb_shape(path,text)
        if combo['te_variant']=='01':
            assert f['glyf']['uni0442'].compile(f['glyf'])==native['glyf']['m'].compile(native['glyf']),path
            for cy,latin in [('та','ma'),('то','mo'),('ти','mu')]:
                assert [p[1:] for p in hb_shape(path,cy)]==[p[1:] for p in hb_shape(reference/'fonts/ttf/InstrumentSerif-Regular.ttf',latin)],path
    if is_ereversed:
        ereversed_checked+=1
        assert f.getBestCmap()[0x44D]=='uni044D',path
        for text in ['это эра','эге эго','дуэт эхо','э\u0301','эо оэ']:
            hb_shape(path,text)
        assert hb_shape(path,'эо')[0][1]==hb_shape(reference/'fonts/ttf/InstrumentSerif-Regular.ttf','oo')[0][1]-40,path
    if is_ereversed or path.is_relative_to(ROOT/'studies/regular/de-cursive'):
        if not is_ereversed:de_quadratic_checked+=1
        # Check the saved integer-grid curves, independently of the build recipe.
        de=f['glyf']['uni044D' if is_ereversed else 'uni0434'];start=0
        for end in de.endPtsOfContours:
            ring=list(de.coordinates[start:end+1]);flags=list(de.flags[start:end+1])
            for i,point in enumerate(ring):
                if not flags[i]&1:continue
                previous=ring[i-1];following=ring[(i+1)%len(ring)]
                incoming=(point[0]-previous[0],point[1]-previous[1])
                outgoing=(following[0]-point[0],following[1]-point[1])
                assert incoming[0]*outgoing[1]-incoming[1]*outgoing[0]==0,(path,i)
                assert incoming[0]*outgoing[0]+incoming[1]*outgoing[1]>0,(path,i)
            start=end+1
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
    for stage in ['i-selected','shorti','ka','de-native','de-cyrillic','de-cursive','de-reimagined','te','ereversed','ereversed-refined']:
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
report={'status':'passed','source_commit':COMMIT,'retained':counts,'latest_combinations_checked':len(latest),'retained_rejected_combinations_checked':len(retained_rejected),'retained_te_alternative_combinations_checked':len(retained_alternatives),'retained_initial_ereversed_combinations_checked':len(retained_ereversed),'handwritten_de_integer_grid_g1_checked':de_quadratic_checked,'selected_de_exact_in_current_builds':selected_de_checked,'te_combinations_checked':te_checked,'ereversed_combinations_and_integer_g1_checked':ereversed_checked,'selected_te_primary_checked':selected_te_checked,'selected_te_alternative_checked':alternative_te_checked,'baseline_glyphs_checked':len(baseline),'original_glyphs_preserved':len(native.getGlyphOrder()),'latin_pair_samples_preserved':len(latin_tests),'precomposed_decomposed_shorti_and_features_checked':True,'portable_rebuilt_fonts_semantically_identical':rebuilt_count,'fontbakery':'not run','hyperglot':'not run','final_cyrillic_kerning':'not completed','fresh_dependency_install':'not repeated; current pinned environment used'}
args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
