"""Show retained ghe designs with selected te02/de01; do not alter fonts."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch
from study_layout import hb_shape

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font',type=Path,default=ROOT/'studies/regular/te/te-02.ttf')
parser.add_argument('--output-dir',type=Path,default=ROOT/'build/ghe-context')
args=parser.parse_args();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
font=args.font.resolve();tt=TTFont(font)
selected=json.loads((ROOT/'data/selected-te.json').read_text())
assert hashlib.sha256(tt['glyf']['uni0442'].compile(tt['glyf'])).hexdigest()==selected['glyf_sha256']
variants=[('02','Капля · основная',{},'uni0433'),('01','Клюв · альтернатива',{'ss05':True},'ghe.altBeak')]
runs=[]
class PlotPen(BasePen):
    def __init__(self,gs):super().__init__(gs);self.vertices=[];self.codes=[]
    def _moveTo(self,p):self.vertices.append(p);self.codes.append(MP.MOVETO)
    def _lineTo(self,p):self.vertices.append(p);self.codes.append(MP.LINETO)
    def _curveToOne(self,a,b,c):self.vertices.extend([a,b,c]);self.codes.extend([MP.CURVE4]*3)
    def _closePath(self):self.vertices.append((0,0));self.codes.append(MP.CLOSEPOLY)
def draw(ax,name,x=0,y=0,scale=1,color='#282334'):
    gs=tt.getGlyphSet();p=PlotPen(gs);gs[name].draw(p)
    if p.vertices:ax.add_patch(PathPatch(MP(np.array(p.vertices)*scale+[x,y],p.codes),facecolor=color,lw=0))
def word(ax,text,features,x,y,scale):
    shaped=hb_shape(font,text,features);runs.append({'text':text,'features':features,'glyph_positions':shaped})
    for name,adv,_,dx,dy in shaped:
        draw(ax,name,x+dx*scale,y+dy*scale,scale);x+=adv*scale

fig=plt.figure(figsize=(16,14),facecolor='#f5f1e9')
fig.text(.055,.958,'г / капля и клюв',fontsize=27,color='#282334')
fig.text(.055,.921,'Сохранённые рисунки в контексте выбранных т02 и д01',fontsize=12,color='#827b73')
for i,(v,label,features,glyph) in enumerate(variants):
    x=.055+i*.49;fig.text(x,.86,f'{v} / {label}',fontsize=19,color='#282334')
    assert hb_shape(font,'г',features)[0][0]==glyph
    ax=fig.add_axes([x+.045,.59,.335,.235]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(-20,365);ax.set_ylim(-30,555);draw(ax,glyph)
    ax=fig.add_axes([x,.395,.425,.17]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,3400);ax.set_ylim(-260,950)
    pos=0
    for ch in ['г','r','f','n','т','д']:
        name=glyph if ch=='г' else tt.getBestCmap()[ord(ch)]
        draw(ax,name,pos,color='#8d8479' if ch in ['r','f','n'] else '#282334')
        ax.text(pos+tt['hmtx'][name][0]/2,885,ch,ha='center',fontsize=10,color='#827b73');pos+=tt['hmtx'][name][0]+80
    ax=fig.add_axes([x,.10,.425,.265]);ax.axis('off');ax.set_aspect('equal');ax.set_xlim(0,3700);ax.set_ylim(-220,2650)
    for text,y in [('гора город',1900),('игра итог',950),('бег тогда',0)]:word(ax,text,features,0,y,.70)
fig.text(.055,.05,'Серые r/f/n — исходный Instrument Serif. Все буквы — реальные контуры текущей пробной сборки.',fontsize=10,color='#827b73')
fig.text(.055,.027,'Выбор г не меняется: Капля основная, Клюв через ss05. Рисунки сохранены без изменений.',fontsize=10,color='#827b73')
fig.savefig(out/'comparison.png',dpi=160,facecolor=fig.get_facecolor());fig.savefig(out/'comparison.svg',facecolor=fig.get_facecolor());plt.close(fig)
(out/'shaping.json').write_text(json.dumps({'source_font':str(font.relative_to(ROOT)),'source_sha256':hashlib.sha256(font.read_bytes()).hexdigest(),'purpose':'Retained ghe designs with selected te02/de01; no font edits.','runs':runs},ensure_ascii=False,indent=2)+'\n')
print(out)
