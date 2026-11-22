"""Our own checks: colormaps, table fills and categorical palettes.

    uv run python report/analysis.py

Writes report/data.json. Every number in the report's computed
tables and figures comes from that file; nothing is typed in by hand.

Measures (all on OKLab, Ottosson 2020, with L scaled to 0-100 "points"):

- lightness reversal: the largest amount a colormap's lightness moves back
  against its overall direction. 0 means lightness is monotonic, so the order
  of values survives a grey print.
- lightness span: max L minus min L along the map.
- step unevenness: coefficient of variation (std / mean, in %) of the color
  difference between consecutive samples taken at equal steps of the data.
  0 means equal data steps look equally far apart.
- black-text contrast: WCAG 2 contrast ratio of black text on a fill
  (1 to 21; 7 is the WCAG AAA threshold for body text).
- grey gap: difference in L between the "best" and "second" fills of a table,
  the separation left on a black-and-white print.
- minimum color difference: smallest Euclidean OKLab distance between any two
  colors of a palette, under normal vision and under simulated color vision
  deficiency (Machado et al. 2009, severity 1.0).
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np

import pubviz as pv
from pubviz.color import contrast, hex_to_oklch, hex_to_rgb, linear_to_oklab, oklch_to_hex
from pubviz.theme import FILL_LEVELS

OUT = Path(__file__).with_name("data.json")
BLACK = "#000000"

# Machado, Oliveira & Fernandes (2009), severity 1.0 (dichromacy), copied from
# Table 1 of the authors' page:
# https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
# The authors do not say whether the matrices take linear or gamma-encoded
# RGB; we apply them to linearised sRGB, since they are built from the
# primaries' spectra. Tritanopia is left out: the paper does not model it.
CVD = {
    "protanopia": [[0.152286, 1.052583, -0.204868],
                   [0.114503, 0.786281, 0.099216],
                   [-0.003882, -0.048116, 1.051998]],
    "deuteranopia": [[0.367322, 0.860646, -0.227968],
                     [0.280085, 0.672501, 0.047413],
                     [-0.011820, 0.042940, 0.968881]],
}


def to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_srgb(c: float) -> float:
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklab_of_rgb(rgb) -> np.ndarray:
    """OKLab of an sRGB triple in [0, 1]."""
    return np.array(linear_to_oklab(*(to_linear(c) for c in rgb)))


def rgb_of_hex(value: str) -> tuple[float, float, float]:
    return hex_to_rgb(value)


def hex_of_rgb(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(round(255 * min(max(c, 0.0), 1.0))) for c in rgb)


# ---- colormaps ---------------------------------------------------------------

def sample_map(name: str, n: int) -> list[tuple[float, float, float]]:
    """n colors at equal data steps, as float sRGB."""
    if name == "pubviz table shading":
        # The nine steps pvtable shades cells with, interpolated where n > 9.
        steps = [rgb_of_hex(c) for c in pv.Theme().heat]
        t = np.linspace(0, len(steps) - 1, n)
        return [tuple(np.interp(x, range(len(steps)), [s[i] for s in steps]) for i in range(3)) for x in t]
    if name == "pubviz figure map":
        cmap = pv.Theme().cmap()
    elif name == "pubviz level map":
        cmap = pv.pictures.level_map()
    else:
        cmap = matplotlib.colormaps[name]
    return [tuple(cmap(t)[:3]) for t in np.linspace(0, 1, n)]


def map_measures(colors) -> dict:
    lab = np.array([oklab_of_rgb(c) for c in colors])
    L = 100 * lab[:, 0]
    direction = 1.0 if L[-1] >= L[0] else -1.0
    peak, reversal = -np.inf, 0.0
    for value in direction * L:
        peak = max(peak, value)
        reversal = max(reversal, peak - value)
    steps = np.linalg.norm(np.diff(lab, axis=0), axis=1)
    return {
        "reversal": round(float(reversal), 1),
        "span": round(float(L.max() - L.min()), 1),
        "unevenness": round(float(100 * steps.std() / steps.mean()), 1),
        "black_contrast": round(min(contrast(BLACK, hex_of_rgb(c)) for c in colors), 1),
    }


MAPS = {
    # name in the report: (matplotlib or pubviz name, family)
    "jet": ("jet", "rainbow"),
    "turbo": ("turbo", "rainbow"),
    "viridis": ("viridis", "ordered"),
    "Greys": ("Greys", "ordered"),
    "magma": ("magma", "ordered"),
    "pubviz figure map": ("pubviz figure map", "pubviz"),
    "pubviz table shading": ("pubviz table shading", "pubviz"),
    "pubviz level map": ("pubviz level map", "pubviz"),
}


def colormaps() -> dict:
    out = {}
    for label, (name, family) in MAPS.items():
        # 17 samples: coarse enough that 8-bit rounding does not swamp the
        # step sizes, fine enough to catch a rainbow's turns.
        measures = map_measures(sample_map(name, 17))
        curve = [round(float(100 * oklab_of_rgb(c)[0]), 2) for c in sample_map(name, 101)]
        out[label] = {"family": family, **measures, "lightness": curve}
    return out


# ---- table fills ------------------------------------------------------------

def tint(value: str, percent: float) -> str:
    """xcolor's value!percent: the color mixed with white in sRGB."""
    r, g, b = rgb_of_hex(value)
    k = percent / 100
    return hex_of_rgb((k * r + 1 - k, k * g + 1 - k, k * b + 1 - k))


def fill_design(best_of, second_of) -> dict:
    accents = [pv.Theme(name).accent for name in pv.ACCENTS]
    best = [best_of(a) for a in accents]
    second = [second_of(a) for a in accents]
    L_best = [100 * hex_to_oklch(b)[0] for b in best]
    gaps = [100 * (hex_to_oklch(s)[0] - hex_to_oklch(b)[0]) for b, s in zip(best, second)]
    return {
        "spread": round(max(L_best) - min(L_best), 1),
        "min_gap": round(min(gaps), 1),
        "min_contrast": round(min(contrast(BLACK, b) for b in best), 1),
        "per_accent": {name: {"best_L": round(Lb, 1), "gap": round(g, 1)}
                       for name, Lb, g in zip(pv.ACCENTS, L_best, gaps)},
    }


def fixed(level: float, share: float):
    def make(accent: str) -> str:
        L, C, h = hex_to_oklch(accent)
        return oklch_to_hex(level, C * share, h)
    return make


def fills() -> dict:
    (_, s1), (L2, s2), _ = FILL_LEVELS
    designs = {}
    for k1, k2 in [(30, 10), (40, 15), (50, 20), (60, 25)]:
        designs[f"tint {k1}/{k2}"] = fill_design(lambda a, k=k1: tint(a, k), lambda a, k=k2: tint(a, k))
    for level in (0.80, 0.85, 0.90):
        designs[f"fixed L={level:.2f}"] = fill_design(fixed(level, s1), fixed(L2, s2))
    return designs


# ---- categorical palettes under color vision deficiency ----------------------

PALETTES = {
    "matplotlib tab10": [matplotlib.colors.to_hex(c) for c in matplotlib.colormaps["tab10"].colors[:6]],
    "Okabe-Ito": ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00"],
    "rainbow (HSV)": [matplotlib.colors.to_hex(matplotlib.colors.hsv_to_rgb((h / 6, 1, 1))) for h in range(6)],
    "pubviz kinds": [pv.Theme().roles[f"kind{i}"] for i in range(1, 7)],
}


def simulate(value: str, matrix) -> np.ndarray:
    lin = np.array([to_linear(c) for c in rgb_of_hex(value)])
    out = np.clip(np.asarray(matrix) @ lin, 0.0, 1.0)
    return np.array(linear_to_oklab(*out))


def palettes() -> dict:
    out = {}
    for name, colors in PALETTES.items():
        row = {}
        for vision, matrix in [("normal", np.eye(3)), *CVD.items()]:
            labs = [simulate(c, matrix) for c in colors]
            row[vision] = round(min(float(100 * np.linalg.norm(a - b)) for a, b in combinations(labs, 2)), 1)
        # A grey print keeps lightness only.
        Ls = [100 * simulate(c, np.eye(3))[0] for c in colors]
        row["grey print"] = round(min(abs(a - b) for a, b in combinations(Ls, 2)), 1)
        out[name] = {"colors": colors, "min_difference": row}
    return out


def main() -> None:
    data = {"colormaps": colormaps(), "fills": fills(), "palettes": palettes()}
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    for section, rows in data.items():
        print(f"== {section}")
        for name, row in rows.items():
            print(f"  {name:24s}", {k: v for k, v in row.items() if k not in ("lightness", "per_accent", "colors")})


if __name__ == "__main__":
    main()
