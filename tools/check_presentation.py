#!/usr/bin/env python3
"""Artifact checks and actual raster intersections between presentation texts."""
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import cairosvg
import numpy as np
from PIL import Image
from pypdf import PdfReader

ROOT=Path('docs/presentation')
SVG='http://www.w3.org/2000/svg'
ns={'s':SVG}


def main():
    m=json.loads((ROOT/'manifest.json').read_text())
    count=0; collision_candidates=0; ids=set(); details=[]
    def ck(value,label):
        nonlocal count
        assert value,label
        count+=1
    for face,path in [('R',Path('fonts/ttf/VeryPeriSerif-Regular.ttf')),('I',Path('fonts/ttf/VeryPeriSerif-Italic.ttf'))]:
        ck(hashlib.sha256(path.read_bytes()).hexdigest()==m['font_sha256'][face],('source font hash',face))
    for page in m['pages']:
        number=page['number'];path=ROOT/'slides'/f'{number:02d}.svg'
        svg=ET.fromstring(path.read_bytes());defs=svg.find('s:defs',ns);groups=svg.findall('s:g',ns)
        ck(svg.get('viewBox')=='0 0 1600 900',('slide size',number))
        ck(len(groups)==len(page['text_objects']),('text inventory',number))
        ck(not svg.findall('.//s:text',ns),('no external font requirement',number))
        for p in svg.findall('.//*[@id]'):
            ident=p.get('id');ck(bool(re.match(r'^[A-Za-z_][A-Za-z0-9_.-]*$',ident)),('valid SVG identifier',ident))
            ck(ident not in ids,('unique viewer identifier',ident));ids.add(ident)
        for use in svg.findall('.//s:use',ns):
            ref=use.get('{http://www.w3.org/1999/xlink}href')
            ck(ref and ref.startswith('#'),('no external glyph dependency',number))
        im=Image.open(ROOT/'previews'/f'{number:02d}.png')
        ck(im.size==(2400,1350),('preview resolution',number))
        cache={}
        for i,j in itertools.combinations(range(len(groups)),2):
            a,b=page['text_objects'][i],page['text_objects'][j]
            aa,bb=a['bounds'],b['bounds']
            iw=min(aa[2],bb[2])-max(aa[0],bb[0]);ih=min(aa[3],bb[3])-max(aa[1],bb[1])
            if iw<=0 or ih<=0:continue
            collision_candidates+=1
            for k in (i,j):
                if k not in cache:
                    group=copy.deepcopy(groups[k]);group.set('fill','#ffffff');group.set('opacity','1')
                    doc=ET.Element('{'+SVG+'}svg',{'width':'1600','height':'900','viewBox':'0 0 1600 900'})
                    doc.append(copy.deepcopy(defs));doc.append(group)
                    raw=cairosvg.svg2png(bytestring=ET.tostring(doc))
                    cache[k]=np.array(Image.open(io.BytesIO(raw)))[:,:,3]>127
            pixels=int(np.logical_and(cache[i],cache[j]).sum())
            ck(pixels==0,('unintended text intersection',number,a['text'],b['text'],pixels))
            details.append({'page':number,'texts':[a['text'],b['text']],'intersecting_pixels':pixels})
    pdf=PdfReader(ROOT/'VeryPeriSerif-Presentation.pdf')
    ck(len(pdf.pages)==14,'PDF slide count')
    ck(pdf.metadata.author=='Yerbolat Rakhatuly (DEW)','PDF author')
    for i,page in enumerate(pdf.pages):
        ck(tuple(float(v) for v in page.mediabox[2:])==(1200.,675.),('PDF aspect ratio',i))
        xobjects=page.get('/Resources',{}).get('/XObject',{})
        ck(not any(obj.get_object().get('/Subtype')=='/Image' for obj in xobjects.values()),('vector PDF',i))
    annotations=[a.get_object() for a in pdf.pages[-1].get('/Annots',[])]
    ck(any(a.get('/A',{}).get('/URI','').endswith('VeryPeriSerif-latest.zip') for a in annotations),'working PDF download annotation')
    with zipfile.ZipFile(ROOT/'VeryPeriSerif-Presentation.pptx') as z:
        ck(z.testzip() is None,'PPTX CRC')
        slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        ck(len(slides)==14,'PowerPoint slide count')
        vectors=[n for n in z.namelist() if n.startswith('ppt/media/vector') and n.endswith('.svg')]
        ck(len(vectors)==14,'PowerPoint vector slide count')
        for name in slides:
            root=ET.fromstring(z.read(name))
            ck(len(root.findall('.//{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip'))==1,('PowerPoint SVG plus PNG fallback',name))
    posters=list((ROOT/'social').glob('*.png'));ck(len(posters)==3,'poster count')
    for path in posters:ck(Image.open(path).size==(2160,2700),('poster resolution',path.name))
    with zipfile.ZipFile('dist/VeryPeriSerif-Presentation-1.114.zip') as z:
        ck(z.testzip() is None,'kit CRC')
        base='VeryPeriSerif-Presentation/'
        for line in z.read(base+'SHA256SUMS.txt').decode().splitlines():
            digest,name=line.split('  ',1)
            ck(hashlib.sha256(z.read(base+name)).hexdigest()==digest,('kit checksum',name))
    report={'passed':count,'failed':0,'slides':14,'social_posters':3,'pdf_vector':True,
            'source_font_version':'1.114','actual_text_intersection_candidates':collision_candidates,
            'text_intersections':details,'unintended_intersections':0,
            'pptx':'14 embedded SVG slides with PNG fallback; native Office not tested',
            'offline_viewer_browser_test':'Not completed: managed Chromium blocks file URL navigation; PDF and SVG rendering checked independently.',
            'visual_review':'Full-deck contact sheet, enlarged Kazakh and ss10 slides, social posters; independent PDF raster reviewed.'}
    Path('docs/qa/presentation-1.114.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='text_intersections'},ensure_ascii=False))


if __name__=='__main__':main()
