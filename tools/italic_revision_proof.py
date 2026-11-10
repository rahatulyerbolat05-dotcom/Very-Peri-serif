#!/usr/bin/env python3
"""Compare the accepted Italic 1.116 revision with frozen release 1.115.

Proofs use the actual final serialized font, exact outline paths and HarfBuzz
shaping. The separate м studies are intentionally not used in this release.
"""
import argparse
import datetime
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['path.simplify'] = False
matplotlib.rcParams['svg.hashsalt'] = 'VeryPeriSerifItalicRevision1116'
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import PathPatch
from family_proof import Proof, page
from alphabet_sheet import MplPen

BASELINE = '0330c598b690e4e9ddc6aec53a57218bba476035'
BG, INK, OLD = '#f5f2ec', '#8c3949', '#a6a09a'
MUTED, RULE = '#77716d', '#ddd6cd'
DATE = datetime.datetime(2026,11,10,tzinfo=datetime.timezone.utc)
CHANGED = 'нңйцшщыүұжчя'


def label(ax, x, y, value, size=13, color=MUTED):
    ax.text(x,y,value,fontsize=size,color=color,family='DejaVu Sans')


def text(proof, ax, value, x, y, size, right, color=INK, **kwargs):
    end=proof.line(ax,value,x,y,size,color=color,**kwargs)
    assert end < right, ('Specimen overflow',value,end,right)
    return end


def cropped(ax, proof, ch, box, title, color=INK):
    xmin,ymin,xmax,ymax=box
    ax.set_facecolor(BG);ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax);ax.set_aspect('equal')
    name=proof.font.getBestCmap()[ord(ch)]
    pen=MplPen(proof.gs);proof.gs[name].draw(pen)
    ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none'))
    ax.set_xticks([]);ax.set_yticks([])
    for spine in ax.spines.values():spine.set_color(RULE)
    ax.set_title(title,fontsize=12,color=MUTED,pad=12)


def hero(old,new):
    fig,ax=page('Very Peri Serif 1.116 · принятая доработка курсива',1500,1180)
    label(ax,60,105,'Верхние окончания',16,'#48423f')
    for k,p in enumerate((old,new)):
        x=65+k*355;color=OLD if k==0 else INK
        label(ax,x,155,'1.115 · было' if k==0 else '1.116 · стало',13)
        ax.plot([x,x+290],[465,465],color=RULE,lw=.8)
        text(p,ax,'н',x+15,465,520,x+300,color)
    label(ax,865,160,'Родная p задаёт характер скругления',12)
    a=fig.add_axes([.585,.61,.17,.22]);b=fig.add_axes([.79,.61,.17,.22])
    cropped(a,old,'p',(130,535,230,600),'p · Instrument Serif',OLD)
    cropped(b,new,'н',(348,462,448,527),'н · 1.116',INK)
    text(old,ax,'тишина · новый день',60,565,76,700,OLD)
    text(new,ax,'тишина · новый день',795,565,76,1455,INK)
    ax.plot([45,1455],[610,610],color=RULE,lw=.8)
    label(ax,60,660,'я · классическое верхнее окончание',16,'#48423f')
    for k,p in enumerate((old,new)):
        x=65+k*355;color=OLD if k==0 else INK
        label(ax,x,710,'Было' if k==0 else 'Стало',13)
        ax.plot([x,x+270],[1025,1025],color=RULE,lw=.8)
        text(p,ax,'я',x+20,1025,510,x+285,color)
    a=fig.add_axes([.575,.13,.18,.23]);b=fig.add_axes([.79,.13,.18,.23])
    cropped(a,old,'я',(220,425,410,545),'Было',OLD)
    cropped(b,new,'я',(220,425,410,545),'Стало',INK)
    text(old,ax,'маяк · идея',60,1120,100,700,OLD)
    text(new,ax,'маяк · идея',795,1120,100,1455,INK)
    return fig


def all_changed(old,new):
    fig,ax=page('Все 12 изменённых букв · слева 1.115, справа 1.116',1500,1330)
    for j,ch in enumerate(CHANGED):
        x=45+(j%4)*370;y=375+(j//4)*400
        label(ax,x,y-220,ch,15)
        text(old,ax,ch,x,y,245,x+180,OLD)
        text(new,ax,ch,x+180,y,245,x+365,INK)
    return fig


def ya_details(old,new):
    fig,ax=page('я · окончание, чаша и стойка',1500,1300)
    for k,p in enumerate((old,new)):
        x=65+k*740;color=OLD if k==0 else INK
        label(ax,x,120,'1.115' if k==0 else '1.116',16)
        a=fig.add_axes([.065+k*.49,.57,.38,.25])
        cropped(a,p,'я',(175,375,425,545),'Было' if k==0 else 'Стало',color)
        for j,value in enumerate(('ярмарка','маяк · идея','жария · ұя','я́ · я̀ · я̈')):
            text(p,ax,value,x,730+j*145,125,x+665,color)
    return fig


def words(old,new,dark=False):
    fig,ax=page('1.116 · слова, размеры и ритм'+(' · тёмный фон' if dark else ''),1500,1380,dark=dark)
    color=BG if dark else INK
    y=135
    for size in (24,40,72,115):
        label(ax,60,y,f'{size} px',11,BG if dark else MUTED)
        y+=size*1.2+38
        value='Жизнь, тишина, новый день. Маяк и память.' if size<100 else 'Жизнь, тишина, маяк.'
        text(new,ax,value,60,y,size,1440,color)
        y+=45
    text(new,ax,'Қазақ тілі · жаңғырық · үміт · ұя',60,y+120,95,1440,color)
    label(ax,60,y+230,'м сохранена в рисунке 1.115',13,BG if dark else MUTED)
    text(old,ax,'мама · мимика',60,y+330,105,700,BG if dark else OLD)
    text(new,ax,'мама · мимика',795,y+330,105,1455,color)
    label(ax,60,y+430,'Принятая арочная л остаётся основной',13,BG if dark else MUTED)
    text(new,ax,'лилия · люблю · әлем',60,y+530,105,1440,color)
    return fig


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--font',type=Path,default=Path('build/release/VeryPeriSerif-Italic.ttf'))
    ap.add_argument('--output-root',type=Path,default=Path('.'))
    ap.add_argument('--allow-preview',action='store_true',help='Layout-only preview before the final release exists')
    args=ap.parse_args()
    out=args.output_root
    images=out/'docs/img';specimen=out/'docs/specimen';tmp=out/'build/italic-revision'
    for path in (images,specimen,tmp):path.mkdir(parents=True,exist_ok=True)
    baseline=tmp/'Italic-1.115.ttf'
    baseline.write_bytes(subprocess.check_output(['git','show',BASELINE+':fonts/ttf/VeryPeriSerif-Italic.ttf']))
    old,new=Proof(baseline),Proof(args.font)
    if not args.allow_preview:
        assert new.font['name'].getDebugName(5).startswith('Version 1.116'), 'Use the final 1.116 font'
    metadata={'Title':'Very Peri Serif 1.116 — принятая доработка курсива',
              'Author':'Very Peri Serif project','CreationDate':DATE,'ModDate':DATE}
    pdf=specimen/'VeryPeriSerif-Italic-Revision-1.116.pdf'
    with PdfPages(pdf,metadata=metadata) as pages:
        fig=hero(old,new);pages.savefig(fig)
        fig.savefig(images/'italic-revision-1.116.svg',metadata={'Date':DATE.isoformat()})
        fig.savefig(images/'italic-revision-1.116.png',dpi=96);plt.close(fig)
        for stem,make in [('all-changed',all_changed),('ya-details',ya_details)]:
            fig=make(old,new);pages.savefig(fig);fig.savefig(tmp/(stem+'.png'),dpi=96);plt.close(fig)
        for dark in (False,True):
            fig=words(old,new,dark);pages.savefig(fig)
            fig.savefig(tmp/('words-dark.png' if dark else 'words-light.png'),dpi=96);plt.close(fig)
    print(pdf)
    print(images/'italic-revision-1.116.png')

if __name__=='__main__':main()
