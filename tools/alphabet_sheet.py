#!/usr/bin/env python3
"""Render the exact GLIF outlines in the shared Cyrillic inventory.

python3 tools/alphabet_sheet.py [docs/img/alphabet_status.png]

The optional codex section supplements, rather than overwrites, done. Border
colours identify provenance, not approval. No source font, path simplification,
boolean operation or glyph re-export is involved. PNG and SVG are emitted for
both the inventory and the к/т comparison.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["path.simplify"] = False
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.transforms import Affine2D
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ufoLib.glifLib import readGlyphFromString

ROOT = Path(__file__).resolve().parents[1]
UP = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LOW = UP.lower()
KZ_UP = "ӘҒҚҢӨҰҮҺІ"
KZ_LOW = KZ_UP.lower()
BLUE = "#2563EB"
GREEN = "#22AA77"
PURPLE = "#9333EA"
AMBER = "#D99316"
INK = "#272333"
MUTED = "#7D7C83"
FAINT = "#D6D4D0"
BG = "#F5F2EC"
DPI = 100
SANS = font_manager.FontProperties(family="DejaVu Sans")
SANS_BOLD = font_manager.FontProperties(family="DejaVu Sans", weight="bold")
SERIF = font_manager.FontProperties(family="DejaVu Serif")


class MplPen(BasePen):
    """Keep the source cubic/quadratic curves and contour winding intact."""

    def __init__(self, glyph_set):
        super().__init__(glyph_set)
        self.vertices = []
        self.codes = []
        self.start = None

    def _moveTo(self, pt):
        self.start = pt
        self.vertices.append(pt)
        self.codes.append(MplPath.MOVETO)

    def _lineTo(self, pt):
        self.vertices.append(pt)
        self.codes.append(MplPath.LINETO)

    def _curveToOne(self, p1, p2, p3):
        self.vertices.extend((p1, p2, p3))
        self.codes.extend((MplPath.CURVE4,) * 3)

    def _qCurveToOne(self, p1, p2):
        self.vertices.extend((p1, p2))
        self.codes.extend((MplPath.CURVE3,) * 2)

    def _closePath(self):
        self.vertices.append(self.start)
        self.codes.append(MplPath.CLOSEPOLY)

    def _endPath(self):
        pass

    def result(self):
        return MplPath(self.vertices, self.codes)


class GlifGlyph:
    def __init__(self, filename):
        self.filename = filename

    def draw(self, pen):
        rec, _ = recording(self.filename)
        rec.replay(pen)


class GlifSet(dict):
    """Resolve any GLIF components without flattening or rewriting sources."""

    def __missing__(self, name):
        for filename in (ROOT / "data").rglob("*.glif"):
            if ET.parse(filename).getroot().get("name") == name:
                value = GlifGlyph(filename)
                self[name] = value
                return value
        raise KeyError(f"Component {name!r} has no GLIF in data/")


GLYPHS = GlifSet()


@lru_cache(maxsize=None)
def recording(filename):
    metadata = SimpleNamespace(width=0)
    rec = RecordingPen()
    readGlyphFromString(
        Path(filename).read_text(encoding="utf-8"), metadata,
        PointToSegmentPen(rec),
    )
    return rec, metadata.width


@dataclass(frozen=True)
class Outline:
    path: MplPath
    bounds: tuple
    advance: float


@lru_cache(maxsize=None)
def load_glif(relative_path):
    filename = ROOT / relative_path
    rec, advance = recording(filename)
    pen = MplPen(GLYPHS)
    bounds = BoundsPen(GLYPHS)
    rec.replay(pen)
    rec.replay(bounds)
    if bounds.bounds is None:
        raise ValueError(f"No outline in {relative_path}")
    return Outline(pen.result(), bounds.bounds, advance)


def text(ax, x, y, label, size=18, color=INK, bold=False, **kwargs):
    ax.text(
        x, y, label, fontsize=size * 72 / DPI, color=color,
        fontproperties=SANS_BOLD if bold else SANS, va="top", **kwargs,
    )


def canvas(width, height):
    fig, ax = plt.subplots(figsize=(width / DPI, height / DPI), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return fig, ax


def rectangle(ax, x, y, w, h, color, lw=2, dashed=False, fill="white"):
    ax.add_patch(Rectangle(
        (x, y), w, h, facecolor=fill, edgecolor=color,
        linewidth=lw, linestyle=(0, (4, 4)) if dashed else "solid",
        joinstyle="round",
    ))


def glyph(ax, filename, center_x, baseline, scale, color=INK):
    outline = load_glif(filename)
    xmin, _, xmax, _ = outline.bounds
    dx = center_x - (xmin + xmax) * scale / 2
    transform = Affine2D().scale(scale, -scale).translate(dx, baseline)
    ax.add_patch(PathPatch(
        outline.path, facecolor=color, edgecolor="none",
        transform=transform + ax.transData,
    ))


def codex_items(entry):
    return entry.get("variants", [])


def codex_variant_name(item):
    return str(item.get("variant", item.get("id", "")))


def source_items(ch, cfg):
    """Return the drawings to show, omitting genuinely shared duplicates."""
    if ch in cfg.get("user", {}):
        item = next(v for v in cfg["user"][ch]["variants"] if v["role"] == "primary")
        archive = cfg["user"][ch].get("origin") == "Claude"
        return [{"path": item["path"], "short": "Claude · архив" if archive else "Автор", "color": GREEN if archive else PURPLE}]
    done = cfg["done"]
    entry = cfg.get("codex", {}).get(ch)
    result = []
    if entry:
        if ch in done and entry.get("conflict", False):
            result.append({"path": done[ch][0], "short": "Claude", "color": GREEN})
        for item in codex_items(entry):
            if entry.get("selected") and codex_variant_name(item) != entry["selected"]:
                continue
            variant = codex_variant_name(item)
            label = f"C{variant}" if len(codex_items(entry)) > 1 else f"Codex {variant}"
            if ch == "ж":
                label = item.get("label", "Cyr11 / импорт")
            if entry.get("shared_with_claude"):
                label = f"{variant} = Claude" if ch == "й" and variant == "01" else label
            result.append({"path": item["path"], "short": label, "color": BLUE})
    elif ch in done:
        result.append({"path": done[ch][0], "short": done[ch][1], "color": GREEN})
    return result


def trim(label, limit=24):
    return label if len(label) <= limit else label[:limit - 1] + "…"


def cell_caption(ch, cfg):
    if ch in cfg.get("user", {}):
        if cfg["user"][ch].get("origin") == "Claude":
            return "Claude · на рассмотрении", GREEN
        return "Автор · SVG / исходник", PURPLE
    entry = cfg.get("codex", {}).get(ch)
    if entry:
        if entry.get("conflict"):
            return "версии расходятся", AMBER
        if entry.get("shared_with_claude"):
            if ch == "й":
                return "общая 01 · выбор открыт", BLUE
            return "общая · Codex / Claude", BLUE
        if ch == "ж" and "Claude" in entry.get("provenance", ""):
            return "импорт · архив Claude", BLUE
        if entry.get("selected") is not None:
            return f"Codex · выбрана {entry['selected']}", BLUE
        return "Codex · выбор открыт", BLUE
    if ch in cfg["done"]:
        label = cfg["done"][ch][1]
        if ch in set(cfg.get("latin_donor", [])):
            label = label.replace("латинская ", "лат. ").replace("латинский ", "лат. ")
            return f"Claude · {label}", GREEN
        return f"Claude · {trim(label, 17)}", GREEN
    notes = cfg.get("shared_review", {}).get("missing_notes", {})
    return ("есть эскиз · вне основ", MUTED) if ch in notes else ("нет основы", MUTED)


def draw_cell(ax, ch, cfg, x, y, width=188, height=252):
    entry = cfg.get("codex", {}).get(ch)
    items = source_items(ch, cfg)
    has_claude = ch in cfg["done"]
    border = (GREEN if cfg["user"][ch].get("origin") == "Claude" else PURPLE) if ch in cfg.get("user", {}) else BLUE if entry else GREEN if has_claude else FAINT
    rectangle(ax, x + 4, y + 4, width - 8, height - 8, border, 2 if items else 1, not items)
    if entry and has_claude:
        rectangle(ax, x + 9, y + 9, width - 18, height - 18, GREEN, 1, fill="none")
    text(ax, x + 17, y + 16, ch, 20, bold=True)
    if entry and entry.get("conflict"):
        ax.text(
            x + width - 24, y + 25, "!", fontsize=15, color="white", ha="center", va="center",
            bbox={"boxstyle": "circle,pad=0.2", "fc": AMBER, "ec": "none"},
        )
    baseline = y + 167
    # The same em scale is used for every drawing within this cell, including conflicts.
    if items:
        widths = [load_glif(item["path"]).bounds[2] - load_glif(item["path"]).bounds[0] for item in items]
        gap = 12
        scale = min(.172, (width - 34 - gap * (len(items) - 1)) / sum(widths))
        total = sum(widths) * scale + gap * (len(items) - 1)
        left = x + (width - total) / 2
        for item, ink_width in zip(items, widths):
            center = left + ink_width * scale / 2
            glyph(ax, item["path"], center, baseline, scale)
            if len(items) > 1:
                text(ax, center, y + 205, item["short"], 13, item["color"], ha="center")
            left += ink_width * scale + gap
        if len(items) == 1 and entry and ch not in ("и",):
            text(ax, x + width / 2, y + 205, trim(items[0]["short"]), 14, BLUE, ha="center")
    else:
        ax.text(
            x + width / 2, baseline - 2, ch, fontsize=73 * 72 / DPI,
            fontproperties=SERIF, color="#C9C5BF", ha="center", va="bottom",
        )
    caption, color = cell_caption(ch, cfg)
    text(ax, x + width / 2, y + height - 27, caption, 12.5, color, ha="center")


def legend(ax, x, y, color, label, double=False, dashed=False):
    rectangle(ax, x, y, 24, 24, color, 2, dashed)
    if double:
        rectangle(ax, x + 5, y + 5, 14, 14, GREEN, 1, fill="none")
    text(ax, x + 36, y + 1, label, 17)


def validate(cfg):
    """Fail before replacing pictures if a configured outline is unavailable."""
    for ch in cfg["done"]:
        for item in source_items(ch, cfg):
            load_glif(item["path"])
    for ch in set(cfg.get("codex", {})) | set(cfg.get("user", {})):
        for item in source_items(ch, cfg):
            load_glif(item["path"])


def save(fig, filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(filename, dpi=DPI, facecolor=BG)
    fig.savefig(filename.with_suffix(".svg"), facecolor=BG)
    plt.close(fig)


def inventory(cfg, filename):
    present = set(cfg["done"]) | set(cfg.get("codex", {})) | set(cfg.get("user", {}))
    ru_upper = sum(ch in present for ch in UP)
    ru_lower = sum(ch in present for ch in LOW)
    kz = sum(ch in present for ch in KZ_UP + KZ_LOW)
    total = ru_upper + ru_lower
    columns, cell_width, cell_height, pad = 11, 188, 252, 40
    blocks = [("РУССКОЕ ЯДРО · прописные", UP), ("РУССКОЕ ЯДРО · строчные", LOW),
              ("КАЗАХСКИЕ · прописные", KZ_UP), ("КАЗАХСКИЕ · строчные", KZ_LOW)]
    header = 330
    height = header + sum(66 + math.ceil(len(letters) / columns) * cell_height for _, letters in blocks) + 255
    width = pad * 2 + columns * cell_width
    fig, ax = canvas(width, height)
    text(ax, pad, 30, "Very Peri Serif · общая карта", 41, bold=True)
    text(ax, pad, 94, f"Есть основа: {total}/66 · прописные {ru_upper}/33 · строчные {ru_lower}/33", 28)
    text(ax, pad, 138, f"Казахские: {kz}/18   |   обе разработки учтены вместе, совпадения не удваиваются", 20, MUTED)
    rectangle(ax, pad, 186, width - pad * 2, 9, "#DCD8D0", 0, fill="#DCD8D0")
    rectangle(ax, pad, 186, (width - pad * 2) * total / 66, 9, BLUE, 0, fill=BLUE)
    legend(ax, pad, 217, GREEN, "Claude · его ветка")
    legend(ax, pad + 360, 217, BLUE, "Codex · наши материалы")
    legend(ax, pad + 780, 217, BLUE, "общая основа", double=True)
    legend(ax, pad + 1110, 217, FAINT, "нет интегрированной основы", dashed=True)
    legend(ax, pad + 1680, 217, PURPLE, "Автор · его SVG")
    text(ax, pad, 267, "Цвет — источник. Наличие рисунка не означает утверждение. Открытые варианты показаны рядом.", 19, MUTED)
    text(ax, pad, 297, "Латинские доноры сохранены в зелёном слое; ж — импорт из архива пользователя / Claude Cyr11.", 16, MUTED)
    y = header
    for title, letters in blocks:
        count = sum(ch in present for ch in letters)
        text(ax, pad + 4, y + 13, f"{title}   {count}/{len(letters)}", 24, bold=True)
        y += 66
        for i, ch in enumerate(letters):
            r, c = divmod(i, columns)
            draw_cell(ax, ch, cfg, pad + c * cell_width, y + r * cell_height, cell_width, cell_height)
        y += math.ceil(len(letters) / columns) * cell_height
    text(ax, pad, y + 30, "Ещё без основы", 25, bold=True)
    missing_lower = " ".join(ch for ch in LOW if ch not in present) or "—"
    missing_upper = " ".join(ch for ch in UP if ch not in present) or "—"
    text(ax, pad, y + 76, f"Строчные: {missing_lower}", 23)
    text(ax, pad, y + 116, f"Прописные: {missing_upper}", 23)
    text(ax, pad, y + 165, "Авторские SVG и У/Ұ из архива добавлены как исходники. Архивные формы ещё на рассмотрении.", 17, MUTED)
    text(ax, pad, y + 201, "Источник: data/alphabet.json и указанные GLIF. Основы и альтернативы к/т вынесены на отдельный лист.", 16, MUTED)
    save(fig, filename)
    return {"russian": total, "russian_upper": ru_upper, "russian_lower": ru_lower, "kazakh": kz,
            "missing_lower": missing_lower, "missing_upper": missing_upper}


def conflict_panel(cfg, filename):
    width, height, pad = 1800, 1730, 70
    fig, ax = canvas(width, height)
    text(ax, pad, 35, "к / т · основы и альтернативы", 40, bold=True)
    text(ax, pad, 101, "Выбор пользователя: к Codex02, т Codex02. Остальные контуры сохранены.", 22, MUTED)
    legend(ax, pad, 158, GREEN, "Claude")
    legend(ax, pad + 250, 158, BLUE, "Codex")
    text(ax, pad, 225, "т · две разные конструкции", 28, bold=True)
    t_items = []
    if "т" in cfg["done"]:
        t_items.append((cfg["done"]["т"][0], f"Claude · {cfg['done']['т'][1]}", GREEN, "альтернативный стиль · ss08"))
    te = cfg.get("codex", {}).get("т", {})
    for item in codex_items(te):
        t_items.append((item["path"], f"Codex · {codex_variant_name(item)}", BLUE, item.get("label", "")))
    slot = (width - pad * 2) / max(1, len(t_items))
    for i, (path, label, color, subtitle) in enumerate(t_items):
        cx = pad + slot * (i + .5)
        rectangle(ax, pad + slot * i + 8, 285, slot - 16, 438, color, 2)
        glyph(ax, path, cx, 618, .50)
        text(ax, cx, 650, label, 24, color, ha="center", bold=True)
        text(ax, cx, 687, subtitle, 18, MUTED, ha="center")
    text(ax, pad, 778, "к · три основы и контекстная форма Claude", 28, bold=True)
    k_items = []
    if "к" in cfg["done"]:
        k_items.append((cfg["done"]["к"][0], "Claude · к", GREEN, "сохранённая прежняя основа"))
    for item in codex_items(cfg.get("codex", {}).get("к", {})):
        k_items.append((item["path"], f"Codex · {codex_variant_name(item)}", BLUE, ('основа' if item['variant'] == '02' else 'сохранённая альтернатива')))
    short_path = "data/ka/ka_short.glif"
    if (ROOT / short_path).exists():
        k_items.append((short_path, "Claude · к short", GREEN, "контекстная форма"))
    slot = (width - pad * 2) / max(1, len(k_items))
    max_width = max(load_glif(item[0]).bounds[2] - load_glif(item[0]).bounds[0] for item in k_items)
    scale = min(.49, (slot - 80) / max_width)
    for i, (path, label, color, subtitle) in enumerate(k_items):
        cx = pad + slot * (i + .5)
        rectangle(ax, pad + slot * i + 8, 838, slot - 16, 470, color, 2)
        glyph(ax, path, cx, 1198, scale)
        text(ax, cx, 1230, label, 22, color, ha="center", bold=True)
        text(ax, cx, 1268, subtitle, 17, MUTED, ha="center")
    text(ax, pad, 1370, "Что различается", 25, bold=True)
    text(ax, pad, 1420, "т: конструкция Claude имеет верхнюю перекладину; выбранная в Codex — две арки и письменный выход.", 20)
    text(ax, pad, 1462, "к: Codex02 — основа; короткая Claude включается перед верхней левой засечкой следующей буквы.", 20)
    text(ax, pad, 1504, "к short включается контекстом; она не считается четвёртой самостоятельной буквой или новым выбором.", 20)
    text(ax, pad, 1572, "Общий масштаб внутри каждой строки. Цвет рамки показывает источник; контуры GLIF не изменены.", 18, MUTED)
    text(ax, pad, 1615, "Выборы к/т согласованы пользователем. Й остаётся открытым выбором.", 18, MUTED)
    save(fig, filename)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="docs/img/alphabet_status.png")
    args = parser.parse_args()
    cfg = json.loads((ROOT / "data/alphabet.json").read_text(encoding="utf-8"))
    validate(cfg)
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    report = inventory(cfg, output)
    conflict_panel(cfg, output.with_name("alphabet_conflicts.png"))
    print(json.dumps({"output": str(output), "svg": str(output.with_suffix('.svg')), **report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
