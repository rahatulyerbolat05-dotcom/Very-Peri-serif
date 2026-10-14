#!/usr/bin/env python3
"""Rebuild native-outline Cyrillic de reference proofs from SHA-pinned sources.

The manifest contains the source/license URLs and records the actual language
and stylistic-set choices. Reference binaries are cached, never project fonts.
No glyph is slanted, made upright, or scaled independently for this proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_verified(path: Path, url: str, expected: str) -> None:
    if path.exists():
        if digest(path) != expected:
            raise ValueError(f"Cache checksum mismatch: {path}")
        return
    if not url.startswith("https://"):
        raise ValueError(f"Only HTTPS sources are accepted: {url}")
    with urlopen(url, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Downloaded checksum mismatch: {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            stream.write(data)
            temporary = Path(stream.name)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=project / "studies/reference-analysis/cursive-de/reference-sources.json")
    parser.add_argument("--cache-dir", type=Path, default=project / "build/references/cursive-de")
    parser.add_argument("--output-dir", type=Path, default=project / "build/reference-proofs/cursive-de")
    args = parser.parse_args()
    manifest = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = {row["family"]: row for row in manifest["sources"]}
    rows = manifest["proof_rows"]
    shown_families = sorted({row["family_key"] for row in rows})
    paths = {}
    downloads = []
    for key in shown_families:
        if not key.isalnum():
            raise ValueError(f"Unsafe family cache key: {key}")
        source = sources[key]
        filename = Path(source["analysis"]["file"]).name
        entry = next(item for item in source["font_files"] if item["file"] == filename)
        if Path(entry["file"]).name != entry["file"]:
            raise ValueError(f"Unsafe font filename: {entry['file']}")
        font_path = args.cache_dir / key / filename
        license_path = args.cache_dir / key / "OFL.txt"
        fetch_verified(font_path, entry["url"], entry["sha256"])
        fetch_verified(license_path, source["license_url"], source["license_sha256"])
        paths[key] = font_path
        downloads.append({"family": key, "font_sha256": digest(font_path), "ofl_sha256": digest(license_path)})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(args.output_dir / ".mpl-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.path import Path as PlotPath
    from matplotlib.patches import PathPatch
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.pens.basePen import BasePen
    from fontTools.pens.transformPen import TransformPen
    import uharfbuzz as hb

    class OutlinePen(BasePen):
        def __init__(self, glyph_set):
            super().__init__(glyph_set)
            self.vertices = []
            self.codes = []

        def _moveTo(self, point):
            self.vertices.append(point)
            self.codes.append(PlotPath.MOVETO)

        def _lineTo(self, point):
            self.vertices.append(point)
            self.codes.append(PlotPath.LINETO)

        def _curveToOne(self, point1, point2, point3):
            self.vertices.extend((point1, point2, point3))
            self.codes.extend((PlotPath.CURVE4,) * 3)

        def _qCurveToOne(self, point1, point2):
            self.vertices.extend((point1, point2))
            self.codes.extend((PlotPath.CURVE3,) * 2)

        def _closePath(self):
            self.vertices.append((0, 0))
            self.codes.append(PlotPath.CLOSEPOLY)

        def _endPath(self):
            pass

    loaded = {}
    fig, axes = plt.subplots(len(rows), 1, figsize=(16, 22), squeeze=False)
    proof = []
    for index, (axis, row) in enumerate(zip(axes[:, 0], rows)):
        key = row["family_key"]
        instance_key = (key, tuple(sorted(row["axes"].items())))
        if instance_key not in loaded:
            font = TTFont(paths[key])
            if font["head"].unitsPerEm != 1000:
                raise ValueError(f"Manifest expects a 1000-unit em: {key}")
            if row["axes"]:
                font = instantiateVariableFont(font, row["axes"], inplace=True)
            glyph_set = font.getGlyphSet()
            glyph_order = font.getGlyphOrder()
            face = hb.Face(paths[key].read_bytes())
            shaping_font = hb.Font(face)
            shaping_font.scale = (1000, 1000)
            shaping_font.set_variations(row["axes"])
            hb.ot_font_set_funcs(shaping_font)
            loaded[instance_key] = (font, glyph_set, glyph_order, shaping_font)
        font, glyph_set, glyph_order, shaping_font = loaded[instance_key]

        def shape(text):
            buffer = hb.Buffer()
            buffer.add_str(text)
            buffer.guess_segment_properties()
            buffer.language = row["language"]
            hb.shape(shaping_font, buffer, row["features"])
            return [
                (glyph_order[info.codepoint], pos.x_advance, pos.y_advance, pos.x_offset, pos.y_offset)
                for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions)
            ]

        shaped = {}
        for text, origin in (("д", 60), ("g", 840), ("доди", 1660)):
            items = shape(text)
            if any(item[0] == ".notdef" for item in items):
                raise ValueError(f"Missing glyph in reference proof: {key}: {text}")
            expected = row["shaped"][text]
            if [item[0] for item in items] != [item[0] for item in expected]:
                raise ValueError(f"Language/feature result changed: {key}: {text}")
            pen = OutlinePen(glyph_set)
            x, y = origin, 0
            for name, dx, dy, ox, oy in items:
                glyph_set[name].draw(TransformPen(pen, (1, 0, 0, 1, x + ox, y + oy)))
                x += dx
                y += dy
            axis.add_patch(PathPatch(PlotPath(pen.vertices, pen.codes), facecolor="#222126", edgecolor="none"))
            shaped[text] = items
        axis.set_xlim(-100, 3900)
        axis.set_ylim(-360, 1200)
        axis.set_aspect("equal")
        axis.axis("off")
        axis.axhline(0, color="#d7d5d1", lw=0.7)
        axis.text(-20, 1040, row["label"], fontsize=11, fontweight="bold", color="#272529")
        optical = f" / opsz {row['axes']['opsz']:g}" if "opsz" in row["axes"] else ""
        axis.text(-20, 925, f"wght {row['axes'].get('wght', 400):g}{optical} / native outlines and original spacing; language {row['language']}", fontsize=8, color="#6e6968")
        if index == 0:
            axis.text(170, 1160, "U+0434", fontsize=10)
            axis.text(960, 1160, "Latin g", fontsize=10)
            axis.text(1670, 1160, "Cyrillic context", fontsize=10)
        proof.append({**row, "shaped": shaped})
    fig.suptitle("Cursive Cyrillic de: actual open-source typeface references", fontsize=17, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.987))
    for extension in ("png", "svg"):
        fig.savefig(args.output_dir / f"cursive-de-real-references.{extension}", dpi=160)
    plt.close(fig)
    report = {"sources_manifest_sha256": digest(args.sources), "harfbuzz_version": hb.__version__, "verified_font_and_license_files": downloads, "native_proof_rows": proof}
    (args.output_dir / "proof-shaping.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(downloads)} reference font/OFL pairs; drew {len(proof)} native-outline rows to {args.output_dir}")


if __name__ == "__main__":
    main()
