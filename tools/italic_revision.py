#!/usr/bin/env python3
"""Apply only the author-approved 1.116 masters to the complete 1.115 geometry.

The ordinary source pipeline first reconstructs the prior accepted family. This
last drawing stage checks that input directly against the published baseline,
then installs twelve GLIFs. All spacing and the original em are retained.
"""
import copy,hashlib,io,json,subprocess,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
from functools import lru_cache
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.ufoLib.glifLib import readGlyphFromString

MANIFEST=Path('data/italic-revision-1.116.json')
TABLES=('cmap','GSUB','GPOS','GDEF','STAT','meta','cvt ','fpgm','prep','gasp','OS/2','hmtx')

def config():return json.loads(MANIFEST.read_text())

@lru_cache(maxsize=6)
def baseline(style,fmt):
    folder='webfonts' if fmt=='woff2' else fmt
    return subprocess.check_output(['git','show',config()['baseline_commit']+f':fonts/{folder}/VeryPeriSerif-{style}.{fmt}'])

def sources():
    result={}
    for name,record in config()['glyphs'].items():
        raw=Path(record['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==record['sha256'],('Accepted source hash',name)
        pen=TTGlyphPointPen(None);meta=SimpleNamespace();readGlyphFromString(raw.decode(),meta,pen)
        result[name]=(pen.glyph(),round(meta.width))
    return result

def verify_protected(font,style,allowed=()):
    old=TTFont(io.BytesIO(baseline(style,'ttf')))
    assert font.getGlyphOrder()==old.getGlyphOrder(),('Input glyph order',style)
    for name in old.getGlyphOrder():
        if name not in allowed:
            assert font['glyf'][name].compile(font['glyf'])==old['glyf'][name].compile(old['glyf']),('Protected outline/hints',style,name)
    for tag in TABLES:
        if tag in old:assert font.getTableData(tag)==old.getTableData(tag),('Protected table',style,tag)

def accepted(font):
    if not font['post'].italicAngle:return False
    if font['name'].getDebugName(5)!='Version '+config()['version']:return False
    for name,(glyph,advance) in sources().items():
        glyph.recalcBounds(font['glyf'])
        if font['glyf'][name].compile(font['glyf'])!=glyph.compile(font['glyf']):return False
    return True

def derived_glyphs(font,names):
    """CFF flattens composites, so synchronize users of the accepted masters."""
    all_names=set(names)
    while True:
        added={name for name in font.getGlyphOrder() if font['glyf'][name].isComposite()
               and all_names.intersection(font['glyf'][name].getComponentNames(font['glyf']))}-all_names
        if not added:return all_names-set(names)
        all_names.update(added)

def convert(src,dst):
    """Elevate twelve masters and their composite; preserve other CFF programs."""
    tt=TTFont(src);style='Italic' if tt['post'].italicAngle else 'Regular'
    records=sources() if style=='Italic' else {}
    verify_protected(tt,style,records)
    if records:assert accepted(tt),'CFF input must match all twelve accepted masters'
    derived=derived_glyphs(tt,records) if records else set()
    assert derived==({'uni0442.srb'} if records else set()),('Dependent CFF glyphs',derived)
    otf=TTFont(io.BytesIO(baseline(style,'otf')));otf.recalcTimestamp=False
    otf['name']=copy.deepcopy(tt['name'])
    for field in ('created','modified','fontRevision'):
        setattr(otf['head'],field,getattr(tt['head'],field))
    top=otf['CFF '].cff.topDictIndex[0];top.version=config()['version']
    top.FullName=tt['name'].getDebugName(4);top.FamilyName=tt['name'].getDebugName(1)
    cs=top.CharStrings;gs=tt.getGlyphSet()
    for name in sorted(set(records)|derived):
        original=cs[name];pen=T2CharStringPen(tt['hmtx'][name][0],gs,roundTolerance=0)
        pen.round=lambda v:round(v*65536)/65536
        gs[name].draw(ReverseContourPen(pen))
        cs[name]=pen.getCharString(private=original.private,globalSubrs=original.globalSubrs)
    otf.save(dst);return dst

def refresh_derived(root):
    """Keep make family's test pair and intermediate archive on final drawings."""
    cfg=json.loads(Path('data/params.json').read_text())['regular_release']
    tag='T'+cfg['version'].replace('.','');dest=Path('dist/test')
    for style in ('Regular','Italic'):
        font=TTFont(root/f'VeryPeriSerif-{style}.ttf');font.recalcTimestamp=False
        ps=f'VeryPeriSerif{tag}-{style}';family=cfg['family']+' '+tag
        values={1:family,3:f'{cfg["version"]};{cfg["vendor_id"]};{ps}',4:family+' '+style,6:ps}
        for record in font['name'].names:
            if record.nameID in values:record.string=values[record.nameID]
        font.save(dest/(ps+'.ttf'))
    # Revalidate the final serialized main and test pair, replacing the
    # previous stage's validation before embedding it in the archive.
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from build_family import validate
    report=root/'family-validation.json';data=json.loads(report.read_text())
    data['checks']=validate(root/'VeryPeriSerif-Regular.ttf',root/'VeryPeriSerif-Italic.ttf')
    data['test_pair']['checks']=validate(dest/f'VeryPeriSerif{tag}-Regular.ttf',dest/f'VeryPeriSerif{tag}-Italic.ttf')
    report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    archive=root/'VeryPeriSerif-Family.zip'
    with zipfile.ZipFile(archive) as previous:
        members=[info.filename.split('/',1)[1] for info in previous.infolist()
                 if info.filename!='VeryPeriSerif/SHA256SUMS-family.txt']
    payload={name:(root/name).read_bytes() for name in members}
    payload['SHA256SUMS-family.txt']=''.join(hashlib.sha256(raw).hexdigest()+'  '+name+'\n'
        for name,raw in sorted(payload.items())).encode()
    date=tuple(map(int,cfg['date'].split('-')))+(0,0,0)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
        for name,raw in sorted(payload.items()):
            info=zipfile.ZipInfo('VeryPeriSerif/'+name,date_time=date)
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            output.writestr(info,raw)
    with zipfile.ZipFile(archive) as output:
        assert output.testzip() is None
        assert all(output.read('VeryPeriSerif/'+name)==raw for name,raw in payload.items())

def main():
    root=Path('build/release');snapshot=Path('build/pre-revision-1.116');snapshot.mkdir(parents=True,exist_ok=True)
    for style in ('Regular','Italic'):
        path=root/f'VeryPeriSerif-{style}.ttf';raw=path.read_bytes();font=TTFont(io.BytesIO(raw));font.recalcTimestamp=False
        # The complete input, including all previous repairs and kerning, must
        # match the published baseline before any new source is installed.
        verify_protected(font,style)
        (snapshot/path.name).write_bytes(raw)
        if style=='Italic':
            for name,(glyph,advance) in sources().items():
                assert advance==font['hmtx'][name][0],name
                glyph.recalcBounds(font['glyf'])
                assert glyph.xMin==font['hmtx'][name][1],name
                font['glyf'][name]=glyph
            # The previous build stage generated its identity from the old
            # outlines. Bind the final unique identifier to the actual drawing.
            digest=hashlib.sha256(b''.join(font['glyf'][n].compile(font['glyf']) for n in font.getGlyphOrder())).hexdigest()[:12]
            for record in font['name'].names:
                if record.nameID==3:record.string=f'1.116;VPER;VeryPeriSerif-Italic;{digest}'
        font.save(path)
        web=TTFont(path);web.recalcTimestamp=False;web.flavor='woff2';web.save(path.with_suffix('.woff2'))
        convert(path,path.with_suffix('.otf'))
    report=root/'family-validation.json'
    if report.exists():
        d=json.loads(report.read_text())
        for style in ('Regular','Italic'):
            d[style.lower()]['sha256']=hashlib.sha256((root/f'VeryPeriSerif-{style}.ttf').read_bytes()).hexdigest()
        d['italic']['woff2_sha256']=hashlib.sha256((root/'VeryPeriSerif-Italic.woff2').read_bytes()).hexdigest()
        d['accepted_revision']={'manifest':str(MANIFEST),'glyphs':sorted(sources()),
            'derived_cff_glyphs':['uni0442.srb'],'spacing':'exactly 1.115','em':'exactly 1.115'}
        report.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    refresh_derived(root)
    print('Applied accepted 1.116 masters; all original metrics, kerning and em retained.')

if __name__=='__main__':main()
