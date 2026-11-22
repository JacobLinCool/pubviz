import math

import pytest

from pubviz.color import contrast, fit_chroma, hex_to_oklch, in_gamut, lightness, oklch_to_hex, to_gray


def test_white_and_black():
    assert hex_to_oklch("#FFFFFF")[0] == pytest.approx(1.0, abs=1e-4)
    assert hex_to_oklch("#000000")[0] == pytest.approx(0.0, abs=1e-6)
    assert hex_to_oklch("#FFFFFF")[1] == pytest.approx(0.0, abs=1e-4)


def test_known_red():
    # Reference value from the OKLab definition (Ottosson, 2020).
    L, C, h = hex_to_oklch("#FF0000")
    assert L == pytest.approx(0.6280, abs=1e-3)
    assert C == pytest.approx(0.2577, abs=1e-3)
    assert math.degrees(h) == pytest.approx(29.23, abs=0.1)


@pytest.mark.parametrize("value", ["#E4AE1A", "#1A73D5", "#009A9A", "#101010", "#F8DC8C", "#808080"])
def test_round_trip(value):
    assert oklch_to_hex(*hex_to_oklch(value)) == value


def test_out_of_gamut_keeps_lightness():
    # Very saturated blue at high lightness cannot be shown; chroma drops, lightness stays.
    h = math.radians(260)
    assert not in_gamut(0.9, 0.2, h)
    c = fit_chroma(0.9, 0.2, h)
    assert 0 < c < 0.2 and in_gamut(0.9, c, h)
    assert lightness(oklch_to_hex(0.9, 0.2, h)) == pytest.approx(0.9, abs=3e-3)


def test_gray_keeps_lightness():
    for value in ["#E4AE1A", "#1A73D5", "#DA4339"]:
        assert lightness(to_gray(value)) == pytest.approx(lightness(value), abs=3e-3)
        assert hex_to_oklch(to_gray(value))[1] < 1e-3


def test_contrast():
    assert contrast("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast("#777777", "#777777") == pytest.approx(1.0)
