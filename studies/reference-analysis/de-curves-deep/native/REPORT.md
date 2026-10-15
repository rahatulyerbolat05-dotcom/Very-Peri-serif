# Instrument Serif Regular — native curve and terminal grammar for the next д

This is an anatomy study, not a replacement Cyrillic drawing. No project outline,
source font, selected glyph, spacing or feature was edited.

## Source and repeatability

- Original: [Instrument/instrument-serif](https://github.com/Instrument/instrument-serif),
  commit `65c0ef225f386a3c7e87570a4aa9cc0262c2fd81`.
- Exact cubic source: `sources/Instrument_Serif.glyphs`, master `m01` (Regular),
  UPM 1000, SHA-256 `e7dd989a8d17b7cdc13130b79597d44bdd4b9dd043c801639468ef38d58a706f`.
- Ten anatomy glyphs: a, d, u, t, f, g, r, c, e, o. A separate all-master
  cap-candidate scan checks whether claims inferred from these ten are too broad.
- `native-curve-facts.json` contains all cubic points and source command indices,
  tangent angles, signed curvature, exact reuse matches and width-ray intersections.
- Curvature is `det(B′,B″)/|B′|³`; radius is `abs(1/curvature)`. Units are font
  units. Cubic t is **not** normalized arclength. Listed samples are not assertions
  about extrema. Floating-point root tolerances and exceptions are in the JSON.
- Widths use cubic-polynomial intersections along the contour normal, not pixels
  or horizontal measurements. At complex junctions a ray may hit another branch;
  the hit segment and intersection point are recorded so this can be recognized.
- Reproduce from the repository with `tools/de_research/native_supplement.py`,
  then `tools/de_research/native_cap_scan.py`, using requirements-fonts.txt.
  These tested generators write only the ignored build/research-deep/native
  directory; retained source assets are not overwritten.

## The strongest observed native patterns

### 1. Several terminal families coexist; choosing the family comes before rounding

The original contains all of the following:

- Narrow rounded exit tips: a/d/t and lower c/e.
- Asymmetric bulbs with a concave return: f/r/g, and a's upper-left terminal.
- Flared flag-like endings with small rounded corners: u's lower right.
- A tall constrained upper spur: c's upper right; it is not a free circular ball.
- Flat structural portions and bracket curves, e.g. u's upper heads and d's
  ascender head. Their outlines are not interchangeable with a free ball tip.

Thus neither “all tips must be drops” nor “round caps are alien” is supported.
The closed top caps of rejected д01/02 are not disqualified merely because they
are rounded. Their angle, scale, the return into the arch and the continuation
of the stroke must be assessed together.

### 2. a and d really share a multi-segment exit; they are not just visually similar

After translation `(58, 0)`, native a commands 5–8 equal d commands 5–8 exactly,
including every control point. This includes both cap segments and the inner
return down into the stem. a command 4 and d command 4 are near matches with
one-unit difference at the starting point; they are not listed as exact reuse.

The a/d cap begins `(394,129)` / `(452,129)` and ends `(369,130)` / `(427,130)`.
It is made of two asymmetric cubic halves, not a pasted half-circle:

- Start-to-end chord: 25.020 units, slightly tilted.
- Maximum projected depth from that chord: about 16.518 units.
- At the cap summit the radius from both halves is 14.700 units.
- In the a exit's last stretch, outer-curve `t=.60,.75,.90` has local normal
  widths 38.106, 28.554, 25.479 units, each intersecting the actual inner-return
  segment 7. It progressively thins toward the cap; a constant-width bent line
  does not reproduce it. Earlier rays cross other letter regions, so their
  much larger values must not be described as this tail's stroke thickness.

The t cap is related but not an exact a/d clone: chord25.020, depth14.520,
cap-summit radius14.700. Its outer turn and inner return are different.

### 3. c/e lower terminals are similar asymmetric caps, not a universal cut angle

c command2 equals e command2 after translation `(12,-16)` exactly. Their next
segments differ slightly. The cap-summit radii are 12.000 incoming and 18.375
outgoing; both halves have the same tangent at the summit, but different curvature.
The c/e cap mouth lengths are22.847 and23.770 units. Their outer exits thin
continuously through the sampled stations: c49.402→25.203 and e49.339→25.444
for t=.15→.90 on command1.

c's upper spur cap is another shape: mouth26.077, projected depth14.067,
join radii18.375/10.800. A general rule giving every terminal the same radius
or the same finish would erase measured native differences.

### 4. f/r/g bulbs have a recurring concave-to-convex connector, not a circular bead

Native f19, r22 and g11 each contain one mathematical inflection in the same
kind of connector, at cubic t≈.490381, .481224 and .479130 respectively.
These are separately drawn source cubics, not exact cloned paths.

The f bulb's important joins are unusually controlled:

| Join | Radius arriving | Radius departing |
|---|---:|---:|
| Inner upper crown `(196,717)` | 43.740 | 44.118 |
| Bulb bottom `(277,632)` | 51.459 | 50.885 |
| Rightmost bulb point `(312,670)` | 66.964 | 67.646 |
| Outer upper crown `(218,748)` | 120.386 | 118.021 |

r has similar close curvature at its bulb bottom/right/crown joins, while g
has more local departures. This supports a **local model for a free upper
return**, not a universal G2 mandate for every native contour.

### 5. o is a separately shaped inside and outside, not a scaled/offset ellipse

Exact cubic extrema and thickness:

- Outside `(23,-9)..(383,516)`, inside `(99,16)..(307,491)`.
- x center203, side extremum y254, side thickness76, crown/bottom thickness25.
- Outer top horizontal handles101; bottom102. Outer side vertical handles147
  at the top and149 at the bottom. Inner handles70/71 and157/159 respectively.
- Along the upper-right outside quarter, normal widths at
  `t=0,.125,.25,.375,.5,.625,.75,.875,1` are
  `76,74.050,68.725,60.791,51.105,40.827,31.786,26.334,25`.
- Outer crown radius133.057; inner crown91.875. At the outer right side the
  incoming/outgoing radii426.942/410.297; inner right side1087.456/1149.136.

The upper/lower differences are real one-/two-unit source decisions. They must
not be “cleaned up” to make a geometric ellipse. Preserving the whole o counter
is exact reuse, but it does not prove a newly attached upper stroke belongs to
that counter. The transition and the black/white distribution remain new design.

## What the rejected д actually gets wrong, and what the numbers cannot prove

The user's clarification identifies **curves and endings**, rather than the
upper-ascender Cyrillic skeleton, as the principal failure. The measurements
support investigating the following local regions before changing skeleton again.

1. **The inner top of д02 has a hard curvature concentration hidden by G1.**
   At `(245,715)` its incoming radius135.482 becomes12.398, an instantaneous
   10.927× increase in curvature magnitude. The tangent mismatch is exactly0°.
   This creates a very tight start to the descending inner stroke after a much
   flatter approach. Native f's comparable free inner crown is43.740→44.118.
   д01 is less extreme but still79.350→28.711 at `(231,715)`.
2. **Both candidates reuse an artificial neck curve rather than native d's
   complete joining logic.** At `(266,495)` the radius22.361 becomes611.285,
   with no change in tangent direction or curvature sign: a27.3375× drop in
   curvature at one point. It is a tight concave fillet that suddenly opens out
   into an almost flat approach to the o crown. Native d has a related neck,
   but its comparable two radii41.926/127.379 differ by≈3.04× and change sign;
   it is not this reused generic fillet. Compare the original coordinates and
   surrounding white space, not just the fact that each has a neck.
3. **The round end is not numerically out of scale.** д01/02 cap mouths are
   24.759/25.456 units and projected depths13.823/15.556. Those overlap native
   narrow-cap magnitudes. The problem is the complete curve gesture and return,
   not a demonstrated wrong thickness. д01's cap-summit radii25.456/30.547 and
   д02's19.965/19.965 are less sharply curved at that join than a/d's14.700.
   This contributes to a different cap profile but does not prove rejection
   without viewing the whole terminal and its connector.
4. **A diagonal cap is not forbidden by the source.** An all-master geometric
   scan found a native three center terminal mouth angled−52.696°; comma has
   −43.152° and several marks also have angled caps. The rejected cap chord
   angles−46.637°/−45.000° are therefore not grounds for a categorical ban.

The native sample also has nonzero tangent mismatches (up to4.185° in these ten
letters) and substantial curvature jumps at local head/flag/bridge details.
These measurements do **not** establish intent for each mismatch, but do falsify
“every native join is exactly G1/G2” and “all radii should be continuously equal.”
Improving the rejected glyphs cannot mean globally smoothing their native parts.

## Proposed constraints for the next drawing — not discovered source laws

- Keep the handwritten construction under consideration (no upper-ascender drawing is approved); do not
  respond to a terminal failure by returning to a printed platform or Latin g.
- Before drawing the upper return, choose its function: thin free cap, bulbous
  head, or flared head. Name the native donor family and show it at equal UPM.
- Borrow a **complete gesture** (approach, cap/bulb, return) as the geometric
  reference. A source-colored endpoint pasted onto a generic arch is insufficient.
- Inspect the inner crown and the o-attachment as paired black/white contours.
  Compare their curvature comb and thickness through the entire transition.
- Keep exact native o geometry only where it supports the new gesture; a full
  untouched o counter is a useful starting constraint, not an approval criterion.
- Use a local source analogy to justify every newly tight/flat turn. No global
  radius or G2 threshold is proposed; native intentional local distinctions stay.
- Present the next contour against real native f/r/g upper anatomy and o/d body
  anatomy, alongside selected б/г. Export-integrity checks follow visual selection;
  “0° joins, no duplicate points” alone is not evidence of style.

## Artifacts

- `native-terminal-atlas.svg` / `.png`: ten exact original glyphs, relevant
  segments highlighted; five source detail magnifications.
- `native-detail-magnifications.svg` / `.png`: native exit caps, bulb connectors,
  and the u lower flag, with source controls and endpoint labels.
- `native-curve-facts.json`: detailed numeric evidence and rejected-outline
  comparison. Some whole-outline normal rays hit other branches: inspect recorded
  intersection segment before reusing a thickness value.
- `all-master-cap-candidates.json`: broad geometric falsification scan. Candidates
  are **not** automatically classified as meaningful terminal donors.

No FontBakery, Hyperglot or new font export is relevant to this source-only study;
none was run, and no final д design is approved by this report.
