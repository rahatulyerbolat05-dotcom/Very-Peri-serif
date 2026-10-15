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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capital-i';FONT=OUT/'capital-i-shorti01.ttf';f=TTFont(FONT);gs=f.getGlyphSet()
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
fig,ax=plt.subplots(figsize=(12,10),dpi=110);fig.patch.set_facecolor('#f5f2ec');ax.set_xlim(0,1200);ax.set_ylim(1000,0);ax.axis('off');fig.subplots_adjust(0,0,1,1)
def label(x,y,t,size=18,c='#78747c'):ax.text(x,y,t,fontsize=size,va='top',color=c,fontfamily='DejaVu Sans')
label(60,35,'Very Peri Serif · заглавная И',27,'#272333');label(60,85,'Один вариант · Regular · 16.10.2026',14)
for x,ch,c in [(90,'H','#8a858e'),(450,'И','#272333'),(810,'N','#8a858e')]:
 line(ax,ch,x,530,500,c)
 label(x+80,560,'Новая И' if ch=='И' else 'Родная '+ch,17,'#2563eb' if ch=='И' else '#78747c')
ax.plot([60,1140],[530,530],color='#dbd5cc',lw=.8);ax.plot([60,1140],[170,170],color='#dbd5cc',lw=.8)
label(60,625,'В НАБОРЕ С ВЫБРАННЫМИ СТРОЧНЫМИ',13)
line(ax,'Ива  Ира  Игоря',65,760,125)
line(ax,'Ии  HИH  OИO',65,900,115)
label(60,950,'На рассмотрение. Стойки и засечки H; восходящая диагональ ≈30 ед.',13)
fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());fig.savefig(ROOT/'build/capital-i-preview.png',facecolor=fig.get_facecolor());plt.close(fig)
