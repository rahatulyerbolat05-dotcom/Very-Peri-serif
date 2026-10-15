# Cyrillic serif corpus: curves and endings of д

This is read-only reference research, not a new glyph proposal. The source is pinned Google Fonts snapshot `67bc647ce1910e92f461bcc82aae30f21d21a9cc`. Source fonts and licenses are SHA-256 recorded in `sources.json`; actual cmap and HarfBuzz results are in `proof-shaping.json`, with all 1,060 tested configurations retained in `audit.json`.

## Scope and exclusions

The core corpus contains **12 families / 22 styles**: Prata, Oranienbaum, Brygada 1918, Vollkorn, Old Standard TT, PT Serif, Libertinus Serif, STIX Two Text, Source Serif 4, Noto Serif Display, Merriweather and Roboto Serif. Regular and Italic are both included where the family provides them. Kurale/PT Serif Caption downloads are recorded but their analysis is left to the parallel localized-corpus study. Neuton and Gelasio were checked and **excluded because these pinned font files do not map U+0434**. No fallback glyphs substitute for missing Cyrillic.

The drawings share one native em size; 2000-UPM Merriweather is normalized as a whole-font instance to the same em, not enlarged to match x-height. Native italic angles remain visible. Every variable source is instantiated at wght 400, with other axes at the stated defaults. Source name-table “Light”/“20pt” labels are kept separately from these actual instance coordinates.

## Actual diversity

A list of 12 families does **not** reveal 12 different Cyrillic skeletons. Most Russian italic defaults have an upper-return (delta-like) construction. Native Bulgarian/Serbian localization often exposes a lower-loop form. Verified localized alternatives include Vollkorn BGR; STIX Two Text Italic SRB; Source Serif 4 BGR; Noto Serif Display Italic SRB; Merriweather BGR; Roboto Serif Regular BGR. Their exact actual glyph names and language/feature settings are in the JSON. aalt sometimes exposes small caps; those are documented, not presented as lowercase alternatives. No ss/cv result is claimed merely because a similarly named glyph exists.

For the current user objection, **the upper-return skeleton is not ruled out**. The useful comparative evidence is how differently these fonts finish and accelerate the same basic motion.

## Three materially different terminal constructions

`terminal-case-studies.svg` shows the genuine complete д next to a common-scale upper-return crop. `terminal-case-studies.json` includes source/license SHA, exact contour commands, endpoints, tangent directions and angle methods.

| Source, native Italic | Actual final boundary | Length / 1000 UPM | Direction from +x in source contour order | Observation |
| --- | --- | --- | --- | --- |
| Old Standard TT | (217,608) → (191,618) | 27.86 | 158.96° | A directional flat cut on a thin return; the arch gains weight toward the right. |
| PT Serif | (160,676) → (147,695) | 23.02 | 124.38° | A directional flat cut with a visibly wedge-shaped widening into the arch. |
| Libertinus Serif | (195,703) → (196,703) | 1.00 | 0° | A pointed pen-like tip that opens into a broad leaf; no rounded cap. The tiny segment is real native data, not proof of an artifact. |

The two flat-cut examples have deliberate corners at the cut. Old Standard turns approximately −86.50° into the cut and −94.97° out of it; PT Serif approximately −83.17° and −76.89°. Forcing those endpoints into a globally smooth rounded closure would change the terminal design. Libertinus has a continuous tangent into the tiny tip segment and a −30.26° contour turn after it, again a deliberate pointed construction.

The old-standard outer/inner crown extrema are (346,720)/(342,696), a **vertical extremum gap** of 24. PT Serif uses (307,754)/(267,702), a vertical gap of 52. These extrema are at different x positions: **neither number is a measurement of normal stroke thickness**. None of the cut lengths, angles, or gaps is a universal target for Instrument Serif.

## What this helps verify in Instrument

1. A curved stroke needs a designed width evolution. A broad outer arc and tighter inner return can create a pen-like widening; parallel offset contours plus a round end produce a different effect even when the centerline matches.
2. A terminal is an independent design event: flat directional cut, pointed leaf, hooked taper or localized ink swelling. It must be compared with Instrument's native terminals before selecting its outline. It must not default to a circular cap because the letter is handwritten in skeleton.
3. Separate genuine smooth curve junctions from intended endpoint corners. Check tangent direction/curvature continuity at smooth joins, while retaining native-style cuts and cusps where their design role is clear.
4. The return and the bowl must be read together. The proof pairs each д with its own б, g and o. A donor o used unchanged is not sufficient evidence of integration if its upper-right shoulder meets the new return with the wrong tension or ink distribution.
5. Judge the upright result against Instrument Regular native bowls/stems/terminals at text sizes. Foreign Italic slope, em dimensions, terminal angles and donor outlines remain reference observations, not transfer instructions.

The corpus does not approve a particular next д. Optical suitability and the user's acceptance remain open.
