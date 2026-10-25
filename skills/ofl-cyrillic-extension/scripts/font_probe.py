#!/usr/bin/env python3
"""Snapshot and measure one supplied font; no new glyphs or legal approval."""
import argparse
import html
import json
import math
from pathlib import Path
import shutil
import statistics
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen, ControlBoundsPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.svgPathPen import SVGPathPen
from font_support import CONTROL,PROOF_TEXT,TARGET,sha,glyph_signature,write_json
from outline_geometry import read_outline


def horizontal_runs(contours,y):
    """Approximate nonzero-winding ink intervals on one horizontal scanline."""
    events=[]
    for contour in contours:
        for segment in contour:
            _,xy=segment.flatten(tolerance=.025)
            for a,b in zip(xy,xy[1:]):
                if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):
                    x=float(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
                    events.append((round(x,9),1 if b[1]>a[1] else -1))
    grouped={}
    for x,d in events:grouped[x]=grouped.get(x,0)+d
    winding=0;start=None;runs=[]
    for x,d in sorted(grouped.items()):
        old=winding;winding+=d
        if old==0 and winding!=0:start=x
        if old!=0 and winding==0 and start is not None:runs.append([round(start,4),round(x,4)])
    if winding:raise ValueError('Unbalanced scanline winding')
    return runs


def bounds(gs,name,control=False):
    pen=(ControlBoundsPen if control else BoundsPen)(gs);gs[name].draw(pen)
    return list(pen.bounds) if pen.bounds is not None else None


def control_svg(font,gs,cm,path):
    chars=[ch for ch in CONTROL if ord(ch) in cm];scale=96/font['head'].unitsPerEm
    boxes=[bounds(gs,cm[ord(ch)]) for ch in chars];boxes=[b for b in boxes if b]
    ymax=max([b[3] for b in boxes]+[font['head'].unitsPerEm]);ymin=min([b[1] for b in boxes]+[0])
    width=max(145,max([b[2]-min(0,b[0]) for b in boxes]+[1000])*scale+48)
    height=max(150,(ymax-ymin)*scale+55);cols=7;rows=math.ceil(len(chars)/cols)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols*width:.2f}" height="{rows*height+60:.2f}" viewBox="0 0 {cols*width:.2f} {rows*height+60:.2f}">',
         '<rect width="100%" height="100%" fill="#f5f2ec"/>',
         '<text x="20" y="28" font-family="sans-serif" font-size="18">Native controls · 96 px, common scale · no Cyrillic generated</text>']
    for i,ch in enumerate(chars):
        x=(i%cols)*width;y=60+(i//cols)*height;base=y+25+ymax*scale
        name=cm[ord(ch)];box=bounds(gs,name) or [0,0,0,0];origin=x+20-min(0,box[0])*scale
        pen=SVGPathPen(gs);gs[name].draw(pen)
        svg += [f'<text x="{x+20:.2f}" y="{y+12:.2f}" font-family="sans-serif" font-size="12">{html.escape(ch)} · {html.escape(name)}</text>',
                f'<path d="M{x+10:.2f} {base:.2f}h{width-20:.2f}" stroke="#dbbcbc" fill="none"/>',
                f'<path d="{html.escape(pen.getCommands(),quote=True)}" transform="translate({origin:.8f},{base:.8f}) scale({scale:.12f},-{scale:.12f})" fill="#272333"/>']
    svg.append('</svg>');path.write_text('\n'.join(svg),encoding='utf8')


def probe(source,out,license_path=None,location=None,font_number=None):
    source=Path(source).resolve();out=Path(out);raw=source.read_bytes();identity=sha(raw)
    if raw[:4]==b'ttcf' and font_number is None:raise ValueError('Collection: explicitly choose --font-number')
    font=TTFont(source,fontNumber=font_number if font_number is not None else -1)
    axes={a.axisTag:a for a in font['fvar'].axes} if 'fvar' in font else {}
    location=location or {}
    for key,value in location.items():
        if key not in axes or not axes[key].minValue<=value<=axes[key].maxValue:raise ValueError('Invalid axis coordinate: '+key)
    existing=out/'font-profile.json'
    if existing.exists():
        old=json.loads(existing.read_text())
        if (old['input_sha256'],old['measurement_location'],old['font_number'])!=(identity,location,font_number):raise ValueError('Output belongs to another input or instance; choose a new --out')
    out.mkdir(parents=True,exist_ok=True);snapshot=out/'input';snapshot.mkdir(exist_ok=True)
    target=snapshot/(identity[:12]+'-'+source.name)
    if target.exists() and sha(target)!=identity:raise ValueError('Existing input snapshot changed')
    if not target.exists():shutil.copyfile(source,target)
    license_info={'status':'unverified','supplied_file':None,'sha256':None,'note':'Providing a file does not prove rights; inspect source/version, OFL terms and RFN.'}
    if license_path:
        lp=Path(license_path);dest=snapshot/('license-'+sha(lp)[:12]+'.txt')
        if not dest.exists():shutil.copyfile(lp,dest)
        license_info.update(supplied_file=str(dest),sha256=sha(lp))
    cm=font.getBestCmap() or {};gs=font.getGlyphSet(location=location or None)
    upm=font['head'].unitsPerEm;factor=1000/upm;os2=font.get('OS/2');measurements={}
    xheight=getattr(os2,'sxHeight',0) or None;capheight=getattr(os2,'sCapHeight',0) or None
    inferred={}
    if not xheight:
        tops=[b[3] for ch in 'xno' if ord(ch) in cm and (b:=bounds(gs,cm[ord(ch)]))]
        if tops:xheight=statistics.median(tops);inferred['x_height']='median ink top of available x/n/o; optical proxy, not nominal line'
    if not capheight:
        tops=[b[3] for ch in 'HIE' if ord(ch) in cm and (b:=bounds(gs,cm[ord(ch)]))]
        if tops:capheight=statistics.median(tops);inferred['cap_height']='median ink top of available H/I/E; proxy'
    for ch in CONTROL:
        if ord(ch) not in cm:continue
        name=cm[ord(ch)];b=bounds(gs,name);control=bounds(gs,name,True);area=AreaPen(gs);gs[name].draw(area)
        height=capheight if ch.isupper() else xheight;profiles={}
        if height:
            # For variable measurements getGlyphSet location affects outlines;
            # the generic reader uses the default instance, so leave profiles
            # uncomputed rather than silently mixing locations.
            if not location:
                cs,_=read_outline(font,name)
                for fraction in (.25,.5,.75):
                    y=height*factor*fraction;profiles[str(round(y,4))]=horizontal_runs(cs,y)
        measured=gs[name];measured.draw(BoundsPen(gs))
        measurements[ch]={'glyph':name,'advance':measured.width,'lsb':font['hmtx'][name][1] if not location else None,
            'source_default_hmtx':list(font['hmtx'][name]),'lsb_unmeasured_at_nondefault_location':bool(location),
            'true_bounds':b,'control_bounds':control,'signed_outline_area':area.value,
            'horizontal_ink_runs_1000_upm':profiles,'scanline_flatness_1000_upm':.025,
            'profiles_are_stroke_candidates_not_final_weight_measurements':True}
    profile={'schema':1,'input_file':str(source),'snapshot':str(target),'input_sha256':identity,'font_number':font_number,
       'measurement_location':location,'variable':bool(axes),'axes':{k:{'min':v.minValue,'default':v.defaultValue,'max':v.maxValue} for k,v in axes.items()},
       'variation_scope':'measurement only; no Cyrillic master or variable extension generated',
       'names':{str(i):font['name'].getDebugName(i) for i in (0,1,2,5,6,8,9,11,12,13,14)},
       'outline_type':'glyf' if 'glyf' in font else 'CFF2' if 'CFF2' in font else 'CFF' if 'CFF ' in font else 'unsupported',
       'units_per_em':upm,'glyph_count':len(font.getGlyphOrder()),'cmap':{f'U+{cp:04X}':n for cp,n in sorted(cm.items())},
       'heights':{'x_height':xheight,'cap_height':capheight,'ascender':getattr(os2,'sTypoAscender',None),'descender':getattr(os2,'sTypoDescender',None),'inferences':inferred},
       'declared_italic_angle':font['post'].italicAngle if 'post' in font else None,
       'slant_is_not_stress_axis':True,'license':license_info,
       'features':{tag:sorted({r.FeatureTag for r in font[tag].table.FeatureList.FeatureRecord}) if font[tag].table.FeatureList else [] for tag in ('GSUB','GPOS') if tag in font},
       'target_scope':'Russian + Kazakh codepoint inventory only; not a language/localization certification',
       'target_existing':{ch:cm[ord(ch)] for ch in TARGET if ord(ch) in cm},'target_missing':[ch for ch in TARGET if ord(ch) not in cm],
       'controls':measurements,'status':'measured_intake; design, legal and optical review pending'}
    write_json(existing,profile)
    # Raw signatures represent the supplied original/default font, not a synthetic instance.
    write_json(out/'native-baseline.json',{'input_sha256':identity,'units_per_em':upm,'glyphs':{n:glyph_signature(font,n) for n in font.getGlyphOrder()},'table_sha256':{t:sha(font.getTableData(t)) for t in font.keys() if t!='GlyphOrder'}})
    control_svg(font,gs,cm,out/'native-controls.svg');(out/'proof-text.txt').write_text(PROOF_TEXT,encoding='utf8')
    return {'profile':str(existing),'input_sha256':identity,'glyphs':len(font.getGlyphOrder()),'missing_ru_kz':len(profile['target_missing']),'status':profile['status']}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('font',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--license',type=Path);ap.add_argument('--font-number',type=int);ap.add_argument('--location',default='',help='wght=400,wdth=100; measurement only')
    args=ap.parse_args();location={}
    for item in filter(None,args.location.split(',')):
        key,value=item.split('=',1);location[key]=float(value)
    try:result=probe(args.font,args.out,args.license,location,args.font_number)
    except (ValueError,KeyError) as e:ap.error(str(e))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
