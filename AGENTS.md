# Working on Very Peri Serif

Read CLAUDE.md, docs/decisions.md and data/progress.json before drawing.
Explicit user decisions take priority over historical construction recipes.
Keep Instrument Serif Regular geometry and the approved glyph hashes intact.
Project inventory includes both branches. Consult data/cross-branch-inventory.json:
Claude's selected ш/ь/ы/ъ sketches are not yet in the Codex font exports.
Do not equate current font cmap coverage with all completed source studies.

Lowercase designs use Cyrillic handwritten/cursive skeletons in upright
Regular. Preserve Instrument Serif Regular stress, contrast, terminals and
curve character; the separate Italic style is still postponed. Do not enforce
historical bans on cursive skeletons or assume all curves must be smooth.

The primary и is exact native u; ss07 retains its diagonal alternative.
The user selected de-reimagined01 «Острый свод» as the main д. Pin its
accepted contour and metrics through data/selected-de.json. Do not redraw it
while adding letters. De-reimagined02 is retained separately as an alternative.
Historical native-g, printed pedestal and de-cursive drawings remain retained
but rejected. The user selected т02 «Письменный выход» as primary and
т01 «Родные арки» as the alternative style. Pin both through
data/selected-te.json. Both к and й variants remain unselected.
Do not infer approval from a technical default. Technical G1 checks do not
establish stylistic success. Present actual drawings with native neighbours.

Use the portable tools and requirements-fonts.txt described in README.md.
Build outputs belong in ignored build/; do not run archived/uploaded scripts.
Do not introduce global smoothing, contour compression or accidental metric
drift. Compare exported glyphs with genuine original Latin neighbours.

Before changing retained artifacts, update the manifest and run
tools/verify_studies.py with the pinned original source. Report unrun
FontBakery/Hyperglot checks and unfinished Cyrillic kerning honestly.
Never remove earlier studies merely because a new candidate is produced.
Do not commit original reference binaries, PNG, uploaded archives or Python
dependency caches. SVG proofs and derivative study fonts are tracked.
