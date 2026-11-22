"""Exhibits drawn from the evidence, to be reused by the technical report.

    uv run python report/analysis.py
    uv run python report/figures.py <layout file> <output folder>

The language comes from the layout file the report's LaTeX writes, so the
English and Chinese versions show the same numbers.

Values quoted from the surveyed papers come from literature.json, each with
the location it was read from; our own checks come from data.json,
which analysis.py writes. Tables are written as pvtable sources with
pv.pvtable, so no number is typed into the paper by hand.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

import pubviz as pv
from pubviz.theme import FILL_LEVELS

HERE = Path(__file__).parent
DATA = json.loads((HERE / "data.json").read_text())
LIT = json.loads((HERE / "literature.json").read_text())

# Every word a figure or table shows, in Traditional Chinese. Names of
# colormaps and palettes that are proper names stay as they are.
ZH = {
    "95% CI bars": "95% 信賴區間", "SE bars": "標準誤", "correct, $p$ = .05": "正確位置，$p$ = .05",
    "Implied $p$": "隱含的 $p$ 值", "All": "全部", "Psychology": "心理學",
    "Behav. neurosci.": "行為神經科學", "Medicine": "醫學",
    "Truncated bar axis": "截斷長條圖的軸", "Stretched aspect ratio": "拉長長寬比",
    "Value as bubble area": "以泡泡面積表示數值",
    "Change in rating (five-point scale)": "評分變化（五點量表）",
    "pv figure": "pv 圖", "pv table": "pv 表格", "pv level": "pv 強度", "Position along the colormap": "在色階上的位置",
    "Lightness (OKLab $L$)": "明度（OKLab $L$）",
    "rainbow (HSV)": "彩虹（HSV）", "pubviz kinds": "pubviz 類別色",
    "Normal": "一般色覺", "Protanopia": "第一型色盲", "Deuteranopia": "第二型色盲", "Grey print": "灰階列印",
    "tint ": "混白 ", "fixed $L$ = ": "固定 $L$ = ",
    "Grey gap, best vs second ($L$ points)": "灰階差距，最佳與次佳（$L$ 點）",
    "Black-text contrast": "黑字對比",
    "Reversal": "回折", "Span": "範圍", "Unevenness (\\%)": "不均勻度（\\%）", "Black text": "黑字對比",
    "Rainbow": "彩虹", "Ordered": "有序", "Colormap": "色階",
    "Spread": "跨主色差異", "Grey gap": "灰階差距", "Contrast": "對比", "Fill design": "底色設計",
    "the level pubviz uses now": "pubviz 目前的設定",
}


def say(text: str) -> str:
    """``text`` in the language of the paper being built."""
    return text if pv.current().language == "en" else ZH.get(text, text)


def label(text: str) -> str:
    """Text drawn in a figure. matplotlib sets a whole label that contains
    $...$ in its math fonts, which have no Chinese characters, so Chinese
    labels drop the $ and set L and p upright."""
    out = say(text)
    return out if pv.current().language == "en" else out.replace("$", "")


HALF = 0.485  # of the text width, for two figures side by side
EXAMPLES = HERE.parent / "examples" / "figures"


def belia(out: Path) -> None:
    """Where researchers put two means to be 'just significantly different'."""
    implied = LIT["belia2005"]["implied_p"]
    tasks = ["95% CI bars", "SE bars"]
    from matplotlib.lines import Line2D

    fig, ax = pv.figure("text", ratio=0.26)
    handles = pv.bars(ax, {say(t): {say(group): v[t] for group, v in implied.items()} for t in tasks},
                      fmt="{:.3f}", ylabel=label("Implied $p$"), legend=False)
    style = {"color": "#8C8C8C", "linewidth": 0.8, "linestyle": (0, (3, 2))}
    ax.axhline(0.05, zorder=1, **style)
    ax.legend([*handles, Line2D([], [], **style)], [*map(say, tasks), label("correct, $p$ = .05")], loc="lower left",
              bbox_to_anchor=(0, 1.01), ncol=3, frameon=False, handlelength=1.4, borderaxespad=0)
    pv.save(fig, str(out / "belia"))


def pandey(out: Path) -> None:
    """How much each distortion raised the rated difference, with the interval
    of the change approximated from the two reported 95% intervals."""
    changes = {}
    for name, c in LIT["pandey2015"]["conditions"].items():
        (mc, lc, hc), (md, ld, hd) = c["control"], c["distorted"]
        half = math.hypot((hc - lc) / 2, (hd - ld) / 2)  # independent groups
        changes[say(name)] = (md - mc, md - mc - half, md - mc + half)
    fig, ax = pv.figure("text", ratio=0.2)
    pv.deltas(ax, changes, better="lower", fmt="{:+.2f}", xlabel=say("Change in rating (five-point scale)"))
    pv.save(fig, str(out / "pandey"))


SHORT = {"pubviz figure map": "pv figure", "pubviz table shading": "pv table", "pubviz level map": "pv level"}


def short(name: str) -> str:
    return say(SHORT.get(name, name))


def lightness(out: Path) -> None:
    maps = DATA["colormaps"]
    x = np.linspace(0, 1, 101)
    series = {short(k): np.array(v["lightness"]) for k, v in maps.items()}
    fig, ax = pv.figure(HALF, ratio=0.72)
    pv.curves(ax, x, series, ours=[say("pv figure"), say("pv table"), say("pv level")],
              xlabel=say("Position along the colormap"), ylabel=label("Lightness (OKLab $L$)"))
    ax.set_ylim(0, 100)
    pv.save(fig, str(out / "lightness"))


VISION = {"normal": "Normal", "protanopia": "Protanopia", "deuteranopia": "Deuteranopia", "grey print": "Grey print"}


def palettes(out: Path) -> None:
    rows = DATA["palettes"]
    values = [[row["min_difference"][v] for v in VISION] for row in rows.values()]
    fig, ax = pv.figure(HALF, ratio=0.62)
    pv.heatmap(ax, values, [say(r) for r in rows], [say(v) for v in VISION.values()], mark="column")
    # Four condition names do not fit side by side in half a text width, and
    # slanted ones still crowd each other, so they stand upright.
    for tick in ax.get_xticklabels():
        tick.set(rotation=90, ha="center")
    pv.save(fig, str(out / "palettes"))


# The fill level pubviz uses now, named as the fills check names it.
CURRENT = f"fixed L={FILL_LEVELS[0][0]:.2f}"


def design_label(name: str) -> str:
    return name.replace("fixed L=", say("fixed $L$ = ")).replace("tint ", say("tint "))


def fills_tradeoff(out: Path) -> None:
    designs = DATA["fills"]
    points = {label(design_label(k)): (v["min_gap"], v["min_contrast"]) for k, v in designs.items()}
    fig, ax = pv.figure(HALF, ratio=0.72)
    pv.tradeoff(ax, points, ours=label(design_label(CURRENT)), better_x="higher", better_y="higher",
                xlabel=label("Grey gap, best vs second ($L$ points)"), ylabel=say("Black-text contrast"))
    pv.save(fig, str(out / "fills"))


def tables(out: Path) -> None:
    maps = DATA["colormaps"]
    names = {m: say(n) for m, n in {"reversal": "Reversal", "span": "Span", "unevenness": "Unevenness (\\%)",
                                    "black_contrast": "Black text"}.items()}
    rows = {short(k): {names[m]: v[m] for m in names} for k, v in maps.items()}
    ours = [say("pv figure"), say("pv table"), say("pv level")]
    sections = {say("Rainbow"): ["jet", "turbo"], say("Ordered"): ["viridis", "magma", "Greys"], "pubviz": ours}
    tex = pv.pvtable(rows, ours=ours, lower=[names["reversal"], names["unevenness"]],
                     higher=[names["span"], names["black_contrast"]], sections=sections, corner=say("Colormap"),
                     options="heat=group, ranks=1, stretch=1.1", escape=False)
    (out / "colormaps.tex").write_text(tex + "\\pvkey\n")

    designs = DATA["fills"]
    pick = ["tint 30/10", "tint 40/15", "tint 60/25", "fixed L=0.85", "fixed L=0.90"]
    cols = {m: say(n) for m, n in {"spread": "Spread", "min_gap": "Grey gap", "min_contrast": "Contrast"}.items()}
    rows = {design_label(k): {cols[m]: designs[k][m] for m in cols} for k in pick}
    tex = pv.pvtable(rows, ours=design_label(CURRENT), baseline=design_label("tint 40/15"),
                     lower=[cols["spread"]], higher=[cols["min_gap"], cols["min_contrast"]],
                     corner=say("Fill design"), escape=False)
    key = f"\\pvkey[baseline={{{say('tint ')}40/15}}, ours={{{say('the level pubviz uses now')}}}]\n"
    (out / "fills.tex").write_text(tex + key)


def catalog(layout: str, out: Path) -> None:
    """Every example figure of the library, drawn by its own script at the
    width the report shows it: bars across the text, the rest half of it.
    The scripts read a layout file, so each gets one written for that width."""
    record = json.loads(Path(layout).read_text())
    target = out / "catalog"
    target.mkdir(parents=True, exist_ok=True)
    widths = {"full": record["textwidth_in"], "half": round(HALF * record["textwidth_in"], 4)}
    files = {}
    for name, width in widths.items():
        files[name] = target / f"{name}.pubviz.json"
        files[name].write_text(json.dumps(dict(record, columnwidth_in=width)))
    for script in sorted(EXAMPLES.glob("*.py")):
        size = "full" if script.stem == "bars" else "half"
        subprocess.run([sys.executable, str(script), str(files[size]), str(target)], check=True)


def main(layout: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    catalog(layout, out)
    pv.use(layout)
    belia(out)
    pandey(out)
    lightness(out)
    palettes(out)
    fills_tradeoff(out)
    tables(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
