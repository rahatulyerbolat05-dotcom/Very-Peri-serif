#!/usr/bin/env python3
"""[РЕШЕНИЕ] Rounded д with the native q bowl and j hook; printed д remains ss07."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from sketchlib import Ref,write_glif
from check_context_classes import test,test_top

def main():
    params=json.loads(Path('data/params.json').read_text());d=params['regular_de_tail']
    ref=Ref()
    # The native q bowl already has a designed junction with a descending stem.
    # Preserve its whole bowl and crown, replace only the lower serif by j's hook.
    # Both native stems are exactly 68 units; this is translation only.
    from sketchlib import AND,OR,SUB,rect,shift
    q=ref.glyph('q');j=shift(ref.glyph('j'),d['hook_dx'],0)
    cut=d['hook_join_y'];bowl_floor=d['bowl_floor']
    body=AND(q,rect(-1000,bowl_floor,2000,1000))
    # Keep the lower bowl but remove q's old vertical continuation below the
    # exact j tangent at y44, otherwise a tiny ledge survives near baseline.
    body=SUB(body,rect(d['inner_stem_x'],bowl_floor,2000,cut))
    hook=AND(j,rect(-1000,-1000,2000,cut))
    path=OR(body,hook)
    path=pathops.simplify(path,fix_winding=True,clockwise=True)
    out=Path('data/regular-de-tail');out.mkdir(exist_ok=True);target=out/'uni0434.glif'
    write_glif(path,'uni0434',d['advance'],0x434,str(target))
    cfg=json.loads(Path('data/alphabet.json').read_text())
    # Historical generator must not replace the author's later Cormorant choice.
    if cfg['codex']['д']['variants'][0]['path']=='data/regular-de-cormorant/uni0434.glif' or cfg['codex']['д']['variants'][0]['path'].startswith('data/cormorant-de/'):return
    cfg['stylistic_alternates']['д']=[{'path':'data/regular-de-refinement/uni0434.glif','feature':'ss07','source':'Codex','label':'Печатная д'}]
    item={'path':str(target),'variant':'01','label':'Округлая чаша, нижний крючок','advance':d['advance'],'bounds':list(path.bounds),'glif_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'status':'selected'}
    cfg['codex']['д']=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Codex; author requested a natural lower tail, 17.10.2026')
    ctx=json.loads(Path('data/context/serif_bl.json').read_text());ctx['built_bases']['д']=str(target)
    for rule,inside in [(ctx,test(path)[0]),(ctx['ka_short'],test_top(path)[0])]:
        members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
        if 'д' in members:members.remove('д')
        if 'д' in outside:outside.remove('д')
        (members if inside else outside).append('д')
    event='17.10.2026: основная д — округлая чаша q и родной нижний крючок j; печатная д1.006 сохранена как ss07.'
    if event not in ctx['history']:ctx['history'].append(event)
    manifest=dict(item,bowl_donor='Instrument Serif Regular q',hook_donor='Instrument Serif Regular j',hook_translation=[d['hook_dx'],0],hook_geometry='native quadratic controls, no scaling',printed_alternative=cfg['stylistic_alternates']['д'][0])
    for file,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(out/'manifest.json'),manifest)]:Path(file).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
