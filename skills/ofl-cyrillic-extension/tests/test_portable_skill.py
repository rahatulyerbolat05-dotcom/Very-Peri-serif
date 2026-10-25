"""Portable synthetic controls; no repository history, font downloads or Very Peri imports."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont,newTable
from fontTools.ttLib.tables._g_l_y_f import Glyph,GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables import otTables
from exact_nodes import reduce_points,reduce_glyph,canonical_outline,parent_control
from outline_geometry import Segment,read_outline,inspect_contour
from font_probe import probe,horizontal_runs
from compare_native import compare
from reduce_nodes import reduce,point_reference_blockers,protected_component_bases
from audit_outlines import audit
from install_skill import install,files


def points_glyph(points):
    g=Glyph();g.numberOfContours=1;g.coordinates=GlyphCoordinates([(x,y) for x,y,on in points]);g.flags=bytearray(int(on) for x,y,on in points);g.endPtsOfContours=[len(points)-1];g.program=Program();g.program.fromBytecode([])
    return g


def fixture(path,upm=1000):
    simple=points_glyph([(0,0,1),(50,0,1),(100,0,1),(100,100,1),(0,100,1)])
    glyphs={'.notdef':Glyph(),'space':Glyph(),'H':copy.deepcopy(simple),'n':copy.deepcopy(simple),'o':copy.deepcopy(simple),'simple':simple}
    builder=FontBuilder(upm,isTTF=True);builder.setupGlyphOrder(list(glyphs));builder.setupCharacterMap({32:'space',72:'H',110:'n',111:'o',0x436:'simple'})
    builder.setupGlyf(glyphs);builder.setupHorizontalMetrics({n:(200,0) for n in glyphs});builder.setupHorizontalHeader(ascent=800,descent=-200)
    builder.setupNameTable({'familyName':'Synthetic Test Only','styleName':'Regular','uniqueFontIdentifier':'portable-test','fullName':'Synthetic Test Only Regular','psName':'SyntheticTestOnly-Regular','version':'Version 1.000'})
    builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200,sxHeight=100,sCapHeight=100)
    builder.setupPost();builder.setupMaxp();builder.font.recalcTimestamp=False;builder.save(path);return path


class ExactTests(unittest.TestCase):
    def verify(self,points,expected):
        for upm in (960,1000,2048):
            for reverse in (False,True):
                p=list(reversed(points)) if reverse else points
                for i in range(len(p)):
                    shifted=p[i:]+p[:i];b=FontBuilder(upm,isTTF=True);b.setupGlyphOrder(['a']);b.setupGlyf({'a':points_glyph(shifted)});b.setupHorizontalMetrics({'a':(500,0)})
                    f=b.font;original=canonical_outline(f,'a');result,_=reduce_points(shifted)
                    self.assertEqual(len(shifted)-len(result),expected)
                    f['glyf']['a']=points_glyph(result);f['glyf']['a'].recalcBounds(f['glyf']);self.assertEqual(original,canonical_outline(f,'a'))
    def test_implicit_midpoint(self):self.verify([(0,0,1),(40,100,0),(80,100,1),(120,100,0),(160,0,1)],1)
    def test_line(self):self.verify([(0,0,1),(50,0,1),(100,0,1),(100,100,1),(0,100,1)],1)
    def test_straight_controls(self):self.verify([(0,0,1),(30,0,0),(80,0,0),(100,0,1),(100,100,1),(0,100,1)],2)
    def test_split_inverse_and_near_miss(self):
        self.assertEqual(parent_control((0,0),(25,50),(50,50),(75,50),(100,0)),(50,100))
        self.assertIsNone(parent_control((0,0),(25,50),(50,51),(75,50),(100,0)))
        self.assertEqual(parent_control(*[tuple(Fraction(x,3) for x in p) for p in ((0,0),(25,50),(50,50),(75,50),(100,0))]),(Fraction(50,3),Fraction(100,3)))
    def test_split_reduction(self):self.verify([(0,0,1),(25,50,0),(50,50,1),(75,50,0),(100,0,1),(200,100,1),(-100,100,1)],2)
    def test_bbox_guard(self):self.verify([(0,0,1),(25,50,0),(50,50,1),(75,50,0),(100,0,1),(100,-20,1),(0,-20,1)],1)
    def test_near_straight_preserved(self):self.verify([(0,0,1),(50,1,1),(100,0,1),(100,100,1),(0,100,1)],0)
    def test_half_units_preserved(self):self.verify([(0,0,1),(40,101,0),(81,100,0),(120,0,1),(120,-10,1)],0)
    def test_hints_and_flags_protected(self):
        for flagged in (False,True):
            b=FontBuilder(1000,isTTF=True);b.setupGlyphOrder(['a']);g=points_glyph([(0,0,1),(50,0,1),(100,0,1),(100,100,1),(0,100,1)]);b.setupGlyf({'a':g})
            if flagged:g.flags[0]|=0x40
            else:g.program=Program();g.program.fromBytecode([0])
            result,stats=reduce_glyph(g,b.font['glyf']);self.assertIs(result,g);self.assertFalse(stats)
    def test_all_offcurve_and_component(self):
        b=FontBuilder(960,isTTF=True);g=points_glyph([(0,100,0),(100,100,0),(100,0,0),(0,0,0)])
        pen=TTGlyphPen({'base':g});pen.addComponent('base',(1,0,0,1,30,40))
        b.setupGlyphOrder(['base','component']);b.setupGlyf({'base':g,'component':pen.glyph()});b.setupHorizontalMetrics({'base':(200,0),'component':(200,30)})
        self.assertEqual(len(canonical_outline(b.font,'base')[0][1]),4)
        contours,closed=read_outline(b.font,'component');self.assertEqual(closed,[True]);self.assertEqual(len(contours[0]),4)


class GeometryTests(unittest.TestCase):
    def test_known_hard_corner_is_candidate(self):
        findings,_=inspect_contour([Segment([(0,0),(100,0)]),Segment([(100,0),(100,100)])],False)
        self.assertTrue(any(r['kind']=='tangent_break' for r in findings))
    def test_clean_line(self):
        findings,_=inspect_contour([Segment([(0,0),(100,0)]),Segment([(100,0),(200,0)])],False)
        self.assertEqual([r['kind'] for r in findings],['open_contour'])
    def test_topology_positive_control(self):
        pts=[(0,0),(100,100),(0,100),(100,0),(0,0)]
        findings,_=inspect_contour([Segment([a,b]) for a,b in zip(pts,pts[1:])],True)
        self.assertTrue(any(r['kind']=='self_intersection' for r in findings))
    def test_degenerate_curve_is_not_smooth(self):
        findings,_=inspect_contour([Segment([(0,0),(0,0),(0,0)])],False)
        self.assertTrue(any(r['kind'] in ('zero_segment','undefined_tangent','singular_endpoint') for r in findings))
    def test_known_transverse_step_and_whole_arc(self):
        bad=[Segment([(168,287),(165,292),(162,300)]),Segment([(162,300),(152,301)]),Segment([(152,301),(160,340)])]
        good=[Segment([(212,267),(142,267),(160,340)]),Segment([(160,340),(177,411)])]
        self.assertTrue(any(r['kind']=='transverse_step' for r in inspect_contour(bad,False)[0]))
        self.assertFalse(any(r['kind']=='transverse_step' for r in inspect_contour(good,False)[0]))
    def test_intentional_serif_corner_not_a_step(self):
        cs=[Segment([(0,0),(30,0)]),Segment([(30,0),(30,10)]),Segment([(30,10),(0,10)])]
        self.assertFalse(any(r['kind']=='transverse_step' for r in inspect_contour(cs,False)[0]))
    def test_nonzero_scanline(self):
        outer=[(0,0),(100,0),(100,100),(0,100),(0,0)]
        inner=[(25,25),(25,75),(75,75),(75,25),(25,25)]
        cs=[[Segment([a,b]) for a,b in zip(p,p[1:])] for p in (outer,inner)]
        self.assertEqual(horizontal_runs(cs,50),[[0.,25.],[75.,100.]])


class ToolTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.font=fixture(self.root/'source.ttf')
    def tearDown(self):self.temp.cleanup()
    def test_probe_snapshot_and_refuse_mixed_inputs(self):
        out=self.root/'intake';result=probe(self.font,out)
        data=json.loads((out/'font-profile.json').read_text());self.assertEqual(result['glyphs'],6);self.assertEqual(data['license']['status'],'unverified')
        self.assertTrue((out/'native-controls.svg').read_text().startswith('<svg'))
        self.assertEqual(Path(data['snapshot']).read_bytes(),self.font.read_bytes());probe(self.font,out)
        other=TTFont(self.font);other['hmtx']['H']=(201,0);other.save(self.root/'other.ttf')
        with self.assertRaises(ValueError):probe(self.root/'other.ttf',out)
    def test_native_positive_and_negative(self):
        self.assertEqual(compare(self.font,self.font,self.root/'native.json')['failed'],0)
        changed=TTFont(self.font);changed['glyf']['H'].coordinates[1]=(51,2);changed.save(self.root/'changed.ttf')
        self.assertGreater(compare(self.font,self.root/'changed.ttf',self.root/'negative.json')['failed'],0)
    def test_global_hint_change_detected(self):
        changed=TTFont(self.font);table=newTable('prep');table.program=Program();table.program.fromBytecode([0]);changed['prep']=table;changed.save(self.root/'global-hints.ttf')
        report=compare(self.font,self.root/'global-hints.ttf',self.root/'global-hints.json')
        self.assertTrue(any('global TrueType hint table prep' in error for error in report['errors']))
    def test_apply_serialized_and_source_immutable(self):
        before=self.font.read_bytes();report=reduce(self.font,['simple'],self.root/'dry.json');self.assertEqual(report['points_removed'],1)
        dest=self.root/'reduced.ttf';result=reduce(self.font,['simple'],self.root/'apply.json',dest)
        self.assertEqual(result['points_removed'],1);self.assertEqual(self.font.read_bytes(),before)
        self.assertEqual(TTFont(dest)['hmtx'].metrics,TTFont(self.font)['hmtx'].metrics)
        with self.assertRaises(ValueError):reduce(self.font,['simple'],self.root/'duplicate.json',dest)
    def test_index_references_block(self):
        f=TTFont(self.font);anchor=otTables.Anchor();anchor.Format=2;anchor.XCoordinate=0;anchor.YCoordinate=0;anchor.AnchorPoint=1
        table=newTable('GPOS');table.table=SimpleNamespace(anchor=anchor);f['GPOS']=table
        self.assertTrue(any('GPOS' in x for x in point_reference_blockers(f)))
        del f['GPOS'];table=newTable('GDEF');table.table=SimpleNamespace(AttachList=object(),LigCaretList=None);f['GDEF']=table
        self.assertTrue(any('GDEF' in x for x in point_reference_blockers(f)))
    def test_hinted_composite_protects_base(self):
        f=TTFont(self.font);pen=TTGlyphPen(f.getGlyphSet());pen.addComponent('simple',(1,0,0,1,0,0));g=pen.glyph();g.program=Program();g.program.fromBytecode([0])
        f['glyf']['component']=g;f.setGlyphOrder(f.getGlyphOrder()+['component']);f['hmtx']['component']=(200,0)
        self.assertIn('simple',protected_component_bases(f))
    def test_audit_not_silent_optical_acceptance(self):
        report=audit(self.font,self.root/'audit.json');self.assertFalse(report['errors']);self.assertEqual(report['summary']['parsed_glyphs'],6)
        self.assertGreater(report['summary']['unreviewed_whole_forms'],0);self.assertNotEqual(report['status'],'ledger_review_complete')
        stale={'forms':{row['review_key']:{'status':'reviewed','font_sha256':'wrong','geometry_sha256':row['geometry_sha256'],'detector_sha256':report['detector_sha256'],'reason':'test','proofs':['proof.svg']} for row in report['glyphs']}}
        again=audit(self.font,self.root/'stale.json',stale);self.assertEqual(again['summary']['unreviewed_whole_forms'],report['summary']['unreviewed_whole_forms'])
    def test_current_reasoned_ledger_can_close_fixture(self):
        report=audit(self.font,self.root/'ledger-before.json')
        def decision(shape,status):return {'status':status,'font_sha256':report['font_sha256'],'geometry_sha256':shape,'detector_sha256':report['detector_sha256'],'reason':'Intentional rectangle corner in synthetic control','proofs':['fixture-definition']}
        ledger={'forms':{r['review_key']:decision(r['geometry_sha256'],'reviewed') for r in report['glyphs']},'cases':{r['id']:decision(r['geometry_sha256'],'intentional') for r in report['cases']}}
        accepted=audit(self.font,self.root/'ledger-after.json',ledger)
        self.assertEqual(accepted['status'],'ledger_review_complete')
    def test_variable_point_data_refused(self):
        f=TTFont(self.font);f['gvar']=newTable('gvar')
        self.assertTrue(any('variable data' in reason for reason in point_reference_blockers(f)))
    def test_install_idempotence_and_backup(self):
        dest=self.root/'project';result=install(dest);self.assertTrue(all(r['status']=='installed' for r in result))
        self.assertTrue(all(r['status']=='already_current' for r in install(dest)))
        p=dest/'.agents/skills/ofl-cyrillic-extension/SKILL.md';p.write_text('local changes')
        with self.assertRaises(ValueError):install(dest)
        result=install(dest,replace=True);backup=Path(result[0]['backup']);self.assertEqual((backup/'SKILL.md').read_text(),'local changes')
        self.assertEqual(files(dest/'.agents/skills/ofl-cyrillic-extension'),files(ROOT))


if __name__=='__main__':unittest.main()
