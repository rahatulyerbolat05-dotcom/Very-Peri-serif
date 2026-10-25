#!/usr/bin/env python3
"""Publish the release in the layout of the Instrument Serif repository (and of Google Fonts family repositories):
  fonts/ttf/VeryPeriSerif-{Regular,Italic}.ttf      TrueType, from regular_release.directory (tools/build_regular_release.py, tools/build_family.py)
  fonts/otf/VeryPeriSerif-{Regular,Italic}.otf      OpenType CFF (tools/ttf2otf.py, checked against the TTF)
  fonts/webfonts/*.woff2, very-peri-serif.css       WOFF2 and an @font-face stylesheet
  docs/qa/                                          the validation reports of the builds and of this step (package-check.json)
  docs/specimen/VeryPeriSerif-Regular-Specimen.pdf
  dist/VeryPeriSerif-<version>.zip                  the download: one folder VeryPeriSerif-<version>/ with
      README.txt OFL.txt AUTHORS.txt CONTRIBUTORS.txt FONTLOG.txt ai-disclosure.json SHA256SUMS.txt fonts/{ttf,otf,webfonts}/ specimen/
Licence checks (docs/legal-review.md): OFL.txt opens with the copyright lines of name ID 0 and carries the official OFL 1.1 text unchanged
(compared with the copies shipped by Instrument and Cormorant); every font has the OFL in name IDs 13/14, the AI note in name ID 10, fsType 0;
the Cormorant line only where its outline is (the Regular). Every font passes the OpenType Sanitizer.
Usage: python3 -I tools/package_release.py
"""
import base64,hashlib,io,json,os,re,shutil,subprocess,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
import ots
import ttf2otf

CONFIG=json.loads(Path('data/params.json').read_text())['regular_release']
SRC=Path(CONFIG['directory']);FONTS=Path(CONFIG['release_directory']);DIST=Path(CONFIG['release_archive']);QA=Path('docs/qa')
STYLES=('Regular','Italic');LEGAL=('OFL.txt','AUTHORS.txt','CONTRIBUTORS.txt','FONTLOG.txt')
REPORTS=('build-manifest.json','validation.json','kerning-validation.json','release-validation.json','quality-summary.json','family-validation.json','family-acceptance.json','fontbakery-universal.json','optical-review.json')
OFL_COPIES=('reference/instrument-serif/OFL.txt','data/cormorant-de/OFL.txt')
CSS="""/* Very Peri Serif {version}. SIL Open Font License 1.1, see OFL.txt. */
@font-face {{
  font-family: "Very Peri Serif";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("VeryPeriSerif-Regular.woff2") format("woff2");
}}
@font-face {{
  font-family: "Very Peri Serif";
  font-style: italic;
  font-weight: 400;
  font-display: swap;
  src: url("VeryPeriSerif-Italic.woff2") format("woff2");
}}
"""
README="""Very Peri Serif {version}
{line}

A Cyrillic extension of Instrument Serif: Russian and Kazakh in the Regular and the Italic.
Кириллическое расширение Instrument Serif: русский и казахский, начертания Regular и Italic.
Author of the Cyrillic extension / Автор кириллического расширения: {author}.

Install / Установка
  Desktop (Windows, macOS, Linux, Figma, Adobe, Office): install both files from fonts/ttf
  (or fonts/otf; install one format, not both).
  Компьютер: установите оба файла из fonts/ttf (или fonts/otf; один формат, не оба).
  Web / сайт: fonts/webfonts, connect very-peri-serif.css.

Versions: Regular {regular}, Italic {italic}. Russian, Kazakh and inherited Latin; designed for display use.
Версии: Regular {regular}, Italic {italic}. Русский, казахский и исходная латиница; акцидентный шрифт.
Tabular figures: enable tnum. / Табличные цифры: включите tnum.
family.html is a live-font specimen. Family-Specimen.pdf contains outline examples of both styles and features.
family.html — образец с живым текстом; Family-Specimen.pdf — векторные образцы обоих начертаний и функций.

Licence / Лицензия
  SIL Open Font License 1.1 (OFL.txt). Free to use in any work, commercial included: print, logos, sites, apps.
  The font file itself may not be sold on its own; a modified version must stay under the OFL, and the names
  of the authors may not be used to promote it without their permission. The exact conditions are in OFL.txt.
  Можно использовать в любых работах, в том числе коммерческих. Нельзя продавать сам файл шрифта отдельно;
  изменённая версия остаётся под OFL, имена авторов нельзя использовать для её рекламы без их согласия.
  Точные условия в OFL.txt.

AI / ИИ
  The Cyrillic outlines were made with AI assistance (Anthropic Claude, OpenAI Codex) under the direction of the
  author; the Latin is Instrument Serif, unchanged. ai-disclosure.json, FONTLOG.txt.
  Кириллица сделана с помощью ИИ под руководством автора; латиница Instrument Serif не изменена.

Authors / Авторы: AUTHORS.txt, CONTRIBUTORS.txt. Source / Исходники: {url}
"""


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ofl_body(path):return Path(path).read_text().split('-----------------------------------------------------------',1)[1]


def check_licence(fonts):
    checks={};ck=lambda label,ok:checks.__setitem__(label,bool(ok))
    text=Path('OFL.txt').read_text();head=text.split('\n\nThis Font Software')[0].splitlines()
    for p in OFL_COPIES:
        if Path(p).exists():ck('OFL.txt body is the official OFL 1.1 text ('+p+')',ofl_body('OFL.txt')==ofl_body(p))
    ck('OFL.txt preamble names OFL 1.1 and its FAQ address','This Font Software is licensed under the SIL Open Font License, Version 1.1.' in text and 'https://openfontlicense.org' in text)
    lines=CONFIG['copyright'].split(', Copyright ');lines=[lines[0]]+['Copyright '+x for x in lines[1:]]
    ck('OFL.txt opens with the project copyright lines',head[:len(lines)]==lines)
    ck('OFL.txt carries the Cormorant line',CONFIG['copyright_cormorant'].split(': ',1)[1] in text)
    ck('no Reserved Font Name claimed','Reserved Font Name' not in '\n'.join(head))
    for style,f in fonts.items():
        n=f['name'];c=n.getDebugName(0)
        ck(style+': name 0 = project copyright'+(' + Cormorant' if style=='Regular' else ''),c==(CONFIG['copyright']+'; '+CONFIG['copyright_cormorant'] if style=='Regular' else CONFIG['copyright']))
        ck(style+': name 13/14 OFL 1.1',n.getDebugName(13).startswith('This Font Software is licensed under the SIL Open Font License, Version 1.1') and n.getDebugName(14)=='https://openfontlicense.org')
        ck(style+': name 10 AI note',CONFIG['ai_note'] in (n.getDebugName(10) or ''))
        ck(style+': full Cyrillic author in designer metadata',CONFIG['cyrillic_author'] in (n.getDebugName(9) or ''))
        ck(style+': manufacturer identity',n.getDebugName(8)==CONFIG.get('manufacturer','Very Peri Serif project'))
        ck(style+': name 1 not Instrument Serif',n.getDebugName(1)=='Very Peri Serif' and 'Instrument' not in n.getDebugName(6))
        ck(style+': installable and editable (fsType 0)',f['OS/2'].fsType==0)
    for p in LEGAL:ck(p+' present',Path(p).exists())
    ck('AUTHORS.txt names the Cyrillic author',CONFIG['cyrillic_author'] in Path('AUTHORS.txt').read_text())
    json.loads(Path('font/ai-disclosure.json').read_text());ck('ai-disclosure.json is valid JSON',True)
    return checks


def main():
    approved=json.loads(Path('data/premium-decisions.json').read_text()).get('approved_fonts',{})
    current={s:sha(SRC/f'VeryPeriSerif-{s}.ttf') for s in STYLES}
    if approved!=current:raise RuntimeError('Optical review is not current: inspect the proofs and record the accepted font hashes in data/premium-decisions.json')
    for d in ('ttf','otf','webfonts'):(FONTS/d).mkdir(parents=True,exist_ok=True)
    QA.mkdir(parents=True,exist_ok=True);Path('docs/specimen').mkdir(parents=True,exist_ok=True);DIST.mkdir(exist_ok=True)
    italic_version=TTFont(SRC/'VeryPeriSerif-Italic.ttf')['name'].getDebugName(5).replace('Version ','')
    files={};otf_checks={}
    for s in STYLES:
        ttf=FONTS/'ttf'/f'VeryPeriSerif-{s}.ttf';shutil.copyfile(SRC/ttf.name,ttf)
        woff=FONTS/'webfonts'/f'VeryPeriSerif-{s}.woff2';shutil.copyfile(SRC/woff.name,woff)
        otf=FONTS/'otf'/f'VeryPeriSerif-{s}.otf';ttf2otf.convert(ttf,otf);otf_checks[s]=ttf2otf.check(ttf,otf)
        assert not otf_checks[s]['over_limit'],otf_checks[s]
        files[s]=(ttf,otf,woff)
    (FONTS/'webfonts'/'very-peri-serif.css').write_text(CSS.format(version=CONFIG['version']))
    for r in REPORTS:
        if (SRC/r).exists():shutil.copyfile(SRC/r,QA/r)
    specimen=Path('docs/specimen/VeryPeriSerif-Regular-Specimen.pdf');shutil.copyfile(SRC/'specimen.pdf',specimen)
    family_specimen=Path('docs/specimen/VeryPeriSerif-Family-Specimen.pdf');shutil.copyfile(SRC/'family-specimen.pdf',family_specimen)
    if '--browser' in sys.argv:subprocess.run(['node','tools/check_browser.cjs'],check=True)
    checks=check_licence({s:TTFont(files[s][0]) for s in STYLES})
    for s in STYLES:
        for p in files[s]:
            r=ots.sanitize(str(p),os.devnull,capture_output=True);checks['OpenType Sanitizer '+p.name]=r.returncode==0
        checks[s+': WOFF2 = TTF tables']=all(TTFont(files[s][2]).getTableData(t)==TTFont(files[s][0]).getTableData(t) for t in TTFont(files[s][0]).keys() if t not in ('GlyphOrder','head'))
    if not all(checks.values()):raise RuntimeError('Package validation failed: '+str([k for k,v in checks.items() if not v]))
    for name in ('family-acceptance.json','quality-summary.json'):
        assert (SRC/name).exists(), 'Run make quality before packaging'
    qa=json.loads((SRC/'quality-summary.json').read_text())
    assert qa['fonts']=={p.name:sha(p) for s in STYLES for p in files[s] if p.suffix=='.ttf'}, 'QA is stale'
    acceptance=json.loads((SRC/'family-acceptance.json').read_text())
    assert acceptance['failed']==0 and {r['style']:r['sha256'] for r in acceptance['fonts']}==current, 'Functional acceptance is stale'
    optical=json.loads((SRC/'optical-review.json').read_text())
    assert {s:r['sha256'] for s,r in optical['styles'].items()}==current, 'Optical measurements are stale'
    # Embed WOFF2 in the downloadable specimen so it also opens offline as a
    # file:// document, without cross-origin restrictions on adjacent files.
    live=Path('docs/specimen/family.html').read_text()
    for s in STYLES:
        woff=FONTS/'webfonts'/f'VeryPeriSerif-{s}.woff2'
        live=live.replace('../../fonts/webfonts/'+woff.name,'data:font/woff2;base64,'+base64.b64encode(woff.read_bytes()).decode())
    # the download
    root=f'VeryPeriSerif-{CONFIG["version"]}';title=f'Very Peri Serif {CONFIG["version"]}'
    members={'README.txt':README.format(version=CONFIG['version'],line='='*len(title),regular=CONFIG['version'],italic=italic_version,url=CONFIG['project_url'],author=CONFIG['cyrillic_author']).encode(),
             'ai-disclosure.json':Path('font/ai-disclosure.json').read_bytes(),'specimen/'+specimen.name:specimen.read_bytes(),
             'specimen/'+family_specimen.name:family_specimen.read_bytes(),
             # Inside the archive fonts/ is one level above specimen/.
             'specimen/family.html':live.encode()}
    for p in LEGAL:members[p]=Path(p).read_bytes()
    for s in STYLES:
        for p in files[s]:members['fonts/'+p.parent.name+'/'+p.name]=p.read_bytes()
    members['fonts/webfonts/very-peri-serif.css']=(FONTS/'webfonts'/'very-peri-serif.css').read_bytes()
    members['SHA256SUMS.txt']=''.join(hashlib.sha256(members[m]).hexdigest()+'  '+m+'\n' for m in sorted(members)).encode()
    archive=DIST/f'{root}.zip';date=tuple(map(int,CONFIG['date'].split('-')))+(0,0,0)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        dirs={root+'/'}|{root+'/'+'/'.join(m.split('/')[:k])+'/' for m in members for k in range(1,m.count('/')+1)}
        for d in sorted(dirs):
            info=zipfile.ZipInfo(d,date_time=date);info.external_attr=0o40755<<16;z.writestr(info,b'')
        for m in sorted(members):
            info=zipfile.ZipInfo(root+'/'+m,date_time=date);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,members[m])
    content=buffer.getvalue()
    if archive.exists():
        if archive.read_bytes()!=content:
            raise RuntimeError(f'{archive} already exists with different content; increment the family version. Existing releases are immutable.')
    else:archive.write_bytes(content)
    with zipfile.ZipFile(archive) as z:
        checks['archive opens and every member is intact']=z.testzip() is None
        checks['archive fonts identical to fonts/']=all(z.read(root+'/fonts/'+p.parent.name+'/'+p.name)==p.read_bytes() for s in STYLES for p in files[s])
    report=dict(version=CONFIG['version'],italic_version=italic_version,archive=str(archive),archive_sha256=sha(archive),
                members=sorted(members),otf=otf_checks,checks=checks,passed=sum(checks.values()),failed=[k for k,v in checks.items() if not v])
    (QA/'package-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(archive=str(archive),passed=report['passed'],failed=report['failed'],otf={s:otf_checks[s]['hausdorff_worst'] for s in STYLES}),ensure_ascii=False))
    if report['failed']:sys.exit(1)


if __name__=='__main__':main()
