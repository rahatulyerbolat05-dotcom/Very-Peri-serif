#!/usr/bin/env python3
"""[РЕШЕНИЕ] Refine lowercase ү/ұ with the native Y junction, unscaled.

Run from repository root. Previous proposals remain archived. Cap Y upper
part is translated to x-height; the straight stem ends with the I foot.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import correct_tse_ustraight as previous
from sketchlib import Ref,AND,OR,rect,shift
from glyphparts import _rrect

DATA=Path('data/ustraight-refinement')
BUILD=Path('build/ustraight-refinement')
ORIGINAL_DRAWINGS=previous.drawings


def straight_u(ref):
    params=json.loads(Path('data/params.json').read_text())
    vertical=params['regular']['vertical']
    drop=vertical['flat_cap']-vertical['flat_x']
    bottom=vertical['descender_p']
    # [ИЗМЕРЕНО] Y: стойка204..275, I:89..160, низ ножки0.
    # Верх Y смещается на−210 без масштаба; сочленение остаётся родным.
    # [РЕШЕНИЕ] I-ножка до−205; шов−139 внутри прямой стойки71.
    join=bottom+66
    upper=AND(shift(ref.glyph('Y'),0,-drop),rect(-1000,join,2000,1000))
    foot=AND(shift(ref.glyph('I'),204-89,bottom),rect(-1000,-1000,2000,join))
    return OR(upper,foot),ref.adv('Y')


def compare():
    from alphabet_sheet import canvas,text,glyph,source_items,load_glif
    import matplotlib.pyplot as plt
    cfg=json.loads(Path('data/alphabet.json').read_text())
    fig,ax=canvas(1800,1420)
    text(ax,50,30,'Строчные ү / ұ · сравнение развилки',32)
    text(ax,180,110,'Прежняя форма',25)
    text(ax,1030,110,'Новая форма · родное сочленение Y',25)
    for ch,xold,xnew in [('ү',260,1110),('ұ',650,1500)]:
        glyph(ax,f'data/corrections-tse-ustraight/uni{ord(ch):04X}-01.glif',xold,650,.65,color='#9a9390')
        glyph(ax,source_items(ch,cfg)[0]['path'],xnew,650,.65)
    for j,line in enumerate(('күн  гүл  үміт','ұлт  ұлы  құс')):
        x=70;baseline=940+j*210;scale=.18
        for ch in line:
            if ch==' ':x+=45;continue
            filename=source_items(ch,cfg)[0]['path'];o=load_glif(filename)
            xmin,_,xmax,_=o.bounds
            glyph(ax,filename,x+(xmin+xmax)*scale/2,baseline,scale);x+=o.advance*scale
    text(ax,50,1320,'Прямой вынос и нижняя засечка сохранены; развилка и переход заменены.',23)
    fig.savefig('docs/img/ustraight_refinement.svg')
    fig.savefig(BUILD/'comparison.png',dpi=100);plt.close(fig)


def refined_drawings(ref,params):
    result=ORIGINAL_DRAWINGS(ref,params)
    u,advance=result['ү'];cy=params['regular']['vertical']['descender_p']/3
    thickness=params['regular']['stems_hairlines']['e_crossbar']
    center=(204+275)/2
    result['ұ']=(OR(u,_rrect(center-89,cy-thickness/2,center+89,cy+thickness/2,4)),advance)
    return result


def main():
    cfg=json.loads(Path('data/alphabet.json').read_text())
    if cfg.get('codex',{}).get('ү',{}).get('variants',[{}])[0].get('path','').startswith('data/regular-refinement/'):
        raise SystemExit('Current ү/ұ use tools/finish_regular.py; refusing to restore wider junctions.')
    for ch in 'үұ':
        entry=cfg['codex'][ch]
        if entry['variants'][0]['path'].startswith('data/corrections-tse-ustraight/'):
            cfg['rejected_drawings'][ch+'-junction-v1']=entry
    Path('data/alphabet.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    previous.DATA=DATA;previous.BUILD=BUILD;previous.straight_u=straight_u
    previous.drawings=refined_drawings
    previous.LABELS['ү']='Родная развилка Y, прямой вынос'
    previous.LABELS['ұ']='Родная развилка Y, черта'
    previous.NOTES['ү']='[РЕШЕНИЕ] По замечанию пользователя о развилке и переходе: верх и сочленение родной Y без масштаба сдвинуты на -210 к x-height510. Вертикаль71 (отклонение+3 от n68 в пределах±4); ножка I без масштаба перенесена на -205. Стык внутри прямой стойки. F2: нижняя засечка; F8: прямой вынос. Прежнее нарисованное сочленение сохранено в архиве; ширина477 вместо401 — ширина донора Y, интервалы предварительные.'
    previous.NOTES['ұ']='[РЕШЕНИЕ] Та же уточнённая развилка ү с родным сочленением Y без масштаба, вертикаль71, нижняя ножка I до -205; поперечная черта25. F2/F8. Изменены развилка и переход, прежняя форма в архиве.'
    previous.main()
    context=json.loads(Path('data/context/serif_bl.json').read_text())
    event='16.10.2026: по замечанию пользователя заменены развилка и переход строчных ү/ұ на родное сочленение Y без масштаба; формы остаются предложениями.'
    if event not in context['history']:context['history'].append(event)
    Path('data/context/serif_bl.json').write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n')
    compare()


if __name__=='__main__':main()
