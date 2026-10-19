#!/usr/bin/env python3
"""OpenType additions of the Italic test font (I023, author: "come up with alternate forms, ligatures and kerning"):
  locl SRB, MKD  Serbian and Macedonian italic forms (Krista Radoeva, localfonts.eu; John Hudson proposed locl for these languages):
                 г -> ī (native imacron), д -> g (native g), п -> ū (native umacron), т -> ш with macron (uni0442.srb, composite);
                 б -> ð shape (native eth, drawn by Instrument as a delta) for Serbian only: for Macedonian print the delta б is disputed
                 (freedesktop bug 106488), so MKD keeps the Russian б.
  ss01           the native ss01 (a c d e g without the exit tail) for the Cyrillic homoglyphs а с е ё as well (D10 of the Regular).
  ss02           д with the ascender (the delta form of Russian handwriting), the native eth outline.
  ss03           printed т (T-shaped): stem of the native ı without its entry hook, bar and arm ends of the native T at the x-height.
All substitutions sit under script cyrl, so the Latin n m g of the same glyphs are never touched. Ligatures: none are added on purpose;
measured, no Cyrillic pair of this Italic collides the way f + i or q + j does in the native Latin (the reason for its liga/dlig),
the only near touches are Kazakh ү ұ + у р under the baseline (6-9 units), and they are kerned (tools/italic_kern.py, DESC_CLEAR).
Run after tools/italic_lower.py and before tools/italic_kern.py (the kerning measures the new glyphs too, data/italic-features.json).
Usage: python3 -I tools/italic_features.py [font.ttf]
"""
import copy,glob,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph,GlyphComponent
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import italic_lower as L
from italic_tidy import tidy
from italic_fair import fair

OUT=Path('data/italic-features.json')
T_BAR=150.                     # half length of the printed т bar from the stem centre (ud); native t: 71 left, 93 right of its stem
ARM=60.;ARM_W=70.             # arms of the printed т: depth below the bar top, width of the piece of T taken at each end


def path_of(font,name):
    p=pathops.Path();font.getGlyphSet()[name].draw(p.getPen());return p


def top_centre(font,name,y=470):
    sl=L.slices(path_of(font,name),y);return (sl[0][0]+sl[-1][1])/2+L.S*y


def build_glyphs(font):
    glyf=font['glyf'];hmtx=font['hmtx'];new={}
    # т for Serbian/Macedonian: ш with the macron placed as on ū (umacron: macron moved 29 over u)
    u_off=dict((c.glyphName,c.x) for c in glyf['umacron'].components)['uni0304']
    dx=round(top_centre(font,'uni0448')-top_centre(font,'u')+u_off)
    g=Glyph();g.numberOfContours=-1;g.components=[]
    for name,x in (('uni0448',0),('uni0304',dx)):
        c=GlyphComponent();c.glyphName=name;c.x=x;c.y=0;c.flags=0x4 if name=='uni0448' else 0;g.components.append(c)
    glyf['uni0442.srb']=g;hmtx['uni0442.srb']=hmtx['uni0448'];new['uni0442.srb']=dict(source='uni0448 + uni0304',dx=dx)
    # printed т: stem of ı (entry hook and flag cut), bar with the arms of the native T: cut ARM below the bar top and rounded by a disc as wide
    # as the arm there (T: 190 of 720; the
    # Regular т t1 drops 70), moved down 210 to the x-height, the bar between them as thick as the T bar (28)
    i=path_of(font,'dotlessi');T=path_of(font,'T')
    sl=L.slices(i,300)[0];c=(sl[0]+sl[1])/2
    bar=L.slices(T,705)[0];b0,b1=bar                                                 # T bar ends (ud)
    ys=[y/2 for y in range(1300,1442) if len(L.slices(T,y/2))==1];y_lo,y_hi=min(ys),max(ys)   # rows where the bar is one piece
    D=-210.;sx=-L.S*D                                                                 # move down 210 keeping ud
    arms=L.AND(T,L.OR(L.left_of(b0+ARM_W),L.right_of(b1-ARM_W)))
    arms=L.AND(arms,L.above(720-ARM))
    yc=720-ARM
    def drop(side):                                   # round end on the cut: a disc as wide as the arm there (drop terminal, F5)
        a,b=L.slices(T,yc+1)[0 if side<0 else -1];r=(b-a)/2;u=(a+b)/2
        return L.OR(L.AND(arms,L.left_of(b0+ARM_W) if side<0 else L.right_of(b1-ARM_W)),L.disc(u+L.S*yc,yc,r))
    left=L.transformed(drop(-1),dx=c-T_BAR-b0+L.S*D,dy=D)
    right=L.transformed(drop(1),dx=c+T_BAR-b1+L.S*D,dy=D)
    mid=L.band(c-T_BAR+ARM_W-10,c+T_BAR-ARM_W+10,y_lo+D,y_hi+D)
    stem=L.OR(L.AND(i,L.AND(L.right_of(sl[0]-14),L.below(300))),L.band(sl[0],sl[1],290,y_lo+D+6))
    p=L.OR(stem,left,right,mid);y_lo,y_hi=y_lo+D,y_hi+D
    g=L.to_glyph(p,glyf);g,_=tidy(g,glyf);g,_=fair(g,glyf);g.recalcBounds(glyf)
    lsb,rsb=14,14;g.coordinates.translate((lsb-g.xMin,0));g.recalcBounds(glyf)
    glyf['uni0442.ss03']=g;hmtx['uni0442.ss03']=(int(g.xMax+rsb),g.xMin)
    new['uni0442.ss03']=dict(source='dotlessi stem + T bar and arms',bar=[round(c-T_BAR),round(c+T_BAR)],bar_y=[y_lo,y_hi],points=len(g.coordinates))
    font.setGlyphOrder(glyf.glyphOrder)
    return new


FEA='''languagesystem DFLT dflt;
languagesystem latn dflt;
languagesystem cyrl dflt;
languagesystem cyrl SRB;
languagesystem cyrl MKD;
feature locl {
  script cyrl;
  language SRB exclude_dflt;
    sub uni0431 by eth;
    sub uni0433 by imacron;
    sub uni0434 by g;
    sub n by umacron;
    sub m by uni0442.srb;
  language MKD exclude_dflt;
    sub uni0433 by imacron;
    sub uni0434 by g;
    sub n by umacron;
    sub m by uni0442.srb;
} locl;
feature ss02 {
  featureNames { name "Cyrillic de with ascender"; name 3 1 0x0419 "д с выносом вверх"; };
  script cyrl;
  sub uni0434 by eth;
} ss02;
feature ss03 {
  featureNames { name "Cyrillic printed te"; name 3 1 0x0419 "т печатная"; };
  script cyrl;
  sub m by uni0442.ss03;
} ss03;
'''
NATIVE_FOR_CYRL={'aalt','case','ccmp','dlig','liga','ordn','ss01'}


def merge_gsub(font,extra):
    """Append the lookups and features of extra's GSUB; add script cyrl (default, SRB, MKD) with its own features and the native ones."""
    old=font['GSUB'].table;new=extra['GSUB'].table;off=len(old.LookupList.Lookup)
    from build_draft_font import offset_lookup_records
    for lk in new.LookupList.Lookup:offset_lookup_records(lk,off)
    old.LookupList.Lookup.extend(new.LookupList.Lookup);old.LookupList.LookupCount=len(old.LookupList.Lookup)
    base=len(old.FeatureList.FeatureRecord)
    for r in new.FeatureList.FeatureRecord:
        r.Feature.LookupListIndex=[j+off for j in r.Feature.LookupListIndex];old.FeatureList.FeatureRecord.append(r)
    native=[i for i,r in enumerate(old.FeatureList.FeatureRecord[:base]) if r.FeatureTag in NATIVE_FOR_CYRL]
    cyrl=next(s for s in new.ScriptList.ScriptRecord if s.ScriptTag=='cyrl')
    for ls in [cyrl.Script.DefaultLangSys]+[r.LangSys for r in cyrl.Script.LangSysRecord]:
        ls.FeatureIndex=sorted(set(native+[i+base for i in ls.FeatureIndex]))
    assert 'cyrl' not in [s.ScriptTag for s in old.ScriptList.ScriptRecord]
    old.ScriptList.ScriptRecord.append(cyrl);old.ScriptList.ScriptRecord.sort(key=lambda s:s.ScriptTag);old.ScriptList.ScriptCount=len(old.ScriptList.ScriptRecord)
    # DFLT and latn keep only their own (native) features: the new records are cyrl-only
    order=sorted(range(len(old.FeatureList.FeatureRecord)),key=lambda i:old.FeatureList.FeatureRecord[i].FeatureTag)
    remap={o:n for n,o in enumerate(order)}
    old.FeatureList.FeatureRecord=[old.FeatureList.FeatureRecord[i] for i in order];old.FeatureList.FeatureCount=len(order)
    for s in old.ScriptList.ScriptRecord:
        for ls in [s.Script.DefaultLangSys]+[r.LangSys for r in s.Script.LangSysRecord]:
            if ls is None:continue
            if s.ScriptTag!='cyrl':ls.FeatureIndex=[i for i in ls.FeatureIndex if i<base]
            ls.FeatureIndex=sorted(remap[i] for i in ls.FeatureIndex);ls.FeatureCount=len(ls.FeatureIndex)
            if getattr(ls,'ReqFeatureIndex',0xFFFF)!=0xFFFF:ls.ReqFeatureIndex=remap[ls.ReqFeatureIndex]


def main():
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    path=args[0] if args else sorted(glob.glob('build/italic-lower/VeryPeriSerifItalicI*.ttf'))[-1]
    font=TTFont(path);new=build_glyphs(font)
    extra=copy.deepcopy(font)
    for tag in ('GSUB','GPOS','GDEF'):
        if tag in extra:del extra[tag]
    addOpenTypeFeaturesFromString(extra,FEA)
    # the feature-name strings land in extra's name table: copy them over
    for r in extra['name'].names:
        if r.nameID>=256 and not any(q.nameID==r.nameID for q in font['name'].names):font['name'].names.append(r)
    merge_gsub(font,extra)
    gdef=font['GDEF'].table.GlyphClassDef.classDefs
    for n in new:gdef[n]=1
    font.save(path)
    # glyphs the kerning measures besides the cmap letters: (glyph, letter it stands for, native outline)
    kern_glyphs={'uni0442.srb':['т',False],'uni0442.ss03':['т',False],'eth':['д',True],'g':['д',True],'imacron':['г',True],'umacron':['п',True]}
    OUT.write_text(json.dumps({'note':'tools/italic_features.py','glyphs':new,'kern_glyphs':kern_glyphs,'features':['locl SRB','locl MKD','ss01','ss02','ss03']},ensure_ascii=False,indent=1)+'\n')
    print(path,new)


if __name__=='__main__':main()
