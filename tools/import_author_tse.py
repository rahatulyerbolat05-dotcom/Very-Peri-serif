#!/usr/bin/env python3
"""Import the corrected author Ц with the author's tail, preserving Beziers.

Run from repository root: python -I tools/import_author_tse.py [original.svg]
Only uniform conversion of body height714 to cap height720 is applied.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.svgLib.path import parse_path
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointPen import SegmentToPointPen,PointToSegmentPen
from fontTools.ufoLib.glifLib import writeGlyphToString,readGlyphFromString


def main():
    base=Path('data/author-tse-tail-2026-10-16');base.mkdir(parents=True,exist_ok=True)
    source=base/'ц заглавная.svg'
    if len(sys.argv)>1:
        incoming=Path(sys.argv[1])
        if source.exists():assert source.read_bytes()==incoming.read_bytes(),'Preserve existing original'
        else:shutil.copyfile(incoming,source)
    root=ET.fromstring(source.read_bytes());paths=root.findall('{http://www.w3.org/2000/svg}path')
    assert len(paths)==1 and not paths[0].get('transform')
    params=json.loads(Path('data/params.json').read_text());top=params['regular']['vertical']['flat_cap']
    k=top/714;matrix=(k,0,0,-k,19,top)
    rec=RecordingPen();parse_path(paths[0].attrib['d'],TransformPen(rec,matrix))
    bounds=BoundsPen(None);rec.replay(bounds);advance=round(bounds.bounds[2]+19)
    out=base/'uni0426-primary.glif'
    note='[РЕШЕНИЕ] Новая авторская Ц: вертикальные стойки, нижняя связь и собственный хвост пользователя. Исходные кривые сохранены; равномерное преобразование корпуса714→720, поле19. Без очистки и перерисовки. Интервалы предварительные.'
    out.write_text(writeGlyphToString('Tse-cy',SimpleNamespace(width=advance,unicodes=[0x426],note=note),
        lambda pp:rec.replay(SegmentToPointPen(pp)),formatVersion=2))
    back=RecordingPen();meta=SimpleNamespace()
    readGlyphFromString(out.read_text(),meta,PointToSegmentPen(back))
    canonical=RecordingPen();rec.replay(SegmentToPointPen(PointToSegmentPen(canonical)))
    assert canonical.value==back.value and meta.width==advance
    item={'character':'Ц','role':'primary','path':str(out),'source_name':source.name,
          'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'glif_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
          'transform':list(matrix),'advance':advance,'bounds':list(bounds.bounds),
          'status':'author corrected construction and tail; metrics provisional','note':note}
    cfg=json.loads(Path('data/alphabet.json').read_text())
    cfg.setdefault('user',{})['Ц']={'selected':'primary','origin':'user','variants':[item],
        'provenance':'авторский SVG пользователя','status':'author corrected Ц with own tail; source only'}
    context=json.loads(Path('data/context/serif_bl.json').read_text())
    from check_context_classes import load,test
    context['built_bases']['Ц']=str(out);inside=test(load(str(out)))[0]
    members=context['declared_class']['upper'];outside=context['expected_not_in_class']
    if 'Ц' in members:members.remove('Ц')
    if 'Ц' in outside:outside.remove('Ц')
    (members if inside else outside).append('Ц')
    event='16.10.2026: пользователь прислал исправленную вертикальную Ц со своим хвостом; активная основа заменена точным импортом SVG, классы перепроверены.'
    if event not in context['history']:context['history'].append(event)
    for target,data in [(base/'manifest.json',item),(Path('data/alphabet.json'),cfg),
                        (Path('data/context/serif_bl.json'),context)]:
        target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('Author Ц: exact GLIF roundtrip OK; bounds',bounds.bounds,'advance',advance)


if __name__=='__main__':main()
