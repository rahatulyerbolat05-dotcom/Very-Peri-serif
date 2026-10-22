#!/usr/bin/env python3
"""Independent acceptance of the reviewed curve release against 1.107."""
import hashlib,io,json,math,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from family_curve_audit import inspect,contours,angle,tangent_out
from polish_audit import segments
from curve_finish import load_source
import pathops


def shape(font,name):
    return contours(font,name)


def hard_corners(font,name):
    """Include all joins: a failed smoothing must not escape the small-kink band."""
    found=[]
    for ci,contour in enumerate(contours(font,name)):
        curves=segments(contour)
        for i,curve in enumerate(curves):
            a,b=tangent_out(curves[i-1],True),tangent_out(curve,False)
            degrees=abs(angle(a,b)) if a and b else 0
            if degrees>12:
                found.append({'xy':list(curve[1]),'degrees':degrees,'contour':ci})
    return found


def introduced_corners(old,new,name,translation=(0,0)):
    original=hard_corners(old,name)
    for point in original:
        point['xy']=[point['xy'][i]+translation[i] for i in (0,1)]
    return [p for p in hard_corners(new,name) if not any(
        q['contour']==p['contour'] and math.dist(p['xy'],q['xy'])<7
        and abs(p['degrees']-q['degrees'])<18 for q in original)]


def main():
    baseline='3cff781cad9b14141debcae90b2671f1d12c9dc2'
    manifest=json.loads(Path('data/curve-finish/manifest.json').read_text())
    version=json.loads(Path('data/params.json').read_text())['regular_release']['version']
    result={'baseline_commit':baseline,'version':version,'styles':{},'failed':0};checks=0
    def ck(ok,context):
        nonlocal checks
        assert ok,context
        checks+=1
    for style in ('Regular','Italic'):
        raw=Path(f'build/release/VeryPeriSerif-{style}.ttf').read_bytes();new=TTFont(io.BytesIO(raw))
        old=TTFont(io.BytesIO(subprocess.check_output(['git','show',f'{baseline}:fonts/ttf/VeryPeriSerif-{style}.ttf'])))
        native=TTFont(f'reference/instrument-serif/fonts/ttf/InstrumentSerif-{style}.ttf')
        ck(old.getGlyphOrder()==new.getGlyphOrder(),(style,'glyph order'))
        metrics=[n for n in new.getGlyphOrder() if old['hmtx'][n]!=new['hmtx'][n]]
        intentional_metrics={n:r for n,r in manifest['glyphs'][style].items()
                             if r.get('input_advance_and_lsb',r['advance_and_lsb'])!=r['advance_and_lsb']}
        ck(set(metrics)==set(intentional_metrics),(style,'unplanned metrics',metrics))
        for n,r in intentional_metrics.items():
            ck(list(old['hmtx'][n])==r['input_advance_and_lsb'] and list(new['hmtx'][n])==r['advance_and_lsb'],(style,'declared metrics',n))
        direct=[n for n in new.getGlyphOrder() if old['glyf'][n].compile(old['glyf'])!=new['glyf'][n].compile(new['glyf'])]
        expected=set(manifest['glyphs'][style])|set(manifest.get('derived_from_regular',{}).get(style,{}))
        ck(set(direct)==expected,(style,'unplanned outline changes',set(direct)^expected))
        geometric=[n for n in new.getGlyphOrder() if shape(old,n)!=shape(new,n)]
        for n in native.getGlyphOrder():
            ck(old['glyf'][n].compile(old['glyf'])==new['glyf'][n].compile(new['glyf']),(style,'native hints/outline',n))
        rows={}
        for n,r in manifest['glyphs'][style].items():
            g=new['glyf'][n];source=load_source(n,r)
            ck(g.getCoordinates(new['glyf'])==source.getCoordinates(new['glyf']),(style,'exact reviewed source',n))
            ck(g.numberOfContours==r['contours'],(style,'contours',n))
            before=inspect(old,n,.35,rough=False);after=inspect(new,n,.35,rough=False)
            ck(not any(p['degrees']>=5 for p in after['kinks']),(style,'remaining large tangent break',n,after['kinks']))
            ck(not after['micro'],(style,'remaining short step',n))
            short=lambda d:[p for p in d['waves'] if p['length']<30 and abs(p['turn'])<25]
            ck(not short(after),(style,'remaining short curvature reversal',n))
            introduced=introduced_corners(old,new,n,r.get('comparison_translation',(0,0)))
            ck(not introduced,(style,'introduced hard corner',n,introduced))
            def area(font):
                p=pathops.Path();font.getGlyphSet()[n].draw(p.getPen());return abs(p.area)
            a,b=area(old),area(new)
            ck(abs(b-a)/max(1,a)<r.get('maximum_relative_ink_area_change',.025),(style,'ink area drift',n,a,b))
            rows[n]={'before':before,'after':after,'relative_ink_area_change':round((b-a)/max(1,a),6),'bounds':r['bounds'],'outline_deviation':r['outline_deviation']}
        for n in manifest.get('derived_from_regular',{}).get(style,{}):
            ck(not introduced_corners(old,new,n),(style,'introduced hard corner in derived sign',n))
        result['styles'][style]={'sha256':hashlib.sha256(raw).hexdigest(),'all_glyphs_inventoried':len(new.getGlyphOrder()),'reviewed_direct_changes':direct,'inherited_component_changes':[n for n in geometric if n not in expected],'advance_or_bearing_changes':metrics,'native_outlines_and_hints_preserved':True,'glyphs':rows}
    # The new multi-curve detector must catch the defect accepted by the old node-only test.
    oldya=TTFont(io.BytesIO(subprocess.check_output(['git','show','aa705fd:fonts/ttf/VeryPeriSerif-Regular.ttf'])))
    ck(bool(inspect(oldya,'uni044F',.35,rough=False)['waves']),'1.106 ya regression')
    current=TTFont('build/release/VeryPeriSerif-Regular.ttf')
    ck(not inspect(current,'uni044F',.35,rough=False)['waves'],'accepted ya preserved')
    result['passed']=checks
    Path(f'docs/qa/curve-review-{version}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':checks,'failed':0,'styles':{s:{k:v for k,v in d.items() if k!='glyphs'} for s,d in result['styles'].items()}},ensure_ascii=False))


if __name__=='__main__':main()
