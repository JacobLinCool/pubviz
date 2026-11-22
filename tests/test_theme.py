import pytest

from pubviz.color import contrast, hex_to_oklch, lightness
from pubviz.theme import PRESETS, Theme


@pytest.mark.parametrize("accent", list(PRESETS))
def test_fills_keep_their_order_in_gray(accent):
    # The promise of the theme: best is darker than second, second darker than
    # third, and the steps survive a black-and-white print.
    fills = [lightness(c) for c in Theme(accent).fills]
    assert fills[0] < fills[1] < fills[2] < 0.99
    assert fills[1] - fills[0] > 0.04
    assert fills[2] - fills[1] > 0.015


@pytest.mark.parametrize("accent", list(PRESETS))
def test_black_text_reads_on_every_fill(accent):
    theme = Theme(accent)
    for fill in theme.fills + theme.heat:
        # WCAG AAA for body text is 7:1.
        assert contrast("#000000", fill) >= 7


@pytest.mark.parametrize("accent", list(PRESETS))
def test_strong_is_visible_on_white(accent):
    assert contrast(Theme(accent).strong, "#FFFFFF") >= 3.0


def test_gray_mode_has_no_hue():
    theme = Theme("blue", "gray")
    for value in theme.roles.values():
        assert hex_to_oklch(value)[1] < 1e-3


@pytest.mark.parametrize("accent", list(PRESETS))
@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_others_stay_apart_from_ours(accent, n):
    for mode in ("color", "gray"):
        theme = Theme(accent, mode)
        ours = lightness(theme.ours)
        greys = [lightness(c) for c in theme.others(n)]
        assert all(abs(g - ours) >= 0.095 for g in greys)
        assert len(set(theme.others(n))) == n


def test_categorical_skips_accent_hue():
    assert "#0072B2" not in Theme("blue").categorical(4)
    assert "#E69F00" not in Theme("amber").categorical(4)


def test_heat_darkens_monotonically():
    heat = [lightness(c) for c in Theme().heat]
    assert all(a > b for a, b in zip(heat, heat[1:]))


def test_latex_line():
    assert Theme("blue", "gray").latex() == "\\pvsetup{accent=1A73D5, mode=gray}"


def test_hex_accent_without_hash():
    assert Theme("e4ae1a").accent == "#E4AE1A"
