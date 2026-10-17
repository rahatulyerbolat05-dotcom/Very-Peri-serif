#!/usr/bin/env python3
"""Measure every primary Cyrillic/basic Latin letter and installed Cyrillic alternate."""
import hashlib,io,json,statistics,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from build_draft_font import CHARS
from audit_author_glyphs import runs
import pathops

BASE='f3614aa'
def metrics(font,name,ch):
    gs=font.getGlyphSet();p=pathops.Path();gs[name].draw(p.getPen());height=720 if ch.isupper() else 510
    spans=[];inks=[]
    for y in range(60,height-60,10):
        r=runs(p,y)
        if r:spans.append(r[-1][1]-r[0][0]);inks.append(sum(b-a for a,b in r))
    return dict(advance=font['hmtx'][name][0],bounds=list(p.bounds),median_body_span=round(statistics.median(spans),2),median_ink_per_row=round(statistics.median(inks),2))

def main():
    path=Path('dist/VeryPeriSerifDraft/VeryPeriSerifDraft-Regular.ttf');data=path.read_bytes();font=TTFont(io.BytesIO(data));old=TTFont(io.BytesIO(subprocess.check_output(['git','show',BASE+':'+str(path)])))
    manifest=json.loads(Path('dist/VeryPeriSerifDraft/build-manifest.json').read_text());chars=CHARS+'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';cmap=font.getBestCmap()
    rows=[]
    for ch in chars:
        n=cmap[ord(ch)];rows.append(dict(character=ch,name=n,role='primary',before=metrics(old,n,ch),after=metrics(font,n,ch)))
    for n,r in manifest['glyph_records'].items():
        if '.' in n and r['character'] in CHARS:rows.append(dict(character=r['character'],name=n,role='alternate',before=metrics(old,n,r['character']),after=metrics(font,n,r['character'])))
    result=dict(baseline_commit=BASE,ttf_sha256=hashlib.sha256(data).hexdigest(),primary_cyrillic_reviewed=len(CHARS),basic_latin_reviewed=52,installed_alternates_reviewed=len(rows)-len(chars),measurements=rows,note='Spans and row ink are diagnostics, not universal width/weight targets; structural groups and shaped text determine optical decisions.')
    Path('data/width-refinement/audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Audited',len(rows),'letter forms')
if __name__=='__main__':main()
