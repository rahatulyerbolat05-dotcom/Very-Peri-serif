#!/usr/bin/env python3
"""Check the actual default/ss10 drawings against the published 1.114 identities."""
import argparse
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))

import ots
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from italic_el_alternate import BASE,NAME,is_promoted,unpromoted_view,PREVIOUS_LABEL
from build_draft_font import native_kern
from contour_contacts import Auditor

SWAP={BASE:NAME,NAME:BASE}


class Shaper:
    def __init__(self,font,pua=False):
        self.font=font
        f=copy.deepcopy(font);f.flavor=None;f.recalcTimestamp=False
        if pua:
            for table in f['cmap'].tables:
                if table.isUnicode():table.cmap.update({0xE000+i:n for i,n in enumerate(f.getGlyphOrder())})
        b=io.BytesIO();f.save(b);self.hf=hb.Font(hb.Face(b.getvalue()))
    def shape(self,text,features=None,lang='ru'):
        b=hb.Buffer();b.add_str(text);b.direction='ltr';b.script='cyrl';b.language=lang
        hb.shape(self.hf,b,features or {})
        return [(self.font.getGlyphName(g.codepoint),p.x_advance,p.x_offset,p.y_offset)
                for g,p in zip(b.glyph_infos,b.glyph_positions)]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('build/release'));ap.add_argument('--formats',default='ttf,otf,woff2')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args();version=json.loads(Path('data/params.json').read_text())['regular_release']['version']
    result={};count=0
    def ck(value,label):
        nonlocal count
        assert value,label
        count+=1
    for style in ('Regular','Italic'):
        for fmt in args.formats.split(','):
            folder='webfonts' if fmt=='woff2' else fmt
            filename=f'VeryPeriSerif-{style}.{fmt}'
            path=args.root/filename if (args.root/filename).exists() else args.root/folder/filename
            current=TTFont(path)
            old=TTFont(io.BytesIO(subprocess.check_output(['git','show',f'v1.114:fonts/{folder}/{filename}'])))
            normalized=unpromoted_view(current)
            ck(current.getGlyphOrder()==old.getGlyphOrder(),(style,fmt,'no added or reordered glyphs'))
            ck(current['cmap'].tables[0].cmap==old['cmap'].tables[0].cmap,(style,fmt,'Unicode mapping retained'))
            for tag in old.keys():
                if tag not in ('GlyphOrder','head','name','glyf','loca','CFF '):
                    ck(normalized.getTableData(tag)==old.getTableData(tag),(style,fmt,'exact inverse table',tag))
            for n in old.getGlyphOrder():
                previous=SWAP.get(n,n) if style=='Italic' else n
                ck(current['hmtx'][n]==old['hmtx'][previous],(style,fmt,'drawing keeps its metrics',n))
                if fmt!='otf':
                    ck(current['glyf'][n].compile(current['glyf'])==old['glyf'][previous].compile(old['glyf']),
                       (style,fmt,'exact drawing and hints',n))
                else:
                    a=current['CFF '].cff.topDictIndex[0].CharStrings[n]
                    b=old['CFF '].cff.topDictIndex[0].CharStrings[previous]
                    a.decompile();b.decompile()
                    ck(a.program==b.program,(style,fmt,'exact CFF program',n))
            ck(current['name'].getDebugName(5)=='Version '+version,(style,fmt,'release version'))
            for nid in (0,8,9,13,14):
                ck(current['name'].getDebugName(nid)==old['name'].getDebugName(nid),(style,fmt,'legal metadata',nid))
            ck(ots.sanitize(str(path),'/dev/null',capture_output=True).returncode==0,(style,fmt,'OTS'))
            row={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'glyphs':len(current.getGlyphOrder())}
            if style=='Italic':
                ck(is_promoted(current),'promoted form has the correct feature label')
                ck(current['name'].getDebugName(265)==PREVIOUS_LABEL,'ss10 names the previous form')
                a,b=Shaper(current),Shaper(old)
                def mapped(items):return [(SWAP.get(n,n),adv,dx,dy) for n,adv,dx,dy in items]
                for lang in ('ru','kk','sr','mk'):
                    for mode in (0,1):
                        for text in ('л','л́','л̀','лл','лилия · аллея · люблю','гүл · әлем · ләззат'):
                            ck(a.shape(text,{'ss10':mode},lang)==mapped(b.shape(text,{'ss10':1-mode},lang)),
                               (fmt,lang,mode,'actual default/previous shaping',text))
                    ck(a.shape('л',{'aalt':1},lang)[0][0]==NAME,(fmt,lang,'previous form in alternates menu'))
                for flags in itertools.product((0,1),repeat=6):
                    shared={f'ss{i+1:02d}':v for i,v in enumerate(flags)}
                    for mode in (0,1):
                        ck(a.shape('лдгт',dict(shared,ss10=mode))==mapped(b.shape('лдгт',dict(shared,ss10=1-mode))),
                           (fmt,'all pre-existing set combinations',flags,mode))
                for text in ('я г ғ ч щ ң','дождь · красота','office affine AVATAR'):
                    ck(a.shape(text)==b.shape(text),(fmt,'unrelated shaping retained',text))
                if fmt=='ttf':
                    probe=Shaper(current,pua=True);order=current.getGlyphOrder();indices={n:i for i,n in enumerate(order)}
                    visible=[n for n in order if current['hmtx'][n][0]>0 and current['glyf'][n].numberOfContours]
                    pairs={(a,b) for form in (BASE,NAME) for n in visible for a,b in ((form,n),(n,form))}
                    auditor=Auditor(current)
                    for left,right in sorted(pairs):
                        kern=native_kern(current,left,right)
                        ck(kern==native_kern(old,SWAP.get(left,left),SWAP.get(right,right)),('each drawing keeps its pair',left,right))
                        text=''.join(chr(0xE000+indices[n]) for n in (left,right))
                        on,off=probe.shape(text),probe.shape(text,{'kern':False})
                        ck(sum(p[1] for p in on)-sum(p[1] for p in off)==kern,('real HarfBuzz kerning',left,right))
                        auditor.check(left,right,current['hmtx'][left][0]+kern,(left,right))
                    row['both_forms_visible_pairs_checked']=len(pairs)
                row['default_metrics']=current['hmtx'][BASE];row['ss10_metrics']=current['hmtx'][NAME]
            else:
                a=Shaper(current)
                ck(a.shape('л')==a.shape('л',{'ss10':1}),(fmt,'Regular unchanged'))
            result[style+'/'+fmt]=row
    report={'version':version,'baseline':'v1.114','passed':count,'failed':0,'fonts':result,
            'scope':'Only the two Italic el identities are exchanged. Each drawing retains its exact contours, metrics, marks and kerning. Global artistic queue remains open.'}
    dest=args.output or Path(f'docs/qa/el-default-{version}.json');dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':count,'failed':0,'report':str(dest)}))


if __name__=='__main__':main()
