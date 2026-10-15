from pathlib import Path
import runpy, xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from fontTools.pens.recordingPen import RecordingPen,DecomposingRecordingPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
x=runpy.run_path(str(Path(__file__).with_name('critique_curves.py')));ROOT=x['ROOT'];OUT=x['OUT'];patch=x['patch'];setup=x['setup']
font=TTFont(ROOT/'studies/regular/de-cursive/de-01.ttf');gs=font.getGlyphSet();cmap=font.getBestCmap()
def rec(ch):
 p=DecomposingRecordingPen(gs);gs[cmap[ord(ch)]].draw(p);return p.value
fig,axes=plt.subplots(3,1,figsize=(17,12),facecolor='#f5f2ec',gridspec_kw={'height_ratios':[1,1.1,.9]})
fig.subplots_adjust(top=.9,bottom=.06,hspace=.22)
fig.suptitle('Контекст проекта: окончания и характер соединений',fontsize=23,x=.11,ha='left')
ax=axes[0]
for i,ch in enumerate('бвгджзийк'):
 patch(ax,rec(ch),color='#db6842' if ch=='д' else '#39343d',transform=lambda v,i=i:v*.7+[i*400,0]);ax.text(i*400+140,-65,ch,fontsize=18,ha='center')
setup(ax,(-20,3600),(-130,570));ax.set_title('Глифы сборки: в/й/к без основного; оранжевая д — отклонённая проба',loc='left',fontsize=13)
ax=axes[1]
for i,ch in enumerate('oadubpgfrct'):
 patch(ax,x['native'](ch),color='#77716a',transform=lambda v,i=i:v*.72+[i*340,0]);ax.text(i*340+130,-195,ch,fontsize=18,ha='center')
setup(ax,(-20,3750),(-230,590));ax.set_title('Родной Regular: сравнивать не только толщину, но и целое движение к окончанию',loc='left',fontsize=13)
ax=axes[2]
for i,name in enumerate(['Vector.svg','Vector-1.svg']):
 doc=ET.parse(ROOT/'studies/regular/de-loop/references'/name)
 for path in doc.getroot().iter('{http://www.w3.org/2000/svg}path'):
  p=RecordingPen();parse_path(path.attrib['d'],p);patch(ax,p.value,color='#77716a',transform=lambda v,i=i:v*[2,-2]+[i*410+130,420])
 ax.text(i*410+225,-40,name,fontsize=12,ha='center')
setup(ax,(0,2100),(-80,460));ax.text(950,200,'Исходные эскизы пользователя показывают\nпетлевую нижнюю конструкцию.\nЭто история направления, а не утверждение\nнынешних верхних кривых или их окончаний.',fontsize=13,color='#736b62');ax.set_title('Исторические пользовательские эскизы — сохранены без геометрических изменений',loc='left',fontsize=13)
fig.savefig(OUT/'approved-and-native-context.svg',bbox_inches='tight');fig.savefig(OUT/'approved-and-native-context.png',dpi=150,bbox_inches='tight')
