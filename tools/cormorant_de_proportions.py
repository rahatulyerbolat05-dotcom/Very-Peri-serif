#!/usr/bin/env python3
"""Import the selected actual Cormorant de; change proportions only."""
import copy,hashlib,json,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
import pathops
from sketchlib import write_glif
from check_context_classes import test,test_top


def main():
    current=json.loads(Path('data/alphabet.json').read_text())
    if any(v['path'].startswith('data/width-refinement/') for section in ('user','codex') for e in current.get(section,{}).values() for v in e['variants']):
        print('Keeping width refinements; run tools/refine_widths.py to regenerate the active shapes.');return
    params=json.loads(Path('data/params.json').read_text());design=params['cormorant_de_proportions']
    r=next(r for r in json.loads(Path('data/de-reference-audit.json').read_text())['references'] if r['family_id']=='cormorantgaramond' and r['style']=='normal' and r['features']=={'ss10':1})
    source=Path('build/de-audit/cormorantgaramond')/r['filename']
    if not source.exists():
        import urllib.request
        source.parent.mkdir(parents=True,exist_ok=True)
        source.write_bytes(urllib.request.urlopen(r['url'],timeout=40).read())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==r['sha256']
    font=instantiateVariableFont(TTFont(source),r['axes'],inplace=False);gs=font.getGlyphSet()
    rec=RecordingPen();gs[r['glyph_name']].draw(rec);bounds=BoundsPen(gs);gs[r['glyph_name']].draw(bounds)
    sb=design['body_top']/bounds.bounds[3];hinge=design['tail_hinge'];out=Path('data/cormorant-de');out.mkdir(exist_ok=True)
    shutil.copyfile(r['license'],out/'OFL.txt')
    (out/'NOTICE.txt').write_text('Copyright 2015 the Cormorant Project Authors (github.com/CatharsisFonts/Cormorant)\nModified Cyrillic de from Cormorant Garamond Regular ss10, wght400.\nProportional derivatives for Very Peri Serif, 2026. SIL OFL 1.1, see OFL.txt.\n')
    variants=[]
    for v in design['variants']:
        sx=sb*v['width'];st=sb if v['tail_bottom'] is None else (v['tail_bottom']-hinge*sb)/(bounds.bounds[1]-hinge)
        dx=design['left_bearing']-bounds.bounds[0]*sx
        def mapped(x,y):return x*sx+dx,y*sb if y>=hinge else hinge*sb+(y-hinge)*st
        p=pathops.Path();pen=p.getPen();current=None
        for op,pts in rec.value:
            if op=='qCurveTo':
                ys=[current[1]]+[pt[1] for pt in pts]
                assert min(ys)>=hinge or max(ys)<=hinge,'Curve crosses the proportional hinge'
            if op=='lineTo' and (current[1]-hinge)*(pts[-1][1]-hinge)<0:assert abs(current[0]-pts[-1][0])<.001
            getattr(pen,op)(*(mapped(x,y) for x,y in pts))
            if pts:current=pts[-1]
        p=pathops.simplify(p,fix_winding=True,clockwise=True)
        adv=round(p.bounds[2]+design['right_bearing']);path=out/f"uni0434-{v['id']}.glif";write_glif(p,'uni0434',adv,0x434,str(path))
        variants.append(dict(path=str(path),variant=v['id'],label=v['label'],advance=adv,bounds=list(p.bounds),glif_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),transform=dict(x_scale=sx,body_y_scale=sb,tail_y_scale=st,hinge=hinge,x_offset=dx),status='proportion study; actual Cormorant outline'))
    cfg=json.loads(Path('data/alphabet.json').read_text());old=cfg['codex']['д']
    if old['variants'][0]['path'].split('/')[1]!='cormorant-de':cfg['rejected_drawings']['д-rejected-1.008']=copy.deepcopy(old)
    cfg['codex']['д']=dict(selected=design['selected'],shared_with_claude=False,conflict=False,variants=variants,provenance='Actual Cormorant de imported at explicit user request; proportion studies, OFL1.1')
    chosen=next(v for v in variants if v['variant']==design['selected'])
    ctx=json.loads(Path('data/context/serif_bl.json').read_text());ctx['built_bases']['д']=chosen['path']
    from check_context_classes import load
    p=load(chosen['path'])
    for rule,inside in [(ctx,test(p)[0]),(ctx['ka_short'],test_top(p)[0])]:
        members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
        if 'д' in members:members.remove('д')
        if 'д' in outside:outside.remove('д')
        (members if inside else outside).append('д')
    manifest=dict(source=r,source_bounds=list(bounds.bounds),variants=variants,selected=design['selected'],method='Original quadratic contours retained. Uniform horizontal scale; two vertical affine regions joined on straight stem only, below entire bowl. No redrawing.')
    for path,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),manifest)]:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
