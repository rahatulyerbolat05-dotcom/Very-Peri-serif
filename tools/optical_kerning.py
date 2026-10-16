#!/usr/bin/env python3
"""Pair-specific optical refinement calibrated to the native font's spacing.
Raster edge profiles at 1000 px/em, all visible pairs involving added glyphs.
Never adjusts native/native pairs, whitespace, marks or source outlines.
"""
import copy,io,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

BUILD=Path('build/kerning')
Y=np.arange(-310,1001,2)


def profiles(font):
    f=copy.deepcopy(font);names=f.getGlyphOrder()
    for table in f['cmap'].tables:
        if table.isUnicode():
            table.cmap.update({0xE000+i:n for i,n in enumerate(names)})
    buf=io.BytesIO();f.save(buf);buf.seek(0)
    raster=ImageFont.truetype(buf,1000,layout_engine=ImageFont.Layout.BASIC)
    result={}
    for i,n in enumerate(names):
        advance=f['hmtx'][n][0]
        if advance<=0 or f['glyf'][n].numberOfContours==0:continue
        im=Image.new('L',(2400,1700));ImageDraw.Draw(im).text((500,1200),chr(0xE000+i),font=raster,fill=255,anchor='ls')
        ink=np.asarray(im)[1200-Y,:]>127
        valid=ink.any(axis=1)
        left=np.argmax(ink,axis=1).astype(float)-500
        right=ink.shape[1]-1-np.argmax(ink[:,::-1],axis=1).astype(float)-500+1
        result[n]=(left,right,valid,advance)
    return result


def gap_profile(a,b):
    return a[3]+b[0]-a[1],a[2]&b[2]


def optical(gap,valid,high):
    mask=valid&(Y>=40)&(Y<=high-35)
    if mask.sum()<12:mask=valid&(Y>=-20)&(Y<=900)
    if mask.sum()<5:return None
    g=gap[mask];small=float(g.min());temperature=55.
    # Soft minimum: near approaches dominate, while the full facing edge counts.
    return small-temperature*math.log(float(np.exp(-(g-small)/temperature).mean()))


def refine(font,native,records,native_kern,overrides):
    BUILD.mkdir(parents=True,exist_ok=True)
    actual=profiles(font);reference=profiles(native);allnames=list(actual)
    active={n:r for n,r in records.items() if n in actual and r['character']!='◌'}
    pairs={};report=[];cache={}
    def donor(n,side):return records[n]['donors'][side] if n in records else n
    def islower(n):
        ch=records[n]['character'] if n in records else ''
        if not ch:
            ch=next((chr(c) for c,g in native.getBestCmap().items() if g==n),'')
        return ch.islower()
    lower={n:islower(n) for n in allnames}
    nkcache={}
    def nk(a,b):
        if (a,b) not in nkcache:nkcache[a,b]=native_kern(native,a,b)
        return nkcache[a,b]
    for a in allnames:
        for b in allnames:
            if a not in active and b not in active:continue
            # Dotted-circle is a mark demonstration base, never a kerning partner.
            if a in records and records[a]['character']=='◌' or b in records and records[b]['character']=='◌':continue
            da,db=donor(a,1),donor(b,0)
            if da not in reference or db not in reference:continue
            high=510 if lower[a] or lower[b] else 720
            key=(da,db,high)
            if key not in cache:
                dg,dv=gap_profile(reference[da],reference[db]);dm=optical(dg,dv,high)
                donor_min=float(dg[dv].min()) if dv.any() else 1000
                donor_row=int(Y[np.flatnonzero(dv)[np.argmin(dg[dv])]]) if dv.any() else 0
                cache[key]=(dm,donor_min,nk(da,db),donor_row)
            target,donor_min,base,donor_row=cache[key]
            gap,valid=gap_profile(actual[a],actual[b]);current=optical(gap,valid,high)
            delta=0 if target is None or current is None else target-current
            # Limit extrapolation for substantially different skeletons.
            delta=max(-90.,min(90.,delta))
            requested=base+delta
            text=(records[a]['character'] if a in records else '')+(records[b]['character'] if b in records else '')
            # Reviewed pairs remain explicit decisions; geometry still protects them.
            if a in records and b in records and text in overrides:
                requested=overrides[text]+delta
            requested=max(-180,min(140,round(requested/2)*2))
            raw_min=float(gap[valid].min()) if valid.any() else 1000.
            # Retain native deliberate serif contacts, but prevent new collisions.
            current_row=int(Y[np.flatnonzero(valid)[np.argmin(gap[valid])]]) if valid.any() else 0
            native_contact=abs(delta)<3 and abs(current_row-donor_row)<=12
            minimum=min(5.,donor_min+base) if native_contact else max(1.,min(5.,donor_min+base))
            final=max(requested,math.ceil(minimum-raw_min))
            underlying=nk(a,b)
            additional=int(final-underlying)
            if abs(additional)<=2 and raw_min+underlying>=minimum:
                additional=0;final=underlying
            if additional:pairs[a,b]=additional
            report.append({'left':a,'right':b,'donors':[da,db],
                'optical_delta':round(delta,2),'requested':requested,'total':int(final),
                'additional':additional,'raw_min_gap':raw_min,'minimum_allowed':minimum,
                'final_min_gap':raw_min+final,'collision_limited':final!=requested})
    summary={'method':'Native-calibrated soft-min edge spacing; 2-unit row profiles; 1000 px/em; native contacts retained only for close optical-gap estimates and matching contact height.',
        'pairs_evaluated':len(report),'nonzero_additional_pairs':len(pairs),
        'collision_limited_pairs':sum(r['collision_limited'] for r in report),
        'visible_glyphs':len(allnames),'added_glyphs_kerned':len(active),
        'native_native_pairs_changed':0,'temperature':55,'optical_delta_limit':90,
        'minimum_final_gap':min(r['final_min_gap'] for r in report),
        'note':'Geometric refinement plus proof review; not a claim that all pairs were individually hand-tuned.'}
    (BUILD/'pairs.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n')
    Path('font/kerning-review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))
    return pairs,[{'left':r['left'],'right':r['right'],'requested':r['requested'],'actual':r['total']} for r in report if r['collision_limited']]
