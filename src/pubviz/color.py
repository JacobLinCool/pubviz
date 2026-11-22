"""Color math shared by the LaTeX package and the Python library.

Every derived color is built in OKLCH (lightness, chroma, hue), a color space in
which equal lightness steps look equally far apart. Setting lightness on
purpose is what keeps an ordered set of fills (best, second, third) ordered
when a page is printed in black and white: a grey printer keeps lightness and
drops hue.

``latex/pubviz.sty`` implements the same steps with the same constants. The
test ``tests/test_latex_agreement.py`` compiles that file and checks that both
sides produce the same hex values, so change the two together.
"""

from __future__ import annotations

import math

# Gamut test tolerance and bisection depth. Both must match pubviz.sty.
GAMUT_EPS = 1e-6
BISECT_STEPS = 18


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    """``"#D8A02C"`` or ``"d8a02c"`` to sRGB channels in [0, 1]."""
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"expected a 6-digit hex color, got {value!r}")
    return tuple(int(text[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    """sRGB channels to an uppercase hex string, rounding half up like the LaTeX side."""
    channels = (math.floor(255 * min(1.0, max(0.0, c)) + 0.5) for c in rgb)
    return "#" + "".join(f"{c:02X}" for c in channels)


def _to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c: float) -> float:
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * c ** (1 / 2.4) - 0.055


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1 / 3), x)


def linear_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    l = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def oklab_to_linear(L: float, a: float, b: float) -> tuple[float, float, float]:
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def hex_to_oklch(value: str) -> tuple[float, float, float]:
    """Hex to (L, C, h) with L in [0, 1], C >= 0 and h in radians."""
    r, g, b = (_to_linear(c) for c in hex_to_rgb(value))
    L, a, bb = linear_to_oklab(r, g, b)
    C = math.hypot(a, bb)
    h = math.atan2(bb, a) if C > 1e-6 else 0.0
    return L, C, h


def _oklch_to_linear(L: float, C: float, h: float) -> tuple[float, float, float]:
    return oklab_to_linear(L, C * math.cos(h), C * math.sin(h))


def in_gamut(L: float, C: float, h: float) -> bool:
    return all(-GAMUT_EPS <= c <= 1 + GAMUT_EPS for c in _oklch_to_linear(L, C, h))


def fit_chroma(L: float, C: float, h: float) -> float:
    """The largest chroma <= C that sRGB can show at this lightness and hue.

    Lowering chroma rather than clipping channels keeps lightness and hue, so
    a fill meant to be light stays exactly as light as asked.
    """
    if in_gamut(L, C, h):
        return C
    lo, hi = 0.0, C
    for _ in range(BISECT_STEPS):
        mid = (lo + hi) / 2
        if in_gamut(L, mid, h):
            lo = mid
        else:
            hi = mid
    return lo


def oklch_to_hex(L: float, C: float, h: float) -> str:
    C = fit_chroma(L, C, h)
    r, g, b = (_to_srgb(c) for c in _oklch_to_linear(L, C, h))
    return rgb_to_hex((r, g, b))


def lightness(value: str) -> float:
    """OKLCH lightness of a hex color: what survives a greyscale print."""
    return hex_to_oklch(value)[0]


def to_gray(value: str) -> str:
    """Same lightness, no hue: how the color reads on a black-and-white page."""
    return oklch_to_hex(lightness(value), 0.0, 0.0)


def relative_luminance(value: str) -> float:
    r, g, b = (_to_linear(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    """WCAG 2 contrast ratio between two colors."""
    a, b = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
