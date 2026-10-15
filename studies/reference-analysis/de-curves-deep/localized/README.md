# Native upright/display/localized Cyrillic д: curve and terminal controls

This is a read-only morphological corpus, not new candidate drawings. The user clarified that the failed latest proposals have unsatisfactory **curves and endings**, not that their ascender/∂ skeleton must be abandoned. None of these outlines has been copied into the project or artificially made upright.

## Reproducible corpus

- Google Fonts exact snapshot: `67bc647ce1910e92f461bcc82aae30f21d21a9cc`.
- `reference-sources.json`: immutable font, metadata and OFL URLs and SHA256; native axes and genuine HarfBuzz exposures; explicit negative findings.
- 29 family paths attempted, 28 downloaded; 27 include U+0434. Cormorant Upright Regular contains no Cyrillic д. The pinned `playwriteru` path does not exist and was excluded.
- Each supporting font was shaped with `ru`, `bg`, `sr`, `mk`, then with each actually available `ssXX`/`cvXX` feature. Glyph names were never used as evidence that a localization is exposed.
- 36 per-family exposed outline records, 32 globally different recording hashes. This is **not** a claim of 32 different skeletons: many are printed controls, minor variations, or duplicate g forms.
- `full-survey-1.svg` through `full-survey-4.svg`: all 36 native outline records with actual д, native Latin g, native Cyrillic б and shaped `доди`. PNG siblings are local viewing aids.
- `proof-shaping.json`: glyph IDs, names, clusters, advances and offsets for every displayed run, including contexts.
- `terminal-controls.svg`: ten selected detail controls, with only two script families (Caveat, Marck Script). `terminal-controls-shaping.json` records exact shape settings. Printed forms on this sheet are explicitly rejected controls, never recommendations to return to platform-and-feet д.
- Family folders contain the actual single-glyph SVGs. Binaries remain scratch references, not deliverable font sources.

## Useful observations after looking at the native vectors

1. **Caveat Regular, U+0434**, and its `ss01`/`ss02` forms are genuine upright-font upper-return/∂ constructions. The top return and its entrance into the bowl are one motion; neither is a separate round plug. Their terminal boundary is directional and asymmetrical. This is useful as ductus only: informal monoline brush texture and slant of individual strokes do not belong in Instrument Serif. It does not prescribe the width or curvature of our terminal.
2. **Viaoda Libre Regular, `bg` → `uni0434.loclBGR`**, is genuinely exposed, high contrast, and distinct from its Latin two-storey g. Its lower return runs from a strong right stroke into a very thin bottom sweep, then an inward terminal swelling. The terminal is structurally supported by the return's changing thickness. This is useful for taper/terminal logic; its g-like lower-descender silhouette is not proposed for our d.
3. **Cormorant Garamond Regular, `bg` or `ru+ss10` → `uni0434.ss10`**, shows a different open lower return. A modest asymmetric terminal swelling follows a thin undercurve; the end is not a constant-width tube. It is another terminal/contrast control, not an instruction to turn our d into g.
4. **Commissioner Regular, `bg` → `uni0434.loclBGR`**, is also truly exposed. Its substantially uniform stroke and flat end provide a useful negative control: even a coherent open return looks mechanical when its width changes too little. The low-contrast sans grammar does not solve Instrument Serif endings.
5. **Marck Script Regular** has a lower loop whose apparent weight comes from the loop's direction and crossing. It demonstrates why mechanically attaching a loop or ball to a bowl loses the causal stroke motion. This is a second and final script-family ductus control, not a style target.
6. **Native б alongside each д** is a practical upper-terminal comparison. Kurale, Gabriela, Yeseva One and Viaoda Libre differ in the way the top terminal grows, points, and returns. Their family-specific endings cannot be replaced with one universal circular cap. Their printed д remains excluded from our morphology.
7. **El Messiri versus Philosopher** is an instructive detail check: same д bounds `(16,-155,546,470)`, advance 570, and almost the same skeleton, but the inner foot curves differ. Philosopher uses two quadratic sections on each inside return; El Messiri uses three, altering how the bend tightens near baseline. Therefore matching bounds and even almost the whole outline does not establish equivalent curve quality. They are not independent skeleton precedents.

## Negative and contextual checks

- Cormorant Infant Regular default д, Poiret One's Bulgarian д, Pacifico's nominal д and Comforter д have the **exact same nominal outline as Latin g in the same font**. These are legitimate typefaces, but they do not answer this user's already stated objection to our own native-g transfer.
- In Pacifico the shaped standalone Latin `g` becomes `g.fina`; nominal-outline identity must not be confused with identity of a shaped context.
- Fira Sans Regular in this exact source did not switch д for Bulgarian or for any tested stylistic/character-variant set. It is excluded as a purported Bulgarian d example.
- Bellota and Bellota Text default д are exact outline duplicates, not two independent precedents.
- Caveat contextual alternates change the second д in `доди` even in the default run; `ss02` does not force every contextual д to the nominal ss02 drawing. Lobster likewise uses `uni0434.end` in isolation but `uni0434` inside `доди`. The recorded shaped IDs, not a selected nominal glyph, describe the proof.

## Consequence for our next work

Keep the user's handwritten upright skeleton as a viable direction. Before another glyph presentation, settle a continuous thickness progression and directional terminal treatment using **native Instrument Serif** anatomy. A smooth exported tangent does not prove the bend is designed well. No other typeface's numerical radii, terminal shapes, or control points should be transplanted. The useful transferable information here is how a return changes weight and how the final shape expresses that motion.

No recommendation in this corpus asks for a change to Italic, automatic smoothing, a generic round cap, or printed d feet. No primary д was selected.
