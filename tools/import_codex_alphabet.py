#!/usr/bin/env python3
"""Import exact retained Codex study outlines for the shared alphabet proof.

Usage: python3 tools/import_codex_alphabet.py /path/to/codex-checkout
This adds a separate provenance layer; Claude's done records are not replaced.
No curve fitting, simplification or production-font compilation is performed.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
from types import SimpleNamespace
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen,RecordingPen
from fontTools.pens.pointPen import SegmentToPointPen,PointToSegmentPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ufoLib.glifLib import writeGlyphToString,readGlyphFromString
from fontTools.pens.basePen import BasePen

ROOT=Path(__file__).resolve().parents[1]
BASE='studies/regular/ereversed-refined/ereversed-02.ttf'
SPECS={
 'б':('01',False,False,[('01','Капля',BASE)]),
 'в':('01',False,False,[('01','Структурная','studies/regular/ve/ve-01.ttf'),('02','Мягкая','studies/regular/ve/ve-02.ttf')]),
 'г':('02',False,False,[('02','Капля',BASE)]),
 'д':('01',False,False,[('01','Острый свод',BASE)]),
 'ж':('cyr11',False,False,[('cyr11','Cyr11 / импорт',BASE)]),
 'з':('01',False,False,[('01','Открытый терминал',BASE)]),
 'и':('02',True,False,[('02','Родная u',BASE)]),
 'й':(None,True,False,[('01','Родная кратка','studies/regular/shorti/shorti-01.ttf'),('02','Компактная','studies/regular/shorti/shorti-02.ttf')]),
 'к':('02',False,False,[('01','Головка u','studies/regular/ka/ka-01.ttf'),('02','Головка k','studies/regular/ka/ka-02.ttf')]),
 'т':('02',False,False,[('02','Письменный выход',BASE)]),
 'Б':(None,False,False,[('01','Чаша B, плечо E','studies/regular/capitals-bdzei/capitals-shorti01.ttf')]),
 'Д':(None,False,False,[('01','Наклонная нога, короткие выступы','studies/regular/capitals-bdzei/capitals-shorti01.ttf')]),
 'З':(None,False,False,[('01','Две чаши и капли','studies/regular/capitals-bdzei/capitals-shorti01.ttf')]),
 'И':(None,False,False,[('01','Стойки H, диагональ','studies/regular/capital-i/capital-i-shorti01.ttf')]),
 'ч':(None,False,False,[('01','Поднятая чаша u','studies/regular/che-ya/che-ya-shorti01.ttf')]),
 'я':(None,False,False,[('01','Петля и капля y','studies/regular/che-ya/che-ya-shorti01.ttf')]),
 'э':('02',False,False,[('02','Капля a — ниже',BASE)])}

class CurvePen(BasePen):
    """Canonical cubic segments, ignoring contour start and direction."""
    def __init__(self):super().__init__(None);self.segments=[];self.first=None
    def _moveTo(self,p):self.first=tuple(p)
    def _lineTo(self,p):self.segments.append((tuple(self._getCurrentPoint()),tuple(p)))
    def _curveToOne(self,a,b,c):self.segments.append((tuple(self._getCurrentPoint()),tuple(a),tuple(b),tuple(c)))
    def _closePath(self):
        if self._getCurrentPoint()!=self.first:self._lineTo(self.first)
    def canonical(self):
        return sorted(min(s,tuple(reversed(s))) for s in self.segments if s[0]!=s[-1] or len(s)>2)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('codex_root',type=Path)
    source=parser.parse_args().codex_root.resolve();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    config_path=ROOT/'data/alphabet.json';cfg=json.loads(config_path.read_text());before_done=json.dumps(cfg['done'],ensure_ascii=False,sort_keys=True)
    cfg['codex']={};records=[];out=ROOT/'data/codex';out.mkdir(exist_ok=True)
    for ch,(selected,shared,conflict,variants) in SPECS.items():
        entry={'selected':selected,'shared_with_claude':shared,'conflict':conflict,'variants':[],
               'provenance':'user/Claude Cyr11; integrated and retained by Codex' if ch=='ж' else 'Codex study; native Instrument Serif donors credited in source study'}
        for variant,label,relative in variants:
            f=TTFont(source/relative);name=f.getBestCmap()[ord(ch)];gs=f.getGlyphSet();record=DecomposingRecordingPen(gs);gs[name].draw(record)
            width=f['hmtx'][name][0];g=SimpleNamespace(width=width,unicodes=[ord(ch)])
            glif=writeGlyphToString(f'uni{ord(ch):04X}.codex{variant}',g,lambda pp:record.replay(SegmentToPointPen(pp)),formatVersion=2)
            relative_out=f'data/codex/uni{ord(ch):04X}-{variant}.glif';destination=ROOT/relative_out;destination.write_text(glif,encoding='utf-8')
            reread=RecordingPen();rg=SimpleNamespace();readGlyphFromString(glif,rg,PointToSegmentPen(reread));assert rg.width==width
            a=CurvePen();b=CurvePen();record.replay(a);reread.replay(b);assert a.canonical()==b.canonical(),(ch,variant,'geometry')
            bp=BoundsPen(None);reread.replay(bp)
            data={'path':relative_out,'label':label,'variant':variant,'status':'selected' if selected==variant else 'unselected',
                  'advance':width,'bounds':bp.bounds,'glif_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
                  'source_file':relative,'source_glyph':name,'source_glyf_sha256':hashlib.sha256(f['glyf'][name].compile(f['glyf'])).hexdigest(),
                  'source_file_sha256':hashlib.sha256((source/relative).read_bytes()).hexdigest()}
            entry['variants'].append(data);records.append({'character':ch,**data})
        cfg['codex'][ch]=entry
    assert json.dumps(cfg['done'],ensure_ascii=False,sort_keys=True)==before_done
    cfg['shared_review']={'codex_branch':'codex/cyrillic-studies','codex_source_commit':commit,'claude_base_commit':'d2cd2ee856a85d99aa4880b8f44b126ee49a1eca',
                         'conflicts':[],'open_codex_choices':['й','ч','я','И','Б','Д','З'],'selected_ereversed':'02; direct user choice: оставь 02',
                         'count_meaning':'Available drawings, including undecided alternatives; not production-ready or approved coverage.',
                         'missing_notes':{}}
    config_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    manifest={'source_repository':'https://github.com/rahatulyerbolat05-dotcom/Very-Peri-serif','source_branch':'codex/cyrillic-studies','source_commit':commit,
              'native_source_commit':'65c0ef225f386a3c7e87570a4aa9cc0262c2fd81','license':'SIL OFL1.1; see OFL.txt',
              'geometry':'Exact decomposed quadratic contours from retained study TTFs; canonical cubic segment equality and advance checked after GLIF roundtrip.',
              'curve_simplification':False,'files':records}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (out/'OFL.txt').write_bytes((source/'OFL.txt').read_bytes())
    print(json.dumps({'imported_variants':len(records),'codex_characters':list(cfg['codex']),'claude_done_preserved':True},ensure_ascii=False))

if __name__=='__main__':main()
