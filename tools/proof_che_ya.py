from pathlib import Path
import matplotlib
matplotlib.use('Agg');matplotlib.rcParams['path.simplify']=False
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from study_layout import hb_shape
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/che-ya';FONT=OUT/'che-ya-shorti01.ttf';f=TTFont(FONT);gs=f.getGlyphSet()
class Pen(BasePen):
 def __init__(self):super().__init__(gs);self.v=[];self.c=[]
 def _moveTo(self,p):self.start=p;self.v.append(p);self.c.append(MP.MOVETO)
 def _lineTo(self,p):self.v.append(p);self.c.append(MP.LINETO)
 def _curveToOne(self,a,b,c):self.v.extend([a,b,c]);self.c.extend([MP.CURVE4]*3)
 def _qCurveToOne(self,a,b):self.v.extend([a,b]);self.c.extend([MP.CURVE3]*2)
 def _closePath(self):self.v.append(self.start);self.c.append(MP.CLOSEPOLY)
def line(ax,text,x,y,size,color='#272333'):
 for name,adv,_,dx,dy in hb_shape(FONT,text):
  pen=Pen();gs[name].draw(pen)
  if pen.v:ax.add_patch(PathPatch(MP(pen.v,pen.c),transform=Affine2D().scale(size/1000,-size/1000).translate(x+dx*size/1000,y-dy*size/1000)+ax.transData,facecolor=color,edgecolor='none'))
  x+=adv*size/1000
fig,ax=plt.subplots(figsize=(14,11),dpi=110);fig.patch.set_facecolor('#f5f2ec');ax.set_facecolor('#f5f2ec');ax.set_xlim(0,1400);ax.set_ylim(1100,0);ax.axis('off');fig.subplots_adjust(0,0,1,1)
def label(x,y,t,size=18,c='#78747c'):ax.text(x,y,t,fontsize=size,va='top',color=c,fontfamily='DejaVu Sans')
label(65,40,'Very Peri Serif · ч / я',28,'#272333');label(65,92,'По одному варианту · Regular · 16.10.2026',15)
for x,ch,title in [(160,'ч','ч · поднятая чаша u'),(800,'я','я · петля и капля y')]:
 ax.plot([x-65,x+430],[450,450],color='#dbd5cc',lw=1)
 ax.plot([x-65,x+430],[450-510*.58]*2,color='#dbd5cc',lw=1)
 line(ax,ch,x,450,580);label(x-40,485,title,20,'#2563eb')
label(65,555,'В НАБОРЕ · ВМЕСТЕ С ВЫБРАННЫМИ БУКВАМИ',13)
line(ax,'чача  чичи  чая',70,690,140)
line(ax,'якоря  я тебя',70,820,140)
label(65,865,'РОДНЫЕ ЛАТИНСКИЕ ФОРМЫ ДЛЯ СРАВНЕНИЯ',13)
line(ax,'u a o y',70,1000,140);line(ax,'ч я',700,1000,140,'#2563eb')
label(65,1040,'Новые рисунки на рассмотрение. Интервалы предварительные.',13)
fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor())
(ROOT/'build').mkdir(exist_ok=True);fig.savefig(ROOT/'build/che-ya-preview.png',facecolor=fig.get_facecolor());plt.close(fig)
