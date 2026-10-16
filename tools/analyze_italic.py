#!/usr/bin/env python3
"""Measure the native Italic master and create a Russian cursive research plate.
Handwriting references are study material, never glyph sources for the font.
"""
import hashlib,json,math,re,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from glyphsLib import GSFont
from html import escape

ROOT=Path('reference/instrument-serif');CACHE=Path('build/italic-research')
UP='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ';KZ='ӘҒҚҢӨҰҮҺІ';CHARS=UP+UP.lower()+KZ+KZ.lower()
DIRECT={'А':'A','В':'B','Е':'E','Ё':'Edieresis','К':'K','М':'M','Н':'H','О':'O','Р':'P','С':'C','Т':'T','Х':'X',
        'І':'I','а':'a','е':'e','ё':'edieresis','и':'u','о':'o','п':'n','р':'p','с':'c','т':'m','у':'y','х':'x','і':'i','һ':'h'}
DEPEND={'Й':['И','breve'],'й':['и','breve'],'Ц':['П','tail'],'ц':['и','tail'],'Щ':['Ш','tail'],'щ':['ш','tail'],
        'Ғ':['Г','bar'],'ғ':['г','bar'],'Қ':['К','tail'],'қ':['к','tail'],'Ң':['Н','tail'],'ң':['н','tail'],
        'Ө':['О','bar'],'ө':['о','bar'],'Ұ':['Ү','bar'],'ұ':['ү','bar'],'Ы':['Ь','I-module'],'ы':['ь','i-module'],
        'Ъ':['Ь','head'],'ъ':['ь','head'],'Ю':['I-module','О','bridge'],'ю':['i-module','о','bridge'],
        'Ф':['oval-module','through-stem'],'ф':['oval-module','through-stem']}


def bounds(font,name):
    gs=font.getGlyphSet();pen=BoundsPen(gs);gs[name].draw(pen);return list(pen.bounds)

def main():
    CACHE.mkdir(exist_ok=True,parents=True)
    src=GSFont(ROOT/'sources/Instrument_Serif_Italic.glyphs');master=src.masters[0]
    italic=TTFont(ROOT/'fonts/ttf/InstrumentSerif-Italic.ttf');regular=TTFont(ROOT/'fonts/ttf/InstrumentSerif-Regular.ttf')
    assert master.xHeight==510 and master.italicAngle==13
    assert all(n in italic.getGlyphOrder() for n in DIRECT.values())
    assert set(DIRECT).isdisjoint(DEPEND) and set(DIRECT)|set(DEPEND)<=set(CHARS)
    params_path=Path('data/params.json');params=json.loads(params_path.read_text())
    # Correct a mislabeled old value: n's curved outline top is not xHeight.
    params['italic']['vertical']['flat_x']=master.xHeight
    params['italic']['vertical']['n_outline_top']=bounds(italic,'n')[3]
    study={'source_sha256':hashlib.sha256((ROOT/'sources/Instrument_Serif_Italic.glyphs').read_bytes()).hexdigest(),
        'master':{'x_height':master.xHeight,'cap_height':master.capHeight,'ascender':master.ascender,'descender':master.descender,'italic_angle_right':master.italicAngle},
        'post_angle':italic['post'].italicAngle,'caret_rise':italic['hhea'].caretSlopeRise,'caret_run':italic['hhea'].caretSlopeRun,
        'slant_dx_per_dy':math.tan(math.radians(master.italicAngle)),
        'donors':{}}
    exported_anchors={}
    for lookup in italic['GPOS'].table.LookupList.Lookup:
        for sub in lookup.SubTable:
            if hasattr(sub,'BaseCoverage'):
                exported_anchors.update({n:[None if a is None else [a.XCoordinate,a.YCoordinate] for a in r.BaseAnchor] for n,r in zip(sub.BaseCoverage.glyphs,sub.BaseArray.BaseRecord)})
    for name in sorted(set(DIRECT.values())|set('dfgijlmnpuHIOY')):
        layer=src.glyphs[name].layers[0];b=bounds(italic,name);rb=bounds(regular,name)
        study['donors'][name]={'source_advance':layer.width,'ttf_advance':italic['hmtx'][name][0],'ttf_bounds':b,
            'ttf_lsb':b[0],'ttf_rsb':italic['hmtx'][name][0]-b[2],
            'source_anchors':{a.name:list(a.position) for a in layer.anchors},'exported_gpos_anchor_classes':exported_anchors.get(name),
            'regular_advance':regular['hmtx'][name][0],'regular_bounds':rb}
    params['italic']['research']=study
    note='16.10.2026: Italic flat_x corrected to source master xHeight510; previous516 was n outline top, now n_outline_top. Added source master, donor bounds/advances/anchors and slant measurements; no outline changes.'
    revisions=params['meta'].setdefault('revisions',[])
    if note not in revisions:revisions.append(note)
    params_path.write_text(json.dumps(params,ensure_ascii=False,indent=1)+'\n')
    refs=[]
    for family,name in [('badscript','BadScript-Regular.ttf'),('marckscript','MarckScript-Regular.ttf')]:
        folder=CACHE/family;folder.mkdir(exist_ok=True)
        for filename in (name,'OFL.txt','METADATA.pb'):
            dest=folder/filename
            if not dest.exists():dest.write_bytes(urllib.request.urlopen(f'https://raw.githubusercontent.com/google/fonts/main/ofl/{family}/{filename}',timeout=30).read())
        meta=(folder/'METADATA.pb').read_text();font=TTFont(folder/name)
        assert all(ord(ch) in font.getBestCmap() for ch in 'гдийтмплншщ')
        previous=Path('data/italic-plan.json')
        if previous.exists():
            expected={r['font_path']:r['sha256'] for r in json.loads(previous.read_text())['references']}
            if str(folder/name) in expected:
                assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected[str(folder/name)],'Research font changed; review the new reference explicitly'
        refs.append({'reference_type':'handwriting','family':font['name'].getDebugName(1),'font_path':str(folder/name),
            'download_url':f'https://raw.githubusercontent.com/google/fonts/main/ofl/{family}/{name}',
            'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest(),
            'upstream_repository':re.search(r'repository_url: "([^"]+)"',meta).group(1),
            'upstream_commit_declared_by_metadata':re.search(r'commit: "([^"]+)"',meta).group(1),
            'license':'SIL OFL1.1; binary retained only in ignored study cache',
            'purpose':'Handwriting structure comparison; not an outline donor'})
    printed=Path('/usr/share/fonts/truetype/noto/NotoSerif-Italic.ttf')
    refs.append({'reference_type':'printed italic','family':'Noto Serif Italic','font_path':str(printed),
        'sha256':hashlib.sha256(printed.read_bytes()).hexdigest(),'purpose':'Installed printed-cursive comparison, not an outline donor'})
    # No binary reference fonts enter data/alphabet.json or the build manifest.
    plan={'status':'research and construction proposals, not an approved Italic alphabet','regular_reference':'1.005',
        'parameter_source':'data/params.json -> italic.research','references':refs,
        'direct_donor_candidates':DIRECT,'component_candidates':DEPEND,
        'custom_construction':[ch for ch in CHARS if ch not in DIRECT and ch not in DEPEND],
        'counts':{'total':len(CHARS),'direct_candidates':len(DIRECT),'component_candidates':len(DEPEND),
                  'custom_construction':len(CHARS)-len(DIRECT)-len(DEPEND)},
        'pilot_letters':list('гдитмплншцщ'),
        'default_russian_rules':{'п':'n-like','т':'m-like','и':'u-like','н':'transverse connection retained; never n',
            'м':'distinct central dip; never Latin m','д':'propose one-bowl handwritten g-like model; native two-story g is not a direct donor',
            'г':'flowing opposing turns; no mandatory upright Г silhouette'},
        'open_design_choices':['final д loop','л hook and м junction','з descender variant','italic drop-tail contour','context feature need after word tests']}
    Path('data/italic-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    # Normalize displayed x-height only for comparison, never mutate donors.
    width,height=2400,2200
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="#f5f2ec"/>']
    def label(x,y,s,size=28):svg.append(f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="#69656a">{escape(s)}</text>')
    label(45,60,'Исследование Italic · русская письменная структура и родные доноры',37)
    rows=[('Наш Regular1.005: преемственность',TTFont('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf'),'г д и й т м п л н ш щ','и'),
          ('Instrument Serif Italic: источники деталей',italic,'a e g i m n u k p q h','u'),
          ('Noto Serif Italic: печатный курсив, модель для сравнения',TTFont('/usr/share/fonts/truetype/noto/NotoSerif-Italic.ttf'),'г д и й т м п л н ш щ','и'),
          ('Bad Script: современная интерпретация почерка',TTFont(refs[0]['font_path']),'г д и й т м п л н ш щ','и'),
          ('Marck Script: другая интерпретация почерка',TTFont(refs[1]['font_path']),'г д и й т м п л н ш щ','и')]
    for i,(title,font,s,probe) in enumerate(rows):
        top=130+i*340;label(45,top,title);cm=font.getBestCmap();gs=font.getGlyphSet();h=bounds(font,cm[ord(probe)])[3];scale=130/h
        x=60;baseline=top+225
        svg.append(f'<path d="M45 {baseline} H2355" stroke="#ddd5ce"/>')
        for ch in s:
            if ch==' ':x+=45;continue
            name=cm[ord(ch)];pen=SVGPathPen(gs);gs[name].draw(pen)
            svg.append(f'<path transform="translate({x} {baseline}) scale({scale} {-scale})" fill="#272333" d="{pen.getCommands()}"/>');x+=font['hmtx'][name][0]*scale
    label(45,1935,'н ≠ п · м ≠ т · нижние повороты и/ш отличаются от верхних арок п/т',30)
    label(45,1990,'Рукописные примеры — анализ движения и различимости; контуры в наш шрифт не переносятся.',26)
    label(45,2040,'Bad Script: Project Authors / Gaslight; Marck Script: Denis Masharov & Marck Fogel. SIL OFL1.1.',23)
    label(45,2090,'Источники, SHA256 и лицензии: data/italic-plan.json; docs/research/italic-references/.',22)
    svg.append('</svg>');Path('docs/img/italic_research.svg').write_text('\n'.join(svg))
    print(json.dumps(plan['counts'],ensure_ascii=False));print('Master xHeight',master.xHeight,'n outline top',study['donors']['n']['ttf_bounds'][3])

if __name__=='__main__':main()
