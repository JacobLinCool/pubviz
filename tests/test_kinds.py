"""What each figure kind for classes, ratings, scale, pictures and sound computes and draws."""

import math
from statistics import NormalDist

import numpy as np
import pytest

import pubviz as pv


@pytest.fixture(autouse=True)
def setup():
    pv.use("icml", "blue")
    yield
    import matplotlib.pyplot as plt

    plt.close("all")


def texts(ax) -> list[str]:
    return [t.get_text() for t in ax.texts]


# ---- matrices -------------------------------------------------------------------


def test_confusion_shows_row_shares_on_a_fixed_scale():
    fig, ax = pv.figure("column")
    image = pv.confusion(ax, [[8, 2], [1, 3]], ["a", "b"], values="share")
    assert image.get_clim() == (0.0, 1.0)
    assert texts(ax) == ["80", "20", "25", "75"]
    # The correct predictions are outlined and in bold.
    assert len(ax.patches) == 2
    assert [t.get_fontweight() for t in ax.texts] == ["bold", "normal", "normal", "bold"]
    assert ax.get_xlabel() == "Predicted class" and ax.get_ylabel() == "True class"
    assert pv.style.check(fig) == []


def test_confusion_by_column_and_counts():
    fig, ax = pv.figure("column")
    pv.confusion(ax, [[8, 2], [2, 3]], ["a", "b"], normalize="column", values="both")
    assert texts(ax)[0] == "80\n(8)"
    fig, ax = pv.figure("column")
    image = pv.confusion(ax, [[8, 0], [2, 3]], ["a", "b"], normalize="none")
    assert image.get_clim() == (0.0, 8.0) and texts(ax) == ["8", "\u2013", "2", "3"]
    # Both numbers by default for a few classes, the share alone for many.
    fig, ax = pv.figure("column")
    pv.confusion(ax, [[8, 2], [2, 3]], ["a", "b"])
    assert texts(ax)[0] == "80\n(8)"
    fig, ax = pv.figure("column")
    pv.confusion(ax, np.eye(7) * 5 + 1, list("abcdefg"))
    assert "\n" not in texts(ax)[0]
    with pytest.raises(ValueError):
        pv.confusion(ax, [[1, 2, 3]], ["a", "b"])


def test_confusion_turns_labels_only_when_crowded():
    fig, ax = pv.figure("column")
    pv.confusion(ax, np.eye(3), ["a", "b", "c"])
    assert all(t.get_rotation() == 0 for t in ax.get_xticklabels())
    names = [f"a rather long class name {i}" for i in range(6)]
    fig, ax = pv.figure("column")
    pv.confusion(ax, np.eye(6), names)
    assert all(t.get_rotation() == 45 for t in ax.get_xticklabels())


def test_attention_names_every_few_items_of_a_long_sequence():
    fig, ax = pv.figure("column")
    pv.attention(ax, np.random.default_rng(0).random((5, 100)), [f"t{i}" for i in range(100)],
                 [f"o{i}" for i in range(5)], most=20)
    assert len(ax.get_xticks()) == 20 and len(ax.get_yticks()) == 5
    assert len(ax.texts) == 0  # no numbers: the pattern is the point
    with pytest.raises(ValueError):
        pv.attention(ax, np.ones((2, 3)), ["a", "b"])


# ---- classifier curves ------------------------------------------------------------


def separated(n=4000, gap=2.0, share=0.1, seed=0):
    rng = np.random.default_rng(seed)
    labels = rng.random(n) < share
    return labels, rng.normal(0, 1, n) + gap * labels


def test_roc_area_matches_the_normal_model():
    labels, scores = separated(20000, gap=1.5, share=0.5)
    _, _, area = pv.classifiers.rates(labels, scores)
    # For two unit normals a gap d apart, AUC = Phi(d / sqrt 2).
    assert area == pytest.approx(NormalDist().cdf(1.5 / math.sqrt(2)), abs=0.01)
    perfect = pv.classifiers.rates([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])[2]
    assert perfect == 1.0


def test_roc_draws_the_chance_line_and_prints_the_area():
    fig, ax = pv.figure("column", ratio=0.9)
    shown = pv.roc(ax, {"Ours": separated(gap=2.5), "Base": separated(gap=1.0)}, ours="Ours")
    entries = [t.get_text() for t in ax.get_legend().get_texts()]
    assert entries[0].startswith("Ours (AUC 0.9") and entries[-1] == "chance"
    assert shown["Ours"] > shown["Base"]
    assert pv.style.check(fig) == []


def test_precision_recall_baseline_is_the_share_of_positives():
    labels, scores = separated(gap=2.0, share=0.1)
    fig, ax = pv.figure("column", ratio=0.9)
    pv.precision_recall(ax, {"Ours": (labels, scores)}, ours="Ours")
    dashed = [line for line in ax.lines if line.get_linestyle() == "--"]
    assert dashed and dashed[0].get_ydata()[0] == pytest.approx(labels.mean(), abs=1e-6)
    # A perfect ranking has average precision 1.
    assert pv.precision_recall(ax, {"p": ([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])})["p"] == "AP 1.000"


def test_det_equal_error_rate_matches_the_normal_model():
    rng = np.random.default_rng(2)
    target = np.r_[np.ones(20000), np.zeros(20000)]
    scores = rng.normal(0, 1, 40000) + 3.0 * target
    fig, ax = pv.figure("column", ratio=0.9)
    eer = pv.det(ax, {"s": (target, scores)})["s"]
    # Two unit normals 3 apart cross at 1.5: EER = Phi(-1.5).
    assert eer == pytest.approx(NormalDist().cdf(-1.5), abs=0.005)
    assert [t.get_text() for t in ax.get_xticklabels()][:3] == ["0.1", "0.2", "0.5"]


def test_reliability_of_a_calibrated_model_is_near_zero():
    rng = np.random.default_rng(3)
    p = rng.random(50000)
    labels = rng.random(50000) < p
    fig, (ax, counts) = pv.figure("column", ratio=1.1, nrows=2, height_ratios=[3, 1], sharex=True)
    shown = pv.reliability(ax, {"cal": (labels, p), "over": (labels, np.sqrt(p))}, counts_ax=counts)
    assert float(shown["cal"].split()[1]) < 0.01 < float(shown["over"].split()[1])
    assert len(counts.patches) == 20 and counts.get_ylabel() == "Cases"


def test_curves_need_both_classes():
    fig, ax = pv.figure("column")
    with pytest.raises(ValueError, match="both classes"):
        pv.roc(ax, {"a": ([1, 1], [0.2, 0.3])})


# ---- ratings ----------------------------------------------------------------------


def test_ratings_put_each_side_of_the_scale_on_its_side_of_zero():
    fig, ax = pv.figure("column", ratio=0.4)
    shares = pv.ratings(ax, {"A": [10, 10, 20, 30, 30]}, ["1", "2", "3", "4", "5"])
    assert shares["A"].sum() == pytest.approx(100)
    bars = [(p.get_x(), p.get_width()) for p in ax.patches]
    # Negative answers end at minus half the neutral share, positive ones start at plus half.
    assert min(x for x, _ in bars) == pytest.approx(-30)
    assert max(x + w for x, w in bars) == pytest.approx(70)
    assert {"20", "60"} <= set(texts(ax))
    assert pv.style.check(fig) == []


def test_ratings_set_the_neutral_answer_aside():
    fig, ax = pv.figure("column", ratio=0.4)
    pv.ratings(ax, {"vs A": {"loss": 1, "tie": 2, "win": 1}}, ["loss", "tie", "win"], neutral="aside")
    xs = sorted(p.get_x() for p in ax.patches)
    assert xs[0] == pytest.approx(-25) and xs[1] == 0 and xs[2] > 25
    assert all(t <= 30 for t in ax.get_xticks())
    with pytest.raises(ValueError):
        pv.ratings(ax, {"a": [1, 2]}, ["x", "y", "z"])


# ---- many items and scale ---------------------------------------------------------------


def test_ranked_sorts_rows_by_ours():
    fig, ax = pv.figure("column")
    items = pv.ranked(ax, {"a": {"Ours": 1, "B": 5}, "b": {"Ours": 3, "B": 0}, "c": {"Ours": 2, "B": 1}}, ours="Ours")
    assert items == ["b", "c", "a"]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["b", "c", "a"]
    fig, ax = pv.figure("column")
    assert pv.ranked(ax, {"a": 1, "b": 3}, better="lower") == ["a", "b"]
    with pytest.raises(ValueError, match="too many"):
        pv.ranked(ax, {"a": {str(i): i for i in range(9)}})


def test_scaling_fits_on_the_chosen_points_and_hollows_the_rest():
    x = np.array([1e6, 1e7, 1e8, 1e9])
    y = 3.0 * x ** -0.1
    y[-1] *= 1.2  # the held-out point misses the trend
    fig, ax = pv.figure("column")
    fits = pv.scaling(ax, {"m": (x, y)}, upto=1e8, extend=1e10)
    a, b = fits["m"]
    assert a == pytest.approx(3.0) and b == pytest.approx(-0.1)
    hollow = [line for line in ax.lines if line.get_markerfacecolor() == "white"]
    assert len(hollow) == 1 and list(hollow[0].get_xdata()) == [1e9]
    dashed = [line for line in ax.lines if line.get_linestyle() == "--"]
    assert dashed and dashed[0].get_xdata()[-1] == pytest.approx(1e10)
    assert ax.get_xscale() == "log" and ax.get_yscale() == "log"


# ---- pictures and sound -------------------------------------------------------------


def test_images_lay_out_a_grid_with_the_same_zoom_under_each():
    rng = np.random.default_rng(0)
    img = rng.random((30, 40, 3))
    fig, axes = pv.images({"r1": {"In": img, "Ours": img}, "r2": {"In": img, "Ours": img}}, ours="Ours",
                          zoom=(5, 5, 10, 5))
    assert axes.shape == (2, 2) and len(fig.axes) == 8  # each image and its crop
    assert pv.style.check(fig) == []
    names = [t for t in axes[0, 1].texts if t.get_text() == "Ours"]
    assert names and names[0].get_fontweight() == "bold"
    with pytest.raises(ValueError, match="same size"):
        pv.images({"a": img, "b": img[:10]})
    # An error row: the difference from the reference under every other image.
    fig, axes = pv.images({"In": img, "Ours": img * 0.5, "Ref": img}, error="Ref")
    assert len(fig.axes) == 6
    err = fig.axes[2].images[0]
    assert err.get_clim()[1] == pytest.approx(float(np.abs(img - img * 0.5).mean(axis=-1).max()), rel=0.2)
    with pytest.raises(ValueError, match="reference"):
        pv.images({"In": img, "Ours": img}, error="GT")


def test_overlay_fades_low_weights_out():
    fig, ax = pv.figure("column")
    shown = pv.overlay(ax, np.ones((4, 4, 3)), np.array([[0.0, 1.0], [0.5, 0.25]]), alpha=0.8, colorbar=False)
    alpha = shown.get_array()[..., 3]
    assert alpha.min() == 0 and alpha.max() == pytest.approx(0.8)
    # A signed map: opacity by size, and the two signs in different hues.
    fig, ax = pv.figure("column")
    shown = pv.overlay(ax, np.ones((4, 4, 3)), np.array([[-1.0, 1.0], [0.0, 0.5]]), colorbar=False)
    rgba = shown.get_array()
    assert rgba[0, 0, 3] == pytest.approx(rgba[0, 1, 3]) and rgba[1, 0, 3] == 0
    assert not np.allclose(rgba[0, 0, :3], rgba[0, 1, :3])


def test_spectrogram_from_audio_and_from_a_given_level():
    sr = 16000
    t = np.arange(sr // 2) / sr
    audio = np.sin(2 * np.pi * 1000 * t)
    fig, ax = pv.figure("column")
    image = pv.spectrogram(ax, audio, sr)
    data = image.get_array()
    # Floor at -80 dB, loudest bin at 0, and the tone in the bin nearest 1 kHz.
    assert data.min() == -80 and data.max() == 0
    n_fft = data.shape[0] * 2 - 2
    assert int(np.argmax(data[:, 5])) == round(1000 / (sr / n_fft))
    fig, ax = pv.figure("column")
    image = pv.spectrogram(ax, sr=22050, level=np.random.default_rng(0).normal(-30, 5, (80, 200)), hop=256, mel=80)
    assert image.get_extent()[1] == pytest.approx(200 * 256 / 22050)
    assert pv.pictures.mel_filters(16000, 512, 40).shape == (40, 257)


def test_embedding_folds_small_classes_into_other():
    rng = np.random.default_rng(0)
    labels = [f"c{i}" for i in range(12) for _ in range(20 - i)]
    points = rng.normal(0, 1, (len(labels), 2))
    fig, ax = pv.figure("column")
    with pytest.warns(UserWarning, match="Other"):
        colors = pv.embedding(ax, points, labels)
    assert "Other" in colors and "c0" in colors and "c11" not in colors
    assert "Other" not in texts(ax)  # it gathers several clusters, so the legend names it
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["Other"]


def test_default_labels_follow_the_language():
    pv.use("icml", "blue", language="zh-tw")
    fig, ax = pv.figure("column")
    pv.confusion(ax, np.eye(2), ["甲", "乙"])
    assert ax.get_ylabel() == "真實類別"
    # A language without built-in labels falls back to English ones.
    pv.use("icml", "blue", language="xx", words={"better": "b", "worse": "w", "crosses": "c"})
    assert pv.current().say("recall") == "Recall"


# ---- token shading ---------------------------------------------------------------------


def test_pvshade_scales_weights_and_escapes_tokens():
    assert pv.pvshade(["a", "b"], [1.0, 4.0]) == "\\pvshade{0.25}{a} \\pvshade{1.00}{b}\n"
    signed = pv.pvshade(["x_1", "$"], [-2.0, 1.0], join="")
    assert signed == "\\pvshade*{-1.00}{x\\_1}\\pvshade*{0.50}{\\$}\n"
    assert pv.pvshade(["a"], [0.5], scale=2.0) == "\\pvshade{0.25}{a}\n"
    with pytest.raises(ValueError):
        pv.pvshade(["a"], [1.0, 2.0])


def test_a_wrapped_legend_reads_row_by_row():
    from pubviz.plots import _row_major

    # matplotlib fills legend columns top to bottom; the entries are reordered
    # so that reading across each row gives the scale in order.
    assert _row_major(list("ABCDE"), 4) == ["A", "E", "B", "C", "D"]
    assert _row_major(list("ABCDE"), 3) == ["A", "D", "B", "E", "C"]
    fig, ax = pv.figure(1.6, ratio=0.8)
    levels = ["Bad", "Poor", "Fair", "Good", "Excellent"]
    pv.ratings(ax, {"A": [1, 2, 3, 4, 5]}, levels)
    legend = ax.get_legend()
    fig.canvas.draw()
    texts = legend.get_texts()
    # Sort the entries by row (top first), then by position in the row.
    placed = sorted(texts, key=lambda t: (-round(t.get_window_extent().y0), t.get_window_extent().x0))
    assert [t.get_text() for t in placed] == levels


# ---- sections: a second level of grouping ----------------------------------------------


def section_bands(ax):
    return [p for p in ax.patches if p.get_zorder() == 0]


def test_sections_group_rows_with_a_gap_a_name_and_bands():
    runs = {"A": [1.0, 2.0], "B": [2.0, 3.0], "C": [3.0, 4.0]}
    fig, ax = pv.figure("column")
    pv.means(ax, runs, sections={"Prior": ["A"], "Ours": ["C", "B"]})
    names = [t.get_text() for t in ax.get_yticklabels()]
    ys = dict(zip(names, ax.get_yticks()))
    # Sections in the order given, top to bottom, with a gap between them.
    assert ys["A"] > ys["C"] > ys["B"]
    assert ys["C"] - ys["B"] == pytest.approx(1.0)
    assert ys["A"] - ys["C"] == pytest.approx(1.0 + pv.plots.SECTION_GAP)
    heads = [t for t in ax.texts if t.get_text() in ("Prior", "Ours")]
    assert len(heads) == 2 and all(t.get_fontweight() == "bold" for t in heads)
    assert len(section_bands(ax)) == 2  # by default every section has its band
    assert pv.style.check(fig) == []
    for band, count in (("alternate", 1), (None, 0)):
        fig, ax = pv.figure("column")
        pv.dots(ax, runs, sections={"Prior": ["A"], "Ours": ["B", "C"]}, band=band)
        assert len(section_bands(ax)) == count


def test_sections_must_list_every_name_once():
    fig, ax = pv.figure("column")
    with pytest.raises(ValueError, match="missing: B"):
        pv.dots(ax, {"A": [1.0], "B": [2.0]}, sections={"x": ["A"]})
    with pytest.raises(ValueError, match="twice: A"):
        pv.dots(ax, {"A": [1.0], "B": [2.0]}, sections={"x": ["A", "B"], "y": ["A"]})
    with pytest.raises(ValueError, match="not in the data: Z"):
        pv.dots(ax, {"A": [1.0], "B": [2.0]}, sections={"x": ["A", "B", "Z"]})


def test_deltas_and_ranked_sort_within_each_section():
    fig, ax = pv.figure("column")
    pv.deltas(ax, {"a": 1.0, "b": 3.0, "c": -1.0, "d": 2.0}, sections={"S1": ["a", "b"], "S2": ["c", "d"]})
    assert [t.get_text() for t in ax.get_yticklabels()] == ["b", "a", "d", "c"]
    fig, ax = pv.figure("column")
    items = pv.ranked(ax, {"x": 1, "y": 5, "z": 3, "w": 4}, sections={"G1": ["x", "y"], "G2": ["z", "w"]})
    assert items == ["y", "x", "w", "z"]


def test_bars_group_benchmarks_into_sections():
    scores = {"Base": {"a": 1, "b": 2, "c": 3}, "Ours": {"a": 2, "b": 3, "c": 4}}
    fig, ax = pv.figure("column")
    pv.bars(ax, scores, ours="Ours", sections={"First": ["c"], "Second": ["a", "b"]})
    assert [t.get_text() for t in ax.get_xticklabels()] == ["c", "a", "b"]
    assert list(ax.get_xticks()) == pytest.approx([0.0, 1.0 + pv.plots.SECTION_GAP, 2.0 + pv.plots.SECTION_GAP])
    assert {t.get_text() for t in ax.texts} >= {"First", "Second"}
    assert pv.style.check(fig) == []


def test_section_member_pairs_give_the_sections_and_repeat_names():
    runs = {("Prior", "3 passes"): [1.0, 2.0, 3.0], ("Ours", "1 pass"): [2.0, 3.0, 4.0],
            ("Ours", "3 passes"): [3.0, 4.0, 5.0]}
    fig, ax = pv.figure("column")
    pv.means(ax, runs, ours=("Ours", "3 passes"))
    labels = ax.get_yticklabels()
    assert [t.get_text() for t in labels] == ["3 passes", "1 pass", "3 passes"]
    assert [t.get_fontweight() for t in labels] == ["normal", "normal", "bold"]
    assert {t.get_text() for t in ax.texts} >= {"Prior", "Ours"}


def test_bars_values_stand_upright_when_crowded():
    scores = {m: {f"bench {i}": 50.0 + i + k for i in range(6)} for k, m in enumerate(["A", "B", "C", "D"])}
    fig, ax = pv.figure(2.5, ratio=0.6)
    pv.bars(ax, scores, legend=False)
    assert all(t.get_rotation() == 90 for t in ax.texts if t.get_text())
    fig, ax = pv.figure("text", ratio=0.3)
    pv.bars(ax, {"A": {"x": 1.0, "y": 2.0}}, legend=False)
    assert all(t.get_rotation() == 0 for t in ax.texts if t.get_text())
