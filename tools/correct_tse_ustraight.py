#!/usr/bin/env python3
"""[РЕШЕНИЕ] Replace diagonal Ц and Latin-y ү; update dependent ұ.

Run from repository root. Superseded drawings remain on disk and in archive
metadata. Native Latin donors are neither scaled nor edited.
"""
import hashlib
import json
import sys
from pathlib import Path as FilePath
from types import SimpleNamespace

sys.path.insert(0, str(FilePath(__file__).resolve().parent))
from sketchlib import Ref, Path, SUB, OR, rect, write_svg
from glyphparts import _rrect
from tails import cut_stem, attach, module
from fontTools.pens.pointPen import SegmentToPointPen, PointToSegmentPen
from fontTools.ufoLib.glifLib import writeGlyphToString, readGlyphFromString
import pathops

DATA=FilePath('data/corrections-tse-ustraight')
BUILD=FilePath('build/corrections-tse-ustraight')
NAMES={'Ц':'Tse-cy','ү':'ustraight-cy','ұ':'ustraightstroke-cy'}
LABELS={'Ц':'Две стойки, нижняя связь','ү':'Прямой нижний вынос','ұ':'Прямой вынос с чертой'}
NOTES={
 'Ц':'[РЕШЕНИЕ] По исправлению пользователя: две вертикальные стойки и нижняя горизонталь вместо диагонали. Ход: левая стойка вниз, нижняя связь вправо, правая стойка в хвост. Стойки H и связь толщины H; F2: левая ножка H; F8: правый крюк J, модуль K2 без масштаба. Новый хвост достигает родного уровня -215; авторский диагональный рисунок сохранён в архиве. Интервалы предварительные.',
 'ү':'[РЕШЕНИЕ] По исправлению пользователя: развилка и прямой вертикальный нижний вынос вместо обычной y. Ход: левая ветвь вниз вправо, правая вниз в развилку, затем стойка вниз. Верхние ветви и засечки y без масштаба; сочленение нарисовано заново, вертикаль68 и нижняя ножка p. F2: нижняя ножка; F8: прямой вынос -205. Капля и изогнутый хвост y убраны как неверная конструкция ү. Интервалы предварительные.',
 'ұ':'[РЕШЕНИЕ] Зависимая правка: исправленная ү с прямым нижним выносом и поперечной чертой толщины e25. Исходная ұ на основе y сохранена в архиве. F2: нижняя ножка p; F8: прямой вынос -205. Интервалы предварительные.'}


def straight_u(ref):
    # [ИЗМЕРЕНО] Верхние контуры y, включая толщины и родные засечки.
    # [РЕШЕНИЕ] Новое нижнее сочленение и вертикальная стойка x185..253.
    p=Path();q=p.getPen();q.moveTo((157,96));q.lineTo((48,443))
    q.qCurveTo((41,467),(28,481),(14,484));q.lineTo((-1,487))
    q.qCurveTo((-14,490),(-14,500));q.qCurveTo((-14,510),(0,510))
    q.lineTo((165,510));q.qCurveTo((179,510),(179,500))
    q.qCurveTo((179,489),(166,487));q.lineTo((150,485))
    q.qCurveTo((126,482),(113,465),(120,443));q.lineTo((208,150))
    q.qCurveTo((211,140),(224,140),(227,150));q.lineTo((312,425))
    q.qCurveTo((320,452),(313,479),(288,483));q.lineTo((267,487))
    q.qCurveTo((254,490),(254,500));q.qCurveTo((254,510),(268,510))
    q.lineTo((395,510));q.qCurveTo((409,510),(409,499))
    q.qCurveTo((409,489),(397,485));q.lineTo((388,482))
    q.qCurveTo((373,477),(353,451),(342,419));q.lineTo((268,185))
    q.qCurveTo((253,138),(253,80));q.lineTo((253,-138))
    # [ИЗМЕРЕНО] Нижняя ножка p сдвинута на112 без масштаба.
    q.qCurveTo((253,-159),(266,-174),(287,-177));q.lineTo((324,-182))
    q.qCurveTo((335,-184),(335,-193));q.qCurveTo((335,-205),(320,-205))
    q.lineTo((139,-205));q.qCurveTo((124,-205),(124,-194))
    q.qCurveTo((124,-183),(137,-182));q.lineTo((151,-180))
    q.qCurveTo((172,-177),(185,-159),(185,-138));q.lineTo((185,-40))
    q.qCurveTo((185,7),(157,96));q.closePath()
    return p,ref.adv('y')


def drawings(ref,params):
    stems=SUB(ref.glyph('H'),rect(160,330,386,410))
    body=OR(stems,rect(119,0,427,params['regular']['stems_hairlines']['H_crossbar']))
    tse=OR(attach(cut_stem(body,386,457),module(ref,'K2',True),386),
           rect(119,0,427,params['regular']['stems_hairlines']['H_crossbar']))
    u,advance=straight_u(ref)
    cy=params['regular']['vertical']['descender_p']/3
    t=params['regular']['stems_hairlines']['e_crossbar']
    struck=OR(u,_rrect(130,cy-t/2,308,cy+t/2,4))
    return {'Ц':(tse,round(tse.bounds[2]+19)),'ү':(u,advance),'ұ':(struck,advance)}


def main():
    DATA.mkdir(parents=True,exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(FilePath('data/alphabet.json').read_text())
    context=json.loads(FilePath('data/context/serif_bl.json').read_text())
    params=json.loads(FilePath('data/params.json').read_text());ref=Ref()
    archive=cfg.setdefault('rejected_drawings',{})
    if 'Ц' in cfg.get('user',{}):
        old=cfg['user'].pop('Ц');old['selected']=None
        old['status']='superseded: user rejected diagonal construction; preserve original'
        archive['Ц-diagonal-author']=old
    if 'ү' in cfg['done']:
        old=cfg['done'].pop('ү')
        archive['ү-latin-y']={'path':old[0],'status':'user rejected ordinary y as lowercase ү'}
    cfg['latin_donor']=[ch for ch in cfg['latin_donor'] if ch!='ү']
    if 'ұ' in cfg['codex'] and cfg['codex']['ұ']['variants'][0]['path'].startswith('data/kz-completion/'):
        archive['ұ-latin-y-base']=cfg['codex']['ұ']
    result=drawings(ref,params);manifest={}
    from check_context_classes import test,test_top
    for ch,(p,advance) in result.items():
        p.simplify();filename=DATA/f'uni{ord(ch):04X}-01.glif'
        g=SimpleNamespace(width=advance,unicodes=[ord(ch)],note=NOTES[ch])
        filename.write_text(writeGlyphToString(NAMES[ch],g,
            lambda pp:p.draw(SegmentToPointPen(pp)),formatVersion=2))
        write_svg(p,advance,str(filename.with_suffix('.svg')))
        back=Path();meta=SimpleNamespace()
        readGlyphFromString(filename.read_text(),meta,PointToSegmentPen(back.getPen()))
        assert back.bounds==p.bounds and meta.width==advance
        assert abs(pathops.op(p,back,pathops.PathOp.XOR).area)<.01
        item={'path':str(filename),'label':LABELS[ch],'variant':'01','status':'corrected proposal',
              'advance':advance,'bounds':list(p.bounds),'glif_sha256':hashlib.sha256(filename.read_bytes()).hexdigest()}
        cfg['codex'][ch]={'selected':None,'shared_with_claude':False,'conflict':False,
                         'variants':[item],'provenance':'Codex; construction corrected at user request'}
        manifest[ch]=dict(item,note=NOTES[ch],contours=len(list(p.contours)))
        context['built_bases'][ch]=str(filename)
        for rule,inside in [(context,test(p)[0])]+([(context['ka_short'],test_top(p)[0])] if ch.islower() else []):
            members=rule['declared_class']['upper' if ch.isupper() else 'lower'];outside=rule['expected_not_in_class']
            if ch in members:members.remove(ch)
            if ch in outside:outside.remove(ch)
            (members if inside else outside).append(ch)
    event='16.10.2026: пользователь отклонил диагональную Ц и ү=y; новые Ц с нижней связью, ү с прямым выносом, зависимая ұ исправлена; старые формы в архиве.'
    if event not in context['history']:context['history'].append(event)
    for filename,obj in [(DATA/'manifest.json',manifest),(FilePath('data/alphabet.json'),cfg),
                         (FilePath('data/context/serif_bl.json'),context)]:
        filename.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    # Reuse font roundtrip/raster validation; originals remain unchanged.
    import sketch_remaining_kz as checks
    checks.BUILD=BUILD;checks.NAMES=NAMES;checks.check_ttf(ref,result)
    render(cfg)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


def render(cfg):
    from alphabet_sheet import canvas,text,glyph,load_glif,source_items
    import matplotlib.pyplot as plt
    fig,ax=canvas(1700,1400);text(ax,50,30,'Ц ү ұ · исправленная конструкция',32)
    for x,ch in zip((290,850,1370),NAMES):glyph(ax,cfg['codex'][ch]['variants'][0]['path'],x,560,.55)
    for j,line in enumerate(('ЦЕНА  ЦВЕТ  ЦЕЛЬ','күн  гүл  үміт','ұлт  ұлы  құс')):
        x,baseline,scale=60,820+j*190,.16
        for ch in line:
            if ch==' ':x+=45;continue
            filename=source_items(ch,cfg)[0]['path'];o=load_glif(filename);xmin,_,xmax,_=o.bounds
            glyph(ax,filename,x+(xmin+xmax)*scale/2,baseline,scale);x+=o.advance*scale
    text(ax,50,1320,'Прежние рисунки сохранены в архиве. Интервалы предварительные.',24)
    fig.savefig('docs/img/corrections_tse_ustraight.svg');fig.savefig(BUILD/'comparison.png',dpi=100);plt.close(fig)


if __name__=='__main__':main()
