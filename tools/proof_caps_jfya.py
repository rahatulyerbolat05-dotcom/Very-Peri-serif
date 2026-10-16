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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capitals-jfya';FONT=OUT/'capitals-shorti01.ttf';f=TTFont(FONT);gs=f.getGlyphSet()
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
fig,ax=plt.subplots(figsize=(14,12),dpi=110);fig.patch.set_facecolor('#f5f2ec');ax.set_xlim(0,1400);ax.set_ylim(1200,0);ax.axis('off');fig.subplots_adjust(0,0,1,1)
def label(x,y,t,size=18,c='#78747c'):ax.text(x,y,t,fontsize=size,va='top',color=c,fontfamily='DejaVu Sans')
label(60,30,'Very Peri Serif · Й Ф Я',30,'#272333');label(60,85,'По одному варианту · заглавные · Regular',15)
for x,ch in [(75,'Й'),(520,'Ф'),(1030,'Я')]:
 line(ax,ch,x,610,520);label(x+80,645,ch,24,'#2563eb')
ax.plot([50,1350],[610,610],color='#dbd5cc',lw=.8);ax.plot([50,1350],[235.6,235.6],color='#dbd5cc',lw=.8)
label(60,715,'В НАБОРЕ С ВЫБРАННЫМИ СТРОЧНЫМИ',13)
line(ax,'Йод  Фора  Яра',65,865,130)
label(60,970,'РОДНЫЕ ПРОПИСНЫЕ ДЛЯ СРАВНЕНИЯ',13)
line(ax,'H O P I',65,1115,120);line(ax,'Й Ф Я',770,1115,120,'#2563eb')
fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());fig.savefig(ROOT/'build/capitals-jfya-preview.png',facecolor=fig.get_facecolor());plt.close(fig)
