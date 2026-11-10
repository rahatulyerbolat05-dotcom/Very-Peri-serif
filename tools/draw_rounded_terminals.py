#!/usr/bin/env python3
"""Local p-derived crowns for authored Cyrillic Italic stems; 1.115 is immutable."""
import hashlib, io, json, subprocess
from pathlib import Path
from types import SimpleNamespace
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPointPen
from fontTools.ufoLib.glifLib import writeGlyphToString

BASELINE = '0330c598b690e4e9ddc6aec53a57218bba476035'
OUT = Path('data/italic-rounded-terminals')
# Native Latin u/и is deliberately not an authored glyph. м is redesigned in
# two separate sources. ч has an entry flag, handled separately below.
NAMES = ['uni043D','uni0439','uni0446','uni044B','uni0448','uni0449',
         'uni04A3','uni04AF','uni04B1','uni0436','uni0447']

def frozen():
    return TTFont(io.BytesIO(subprocess.check_output(['git','show',BASELINE+':fonts/ttf/VeryPeriSerif-Italic.ttf'])))

def contours(glyph, glyf):
    co, ends, flags = glyph.getCoordinates(glyf); rows=[]; start=0
    for end in ends:
        rows.append([(int(x),int(y),bool(flags[i]&1)) for i,(x,y) in enumerate(co[start:end+1],start)])
        start=end+1
    return rows

def glyph_from(rows):
    p=TTGlyphPointPen(None)
    for row in rows:
        p.beginPath()
        for i,(x,y,on) in enumerate(row):
            kind = ('line' if row[i-1][2] else 'qcurve') if on else None
            p.addPoint((x,y),segmentType=kind)
        p.endPath()
    return p.glyph()

def revise(row, name):
    repairs=[]
    # Reverse-order traversal is the winding of the authored crowns.
    caps=[i for i,p in enumerate(row[:-1]) if p[2] and row[i+1][2]
          and p[1]==row[i+1][1]==510 and p[0]-row[i+1][0]==40]
    for i in reversed(caps):
        R,L=row[i][0],row[i+1][0]
        # Last two old points on the incoming shoulder: start at stable body,
        # retain all earlier geometry. For н/ң/ы this includes one local
        # control (the previously faired stem edge), for u-derived legs a line.
        j=i-1
        while not row[j][2]: j-=1
        start=j
        if row[j][1]>=497:
            j-=1
            while not row[j][2]: j-=1
            start=j
        assert row[start][1]<497,(name,row[start])
        k=i+2
        while not row[k][2] and row[k][1]>480: k+=1
        # Off-curve at 460 is a stable body control, not a terminal point.
        stable=row[k]
        n_like=stable[2] and stable[1]==480
        left_end=L-16 if n_like else L-15
        left_control=left_end+5
        left_top=left_control+21
        crown=[(R+7,483,True),(R+10,496,False),(R-2,510,False),
               (R-14,510,True),(left_top,510,True),(left_control,510,False),
               (left_end,489,True)]
        old=row[start+1:k]
        row[start+1:k]=crown
        repairs.append({'old_points':old,'new_points':crown,'start':row[start],
                        'stable_after':stable,'flat_before':40,'flat_after':R-14-left_top,
                        'right_rounding_depth':27,'left_rounding_depth':21})
    if name=='uni0436':
        # The naked ж stem had two literal polygon corners. Derive its two
        # shoulders from p, keeping its real straight-body slopes and weight.
        i=row.index((449,510,True)); assert row[i+1]==(385,510,True)
        crown=[(443,483,True),(446,496,False),(434,510,False),(422,510,True),
               (406,510,True),(385,510,False),(380,489,True)]
        old=row[i:i+2];row[i:i+2]=crown
        repairs.append({'old_points':old,'new_points':crown,'flat_before':64,
                        'flat_after':16,'right_rounding_depth':27,'left_rounding_depth':21})
    if name=='uni0447':
        # Keep the entire accepted entry flag and bowl. Only the right-hand
        # shoulder changes; copying both p shoulders would destroy that flag.
        i=row.index((428,462,True)); j=row.index((336,510,True))
        assert j>i
        crown=[(433,483,True),(436,496,False),(424,510,False),(412,510,True)]
        old=row[i+1:j];row[i+1:j]=crown
        repairs.append({'old_points':old,'new_points':crown,'right_rounding_depth':27,
                        'entry_flag':'retained exactly'})
    assert repairs,name
    return row,repairs

def main():
    OUT.mkdir(parents=True,exist_ok=True); f=frozen(); records={}
    for name in NAMES:
        rows=contours(f['glyf'][name],f['glyf']); changes=[]
        for i,row in enumerate(rows):
            if any(p[1]==510 for p in row):
                try: rows[i],rs=revise(row,name)
                except AssertionError:
                    if len(rows)==1: raise
                else: changes.extend(rs)
        assert changes,name
        g=glyph_from(rows);g.recalcBounds(f['glyf'])
        old=f['glyf'][name]
        assert (g.xMin,g.yMin,g.yMax)==(old.xMin,old.yMin,old.yMax) and g.xMax<=old.xMax,name
        width=f['hmtx'][name][0]
        raw=writeGlyphToString(name,SimpleNamespace(width=width),lambda pen: g.drawPoints(pen,f['glyf']),formatVersion=2).encode()
        path=OUT/(name+'.glif');path.write_bytes(raw+b'\n')
        records[name]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                       'advance_and_lsb':list(f['hmtx'][name]),
                       'bounds':[g.xMin,g.yMin,g.xMax,g.yMax],'repairs':changes}
    manifest={'baseline_commit':BASELINE,'baseline_version':'1.115','donor':'native Latin p',
              'donor_cap_points':[(147,562),(152,583),(173,583),(191,583),(203,583),(215,569),(212,556)],
              'method':'Native p shoulder geometry, adapted to each existing stem. All other points retained.',
              'glyphs':records}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Saved',len(records),'authored Cyrillic glyph masters')

if __name__=='__main__': main()
