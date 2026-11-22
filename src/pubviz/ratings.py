"""Human judgments on an ordered scale.

- ``ratings``  How people's answers spread over a rating scale (a Likert
  item, a five-point quality score, or win / tie / loss against another
  system), as diverging stacked bars centered on the neutral answer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import matplotlib as mpl
import numpy as np

from .plots import EDGE, TEXT, _fit_legend, _fit_rows, _is_ours, _keep_inside, _rows
from .style import current

NEUTRAL_LIGHTNESS = 0.86


def _level_colors(n_side: int, has_neutral: bool) -> tuple[list[str], list[str], str]:
    """Colors of the levels below the neutral one (strongest first), above it
    (weakest first), and of the neutral one. The darkest step stays light
    enough for a printed share to be read on it."""
    theme = current().theme
    cmap = theme.diverging()
    steps = [0.30 + 0.62 * (k + 1) / n_side for k in range(n_side)]  # weakest to strongest, 0..1 from center
    neg = [mpl.colors.to_hex(cmap(0.5 - s / 2)) for s in reversed(steps)]
    pos = [mpl.colors.to_hex(cmap(0.5 + s / 2)) for s in steps]
    return neg, pos, theme.grey(NEUTRAL_LIGHTNESS)


def ratings(ax, data: Mapping, levels: Sequence[str], *, ours=None, neutral: str = "split",
            values: bool = True, fmt: str = "{:.0f}", xlabel: str | None = None, legend: bool = True,
            sections=None, band: str | None = "all"):
    """Diverging stacked bars: one bar per system (or question), one segment
    per answer, as a share of that bar's answers.

    ``levels`` names the answers from the worst to the best, such as
    ``["Bad", "Poor", "Fair", "Good", "Excellent"]`` or ``["Loss", "Tie",
    "Win"]``. ``data`` maps a row name -> counts, one per level (a sequence
    in the order of ``levels`` or a mapping level -> count).

    Answers below the middle go left of zero and those above it go right,
    so the share on each side reads from one baseline. With an odd number of
    levels, the middle one is neutral: ``neutral="split"`` puts half of it on
    each side of zero; ``"aside"`` leaves it out of the bars and prints its
    share at the right. Each side's total share is printed at its end.
    Colors run from the ``neg`` to the ``pos`` hue through grey, darker for
    stronger answers; side and position carry the same information, so the
    bars read in grey. Give the number of raters and answers in the caption.
    ``sections`` groups the rows, such as the questions of one part of a
    survey.
    """
    if neutral not in ("split", "aside"):
        raise ValueError("neutral must be 'split' or 'aside'")
    ctx = current()
    sizes = ctx.sizes
    levels = list(levels)
    k = len(levels)
    if k < 2:
        raise ValueError("a rating scale needs at least two levels")
    names = list(data)
    counts = np.array([[float(data[n][lv]) for lv in levels] if isinstance(data[n], Mapping)
                       else [float(v) for v in data[n]] for n in names])
    if counts.shape[1] != k:
        raise ValueError(f"each row needs {k} counts, one per level")
    totals = counts.sum(axis=1, keepdims=True)
    shares = 100 * np.divide(counts, totals, out=np.zeros_like(counts), where=totals > 0)
    middle = k // 2 if k % 2 else None
    side = k // 2
    neg_colors, pos_colors, mid_color = _level_colors(side, middle is not None)
    colors = neg_colors + ([mid_color] if middle is not None else []) + pos_colors
    ys = _rows(ax, names, ours, sections, band)
    height = 0.62
    texts, handles = [], []
    reach_lo = reach_hi = 0.0
    for name in names:
        row = shares[names.index(name)]
        y = ys[name]
        half = row[middle] / 2 if (middle is not None and neutral == "split") else 0.0
        left = -half - row[:side].sum()
        # Left side, from the strongest negative answer outwards in.
        x = left
        for i in range(side):
            ax.barh(y, row[i], left=x, height=height, color=colors[i], edgecolor="white", linewidth=0.5,
                    zorder=2)
            x += row[i]
        if middle is not None and neutral == "split":
            ax.barh(y, row[middle], left=-half, height=height, color=colors[side], edgecolor="white",
                    linewidth=0.5, zorder=2)
        x = half
        for i in range(k - side, k):
            ax.barh(y, row[i], left=x, height=height, color=colors[i], edgecolor="white", linewidth=0.5,
                    zorder=2)
            x += row[i]
        right = x
        reach_lo, reach_hi = min(reach_lo, left), max(reach_hi, right)
        if values:
            bold = "bold" if _is_ours(name, ours) else "normal"
            neg_share, pos_share = row[:side].sum(), row[k - side:].sum()
            texts.append(ax.annotate(fmt.format(neg_share), xy=(left, y), xytext=(-3, 0), textcoords="offset points",
                                     ha="right", va="center", fontsize=sizes["small"] + 0.5, color=TEXT,
                                     fontweight=bold))
            texts.append(ax.annotate(fmt.format(pos_share), xy=(right, y), xytext=(3, 0), textcoords="offset points",
                                     ha="left", va="center", fontsize=sizes["small"] + 0.5, color=TEXT,
                                     fontweight=bold))
    # Zero sits in the middle, so the two sides compare at a glance.
    reach = max(-reach_lo, reach_hi) * 1.1
    right_end = reach
    if middle is not None and neutral == "aside":
        column = reach * 1.15
        for name in names:
            share = shares[names.index(name)][middle]
            ax.barh(ys[name], share, left=column, height=height, color=colors[side], edgecolor="white",
                    linewidth=0.5, zorder=2)
            if values:
                texts.append(ax.annotate(fmt.format(share), xy=(column + share, ys[name]), xytext=(3, 0),
                                         textcoords="offset points", ha="left", va="center",
                                         fontsize=sizes["small"] + 0.5, color=TEXT))
        right_end = column + float(shares[:, middle].max()) * 1.1
    # Behind the bars (Heiberger & Robbins 2014, p. 8), so a neutral answer split
    # across zero reads as one bar, not two halves.
    ax.axvline(0, color=EDGE, linewidth=0.8, zorder=1)
    ax.set_xlim(-reach, right_end)
    if right_end > reach:
        # Ticks only under the diverging bars; the neutral column has its own printed shares.
        ticks = [t for t in mpl.ticker.MaxNLocator(nbins=6).tick_values(-reach, reach) if -reach <= t <= reach]
        ax.set_xticks(ticks)
        ax.grid(axis="x", visible=False)
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{abs(v):g}"))
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("responses"))
    if legend:
        handles = [mpl.patches.Patch(facecolor=c, edgecolor="none") for c in colors]
        _fit_legend(ax, handles, levels, frameon=False,
                    handlelength=1.0, handleheight=0.8, borderaxespad=0, columnspacing=0.8)
    _fit_rows(ax)
    _keep_inside(ax, texts)
    return {n: shares[i] for i, n in enumerate(names)}
