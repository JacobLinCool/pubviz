"""One accent color in, every color a paper needs out.

A theme is the accent color plus a print mode. Every other color is derived
from the accent by fixed lightness targets, so changing the accent changes the
look but never the meaning: the best result is always the darkest fill, the
second best is lighter, and both stay in that order on a greyscale print.

The roles, and what each one is for:

- ``accent``: the color as given. Names your method in prose and legends.
- ``strong``: the accent moved into a lightness range that reads as a line or
  mark on white. "Ours" in every figure.
- ``fill1``..``fill3``: cell backgrounds for the best, second and third value.
- ``band``: neutral background for section rows in a table.
- ``muted``: grey text for secondary labels and missing values.
- ``pos`` / ``neg``: text color of a change that helps or hurts.
- ``heat0``..``heat8``: a light-to-dark ramp of the accent hue for grids.
- ``others``: neutral greys for the methods you compare against.

``latex/pubviz.sty`` derives the same roles with the same numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property

from .color import hex_to_oklch, lightness, oklch_to_hex, to_gray

# Accent presets. Each is an ordinary hex value: pass any other hex the same way.
PRESETS: dict[str, str] = {
    "amber": "#E4AE1A",
    "blue": "#1A73D5",
    "teal": "#009A9A",
    "green": "#2E9E52",
    "red": "#DA4339",
    "purple": "#8254C4",
    "gray": "#717171",
}
DEFAULT_ACCENT = "amber"

# Lightness range for ``strong``: dark enough to read as a line on white,
# light enough to keep its hue.
STRONG_RANGE = (0.42, 0.66)
# (lightness, share of the accent's chroma) for the best, second and third fill.
# The best fill sits at 0.85: in grey it stays about 10 lightness points from
# the second fill for every preset accent, and black text on it keeps a WCAG
# contrast near 13 (the fills check in report/analysis.py). At 0.90 the gap
# shrank to about 5 points.
FILL_LEVELS = ((0.850, 0.65), (0.955, 0.26), (0.978, 0.12))
BAND_LIGHTNESS = 0.960
MUTED_LIGHTNESS = 0.550
# Heat ramp: nine steps from almost white to a mid tone that black text still
# reads on.
HEAT_STEPS = 9
HEAT_LIGHTNESS = (0.975, 0.780)
HEAT_CHROMA_SHARE = 0.80
# Kinds of block in a diagram: one light fill per kind, all at one lightness,
# with fixed hues (orange, blue, yellow, pink, purple, green) so a kind keeps
# its color across papers. Mirrors the kind-* roles in pubviz.sty.
KIND_LIGHTNESS = 0.920
KIND_CHROMA = 0.070
KIND_HUES = (55.0, 250.0, 105.0, 355.0, 300.0, 150.0)
# Change colors. Independent of the accent so that "better" and "worse" mean
# the same thing in every paper. The sign is always printed as well.
POS_DEFAULT = "#1D7D3E"
NEG_DEFAULT = "#BD3931"
# Greys for compared methods are spread over this lightness range, skipping
# a band around the lightness of "ours" so that ours stays apart from every
# grey on a black-and-white print too.
OTHERS_RANGE = (0.36, 0.88)
OTHERS_GAP = 0.10
# In gray and plain mode "ours" is near black: the one mark without hue still
# has to stand out.
OURS_GRAY_LIGHTNESS = 0.30
# Colors for compared methods when they need their own identity (no "ours",
# or methods from different families). Okabe and Ito's set, which stays
# distinct under the common forms of color blindness. Slots too close in hue
# to the accent are skipped.
CATEGORICAL = ("#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442")
CATEGORICAL_MIN_HUE_GAP = 35.0

MODES = ("color", "gray", "plain")


def resolve_accent(accent: str) -> str:
    """A preset name or a hex value to a hex value."""
    if accent in PRESETS:
        return PRESETS[accent]
    text = accent.strip()
    if not text.startswith("#"):
        text = "#" + text
    hex_to_oklch(text)  # validates
    return text.upper()


@dataclass(frozen=True)
class Theme:
    """The colors of a paper, derived from one accent.

    ``mode`` is ``"color"`` for screens and color print, ``"gray"`` to turn
    every role into the grey of the same lightness, and ``"plain"`` for venues
    that ask for no shading at all (tables then use bold and underline only;
    figures fall back to ``"gray"``).
    """

    accent: str = DEFAULT_ACCENT
    mode: str = "color"
    pos: str = POS_DEFAULT
    neg: str = NEG_DEFAULT

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.mode!r}")
        object.__setattr__(self, "accent", resolve_accent(self.accent))

    @cached_property
    def roles(self) -> dict[str, str]:
        return derive_roles(self.accent, self.pos, self.neg, gray=self.mode != "color")

    def __getitem__(self, role: str) -> str:
        return self.roles[role]

    @property
    def strong(self) -> str:
        return self.roles["strong"]

    @property
    def fills(self) -> list[str]:
        return [self.roles[f"fill{i}"] for i in (1, 2, 3)]

    @property
    def heat(self) -> list[str]:
        return [self.roles[f"heat{i}"] for i in range(HEAT_STEPS)]

    @property
    def ours(self) -> str:
        """The color of "ours" in figures: ``strong``, or near black without hue."""
        if self.mode == "color":
            return self.roles["strong"]
        return oklch_to_hex(OURS_GRAY_LIGHTNESS, 0.0, 0.0)

    def _allowed(self, lo: float, hi: float) -> list[float]:
        ours_L = lightness(self.ours)
        grid = [hi - (hi - lo) * i / 200 for i in range(201)]
        return [L for L in grid if abs(L - ours_L) >= OTHERS_GAP]

    def others(self, n: int, lo: float = OTHERS_RANGE[0], hi: float = OTHERS_RANGE[1],
               single: float = 0.78) -> list[str]:
        """``n`` greys for compared methods, lightest first.

        Spread evenly over [``lo``, ``hi``] without the band around the
        lightness of ``ours``, so every grey differs from ours and from each
        other on a greyscale print. Fills can use light greys; lines and
        points need the darker part of the range (``hi`` about 0.74).
        """
        if n <= 0:
            return []
        allowed = self._allowed(lo, hi)
        if n == 1:
            pick = [min(allowed, key=lambda L: abs(L - single))]
        else:
            pick = [allowed[round(i * (len(allowed) - 1) / (n - 1))] for i in range(n)]
        return [oklch_to_hex(L, 0.0, 0.0) for L in pick]

    def grey(self, target: float) -> str:
        """The grey nearest to ``target`` lightness that stays apart from ours."""
        allowed = self._allowed(0.2, 0.95)
        return oklch_to_hex(min(allowed, key=lambda L: abs(L - target)), 0.0, 0.0)

    def categorical(self, n: int) -> list[str]:
        """``n`` distinct colors for methods that need their own identity.

        Skips slots whose hue is close to the accent, so "ours" stays unique.
        Past the available slots, fold extra methods into "other" or split
        the figure; a generated eighth hue will not be told apart.
        """
        if self.mode != "color":
            return self.others(n)
        accent_h = math.degrees(hex_to_oklch(self.accent)[2])
        accent_c = hex_to_oklch(self.accent)[1]
        slots = []
        for value in CATEGORICAL:
            h = math.degrees(hex_to_oklch(value)[2])
            gap = abs((h - accent_h + 180) % 360 - 180)
            if accent_c < 0.03 or gap >= CATEGORICAL_MIN_HUE_GAP:
                slots.append(value)
        if n > len(slots):
            raise ValueError(f"{n} methods need their own color but only {len(slots)} distinct colors are available")
        return slots[:n]

    def cmap(self, dark: float | None = None):
        """Sequential colormap in the accent hue, from near white to ``dark`` lightness.

        By default the dark end sits a little below ``strong``: going much
        darker turns light hues (amber, yellow) muddy brown.
        """
        from matplotlib.colors import ListedColormap

        L, C, h = hex_to_oklch(self.accent)
        if dark is None:
            dark = min(0.60, max(0.40, lightness(self.roles["strong"]) - 0.08))
        colors = []
        for i in range(256):
            t = i / 255
            c = oklch_to_hex(0.975 + (dark - 0.975) * t, C * t, h)
            colors.append(to_gray(c) if self.mode != "color" else c)
        return ListedColormap(colors, name="pubviz")

    def diverging(self, dark: float = 0.45):
        """Diverging colormap: ``neg`` hue, through near white, to ``pos`` hue."""
        from matplotlib.colors import ListedColormap

        def arm(hex_value, n):
            Lp, Cp, hp = hex_to_oklch(hex_value)
            out = []
            for i in range(n):
                t = i / (n - 1)
                c = oklch_to_hex(0.97 + (dark - 0.97) * t, Cp * t, hp)
                out.append(to_gray(c) if self.mode != "color" else c)
            return out

        neg = arm(self.neg, 128)[::-1]
        pos = arm(self.pos, 128)
        return ListedColormap(neg + pos, name="pubviz-diverging")

    def latex(self) -> str:
        """The ``\\pvsetup`` line that gives a LaTeX document this theme."""
        parts = [f"accent={self.accent.lstrip('#')}", f"mode={self.mode}"]
        if self.pos != POS_DEFAULT:
            parts.append(f"pos={self.pos.lstrip('#')}")
        if self.neg != NEG_DEFAULT:
            parts.append(f"neg={self.neg.lstrip('#')}")
        return "\\pvsetup{" + ", ".join(parts) + "}"


def derive_roles(accent: str, pos: str = POS_DEFAULT, neg: str = NEG_DEFAULT, gray: bool = False) -> dict[str, str]:
    """Every role color from an accent hex. Mirrors ``\\__pv_derive:`` in pubviz.sty."""
    L, C, h = hex_to_oklch(accent)
    roles = {"accent": accent.upper() if accent.startswith("#") else "#" + accent.upper()}
    roles["strong"] = oklch_to_hex(min(max(L, STRONG_RANGE[0]), STRONG_RANGE[1]), C, h)
    for i, (lf, share) in enumerate(FILL_LEVELS, start=1):
        roles[f"fill{i}"] = oklch_to_hex(lf, C * share, h)
    roles["band"] = oklch_to_hex(BAND_LIGHTNESS, 0.0, 0.0)
    roles["muted"] = oklch_to_hex(MUTED_LIGHTNESS, 0.0, 0.0)
    roles["pos"] = pos.upper()
    roles["neg"] = neg.upper()
    lo, hi = HEAT_LIGHTNESS
    for i in range(HEAT_STEPS):
        t = i / (HEAT_STEPS - 1)
        roles[f"heat{i}"] = oklch_to_hex(lo + (hi - lo) * t, C * HEAT_CHROMA_SHARE * t, h)
    for i, hue in enumerate(KIND_HUES, start=1):
        roles[f"kind{i}"] = oklch_to_hex(KIND_LIGHTNESS, KIND_CHROMA, math.radians(hue))
    if gray:
        roles = {name: to_gray(value) for name, value in roles.items()}
    return roles


def describe(theme: Theme) -> str:
    """A plain-text table of the roles with their greyscale lightness."""
    lines = [f"accent {theme.accent}  mode {theme.mode}", ""]
    for name, value in theme.roles.items():
        lines.append(f"  {name:8s} {value}  L={lightness(value):.3f}  grey {to_gray(value)}")
    return "\n".join(lines)

