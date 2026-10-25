#!/usr/bin/env python3
"""Installable T<version> copies with stable names/timestamps and identical tables."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile
from fontTools.ttLib import TTFont
import ots


def main():
    cfg=json.loads(Path('data/params.json').read_text())['regular_release']
    version=cfg['version'];tag='T'+version.replace('.','');family=cfg['family']+' '+tag
    dest=Path('dist/test');dest.mkdir(exist_ok=True);members={}
    for style in ('Regular','Italic'):
        src=Path(cfg['directory'])/f'VeryPeriSerif-{style}.ttf';font=TTFont(src);font.recalcTimestamp=False
        ps=f'VeryPeriSerif{tag}-{style}'
        values={1:family,3:f'{version};{cfg["vendor_id"]};{ps}',4:family+' '+style,6:ps}
        for record in font['name'].names:
            if record.nameID in values:record.string=values[record.nameID]
        font['name'].names=[r for r in font['name'].names if r.nameID not in (16,17,21,22)]
        buffer=io.BytesIO();font.save(buffer);raw=buffer.getvalue();copy=TTFont(io.BytesIO(raw));original=TTFont(src)
        assert copy['name'].getDebugName(1)==family and copy['name'].getDebugName(2)==style
        assert copy['name'].getDebugName(5)=='Version '+version
        assert set(copy.keys())==set(original.keys())
        assert all(copy.getTableData(t)==original.getTableData(t) for t in copy.keys() if t not in ('GlyphOrder','name','head'))
        target=dest/(ps+'.ttf');target.write_bytes(raw)
        assert ots.sanitize(str(target),os.devnull,capture_output=True).returncode==0
        members[target.name]=raw
    for name in ('OFL.txt','AUTHORS.txt','CONTRIBUTORS.txt','FONTLOG.txt'):members[name]=Path(name).read_bytes()
    members['ai-disclosure.json']=Path('font/ai-disclosure.json').read_bytes()
    members['README.txt']=(f'{family}\n\nRenamed installation copy of Very Peri Serif {version}.\n'
        f'Переименованная копия Very Peri Serif {version} для отдельной установки.\n\n'
        f'Cyrillic author / Автор кириллицы: {cfg["cyrillic_author"]}.\n\n'
        f'Install both TTFs. Font-menu family / Имя в списке шрифтов: {family}.\n'
        'Regular and Italic. Outlines, kerning, ligatures and mark anchors match the release.\n'
        'Контуры, кернинг, лигатуры и ударения совпадают с основным выпуском.\n'
        'Only naming metadata differs / Изменены внутренние названия и идентификаторы.\n\n'
        'Licence / Лицензия: SIL Open Font License 1.1, OFL.txt.\n'
        f'Source / Исходники: {cfg["project_url"]}\n').encode()
    members['SHA256SUMS.txt']=''.join(hashlib.sha256(raw).hexdigest()+'  '+name+'\n' for name,raw in sorted(members.items())).encode()
    buffer=io.BytesIO();date=tuple(map(int,cfg['date'].split('-')))+(0,0,0)
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in sorted(members.items()):
            info=zipfile.ZipInfo(f'VeryPeriSerif-{tag}/'+name,date_time=date)
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,raw)
    archive=Path('dist')/f'VeryPeriSerif-{tag}.zip';raw=buffer.getvalue()
    if archive.exists():assert archive.read_bytes()==raw,'Existing renamed archives are immutable'
    else:archive.write_bytes(raw)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read(f'VeryPeriSerif-{tag}/'+name)==data for name,data in members.items())
    print(json.dumps({'archive':str(archive),'family':family,'sha256':hashlib.sha256(raw).hexdigest()}))


if __name__=='__main__':main()
