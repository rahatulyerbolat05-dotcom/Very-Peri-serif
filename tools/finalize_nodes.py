#!/usr/bin/env python3
"""Freeze losslessly reduced sources and accepted CFF programs from 1.112."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import writeGlyphToString
from exact_node_reduction import reduce_glyph,canonical_outline,geometry_fingerprint
from polish_outlines import hausdorff

BASELINE='c1ab4b0aed080873447d44c71943f74030486e15'
PROTECTED={'uni044F','uni0433','uni0493','uni0446','uni0449','uni04A3','uni0447'}
SHARED_REGULAR={'uni2012','uni2020','uni2021','uni2032','uni2033','uni20B4','uni20B8','uni20BD','uni2116','uni018F','uni0259','uni2248','uni25CC'}


def baseline_font(style,fmt='ttf'):
    return TTFont(io.BytesIO(subprocess.check_output(['git','show',f'{BASELINE}:fonts/{fmt}/VeryPeriSerif-{style}.{fmt}'])))


def main():
    path=Path('data/curve-finish/manifest.json');manifest=json.loads(path.read_text())
    previous=json.loads(subprocess.check_output(['git','show',BASELINE+':data/curve-finish/manifest.json']))
    report={'release':'1.113','baseline_commit':BASELINE,'method':'exact rational geometry; no fitting or point displacement','styles':{}}
    programs={};changes={}
    for style in ('Regular','Italic'):
        before=baseline_font(style);after=copy.deepcopy(before)
        native=TTFont(f'reference/instrument-serif/fonts/ttf/InstrumentSerif-{style}.ttf')
        clones={native['glyf'][n].compile(native['glyf']) for n in native.getGlyphOrder() if native['glyf'][n].numberOfContours>0}
        original=TTFont(io.BytesIO(subprocess.check_output(['git','show',manifest['baseline_commit']+f':fonts/ttf/VeryPeriSerif-{style}.ttf'])))
        cff=baseline_font(style,'otf')['CFF '].cff.topDictIndex[0].CharStrings
        rows={};programs[style]={}
        for name in before.getGlyphOrder():
            g=before['glyf'][name]
            if name in native.getGlyphOrder() or name in PROTECTED or (style=='Regular' and name in SHARED_REGULAR) or g.numberOfContours<=0 or g.compile(before['glyf']) in clones:continue
            reduced,stats=reduce_glyph(g,before['glyf'])
            if not stats:continue
            after['glyf'][name]=reduced
            assert canonical_outline(before,name)==canonical_outline(after,name),(style,name,'geometry drift')
            metrics=list(before['hmtx'][name]);source=Path(f'data/curve-finish/{style}/{name}.glif')
            record=copy.deepcopy(previous['glyphs'][style].get(name,{}))
            for key in ('additional_input_advance_and_lsb','input_metrics_note'):
                if key in manifest['glyphs'][style].get(name,{}):record[key]=manifest['glyphs'][style][name][key]
            obj=SimpleNamespace(width=metrics[0],unicodes=[cp for cp,n in before.getBestCmap().items() if n==name])
            raw=writeGlyphToString(name,obj,lambda pen:reduced.drawPoints(pen,after['glyf']),formatVersion=2).encode()
            source.write_bytes(raw)
            old=original['glyf'][name]
            record.update(path=str(source),sha256=hashlib.sha256(raw).hexdigest(),advance_and_lsb=metrics,
                          contours=g.numberOfContours,before_bounds=[old.xMin,old.yMin,old.xMax,old.yMax],
                          bounds=[reduced.xMin,reduced.yMin,reduced.xMax,reduced.yMax],
                          outline_deviation=round(float(hausdorff(old,reduced,original['glyf'])),5))
            data={'points_before':len(g.coordinates),'points_after':len(reduced.coordinates),'operations':stats,
                  'geometry_sha256':geometry_fingerprint(before,name)}
            record.setdefault('repairs',[]).append({'repair':'lossless removal of redundant stored points','baseline_commit':BASELINE,**data})
            manifest['glyphs'][style][name]=record;rows[name]=data
            cs=cff[name];cs.decompile()
            assert 'callsubr' not in cs.program and 'callgsubr' not in cs.program
            programs[style][name]={'geometry_sha256':data['geometry_sha256'],'advance':metrics[0],'program':cs.program}
        dependencies=set(rows);again=True
        while again:
            again=False
            for name in before.getGlyphOrder():
                glyph=before['glyf'][name]
                if name not in dependencies and glyph.isComposite() and any(c.glyphName in dependencies for c in glyph.components):
                    dependencies.add(name);again=True
        for name in dependencies-set(rows):
            cs=cff[name];cs.decompile()
            assert 'callsubr' not in cs.program and 'callgsubr' not in cs.program
            programs[style][name]={'geometry_sha256':geometry_fingerprint(before,name),'advance':before['hmtx'][name][0],'program':cs.program}
        report['styles'][style]={'glyphs':rows,'points_removed':sum(r['points_before']-r['points_after'] for r in rows.values()),
                                 'cff_only_dependencies':sorted(dependencies-set(rows))}
        changes[style]=list(rows)
    manifest['release']='1.113'
    manifest.setdefault('outline_revisions',{})['1.113']={'baseline_version':'1.112','baseline_commit':BASELINE,
        'geometry_preserving':True,'glyphs':changes}
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    dest=Path('data/node-reduction');dest.mkdir(exist_ok=True)
    raw=json.dumps(programs,ensure_ascii=False,separators=(',',':')).encode()+b'\n'
    (dest/'cff-programs.json').write_bytes(raw)
    report['cff_programs_sha256']=hashlib.sha256(raw).hexdigest()
    (dest/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({s:{'glyphs':len(r['glyphs']),'points_removed':r['points_removed']} for s,r in report['styles'].items()}))


if __name__=='__main__':main()
