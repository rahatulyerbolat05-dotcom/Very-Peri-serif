# Working on Very Peri Serif

Read CLAUDE.md, docs/decisions.md and data/progress.json before drawing.
Explicit user decisions take priority over historical construction recipes.
Keep Instrument Serif Regular geometry and the approved glyph hashes intact.

The primary и is the native u-shaped Regular form; ss07 is its diagonal
alternative. The user requested redesign of д; old versions and the new
native-g studies remain retained, with no new primary approved. Both к and
й variants remain unselected. Do not infer approval from a technical default.

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
