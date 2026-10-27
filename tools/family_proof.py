#!/usr/bin/env python3
"""Reproducible outline specimens and complete alphabet proofs from final fonts."""
import datetime
import html
import io
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='VeryPeriSerif'
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D
from fontTools.ttLib import TTFont
from alphabet_sheet import MplPen
import uharfbuzz as hb
from PIL import Image,ImageDraw,ImageFont

UP='АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӘҒҚҢӨҰҮҺІ'
LOW=UP.lower()
BG='#f5f2ec';INK='#272333'


class Proof:
    def __init__(self,path):
        self.path=Path(path);self.font=TTFont(path);self.gs=self.font.getGlyphSet()
        self.hf=hb.Font(hb.Face(self.path.read_bytes()));hb.ot_font_set_funcs(self.hf)
    def line(self,ax,text,x,y,size=75,features=None,color=INK,language='ru'):
        b=hb.Buffer();b.add_str(text);b.guess_segment_properties();b.language=language
        hb.shape(self.hf,b,features or {});z=size/1000
        for n,p in zip(b.glyph_infos,b.glyph_positions):
            pen=MplPen(self.gs);self.gs[self.font.getGlyphName(n.codepoint)].draw(pen)
            if pen.vertices:
                ax.add_patch(PathPatch(pen.result(),facecolor=color,edgecolor='none',
                             transform=Affine2D().scale(z,-z).translate(x+p.x_offset*z,y-p.y_offset*z)+ax.transData))
            x+=p.x_advance*z
        return x


def page(title,width=1200,height=1650,dark=False):
    # Glyph sizes below use CSS pixels (96/in), including 133 1/3 px = 100 pt.
    # Match the figure's physical scale so PDF labels also describe real points.
    fig,ax=plt.subplots(figsize=(width/96,height/96),dpi=96)
    fig.patch.set_facecolor(INK if dark else BG);ax.set_facecolor(INK if dark else BG)
    ax.set_xlim(0,width);ax.set_ylim(height,0);ax.axis('off');fig.subplots_adjust(0,0,1,1)
    ax.text(45,48,title,fontsize=16,color=BG if dark else '#69656a')
    return fig,ax


def main():
    out=Path('build/release');images=Path('build/premium');images.mkdir(parents=True,exist_ok=True)
    (images/'before').mkdir(exist_ok=True)
    for style in ('Regular','Italic'):
        target=images/'before'/f'{style}.ttf'
        if not target.exists():
            target.write_bytes(subprocess.check_output(['git','show',f'a7bec14:fonts/ttf/VeryPeriSerif-{style}.ttf']))
    proofs={s:Proof(out/f'VeryPeriSerif-{s}.ttf') for s in ('Regular','Italic')}
    config=json.loads(Path('data/params.json').read_text())['regular_release']
    version=config['version']
    previous_ghe=images/'before/Italic-1.100.ttf'
    if not previous_ghe.exists():
        previous_ghe.write_bytes(subprocess.check_output(['git','show','fdd1fe5:fonts/ttf/VeryPeriSerif-Italic.ttf']))
    previous_revision=images/'before/Italic-1.101.ttf'
    if not previous_revision.exists():
        previous_revision.write_bytes(subprocess.check_output(['git','show','b0763f3:fonts/ttf/VeryPeriSerif-Italic.ttf']))
    previous_ya=images/'before/Italic-1.102.ttf'
    if version=='1.103' and not previous_ya.exists():
        previous_ya.write_bytes(subprocess.check_output(['git','show','3888bab:fonts/ttf/VeryPeriSerif-Italic.ttf']))
    previous_ya_joins=images/'before/Italic-1.103.ttf'
    if version=='1.104' and not previous_ya_joins.exists():
        previous_ya_joins.write_bytes(subprocess.check_output(['git','show','89e8b25:fonts/ttf/VeryPeriSerif-Italic.ttf']))
    previous_regular_ya=images/'before/Regular-1.104.ttf'
    if version=='1.105' and not previous_regular_ya.exists():
        previous_regular_ya.write_bytes(subprocess.check_output(['git','show','54b903d:fonts/ttf/VeryPeriSerif-Regular.ttf']))
    previous_regular_foot=images/'before/Regular-1.105.ttf'
    if version=='1.106' and not previous_regular_foot.exists():
        previous_regular_foot.write_bytes(subprocess.check_output(['git','show','686e313:fonts/ttf/VeryPeriSerif-Regular.ttf']))
    if version=='1.107':
        previous_regular_foot=images/'before/Regular-1.106.ttf'
        if not previous_regular_foot.exists():
            previous_regular_foot.write_bytes(subprocess.check_output(['git','show','aa705fd:fonts/ttf/VeryPeriSerif-Regular.ttf']))
    date=datetime.datetime.fromisoformat(config['date']).replace(tzinfo=datetime.timezone.utc)
    meta={'Title':'Very Peri Serif '+version+' — Regular & Italic','Author':'Very Peri Serif project',
          'CreationDate':date,'ModDate':date}
    with PdfPages(out/'family-specimen.pdf',metadata=meta) as pdf:
        for style,p in proofs.items():
            fig,ax=page('Very Peri Serif '+version+' · '+style)
            rows=[('Красота начинается',100),('с внимания к деталям.',100),('С любовью к буквам.',110),
                  ('Жизнь, движение, тишина.',90),('Қазақ тілі — әдемі тіл.',100),
                  ('Күн, гүл, үміт, ұлт, құс.',95),('A thoughtful serif.',115),('office affine final · 12 500 ₸',90)]
            for i,(text,size) in enumerate(rows):p.line(ax,text,45,225+i*180,size)
            pdf.savefig(fig);fig.savefig(images/(style+'-words.png'));plt.close(fig)
            # Every letter, one cell per glyph, at 100 pt (133.33 px).
            fig,ax=page(style+' · complete Russian and Kazakh alphabet · 100 pt',1400,2000)
            for i,ch in enumerate(UP+LOW):
                x=30+(i%7)*195;y=220+(i//7)*145
                ax.text(x,y-105,ch,fontsize=10,color='#777777')
                p.line(ax,ch,x+35,y,133.333)
            pdf.savefig(fig);fig.savefig('docs/img/premium-'+style.lower()+'-alphabet.svg',metadata={'Date':config['date']})
            fig.savefig(images/(style+'-alphabet.png'));plt.close(fig)
        fig,ax=page('Stress, decomposed sequences, stacked marks and Kazakh distinctions')
        for i,(style,p) in enumerate(proofs.items()):
            y=150+i*730;ax.text(45,y-35,style,fontsize=16,color='#777777')
            for j,text in enumerate(['о́ я́ ы́ э́ ю́ ә́ ү́ і́ ё́ й́','О́ Я́ Ы́ Э́ Ю́ Ә́ Ү́ І́ Ё́ Й́',
                                     'я̈́ ӛ́ Я̈́ Ӛ́','У Ү Ұ · у ү ұ · Н Ң · н ң','К Қ · к қ · О Ө · о ө · Ә ә Һ һ І і']):
                p.line(ax,text,45,y+90+j*118,85)
        pdf.savefig(fig);fig.savefig(images/'marks.png');plt.close(fig)
        fig,ax=page('Stylistic sets and language-specific forms')
        y=145
        for style,p in proofs.items():
            ax.text(45,y-35,style,fontsize=16,color='#777777')
            modes=[('Default',{},'ru')]
            if style=='Regular':modes += [('ss01',{'ss01':1},'ru'),('ss07',{'ss07':1},'ru'),('ss08',{'ss08':1},'ru'),('ss09',{'ss09':1},'ru')]
            else:modes += [('ss%02d'%i,{'ss%02d'%i:1},'ru') for i in range(1,7)]+[('ss10',{'ss10':1},'ru'),('locl SRB',{},'sr'),('locl MKD',{},'mk')]
            for label,features,lang in modes:
                ax.text(45,y+10,label,fontsize=10,color='#777777')
                p.line(ax,'л · б г д п т · к ж э · ц щ қ ң',200,y+45,67,features,language=lang);y+=85
            y+=90
        pdf.savefig(fig);fig.savefig(images/'alternates.png');plt.close(fig)
        for dark in (False,True):
            fig,ax=page('12 / 24 / 100 pt · '+('dark' if dark else 'light'),dark=dark)
            color=BG if dark else INK;y=150
            for style,p in proofs.items():
                for size in (16,32,133.333):
                    ax.text(45,y-35,style+' · '+str(round(size*.75))+' pt',fontsize=11,color=color)
                    texts=('Жизнь, тишина.','Қазақ тілі: үміт.') if size>100 else ('Жизнь, тишина, любовь.','Қазақ тілі: үміт пен өнер.')
                    for j,text in enumerate(texts):
                        end=p.line(ax,text,45,y+size*(.6+1.25*j)+30*j,size,color=color)
                        assert end<1155,(style,size,text,end)
                    y+=size*2+130
            pdf.savefig(fig);fig.savefig(images/('sizes-dark.png' if dark else 'sizes-light.png'));plt.close(fig)
        fig,ax=page('Numbers, punctuation, ligatures and spacing')
        for k,(style,p) in enumerate(proofs.items()):
            y=180+k*720
            for j,text in enumerate(['0123456789 · 111 000 · 888 000','12 500 ₸ · 500 ₽ · № 24 · −15%',
                                     '«Слова», (слова) — слова…','office affine final · fi fl ffi ffl','То ТА Гл ДО Уд Үл · аА аЖ нТ']):
                p.line(ax,text,45,y+j*115,85)
            p.line(ax,'0123456789 · 111 000 · 888 000',45,y+575,85,{'tnum':1})
        pdf.savefig(fig);fig.savefig(images/'numbers.png');plt.close(fig)
        fig,ax=page('Italic · г · previous / chosen default / Serbian local form',1200,1250)
        old_ghe=Proof(previous_ghe)
        for i,(label,p,lang) in enumerate((('1.100',old_ghe,'ru'),(version,proofs['Italic'],'ru'),('locl SRB',proofs['Italic'],'sr'))):
            ax.text(45+i*400,110,label,fontsize=15,color='#69656a')
            p.line(ax,'г',100+i*400,410,330,language=lang)
        for i,(label,p) in enumerate((('Previous · 1.100',old_ghe),('Default · '+version,proofs['Italic']))):
            y=520+i*360;ax.text(45,y,label,fontsize=15,color='#69656a')
            p.line(ax,'глина · город · дорога',45,y+115,95)
            p.line(ax,'гүл · ертеңгі · ғылым',45,y+245,95)
        pdf.savefig(fig);fig.savefig('docs/img/ghe-revision.svg',metadata={'Date':config['date']})
        fig.savefig(images/'ghe.png');plt.close(fig)
        fig,ax=page('Italic · rounded de bowl and Kazakh barred ghe · 1.101 / '+version,1500,1400)
        old_revision=Proof(previous_revision)
        for col,(label,p) in enumerate((('Before · 1.101',old_revision),('After · '+version,proofs['Italic']))):
            x=45+750*col;ax.text(x,115,label,fontsize=16,color='#69656a')
            p.line(ax,'д',x,610,680)
            p.line(ax,'г ғ',x+345,610,410)
            ax.plot([x,x+660],[610,610],color='#d89595',linewidth=.7)
            p.line(ax,'дело · вода · дождь',x,900,84)
            end=p.line(ax,'ғылым · ғарыш · ағаш',x,1050,84,language='kk')
            assert end<x+700,('Revision specimen width',end-x)
            p.line(ax,'гүл · тоғыз · ғалым',x,1200,84,language='kk')
        pdf.savefig(fig)
        if version=='1.102':fig.savefig('docs/img/italic-1.102.svg',metadata={'Date':config['date']})
        fig.savefig(images/'italic-1.102.png');plt.close(fig)
        # Outline-level enlargement of the defect from the author's screenshot.
        fig,axes=plt.subplots(1,2,figsize=(12,4),facecolor=BG)
        for col,p in enumerate((old_revision,proofs['Italic'])):
            ax=axes[col];ax.set_facecolor(BG);name=p.font.getBestCmap()[ord('д')]
            pen=MplPen(p.gs);p.gs[name].draw(pen)
            ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none'))
            ax.axhline(0,color='#d89595',linewidth=.7)
            ax.set_xlim(35,170);ax.set_ylim(-20,48);ax.set_aspect('equal');ax.axis('off')
            ax.set_title('д · '+('Before 1.101' if col==0 else 'After '+version),fontsize=15,color='#69656a')
        fig.tight_layout();pdf.savefig(fig)
        if version=='1.102':fig.savefig('docs/img/de-bowl-1.102.svg',metadata={'Date':config['date']})
        fig.savefig(images/'de-bowl-1.102.png');plt.close(fig)
        if version=='1.103':
            old_ya=Proof(previous_ya)
            fig,ax=page('Italic я · lower bowl · 1.102 / 1.103',1500,1150)
            for col,(label,p) in enumerate((('Before · 1.102',old_ya),('After · 1.103',proofs['Italic']))):
                x=45+750*col;ax.text(x,105,label,fontsize=16,color='#69656a')
                p.line(ax,'я',x+150,750,790)
                p.line(ax,'моя · яркая · земля',x,960,87)
            pdf.savefig(fig);fig.savefig('docs/img/ya-1.103.svg',metadata={'Date':config['date']})
            fig.savefig(images/'ya-1.103.png');plt.close(fig)
            fig,axes=plt.subplots(1,2,figsize=(12,4),facecolor=BG)
            for col,p in enumerate((old_ya,proofs['Italic'])):
                ax=axes[col];ax.set_facecolor(BG);name=p.font.getBestCmap()[ord('я')]
                pen=MplPen(p.gs);p.gs[name].draw(pen)
                ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none'))
                ax.set_xlim(95,205);ax.set_ylim(182,250);ax.set_aspect('equal');ax.axis('off')
                ax.set_title('я · '+('Before 1.102' if col==0 else 'After 1.103'),fontsize=15,color='#69656a')
            fig.tight_layout();pdf.savefig(fig)
            fig.savefig('docs/img/ya-bowl-1.103.svg',metadata={'Date':config['date']})
            fig.savefig(images/'ya-bowl-1.103.png');plt.close(fig)
        if version=='1.104':
            old_ya=Proof(previous_ya_joins)
            fig,ax=page('Italic я · smooth donor joins · 1.103 / 1.104',1500,1150)
            for col,(label,p) in enumerate((('Before · 1.103',old_ya),('After · 1.104',proofs['Italic']))):
                x=45+750*col;ax.text(x,105,label,fontsize=16,color='#69656a')
                p.line(ax,'я',x+150,750,790)
                p.line(ax,'моя · яркая · земля',x,960,87)
            pdf.savefig(fig);fig.savefig('docs/img/ya-joins-1.104.svg',metadata={'Date':config['date']})
            fig.savefig(images/'ya-joins-1.104.png');plt.close(fig)
            fig,axes=plt.subplots(2,2,figsize=(12,7),facecolor=BG)
            for col,p in enumerate((old_ya,proofs['Italic'])):
                name=p.font.getBestCmap()[ord('я')]
                for row,(xlim,ylim,label) in enumerate((((205,325),(470,530),'top bowl / stem'),((150,265),(135,235),'lower link / stem'))):
                    ax=axes[row,col];ax.set_facecolor(BG);pen=MplPen(p.gs);p.gs[name].draw(pen)
                    ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none'))
                    ax.set_xlim(*xlim);ax.set_ylim(*ylim);ax.set_aspect('equal');ax.axis('off')
                    ax.set_title(label+' · '+('1.103' if col==0 else '1.104'),fontsize=14,color='#69656a')
            fig.tight_layout();pdf.savefig(fig)
            fig.savefig('docs/img/ya-joins-detail-1.104.svg',metadata={'Date':config['date']})
            fig.savefig(images/'ya-joins-detail-1.104.png');plt.close(fig)
        if version=='1.105':
            old_ya=Proof(previous_regular_ya)
            fig,ax=page('Regular я · smooth leg shoulders · 1.104 / 1.105',1500,1150)
            for col,(label,p) in enumerate((('Before · 1.104',old_ya),('After · 1.105',proofs['Regular']))):
                x=45+750*col;ax.text(x,105,label,fontsize=16,color='#69656a')
                p.line(ax,'я',x+150,750,790)
                p.line(ax,'моя · яркая · земля',x,960,87)
            pdf.savefig(fig);fig.savefig('docs/img/ya-regular-1.105.svg',metadata={'Date':config['date']})
            fig.savefig(images/'ya-regular-1.105.png');plt.close(fig)
            fig,axes=plt.subplots(1,2,figsize=(12,4),facecolor=BG)
            for col,p in enumerate((old_ya,proofs['Regular'])):
                ax=axes[col];ax.set_facecolor(BG);name=p.font.getBestCmap()[ord('я')]
                pen=MplPen(p.gs);p.gs[name].draw(pen)
                ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none'))
                ax.set_xlim(130,235);ax.set_ylim(205,270);ax.set_aspect('equal');ax.axis('off')
                ax.set_title('я · '+('1.104' if col==0 else '1.105'),fontsize=15,color='#69656a')
            fig.tight_layout();pdf.savefig(fig)
            fig.savefig('docs/img/ya-regular-detail-1.105.svg',metadata={'Date':config['date']})
            fig.savefig(images/'ya-regular-detail-1.105.png');plt.close(fig)
        if version in ('1.106','1.107'):
            previous='1.105' if version=='1.106' else '1.106'
            old_ya=Proof(previous_regular_foot)
            fig,ax=page('Regular я · right foot · '+previous+' / '+version,1500,1150)
            for col,(label,p) in enumerate((('Before · '+previous,old_ya),('After · '+version,proofs['Regular']))):
                x=45+750*col;ax.text(x,105,label,fontsize=16,color='#69656a')
                p.line(ax,'я',x+150,750,790)
                p.line(ax,'моя · яркая · земля',x,960,87)
            pdf.savefig(fig);fig.savefig('docs/img/ya-regular-foot-'+version+'.svg',metadata={'Date':config['date']})
            fig.savefig(images/('ya-regular-foot-'+version+'.png'));plt.close(fig)
            fig,axes=plt.subplots(1,2,figsize=(12,4),facecolor=BG)
            for col,p in enumerate((old_ya,proofs['Regular'])):
                ax=axes[col];ax.set_facecolor(BG);name=p.font.getBestCmap()[ord('я')]
                pen=MplPen(p.gs);p.gs[name].draw(pen)
                ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none'))
                ax.set_xlim(220,330);ax.set_ylim(-20,125);ax.set_aspect('equal');ax.axis('off')
                ax.set_title('я · '+(previous if col==0 else version),fontsize=15,color='#69656a')
            fig.tight_layout();pdf.savefig(fig)
            fig.savefig('docs/img/ya-regular-foot-detail-'+version+'.svg',metadata={'Date':config['date']})
            fig.savefig(images/('ya-regular-foot-detail-'+version+'.png'));plt.close(fig)
    # Compact before/after proof. The baseline comes from the recorded published
    # a7bec14 binaries, never from a font rebuilt after editing the sources.
    fig,ax=page('Italic · a7bec14 / '+version+' · bowls reconstructed, native Latin unchanged',1600,1050)
    for i,src in enumerate((images/'before/Italic.ttf',out/'VeryPeriSerif-Italic.ttf')):
        p=Proof(src);y=220+i*470
        ax.text(35,y-120,'Before' if i==0 else 'After',fontsize=15,color='#777777')
        p.line(ax,'жизнь · мужчина · вежливость',35,y,115)
        p.line(ax,'ж жж нж жн · н о п и ш т м ж ф ю ы д з в',35,y+170,95)
    fig.savefig('docs/img/premium-comparison.svg',metadata={'Date':config['date']});fig.savefig(images/'comparison.png');plt.close(fig)
    fig,ax=page('Regular · rounded de retained, lower loop -280 / -250',1600,900)
    for i,src in enumerate((images/'before/Regular.ttf',out/'VeryPeriSerif-Regular.ttf')):
        p=Proof(src);y=230+i*410
        ax.text(35,y-120,'Before' if i==0 else 'After',fontsize=15,color='#777777')
        p.line(ax,'дело · вода · звезда · дождь · подход',35,y,115)
        p.line(ax,'д дд нд дн · дно · двадцать · дело',35,y+135,90)
    fig.savefig('docs/img/premium-de-comparison.svg',metadata={'Date':config['date']});fig.savefig(images/'de-comparison.png');plt.close(fig)
    # Enlargements of the actual exported outlines requested by the author.
    # Align ж by its central stem; its overall width has also changed.
    before=Proof(images/'before/Italic.ttf');after=proofs['Italic']
    fig,axes=plt.subplots(2,2,figsize=(16,10),facecolor=BG)
    for row,ch in enumerate('жз'):
        for col,p in enumerate((before,after)):
            ax=axes[row,col];ax.set_facecolor(BG);n=p.font.getBestCmap()[ord(ch)]
            pen=MplPen(p.gs);p.gs[n].draw(pen)
            centre=p.font['hmtx'][n][0]/2+10 if ch=='ж' else 230
            ax.add_patch(PathPatch(pen.result(),facecolor=INK,edgecolor='none',transform=Affine2D().translate(-centre,0)+ax.transData))
            ax.set_xlim((-100,100) if ch=='ж' else (-120,120));ax.set_ylim((120,440) if ch=='ж' else (435,535));ax.set_aspect('equal');ax.axis('off')
            ax.set_title(ch+' · '+('Before a7bec14' if col==0 else 'After '+version),fontsize=16,color='#69656a')
    fig.tight_layout();fig.savefig('docs/img/premium-joins.svg',metadata={'Date':config['date']});fig.savefig(images/'joins.png');plt.close(fig)
    # Minimal portable live-font specimen (PDF above uses outlines deliberately).
    styles='''@font-face{font-family:VP;src:url('../../fonts/webfonts/VeryPeriSerif-Regular.woff2');font-style:normal}
@font-face{font-family:VP;src:url('../../fonts/webfonts/VeryPeriSerif-Italic.woff2');font-style:italic}
body{margin:48px;background:#f5f2ec;color:#272333;font-family:system-ui}main{max-width:1200px;margin:auto}
.sample{font-family:VP,serif;font-size:64px;line-height:1.35;margin:32px 0;overflow-wrap:anywhere}.italic{font-style:italic}.tabular{font-variant-numeric:tabular-nums}
@media print{body{margin:20px}.sample{break-inside:avoid;font-size:40px}}'''
    blocks=['<!doctype html><meta charset="utf-8"><title>Very Peri Serif '+version+'</title><style>'+styles+'</style><main><h1>Very Peri Serif '+version+'</h1>']
    for style in proofs:
        klass='sample'+(' italic' if style=='Italic' else '')
        blocks += ['<h2>'+style+'</h2>']
        for text in [UP,LOW,'Красота начинается с внимания к деталям.','Қазақ тілі: жаңбыр, үміт, ұлы, өмір.',
                     'глина город дорога · гүл ертеңгі',
                     'дело вода дождь · ғылым ғарыш ағаш тоғыз',
                     'моя · яркая · земля',
                     'о́ я́ ы́ э́ ю́ ә́ ү́ і́ ё́ · О́ Я́ Ы́ Э́ Ю́ Ә́ Ү́','office affine final · 12 500 ₸']:
            blocks.append('<p class="'+klass+'">'+html.escape(text)+'</p>')
        blocks.append('<p class="'+klass+' tabular">0123456789 · 111 000 · 888 000</p>')
        if style == 'Italic':
            blocks.append('<h3>ss10 — л: прежняя диагональная форма</h3>')
            blocks.append('<p class="'+klass+'" style="font-feature-settings: &quot;ss10&quot; 1">лилия · аллея · люблю · гүл · әлем</p>')
    blocks.append('</main>')
    Path('docs/specimen').mkdir(parents=True,exist_ok=True)
    Path('docs/specimen/family.html').write_text('\n'.join(blocks))
    print('Family specimen:',out/'family-specimen.pdf')


if __name__=='__main__':main()
