import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import pubviz as pv

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples" / "figures"
KINDS = ["bars", "deltas", "curves", "tradeoff", "heatmap", "dots", "means", "distributions", "ranked", "scaling",
         "ratings", "confusion", "attention", "roc", "precision_recall", "det", "reliability", "images", "overlay",
         "spectrogram", "embedding"]


@pytest.fixture(autouse=True)
def setup():
    pv.use("icml", "blue")
    yield
    import matplotlib.pyplot as plt

    plt.close("all")


def pdf_fonts(path) -> list[bytes]:
    data = Path(path).read_bytes()
    return re.findall(rb"/Subtype\s*/(Type1|Type3|TrueType|Type0|CIDFontType2)", data)


def test_sizes_follow_the_venue():
    assert pv.width("column") == pytest.approx(3.25)
    assert pv.width("text") == pytest.approx(6.75)
    ctx = pv.use("acl")
    assert ctx.sizes["label"] == 9 and ctx.sizes["tick"] == 8
    ctx = pv.use("acm")
    assert ctx.sizes["label"] == 7 and ctx.sizes["small"] == 5


def test_layout_file_carries_the_theme(tmp_path):
    path = tmp_path / "main.pubviz.json"
    path.write_text('{"columnwidth_in": 3.3, "textwidth_in": 7.0, "font_size_pt": 9, "rmfamily": "ptm", '
                    '"accent": "#1A73D5", "mode": "gray", "pos": "#1D7D3E", "neg": "#BD3931"}')
    ctx = pv.use(path)
    assert ctx.layout.column == 3.3 and ctx.layout.family == "times"
    assert ctx.theme.accent == "#1A73D5" and ctx.theme.mode == "gray"


def test_each_figure_kind_saves_clean(tmp_path, capsys):
    scores = {"Base": {"A": 40.0, "B": 55.0}, "Prior": {"A": 52.0, "B": 60.0}, "Ours": {"A": 61.0, "B": 66.0}}
    rng = np.random.default_rng(0)
    steps = np.arange(50)
    kinds = {
        "bars": lambda ax: pv.bars(ax, scores, ours="Ours", ylabel="Accuracy (%)"),
        "deltas": lambda ax: pv.deltas(ax, {"no X": -2.1, "no Y": (-0.4, -1.2, 0.5), "Ours": 1.3},
                                       ours="Ours", xlabel="Accuracy change (points)"),
        "curves": lambda ax: pv.curves(ax, steps, {"Base": rng.normal(0, 0.02, (3, 50)) + np.log1p(steps) / 5,
                                                   "Ours": rng.normal(0, 0.02, (3, 50)) + np.log1p(steps) / 4},
                                       ours="Ours", xlabel="Step", ylabel="Reward"),
        "tradeoff": lambda ax: pv.tradeoff(ax, {"A": (10, 60), "B": (20, 64), "C": (30, 61), "Ours": (12, 66)},
                                           ours="Ours", xlabel="Latency (ms)", ylabel="Accuracy (%)"),
        "heatmap": lambda ax: pv.heatmap(ax, [[1, 2], [3, 4]], ["r1", "r2"], ["c1", "c2"], mark="column"),
    }
    for name, draw in kinds.items():
        fig, ax = pv.figure("column")
        draw(ax)
        problems = pv.style.check(fig)
        assert problems == [], (name, problems)
        (path,) = pv.save(fig, str(tmp_path / name))
        fonts = pdf_fonts(path)
        assert b"Type3" not in fonts, (name, fonts)


def test_check_flags_wrong_width():
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.0, 3.0))  # not built with pv.figure
    assert any("width" in p for p in pv.style.check(fig))
    fig, ax = pv.figure("column")
    fig.set_size_inches(6.0, 3.0)  # resized after the fact
    assert any("width changed" in p for p in pv.style.check(fig))


def test_fraction_of_text_width_is_accepted():
    fig, ax = pv.figure(0.5)  # a subfigure at half the text width
    assert fig.get_size_inches()[0] == pytest.approx(6.75 / 2)
    assert not any("width" in p for p in pv.style.check(fig))


def test_pareto():
    front = pv.pareto([1, 2, 3, 4], [1, 3, 2, 4])
    assert front == [0, 1, 3]


def test_mean_ci_single_seed_is_a_line():
    mean, lo, hi = pv.mean_ci(np.ones((1, 5)))
    assert np.all(lo == hi)


def test_mean_ci_of_per_seed_numbers():
    # Five seeds of one number: the half width is t(4) = 2.776 times the standard error.
    mean, lo, hi = pv.mean_ci([1.0, 2.0, 3.0, 2.0, 2.0])
    assert np.ndim(mean) == 0 and mean == pytest.approx(2.0)
    assert hi - mean == pytest.approx(2.776 * np.sqrt(0.5) / np.sqrt(5))


def test_body_font_registers_tex_fonts():
    ctx = pv.use("lncs", font="body")
    import matplotlib as mpl

    # The body face comes first; CJK fallback fonts, if installed, follow it.
    assert mpl.rcParams["font.family"][0] == "serif"
    assert ctx.layout.family == "cm"


def test_every_figure_kind_has_an_example():
    assert sorted(p.stem for p in EXAMPLES.glob("*.py")) == sorted(KINDS)


@pytest.mark.parametrize("kind", KINDS)
def test_example_saves_clean(kind, tmp_path):
    # acm has the smallest body text (9 pt), so its figure text sits nearest the 5 pt floor.
    result = subprocess.run([sys.executable, str(EXAMPLES / f"{kind}.py"), "acm", str(tmp_path)],
                            capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "pubviz:" not in result.stderr, result.stderr  # save() reports each problem it finds
    fonts = pdf_fonts(tmp_path / f"{kind}.pdf")
    assert fonts and b"Type3" not in fonts


@pytest.mark.parametrize("kind", KINDS)
def test_guide_shows_every_example(kind):
    guide = (ROOT / "docs" / "guide.md").read_text()
    assert f"(../examples/figures/{kind}.py)" in guide
    assert f"(img/fig-{kind}.png)" in guide and (ROOT / "docs" / "img" / f"fig-{kind}.png").exists()


def test_language_comes_from_the_layout_file(tmp_path):
    record = {"columnwidth_in": 3.49, "textwidth_in": 7.14, "font_size_pt": 10, "rmfamily": "ptm",
              "language": "zh-tw"}
    path = tmp_path / "paper.pubviz.json"
    path.write_text(json.dumps(record))
    assert pv.use(str(path)).language == "zh-tw"
    assert pv.use("ieee").language == "en"
    with pytest.raises(ValueError):
        pv.use("ieee", language="fr")
    # A language defined in LaTeX reaches the figures through the layout file.
    record.update(language="de", words={"better": "besser", "worse": "schlechter", "crosses_zero": "kreuzt null"})
    path.write_text(json.dumps(record))
    said = pv.use(str(path)).words
    assert {k: said[k] for k in ("better", "worse", "crosses")} == {"better": "besser", "worse": "schlechter",
                                                                   "crosses": "kreuzt null"}
    # Axis titles a kind writes by default fall back to English for such a language.
    assert said["true"] == "True class"
    # Without a layout file, a language without a built-in set needs its words.
    words = {"better": "mieux", "worse": "pire", "crosses": "croise zéro", "true": "Classe réelle"}
    said = pv.use("ieee", language="fr", words=words).words
    assert {k: said[k] for k in words} == words


def test_cjk_characters_fall_back_to_the_language_font_first():
    from pubviz.style import cjk_fallbacks

    installed = {"PingFang TC", "PingFang SC", "Hiragino Sans", "Apple SD Gothic Neo", "Heiti TC"}
    assert cjk_fallbacks("ja", installed) == ["Hiragino Sans", "PingFang TC", "PingFang SC", "Apple SD Gothic Neo"]
    assert cjk_fallbacks("en", installed)[0] == "PingFang TC"
    assert cjk_fallbacks("ko", {"Heiti TC"}) == ["Heiti TC"]


def test_chinese_axis_labels_stay_out_of_the_math_fonts():
    # matplotlib sets a label holding $...$ in its math fonts, which have no
    # Chinese characters, so the better-direction arrow is a plain character.
    pv.use("icml", language="zh-tw")
    fig, ax = pv.figure("column")
    pv.tradeoff(ax, {"甲": (1.0, 2.0), "乙": (2.0, 1.0)}, better_x="higher", xlabel="差距", ylabel="對比")
    assert ax.get_xlabel() == "差距 ↑" and ax.get_ylabel() == "對比 ↑"
    pv.use("icml")
    fig, ax = pv.figure("column")
    pv.tradeoff(ax, {"a": (1.0, 2.0), "b": (2.0, 1.0)}, better_x="higher", xlabel="gap")
    assert ax.get_xlabel() == r"gap $\uparrow$"


def test_deltas_key_names_only_the_colors_drawn():
    fig, ax = pv.figure("column")
    pv.deltas(ax, {"a": (1.0, 0.5, 1.5), "b": (-1.0, -1.5, -0.5), "c": (0.2, -0.3, 0.7)})
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["better", "worse", "interval crosses zero"]
    fig, ax = pv.figure("column")
    pv.deltas(ax, {"a": 1.0, "b": 2.0}, better="lower")
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["worse"]
    fig, ax = pv.figure("column")
    pv.deltas(ax, {"a": 1.0}, key=False)
    assert ax.get_legend() is None
    # The words follow the language passed on from pubviz.sty.
    pv.use("icml", language="zh-tw")
    fig, ax = pv.figure("column")
    pv.deltas(ax, {"a": (1.0, 0.5, 1.5), "b": (-1.0, -1.5, -0.5), "c": (0.2, -0.3, 0.7)})
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["較好", "較差", "區間跨過零"]
    # In grey the three colors look alike, so a key would explain nothing.
    pv.use("icml", pv.Theme("blue", "gray"))
    fig, ax = pv.figure("column")
    pv.deltas(ax, {"a": 1.0, "b": -1.0})
    assert ax.get_legend() is None


def test_dots_draw_every_run_and_print_the_mean():
    fig, ax = pv.figure("column")
    pv.dots(ax, {"Ours": [1.0, 1.0, 1.0, 2.0], "Base": [0.5, 0.7]}, ours="Ours")
    xs = np.concatenate([line.get_xdata() for line in ax.lines if line.get_marker() == "o"])
    assert sorted(xs) == [0.5, 0.7, 1.0, 1.0, 1.0, 2.0]
    # Equal runs do not hide each other: they move to different heights.
    ys = [y for line in ax.lines if line.get_marker() == "o" for x, y in zip(line.get_xdata(), line.get_ydata()) if x == 1.0]
    assert len(set(ys)) == 3
    texts = [t.get_text() for t in ax.texts]
    assert "1.2" in texts and "0.6" in texts
    assert [t.get_fontweight() for t in ax.texts if t.get_text() == "1.2"] == ["bold"]


def test_means_take_runs_or_estimates():
    fig, ax = pv.figure("column")
    est = pv.means(ax, {"runs": [1.0, 2.0, 3.0], "given": (5.0, 4.0, 6.0)})
    m, lo, hi = pv.mean_ci([1.0, 2.0, 3.0])
    assert est["runs"] == pytest.approx((m, lo, hi)) and est["given"] == (5.0, 4.0, 6.0)
    fig, ax = pv.figure("column")
    pv.means(ax, {"a": (5.0, 4.0, 6.0)}, show="gradient")
    shades = ax.collections[0].get_facecolors()[:, 3]
    # Full inside the interval, fading outside it.
    assert shades.max() == pytest.approx(0.85) and shades.min() < 0.05
    with pytest.raises(ValueError):
        pv.means(ax, {"a": (1.0, 2.0)})
    # Runs are drawn under the estimate unless asked not to; a tuple has none.
    runs = {"a": [1.0, 2.0, 3.0, 4.0], "b": (5.0, 4.0, 6.0)}
    fig, ax = pv.figure("column")
    pv.means(ax, runs)
    faint = [line for line in ax.lines if line.get_marker() == "o" and line.get_alpha() == 0.45]
    assert len(faint) == 1 and len(faint[0].get_xdata()) == 4
    fig, ax = pv.figure("column")
    pv.means(ax, runs, points=False)
    assert not [line for line in ax.lines if line.get_alpha() == 0.45]


@pytest.mark.parametrize("kind", ["box", "strip", "violin", "histogram"])
def test_distributions_warn_on_few_runs(kind):
    rng = np.random.default_rng(0)
    fig, ax = pv.figure("column")
    with pytest.warns(UserWarning, match="draw every run"):
        pv.distributions(ax, {"many": rng.normal(0, 1, 200), "few": [0.1, 0.2, 0.3]}, kind=kind)
    # The median of each method is printed at the end of its row.
    assert "0.2" in [t.get_text() for t in ax.texts]


def test_box_with_points_draws_each_run_once():
    rng = np.random.default_rng(1)
    data = {"a": np.concatenate([rng.normal(0, 1, 60), [9.0, 10.0]])}
    fig, ax = pv.figure("column")
    pv.distributions(ax, data, kind="box", points=True)
    drawn = sum(len(line.get_xdata()) for line in ax.lines if line.get_marker() == "o")
    assert drawn == 62  # the runs as points; no separate outlier dots on top


def test_check_reports_texts_that_overlap_or_run_off():
    fig, ax = pv.figure("column")
    ax.plot([0, 1], [0, 1])
    ax.text(0.5, 0.5, "first label")
    ax.text(0.5, 0.5, "second label")
    ax.text(1.4, 0.5, "far outside")
    problems = pv.style.check(fig)
    assert any(p.startswith("texts overlap") for p in problems)
    assert any(p.startswith("text runs off the figure") for p in problems)


def test_deltas_fit_a_narrow_width():
    # Long names, negative changes and the three-entry key in a 2.4 in panel.
    fig, ax = pv.figure(2.4, ratio=0.7)
    pv.deltas(ax, {"without data mixing": (-3.3, -3.9, -2.6), "larger batch": (0.8, 0.4, 1.2),
                   "without warm-up": (0.2, -0.3, 0.7)})
    assert pv.style.check(fig) == []


@pytest.mark.parametrize("names", [("a", "b", "c"), ("without data mixing", "larger batch", "without warm-up")])
def test_deltas_key_leaves_the_plot_its_width(names):
    # A key wider than the plot reaches over the row names instead of making
    # the layout narrow the plot, which can collapse it to nothing.
    data = dict(zip(names, [(-3.3, -3.9, -2.6), (0.8, 0.4, 1.2), (0.2, -0.3, 0.7)]))
    widths = []
    for key in (False, True):
        fig, ax = pv.figure(2.4, ratio=0.7)
        pv.deltas(ax, data, key=key)
        fig.canvas.draw()
        widths.append(ax.get_window_extent().width)
    assert widths[1] >= 0.97 * widths[0], widths
    legend = ax.get_legend().get_window_extent()
    assert fig.bbox.x0 <= legend.x0 and legend.x1 <= fig.bbox.x1 + 0.5
