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
ADJUST=json.loads(Path('font/kerning-adjust.json').read_text())['pairs']   # reviewed per-pair corrections
EQ_WEIGHT=0.6   # fraction of the distance to the Cyrillic median applied
EQ_LIMIT=40.    # largest equalizing shift, font units
EQ_OFFSET=-8.   # keeps the mean Cyrillic gap where the donor spacing had it
FOOT_MIN=10.    # all Cyrillic/Cyrillic pairs: feet and serifs must not fuse, whatever the donor allowed
Y=np.arange(-310,1001)   # every pixel row: serif tips meeting round tops differ by several units between neighbouring rows


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
    if mask.sum()<24:mask=valid&(Y>=-20)&(Y<=900)
    if mask.sum()<10:return None
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
    # Glyphs whose outline and advance are identical to a native Latin glyph (homoglyphs such as
    # А В Е К М Н О Р С Т Х а е о р с у х) must kern exactly like it, in every pairing.
    ident={}
    for n in allnames:
        if n not in active:
            ident[n]=n;continue
        for m in reference:
            ra,rb=actual[n],reference[m]
            if ra[3]==rb[3] and np.array_equal(ra[2],rb[2]) and np.array_equal(ra[0][ra[2]],rb[0][rb[2]]) and np.array_equal(ra[1][ra[2]],rb[1][rb[2]]):
                ident[n]=m;break
    nkcache={}
    def nk(a,b):
        if (a,b) not in nkcache:nkcache[a,b]=native_kern(native,a,b)
        return nkcache[a,b]
    # Cyrillic lowercase pairs inherit spacing from different Latin donors, so
    # their optical gaps scatter more than the native Latin ones. Pull each
    # donor target part of the way to the script median (bounded, collision
    # limits below still apply).
    def pair_target(a,b):
        da,db=donor(a,1),donor(b,0)
        if da not in reference or db not in reference:return None
        dg,dv=gap_profile(reference[da],reference[db]);return optical(dg,dv,510)
    cyr_pairs=[(a,b) for a in active for b in active if lower[a] and lower[b]]
    raw_targets={p:pair_target(*p) for p in cyr_pairs}
    valid_targets=[t for t in raw_targets.values() if t is not None]
    median_target=float(np.median(valid_targets)) if valid_targets else 0.
    equalized=0;native_overlaps=0
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
            if target is not None and (a,b) in raw_targets:
                shift=max(-EQ_LIMIT,min(EQ_LIMIT,EQ_WEIGHT*(median_target+EQ_OFFSET-target)))
                target+=shift;equalized+=abs(shift)>=1
            gap,valid=gap_profile(actual[a],actual[b]);current=optical(gap,valid,high)
            delta=0 if target is None or current is None else target-current
            # Limit extrapolation for substantially different skeletons.
            delta=max(-90.,min(90.,delta))
            requested=base+delta
            text=(records[a]['character'] if a in records else '')+(records[b]['character'] if b in records else '')
            # Reviewed pairs remain explicit decisions; geometry still protects them.
            if a in records and b in records and text in overrides:
                requested=overrides[text]+delta
            if a in records and b in records:requested+=ADJUST.get(text,0)
            requested=max(-180,min(140,round(requested/2)*2))
            raw_min=float(gap[valid].min()) if valid.any() else 1000.
            # Retain native deliberate serif contacts, but prevent new collisions.
            current_row=int(Y[np.flatnonzero(valid)[np.argmin(gap[valid])]]) if valid.any() else 0
            native_contact=abs(delta)<3 and abs(current_row-donor_row)<=12
            minimum=min(5.,donor_min+base) if native_contact else max(1.,min(5.,donor_min+base))
            final=max(requested,math.ceil(minimum-raw_min))
            # Body, upper heads and descenders must not fuse, even if the native
            # donor allowed a serif overlap. Baseline feet retain native contacts.
            protected=valid&((Y>=55)|(Y<=-25))
            protected_min=float(gap[protected].min()) if protected.any() else 1000.
            final=max(final,math.ceil(8-protected_min))
            if a in active and b in active:final=max(final,math.ceil(FOOT_MIN-raw_min))
            identical=False
            if (a in active or b in active) and a in ident and b in ident:
                native_final=nk(ident[a],ident[b])
                # exactly the native Latin pair value, unless the native pair itself touches or overlaps the bodies (clearance under 3 units)
                if raw_min+native_final>=3:final=native_final;identical=True
                else:native_overlaps+=1
            underlying=nk(a,b)
            additional=int(final-underlying)
            if not identical and abs(additional)<=2 and raw_min+underlying>=minimum and protected_min+underlying>=8 and not(a in active and b in active and raw_min+underlying<FOOT_MIN):
                additional=0;final=underlying
            if additional:pairs[a,b]=additional
            report.append({'left':a,'right':b,'donors':[da,db],
                'optical_delta':round(delta,2),'requested':requested,'total':int(final),
                'additional':additional,'identical_to_native':identical,'raw_min_gap':raw_min,'minimum_allowed':minimum,
                'final_min_gap':raw_min+final,'protected_gap':protected_min+final,'collision_limited':final!=requested})
    summary={'method':'Native-calibrated soft-min edge spacing; 2-unit row profiles; 1000 px/em; native contacts retained only for close optical-gap estimates and matching contact height.',
        'pairs_evaluated':len(report),'nonzero_additional_pairs':len(pairs),
        'collision_limited_pairs':sum(r['collision_limited'] for r in report),
        'visible_glyphs':len(allnames),'added_glyphs_kerned':len(active),
        'native_native_pairs_changed':0,'temperature':55,'optical_delta_limit':90,
        'identical_homoglyph_pairs':sum(r['identical_to_native'] for r in report),'native_pairs_overlapping_kept_protected':native_overlaps,'cyrillic_equalization':{'weight':EQ_WEIGHT,'limit':EQ_LIMIT,'offset':EQ_OFFSET,'foot_min':FOOT_MIN,'median_target':round(median_target,2),'pairs_shifted':int(equalized)},
        'minimum_final_gap':min(r['final_min_gap'] for r in report),'minimum_protected_gap':min(r['protected_gap'] for r in report),
        'note':'Geometric refinement plus proof review; not a claim that all pairs were individually hand-tuned.'}
    (BUILD/'pairs.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n')
    Path('font/kerning-review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))
    return pairs,[{'left':r['left'],'right':r['right'],'requested':r['requested'],'actual':r['total']} for r in report if r['collision_limited']]
