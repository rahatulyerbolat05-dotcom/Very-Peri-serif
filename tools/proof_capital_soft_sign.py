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
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'studies/regular/capital-soft-sign';FONT=OUT/'capitals-shorti01.ttf';f=TTFont(FONT);gs=f.getGlyphSet()
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
label(60,35,'Very Peri Serif · мягкий знак Ь',27,'#272333');label(60,85,'Один вариант · заглавная · Regular',14)
for x,ch,c in [(85,'B','#8a858e'),(460,'Ь','#272333'),(900,'I','#8a858e')]:
 line(ax,ch,x,550,530,c);label(x+65,585,'Новый Ь' if ch=='Ь' else 'Родная '+ch,18,'#2563eb' if ch=='Ь' else '#78747c')
ax.plot([60,1140],[550,550],color='#dbd5cc',lw=.8);ax.plot([60,1140],[168.4,168.4],color='#dbd5cc',lw=.8)
label(60,655,'В НАБОРЕ С НАШИМИ ПРОПИСНЫМИ',13);line(ax,'ЗЯБЬ  ЯЗЬ',65,800,145)
label(60,855,'СОСЕДИ · РОДНЫЕ B / H / O',13);line(ax,'BЬ  HЬ  OЬ',65,960,105)
fig.savefig(OUT/'comparison.svg',facecolor=fig.get_facecolor());fig.savefig(ROOT/'build/capital-soft-sign-preview.png',facecolor=fig.get_facecolor());plt.close(fig)
