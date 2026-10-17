#!/usr/bin/env python3
"""Make a side-by-side test copy of the release TTF under a distinct family name.
The release name stays untouched; the test copy can be installed next to any older
Very Peri Serif without the editor or the OS font cache mixing them up.
Usage: python3 -I tools/make_test_copy.py [tag]   (default tag = release version without dot)
"""
import json,sys
from pathlib import Path
from fontTools.ttLib import TTFont

config=json.loads(Path('data/params.json').read_text())['regular_release']
tag=sys.argv[1] if len(sys.argv)>1 else 'T'+config['version'].replace('.','')
source=Path(config['directory'])/'VeryPeriSerif-Regular.ttf'
out=Path(config['directory']).parent/'test';out.mkdir(exist_ok=True)
font=TTFont(source);family=f"Very Peri Serif {tag}";ps=f"VeryPeriSerif{tag}-Regular"
for record in font['name'].names:
    if record.nameID==1:record.string=family
    elif record.nameID==3:record.string=f"{config['version']};{config['vendor_id']};{ps}"
    elif record.nameID==4:record.string=f"{family} Regular"
    elif record.nameID==6:record.string=ps
font['name'].names=[r for r in font['name'].names if r.nameID not in (16,17,21,22)]
target=out/f"VeryPeriSerif{tag}-Regular.ttf";font.save(target);print(target,family,config['version'])
