#!/usr/bin/env python3
"""Make the upper part of т canonical (author, 1.015): the arches, valleys and the head flag are the native Latin m
outline itself; only the right stem keeps the hooked foot of т. The old т was narrower than m (stem pitch 230 vs 242) and
its arch shoulders differed from m. Cut at CUT_Y just above the hook bracket; the hook part is shifted and scaled
(about 1.5 percent across the stem) so that its edges meet the stem of m exactly. Inputs pinned by SHA256, old
outlines archived (rejected_drawings 'before-te-canon').
"""
import copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from audit_author_glyphs import inspect,runs
from finish_regular import load
from sketchlib import Ref,AND,OR,SUB,rect,tf,write_glif
from alphabet_sheet import source_items
from check_context_classes import test,test_top

OUT=Path('data/te-canon');CUT_Y=100   # the old т has a clean vertical stem above y=95 (534-602); below it the edges flare into the hook


def build(source):
    te,adv=load(source);m=Ref().glyph('m')
    tr=runs(te,CUT_Y);mr=runs(m,CUT_Y);xl_t,xr_t=[r for r in tr if r[1]-r[0]>=60][-1];xl_m,xr_m=[r for r in mr if r[1]-r[0]>=60][-1]
    s=(xr_m-xl_m)/(xr_t-xl_t);hook=tf(OR(AND(te,rect(xl_t-1,-400,2000,CUT_Y)),AND(te,rect(xr_t+3,-400,2000,2000))),(s,0,0,1,xl_m-s*xl_t,0))   # the tip of the hook rises above the cut
    top=SUB(m,rect(xl_m-80,-400,2000,CUT_Y))   # also removes the left foot serif of the third stem: the т has none
    new=pathops.simplify(OR(top,hook),fix_winding=True,clockwise=True)
    lsb=te.bounds[0];rsb=adv-te.bounds[2]
    shift=lsb-new.bounds[0];new=tf(new,(1,0,0,1,shift,0))
    return new,new.bounds[2]+rsb,dict(scale=round(s,4),stem_before=[xl_t,xr_t],stem_m=[xl_m,xr_m],pitch_before=[round(a-b) for a,b in zip([r[0] for r in tr[1:]],[r[0] for r in tr[:-1]])],pitch_after=[round(a-b) for a,b in zip([r[0] for r in runs(new,CUT_Y)[1:]],[r[0] for r in runs(new,CUT_Y)[:-1]])])


def main():
    OUT.mkdir(exist_ok=True)
    cfg=json.loads(Path('data/alphabet.json').read_text());ctx=json.loads(Path('data/context/serif_bl.json').read_text())
    baseline=OUT/'baseline.json'
    if baseline.exists():inputs=json.loads(baseline.read_text())
    else:
        item=source_items('т',cfg)[0];inputs=[dict(character='т',role='primary',source=item['path'],sha256=hashlib.sha256(Path(item['path']).read_bytes()).hexdigest())]
        baseline.write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
    row=inputs[0];ch,source=row['character'],row['source'];assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==row['sha256']
    p,advance,audit=build(source)
    target=OUT/'uni0442-primary.glif';write_glif(p,'uni0442',advance,ord(ch),str(target))
    item=dict(path=str(target),advance=advance,bounds=list(p.bounds),glif_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),role='primary',variant='01',label='Верх как у латинской m',status='canonical upper part requested by author',canon_source_glif=source)
    check=inspect(ch,item);assert check['open_contours']==0 and all(r['simple_approx'] for r in check['ring_diagnostics']),check['ring_diagnostics']
    entry=cfg['codex'][ch];archive=cfg['rejected_drawings'].setdefault('before-te-canon',{})
    if ch not in archive:archive[ch]=copy.deepcopy(entry)
    cfg['codex'][ch]=dict(selected='01',shared_with_claude=False,conflict=False,variants=[item],provenance='Canonical upper part requested by author; previous sources archived')
    ctx['built_bases'][ch]=str(target)
    for rule,inside in [(ctx,test(p)[0]),(ctx['ka_short'],test_top(p)[0])]:
        members=rule['declared_class']['lower'];outside=rule['expected_not_in_class']
        if inside and ch not in members:members.append(ch)
        if not inside and ch in members:members.remove(ch)
        if inside and ch in outside:outside.remove(ch)
        if not inside and ch not in outside:outside.append(ch)
    for path,obj in [('data/alphabet.json',cfg),('data/context/serif_bl.json',ctx),(str(OUT/'manifest.json'),[dict(**row,path=str(target),advance=advance,**audit)])]:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print('te',audit,'advance',advance,'bounds',p.bounds)

if __name__=='__main__':main()
