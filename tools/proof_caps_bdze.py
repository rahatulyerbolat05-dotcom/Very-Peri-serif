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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capitals-bdzei';FONT=OUT/'capitals-shorti01.ttf';f=TTFont(FONT);gs=f.getGlyphSet()
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
fig,ax=plt.subplots(figsize=(16,11),dpi=110);fig.patch.set_facecolor('#f5f2ec');ax.set_xlim(0,1600);ax.set_ylim(1100,0);ax.axis('off');fig.subplots_adjust(0,0,1,1)
def label(x,y,t,size=18,c='#78747c'):ax.text(x,y,t,fontsize=size,va='top',color=c,fontfamily='DejaVu Sans')
label(60,35,'Very Peri Serif · Б Д З И',30,'#272333');label(60,90,'По одному варианту · Regular · И сохранена из предыдущего рисунка',15)
for x,ch in [(65,'Б'),(440,'Д'),(885,'З'),(1220,'И')]:
 line(ax,ch,x,550,550);label(x+65,645,ch,24,'#2563eb')
ax.plot([50,1540],[550,550],color='#dbd5cc',lw=.8);ax.plot([50,1540],[154,154],color='#dbd5cc',lw=.8)
label(60,705,'В НАБОРЕ С ВЫБРАННЫМИ СТРОЧНЫМИ',13)
line(ax,'Боря  Дора  Зоя  Ива',65,840,125)
label(60,900,'РОДНЫЕ ПРОПИСНЫЕ ДЛЯ СРАВНЕНИЯ',13)
line(ax,'B E H O N',65,1030,115);line(ax,'Б Д З И',850,1030,115,'#2563eb')
fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());fig.savefig(ROOT/'build/capitals-bdzei-preview.png',facecolor=fig.get_facecolor());plt.close(fig)
