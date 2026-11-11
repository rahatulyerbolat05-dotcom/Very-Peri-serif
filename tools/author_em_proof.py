#!/usr/bin/env python3
"""Outline proof of the author's Vector.svg in serialized release 1.117.

Both columns are drawn and shaped from actual font bytes, including kerning.
The immutable 1.116 archive is the reference; no intermediate study is used.
"""
import argparse
import datetime
import hashlib
import io
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['path.simplify']=False
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import PathPatch
from fontTools.ttLib import TTFont
import uharfbuzz as hb
from family_proof import Proof,page
from alphabet_sheet import MplPen
matplotlib.rcParams['svg.hashsalt']='VeryPeriSerifAuthorEm1117'

BG,INK,OLD='#f5f2ec','#8c3949','#a6a09a'
MUTED,RULE='#77716d','#ddd6cd'
DATE=datetime.datetime(2026,11,11,tzinfo=datetime.timezone.utc)
ARCHIVE=Path('dist/VeryPeriSerif-1.116.zip')
ARCHIVE_SHA='ea93f22b17b3faf3e3531c3e8371d9b136144c82a4d1c77b1d519514ea3e8ef4'

class MemoryProof(Proof):
    def __init__(self,raw):
        self.font=TTFont(io.BytesIO(raw));self.gs=self.font.getGlyphSet()
        self.hf=hb.Font(hb.Face(raw));hb.ot_font_set_funcs(self.hf)

def label(ax,x,y,value,size=13,color=MUTED):
    ax.text(x,y,value,fontsize=size,color=color,family='DejaVu Sans')

def line(proof,ax,value,x,y,size,right=1495,color=INK,**kwargs):
    end=proof.line(ax,value,x,y,size,color=color,**kwargs)
    assert end<right,('Specimen overflow',value,end,right)

def crop(ax,proof,box,title,color):
    xmin,ymin,xmax,ymax=box
    ax.set_facecolor(BG);ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax)
    ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
    for spine in ax.spines.values():spine.set_color(RULE)
    pen=MplPen(proof.gs);proof.gs['uni043C'].draw(pen)
    ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none'))
    ax.set_title(title,fontsize=13,color=MUTED,pad=14)

def hero(old,new):
    fig,ax=page('Very Peri Serif · авторская курсивная м · 1.117',1560,1130)
    for i,(proof,title,color) in enumerate(((old,'До · 1.116',OLD),(new,'Авторский Vector.svg · 1.117',INK))):
        x=65+i*770
        label(ax,x,125,title,18)
        ax.plot([x,x+650],[630,630],color=RULE,lw=.7)
        ax.plot([x,x+650],[196.5,196.5],color=RULE,lw=.7)
        line(proof,ax,'м',x+80,630,850,x+680,color)
        line(proof,ax,'мама',x+45,815,220,x+680,color)
        line(proof,ax,'мимо · мир',x+45,960,135,x+680,color)
    ax.plot([45,1515],[1010,1010],color=RULE,lw=.8)
    label(ax,65,1060,'Форма из авторского SVG. Сохранены пропорции и ширина набора.',14,'#575150')
    label(ax,65,1100,'Предыдущие доработки окончаний и я сохранены. Сравнение построено из файлов TTF.',12)
    return fig

def details(old,new):
    fig,ax=page('м · верхние переходы и нижний поворот · 1.116 / 1.117',1560,1320)
    rows=[((90,395,245,535),'Левое плечо',.66),
          ((345,410,485,530),'Правое плечо',.365),
          ((140,-30,285,130),'Средний нижний поворот',.07)]
    for box,title,y in rows:
        for i,(proof,color) in enumerate(((old,OLD),(new,INK))):
            axis=fig.add_axes([.06+i*.5,y,.38,.235])
            crop(axis,proof,box,title+' · '+('1.116' if i==0 else '1.117'),color)
    return fig

def context(new):
    fig,ax=page('1.117 · авторская м в словах и рядом с другими буквами',1560,1380)
    label(ax,60,120,'Различие м / н / и / т',14)
    line(new,ax,'м н и т · тм мт · ми им',60,260,145)
    label(ax,60,350,'Русский набор',14)
    for j,value in enumerate(('мама · мимика · музыка','мир · имя · дым · мягкий')):
        line(new,ax,value,60,465+j*150,125)
    label(ax,60,700,'Қазақ тілі',14)
    line(new,ax,'мұра · үміт · әлем · мың',60,815,125,language='kk')
    label(ax,60,910,'Знаки над м и родные латинские u / v',14)
    line(new,ax,'м́ м̀ м̈ м̄ м̈́ · м u v',60,1060,140)
    line(new,ax,'мамам · мимим · тмтм · имим',60,1195,115)
    line(new,ax,'«м» (м) №м · ,м м, · .м м.',60,1325,110)
    return fig

def sizes(new,dark=False):
    fig,ax=page('1.117 · размеры и ритм'+(' · тёмный фон' if dark else ''),1560,1260,dark=dark)
    color=BG if dark else INK;muted='#c5becb' if dark else MUTED
    y=125
    for size,value in [(24,'Мама помнит музыку. Мягкий дым и мимолётная мысль.'),
                       (40,'Мама помнит музыку. Мягкий дым и мимолётная мысль.'),
                       (72,'Мама помнит музыку. Мягкий дым.'),
                       (110,'Мама · мимика · музыка')]:
        label(ax,60,y,f'{size} px',12,muted)
        y+=size*.7+45
        line(new,ax,value,60,y,size,color=color)
        y+=80
    label(ax,60,y,'Қазақ тілі',13,muted)
    line(new,ax,'Мұра мен үміт · әлем',60,y+120,115,color=color,language='kk')
    line(new,ax,'м н и т · мама · мимика',60,y+285,110,color=color)
    return fig

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font',type=Path,default=Path('build/release/VeryPeriSerif-Italic.ttf'))
    args=parser.parse_args()
    raw=ARCHIVE.read_bytes();assert hashlib.sha256(raw).hexdigest()==ARCHIVE_SHA
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        old=MemoryProof(archive.read('VeryPeriSerif-1.116/fonts/ttf/VeryPeriSerif-Italic.ttf'))
    new=Proof(args.font)
    assert old.font['name'].getDebugName(5)=='Version 1.116'
    assert new.font['name'].getDebugName(5)=='Version 1.117','Build the current release first'
    for proof in (old,new):
        assert proof.font['hmtx']['uni043C'][0]==523
    images=Path('docs/img');specimen=Path('docs/specimen')
    for folder in (images,specimen):folder.mkdir(parents=True,exist_ok=True)
    pdf=specimen/'VeryPeriSerif-Author-Em-1.117.pdf'
    metadata={'Title':'Very Peri Serif 1.117 — авторская курсивная м',
              'Author':'Very Peri Serif project','CreationDate':DATE,'ModDate':DATE}
    with PdfPages(pdf,metadata=metadata) as pages:
        fig=hero(old,new);pages.savefig(fig)
        fig.savefig(images/'author-em-comparison.png',dpi=96)
        fig.savefig(images/'author-em-comparison.svg',metadata={'Date':DATE.isoformat()})
        plt.close(fig)
        for name,make in [('details',lambda:details(old,new)),
                          ('context',lambda:context(new)),
                          ('words-light',lambda:sizes(new)),
                          ('words-dark',lambda:sizes(new,True))]:
            fig=make();pages.savefig(fig);fig.savefig(images/('author-em-'+name+'.png'),dpi=96);plt.close(fig)
    print(pdf)
    print(images/'author-em-comparison.png')

if __name__=='__main__':main()
