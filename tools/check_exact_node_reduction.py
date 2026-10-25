#!/usr/bin/env python3
"""Positive and near-miss fixtures for lossless node reduction."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fontTools.fontBuilder import FontBuilder
from fontTools.ttLib.tables._g_l_y_f import Glyph,GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from exact_node_reduction import reduce_points,reduce_glyph,canonical_outline,parent_control
from fractions import Fraction
from curve_finish import check_input_metrics


def font(points):
    g=Glyph();g.numberOfContours=1;g.coordinates=GlyphCoordinates([(x,y) for x,y,on in points]);g.flags=bytearray([int(on) for x,y,on in points]);g.endPtsOfContours=[len(points)-1]
    b=FontBuilder(1000,isTTF=True);b.setupGlyphOrder(['a']);b.setupGlyf({'a':g});b.setupHorizontalMetrics({'a':(500,0)})
    return b.font


class ReductionTests(unittest.TestCase):
    def verify(self,points,expected):
        for reverse in (False,True):
            p=list(reversed(points)) if reverse else points
            for i in range(len(p)):
                shifted=p[i:]+p[:i];f=font(shifted);old=canonical_outline(f,'a')
                result,stats=reduce_points(shifted)
                self.assertEqual(len(shifted)-len(result),expected)
                other=font(result);self.assertEqual(old,canonical_outline(other,'a'))
    def test_implicit_midpoint(self):
        self.verify([(0,0,1),(40,100,0),(80,100,1),(120,100,0),(160,0,1)],1)
    def test_collinear_line(self):
        self.verify([(0,0,1),(50,0,1),(100,0,1),(100,100,1),(0,100,1)],1)
    def test_straight_controls(self):
        self.verify([(0,0,1),(30,0,0),(80,0,0),(100,0,1),(100,100,1),(0,100,1)],2)
    def test_inverse_split(self):
        self.assertEqual(parent_control((0,0),(25,50),(50,50),(75,50),(100,0)),(50,100))
        self.assertIsNone(parent_control((0,0),(25,50),(50,51),(75,50),(100,0)))
        scale=Fraction(1,3)
        self.assertEqual(parent_control(*[tuple(scale*x for x in p) for p in ((0,0),(25,50),(50,50),(75,50),(100,0))]),(Fraction(50,3),Fraction(100,3)))
    def test_exact_split_reduction(self):
        self.verify([(0,0,1),(25,50,0),(50,50,1),(75,50,0),(100,0,1),(200,100,1),(-100,100,1)],2)
    def test_control_bounds_preserved(self):
        # Merging the parabola would move its control box from y=50 to y=100.
        self.verify([(0,0,1),(25,50,0),(50,50,1),(75,50,0),(100,0,1),(100,-20,1),(0,-20,1)],1)
    def test_near_collinear_preserved(self):
        self.verify([(0,0,1),(50,1,1),(100,0,1),(100,100,1),(0,100,1)],0)
    def test_half_unit_implied_points(self):
        self.verify([(0,0,1),(40,101,0),(81,100,0),(120,0,1),(120,-10,1)],0)
    def test_hint_program_protected(self):
        f=font([(0,0,1),(50,0,1),(100,0,1),(100,100,1),(0,100,1)]);g=f['glyf']['a'];g.program=Program();g.program.fromBytecode([0])
        new,stats=reduce_glyph(g,f['glyf']);self.assertIs(new,g);self.assertEqual(stats,{})
    def test_point_flags_protected(self):
        f=font([(0,0,1),(50,0,1),(100,0,1),(100,100,1),(0,100,1)]);g=f['glyf']['a'];g.flags[0]|=0x40
        new,stats=reduce_glyph(g,f['glyf']);self.assertIs(new,g);self.assertEqual(stats,{})
    def test_only_declared_provisional_metrics(self):
        r={'advance_and_lsb':[519,-60],'additional_input_advance_and_lsb':[[519,-59]]}
        self.assertTrue(check_input_metrics((519,-60),r))
        self.assertTrue(check_input_metrics((519,-59),r))
        self.assertFalse(check_input_metrics((520,-59),r))
        self.assertFalse(check_input_metrics((519,-58),r))
        del r['additional_input_advance_and_lsb']
        self.assertFalse(check_input_metrics((519,-59),r))


if __name__=='__main__':unittest.main()
