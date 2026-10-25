#!/usr/bin/env python3
"""Full glyph-order candidate inventory; an error-free scan is not optical approval."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys
from fontTools.ttLib import TTFont
import outline_geometry as geom
from font_support import sha,digest,write_json

DEFAULT_RULES=copy.deepcopy(geom.RULES)


def audit(source,output,decisions=None,rules=None):
    geom.RULES.clear();geom.RULES.update(copy.deepcopy(DEFAULT_RULES))
    if rules:
        unknown=set(rules)-set(geom.RULES)
        if unknown:raise ValueError('Unknown detector rules: '+str(sorted(unknown)))
        for key,value in rules.items():
            values=value if isinstance(value,list) else [value]
            if not values or any(isinstance(v,bool) or not isinstance(v,(float,int)) or v<=0 for v in values):raise ValueError('Rules must be positive numeric values: '+key)
        geom.RULES.update(rules)
    font=TTFont(source);font_sha=sha(source)
    detector=digest({'rules':geom.RULES,'sources':{p:sha(Path(__file__).with_name(p)) for p in ('outline_geometry.py','audit_outlines.py')}})
    ledger=decisions or {};cache={};rows=[];cases=[];errors=[];unreviewed_forms=0;contours_total=0
    for name in font.getGlyphOrder():
        try:
            contours,closed=geom.read_outline(font,name);contours_total+=len(contours)
            shape=digest({'contours':geom.serialize(contours),'closed':closed})
            if shape not in cache:cache[shape]=geom.inspect_outline(contours,closed)[0]
            findings=copy.deepcopy(cache[shape]);review_key=digest([font_sha,name,shape,detector])[:24]
            form=ledger.get('forms',{}).get(review_key,{})
            current=lambda r:r.get('font_sha256')==font_sha and r.get('geometry_sha256')==shape and r.get('detector_sha256')==detector and bool(r.get('reason')) and bool(r.get('proofs'))
            reviewed=not contours or (form.get('status')=='reviewed' and current(form))
            if not reviewed:unreviewed_forms+=1
            for i,finding in enumerate(findings):
                case_id=digest([review_key,i,finding])[:24];decision=ledger.get('cases',{}).get(case_id,{})
                status=decision.get('status') if current(decision) and decision.get('status') in ('intentional','resolved') else 'unreviewed'
                cases.append({'id':case_id,'glyph':name,'font_sha256':font_sha,'geometry_sha256':shape,'detector_sha256':detector,'status':status,'evidence':finding})
            rows.append({'glyph':name,'geometry_sha256':shape,'contours':len(contours),'segments':sum(map(len,contours)),
                         'review_key':review_key,'whole_form_reviewed':reviewed,'candidates':len(findings)})
        except Exception as e:errors.append({'glyph':name,'error':type(e).__name__+': '+str(e)})
    unresolved=sum(c['status']=='unreviewed' for c in cases)
    report={'schema':1,'input':str(Path(source).resolve()),'font_sha256':font_sha,'detector_sha256':detector,
       'rules_1000_upm':geom.RULES,'thresholds_are_calibratable_candidate_heuristics':True,
       'summary':{'expected_glyphs':len(font.getGlyphOrder()),'parsed_glyphs':len(rows),'contours':contours_total,'unique_shapes':len(cache),'candidates':len(cases),'unresolved_candidates':unresolved,'unreviewed_whole_forms':unreviewed_forms,'errors':len(errors),'kinds':dict(Counter(c['evidence']['kind'] for c in cases))},
       'status':'scan_errors' if errors else 'review_pending' if unresolved or unreviewed_forms else 'ledger_review_complete',
       'candidates_are_not_confirmed_defects':True,'glyphs':rows,'cases':cases,'errors':errors}
    write_json(output,report);return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('font',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--decisions',type=Path);ap.add_argument('--rules',type=Path);ap.add_argument('--require-reviewed',action='store_true');args=ap.parse_args()
    try:r=audit(args.font,args.out,json.loads(args.decisions.read_text()) if args.decisions else None,json.loads(args.rules.read_text()) if args.rules else None)
    except (ValueError,KeyError) as e:ap.error(str(e))
    print(json.dumps({'report':str(args.out),'status':r['status'],**r['summary']}))
    if r['errors']:return 1
    if args.require_reviewed and r['status']!='ledger_review_complete':return 3
    return 0


if __name__=='__main__':sys.exit(main())
