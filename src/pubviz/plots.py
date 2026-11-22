"""Figures by what they have to say.

Each function draws one kind of claim onto an existing axes, with the colors
of the active theme:

- ``bars``      Which method scores higher, benchmark by benchmark.
- ``deltas``    How much each change helps or hurts against a baseline.
- ``curves``    How a measure moves over steps, time or scale.
- ``tradeoff``  What a method gains on one axis and pays on another.
- ``heatmap``   Values over a grid of two factors.
- ``dots``      Every run of each method, a handful per method, mean marked.
- ``means``     The level of each method with the uncertainty of its mean.
- ``distributions``  How many runs spread: box plots, violins or histograms.

The rules they share: "ours" wears the accent and every compared method a
grey (or, when no method is "ours", a distinct color); a mark never depends on
hue alone (position, labels and signs carry the same information); text stays
dark grey, never series-colored.
"""

from __future__ import annotations

import math
import re
import warnings
from collections.abc import Mapping, Sequence

import matplotlib as mpl
import numpy as np

from .color import contrast
from .style import current

TEXT = "#1A1A1A"
REFERENCE = "#8C8C8C"  # zero lines, frontiers and other reference marks
EDGE = "#3A3A3A"

_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
        10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}


def _t95(df: int) -> float:
    # Round the degrees of freedom down so the interval errs wide.
    keys = [k for k in _T95 if k <= df]
    return _T95[max(keys)] if keys else _T95[1]


def mean_ci(runs):
    """Mean and 95% t-interval over the first axis (seeds).

    A list of per-seed numbers gives three numbers; an array of shape
    (seeds, n) gives three arrays of length n. One seed gives a zero-width
    interval.
    """
    runs = np.asarray(runs, dtype=float)
    mean = runs.mean(axis=0)
    n = runs.shape[0]
    if n < 2:
        return mean, mean, mean
    half = _t95(n - 1) * runs.std(axis=0, ddof=1) / math.sqrt(n)
    return mean, mean - half, mean + half


def _table(data, rows=None, cols=None) -> tuple[list[str], list[str], np.ndarray]:
    """Mapping of mappings or a DataFrame to (row names, column names, values)."""
    if hasattr(data, "to_numpy") and hasattr(data, "index"):
        rows = rows or [str(r) for r in data.index]
        cols = cols or [str(c) for c in data.columns]
        frame = data.copy()
        frame.index = [str(r) for r in frame.index]
        frame.columns = [str(c) for c in frame.columns]
        values = frame.loc[rows, cols].to_numpy(dtype=float)
        return rows, cols, values
    rows = rows or list(data)
    if cols is None:
        cols = []
        for r in rows:
            for c in data[r]:
                if c not in cols:
                    cols.append(c)
    values = np.array([[float(data[r].get(c, np.nan)) for c in cols] for r in rows])
    return list(rows), list(cols), values


def _series_colors(names: Sequence[str], ours, palette: str, marks: str = "fill") -> dict[str, str]:
    """Ours in the accent; the rest grey, or distinct colors when nothing is ours.

    ``marks="line"`` keeps greys dark enough to read as thin lines on white.
    """
    theme = current().theme
    ours = set([ours] if isinstance(ours, str) else (ours or []))
    rest = [n for n in names if n not in ours]
    if palette == "color" or not ours:
        colors = dict(zip(rest, theme.categorical(len(rest))))
    elif marks == "line":
        colors = dict(zip(rest, theme.others(len(rest), lo=0.30, hi=0.72, single=0.55)))
    else:
        colors = dict(zip(rest, theme.others(len(rest))))
    for n in ours:
        colors[n] = theme.ours
    return colors


def _keep_inside(ax, texts, pad: float = 2.0) -> None:
    """Widen the x range until every label in ``texts`` sits inside the axes.

    Value labels hang off the ends of marks; at a narrow width they would
    otherwise run over the tick labels or off the figure. The labels are
    anchored in data units, so widening moves them too; a few passes settle.
    """
    if not texts:
        return
    fig = ax.figure
    for _ in range(4):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        box = ax.get_window_extent(renderer)
        lo, hi = ax.get_xlim()
        per_px = (hi - lo) / box.width
        left = max(box.x0 + pad - t.get_window_extent(renderer).x0 for t in texts)
        right = max(t.get_window_extent(renderer).x1 - (box.x1 - pad) for t in texts)
        if left <= 0.5 and right <= 0.5:
            return
        ax.set_xlim(lo - max(left, 0) * per_px * 1.1, hi + max(right, 0) * per_px * 1.1)


def _row_major(items: list, ncol: int) -> list:
    """``items`` reordered so that a legend in ``ncol`` columns, which
    matplotlib fills column by column, reads row by row in the given order."""
    rows, wide = divmod(len(items), ncol)
    order = []
    for j in range(ncol):
        for i in range(rows + (1 if j < wide else 0)):
            order.append(items[i * ncol + j])
    return order


def _fit_legend(ax, handles, labels, **kwargs):
    """A legend above the axes, in as many columns as fit over the plot and
    the row names beside it. It starts at the plot's left edge; one wider
    than the plot ends at the plot's right edge instead and reaches over the
    names. When it wraps, the entries still read left to right, row by row.

    The widths are measured before the legend is placed. A legend wider than
    its axes would make the layout narrow the plot to fit it, and that
    narrowing can collapse the plot."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = ax.get_window_extent(renderer)
    whole = box.x1 - ax.get_tightbbox(renderer).x0
    for ncol in range(len(handles), 0, -1):
        args = (_row_major(list(handles), ncol), _row_major(list(labels), ncol))
        legend = ax.legend(*args, ncol=ncol, loc="lower left", bbox_to_anchor=(0, 1.01), **kwargs)
        width = legend.get_window_extent(renderer).width
        if width <= whole or ncol == 1:
            break
    if width > box.width:
        legend = ax.legend(*args, ncol=ncol, loc="lower right", bbox_to_anchor=(1, 1.01), **kwargs)
    return legend


ROW_LINES = 1.5  # the least height of a row, in lines of tick-label text


def _fit_rows(ax, n: float | None = None, lines: float = ROW_LINES) -> None:
    """Make the figure taller, if needed, so that each of the ``n`` rows of
    ``ax`` is at least ``lines`` lines of tick-label text high and no two row
    names touch. The width never changes, so the figure still prints at the
    size it was built for; only a figure whose height was too small for its
    rows grows."""
    fig = ax.figure
    if fig.get_layout_engine() is None:
        return
    if n is None:
        lo, hi = ax.get_ylim()
        n = abs(hi - lo) - 0.2  # the rows and gaps, without the margins
    size = mpl.font_manager.FontProperties(size=mpl.rcParams["ytick.labelsize"]).get_size_in_points()
    need = n * lines * size / 72
    for _ in range(4):
        fig.canvas.draw()
        have = ax.get_window_extent().height / fig.dpi
        if have >= need * 0.98:
            return
        w, h = fig.get_size_inches()
        fig.set_size_inches(w, h + (need - have) * 1.05, forward=False)


def _is_ours(name, ours) -> bool:
    """Whether ``name`` is ours: ``ours`` is one name, a (section, member)
    pair, or a list of either."""
    if not ours:
        return False
    if isinstance(ours, str) or (isinstance(ours, tuple) and isinstance(name, tuple)):
        return name == ours
    return name in ours


def bars(ax, data, *, methods=None, groups=None, ours=None, palette: str = "gray",
         values: bool = True, fmt: str = "{:.1f}", errors=None, ylabel: str | None = None,
         legend: bool = True, ylim=None, sections=None, band: str | None = "all"):
    """Grouped bars: each group is a benchmark, each bar a method.

    ``data`` maps method -> {benchmark: score} (or is a DataFrame with methods
    as rows). Bars start at zero, so use them for quantities measured from
    zero (accuracy, pass rate, counts). Method order stays fixed in every
    group and in the legend. ``errors`` has the same shape and draws error
    bars; say in the caption what they are. ``sections`` groups the
    benchmarks, such as by domain: a gap before each section, its name under
    its benchmarks, and a light band behind each section (``band``).
    """
    sizes = current().sizes
    methods, groups, matrix = _table(data, methods, groups)
    sec_groups = _sections(groups, sections)
    if sec_groups:
        groups = [g for _, members in sec_groups for g in members]
        methods, groups, matrix = _table(data, methods, groups)
    colors = _series_colors(methods, ours, palette)
    n = len(methods)
    width = 0.8 / n
    places, spans = _places(groups, sec_groups)
    x = np.array([places[g] for g in groups])
    err = None if errors is None else _table(errors, methods, groups)[2]
    handles, printed = [], []
    for i, name in enumerate(methods):
        offset = (i - (n - 1) / 2) * width
        bar = ax.bar(x + offset, matrix[i], width * 0.92, label=name, color=colors[name],
                     edgecolor=EDGE, linewidth=0.4, zorder=2,
                     yerr=None if err is None else err[i],
                     error_kw={"elinewidth": 0.6, "capsize": 1.2, "ecolor": EDGE})
        handles.append(bar)
        if values:
            labels = ["" if not np.isfinite(v) else fmt.format(v) for v in matrix[i]]
            texts = ax.bar_label(bar, labels=labels, fontsize=sizes["small"], padding=1.2, color=TEXT)
            printed.extend(texts)
            if _is_ours(name, ours):
                for t in texts:
                    t.set_fontweight("bold")
    ax.set_xticks(x, [_shown(g) for g in groups])
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.5, float(x.max()) + 0.5)
    if ylim is not None:
        ax.set_ylim(*ylim)
    else:
        top = np.nanmax(matrix + (0 if err is None else np.nan_to_num(err)))
        ax.set_ylim(0, _nice_top(top * 1.12))
    if ylabel:
        ax.set_ylabel(ylabel)
    if legend:
        ax.legend(handles, methods, loc="lower left", bbox_to_anchor=(0, 1.01), ncol=min(n, 4),
                  frameon=False, handlelength=1.0, borderaxespad=0)
    _column_sections(ax, spans, band)
    _turn_crowded_values(ax, printed)
    return handles


def _turn_crowded_values(ax, texts) -> None:
    """Turn the values on bars upright when, set level, neighbours would touch."""
    texts = [t for t in texts if t.get_text()]
    if len(texts) < 2:
        return
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = sorted((t.get_window_extent(renderer) for t in texts), key=lambda b: b.x0)
    if any(b.x0 < a.x1 + 0.5 and b.y0 < a.y1 and a.y0 < b.y1 for a, b in zip(boxes, boxes[1:])):
        for t in texts:
            t.set(rotation=90, ha="center", va="bottom")
        top = ax.get_ylim()[1]
        fig.canvas.draw()
        # Upright values are taller: make room above the highest bar.
        tallest = max(t.get_window_extent(renderer).y1 for t in texts)
        over = tallest - ax.get_window_extent(renderer).y1
        if over > 0:
            per_px = (top - ax.get_ylim()[0]) / ax.get_window_extent(renderer).height
            ax.set_ylim(ax.get_ylim()[0], top + over * per_px * 1.1)


def _nice_top(value: float) -> float:
    """Round up to the next half step of the value's order of magnitude (77.7 -> 80)."""
    if value <= 0:
        return 1.0
    unit = 10 ** math.floor(math.log10(value)) / 2
    return math.ceil(value / unit - 1e-9) * unit


def _signed(text: str) -> str:
    """Use a true minus sign, as the tick labels do."""
    return text.replace("-", "\u2212")


def deltas(ax, data, *, better: str = "higher", ours=None, fmt: str = "{:+.1f}", unit: str = "",
           sort: bool = True, xlabel: str | None = None, key: bool = True, sections=None,
           band: str | None = "all"):
    """Change against a baseline, one row per variant, with a line at zero.

    ``data`` maps name -> change, or name -> (change, low, high) for an
    interval of the change itself (not of each variant). A change that helps
    is drawn in ``pos``, one that hurts in ``neg``; an interval that crosses
    zero is grey, because the data cannot tell its sign. The signed value is
    printed beside every row, so the plot reads without color. ``key`` names
    the colors above the plot, each beside its own mark, so the caption does
    not have to; in a grey theme the colors are alike and the key is left out.
    """
    theme = current().theme
    sizes = current().sizes
    items = []
    for name, value in data.items():
        if isinstance(value, Sequence) and not isinstance(value, str):
            d, lo, hi = (float(v) for v in value)
        else:
            d = lo = hi = float(value)
        items.append((name, d, lo, hi))
    sign = 1 if better == "higher" else -1
    by = {item[0]: item for item in items}
    groups = _sections(list(by), sections)
    if sort:
        # The best change on top, within each section.
        best_first = lambda names: sorted(names, key=lambda n: -sign * by[n][1])  # noqa: E731
        groups = [(sec, best_first(members)) for sec, members in groups]
        if not groups:
            items = [by[n] for n in best_first(list(by))]
    ys = _rows(ax, [i[0] for i in items], ours, {sec: m for sec, m in groups} or None, band)
    shown = set()
    labels = []
    for name, d, lo, hi in items:
        y = ys[name]
        crosses = lo < 0 < hi
        helps = sign * d > 0
        kind = "muted" if (crosses or d == 0) else ("pos" if helps else "neg")
        shown.add(kind)
        color = theme[kind]
        if hi > lo:
            ax.plot([lo, hi], [y, y], color=color, linewidth=1.0, solid_capstyle="round", zorder=2)
        ax.plot([d], [y], "o", color=color, markersize=4, zorder=3)
        end = hi if d >= 0 else lo
        labels.append(ax.annotate(_signed(fmt.format(d)) + unit, xy=(end, y), xytext=(4 if d >= 0 else -4, 0),
                                  textcoords="offset points", va="center", ha="left" if d >= 0 else "right",
                                  fontsize=sizes["small"] + 0.5, color=TEXT,
                                  fontweight="bold" if _is_ours(name, ours) else "normal"))
    ax.axvline(0, color=REFERENCE, linewidth=0.8, zorder=1)
    span = max(max(abs(i[2]), abs(i[3]), abs(i[1])) for i in items) or 1.0
    ax.set_xlim(-span * 1.35 if min(i[2] for i in items) < 0 else -span * 0.08, span * 1.35)
    if xlabel:
        ax.set_xlabel(xlabel)
    if key and theme.mode == "color":
        from matplotlib.lines import Line2D

        said = current().words
        words = {"pos": said["better"], "neg": said["worse"], "muted": said["crosses"]}
        handles = [Line2D([], [], color=theme[k], marker="o", markersize=4, linewidth=1.0)
                   for k in words if k in shown]
        _fit_legend(ax, handles, [words[k] for k in words if k in shown], frameon=False, handlelength=1.4,
                    borderaxespad=0)
    _fit_rows(ax)
    _keep_inside(ax, labels)


def curves(ax, x, series: Mapping, *, ours=None, palette: str = "gray", band: bool = True,
           labels: str = "end", xlabel: str | None = None, ylabel: str | None = None):
    """Lines over steps, time or scale; mean with a 95% band when seeds are given.

    ``series`` maps name -> values of shape (n,) or (seeds, n). ``labels`` is
    ``"end"`` to name each line at its right end (no legend to decode),
    ``"legend"``, or ``None``. State the number of seeds in the caption.
    """
    sizes = current().sizes
    names = list(series)
    colors = _series_colors(names, ours, palette, marks="line")
    order = [n for n in names if not _is_ours(n, ours)] + [n for n in names if _is_ours(n, ours)]
    lines = {}
    for name in order:
        mean, lo, hi = mean_ci(np.atleast_2d(series[name]))
        mine = _is_ours(name, ours)
        (line,) = ax.plot(x, mean, color=colors[name], linewidth=1.7 if mine else 1.1,
                          label=name, zorder=4 if mine else 3)
        if band and np.any(hi > lo):
            ax.fill_between(x, lo, hi, color=colors[name], alpha=0.2 if mine else 0.15, linewidth=0, zorder=2)
        lines[name] = line
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if labels == "end":
        label_ends(ax, [lines[n] for n in names], names, bold=[_is_ours(n, ours) for n in names],
                   fontsize=sizes["legend"])
    elif labels == "legend":
        ax.legend([lines[n] for n in names], names)
    return lines


def label_ends(ax, lines, names, bold=None, fontsize=None, min_gap_pt: float | None = None):
    """Name each line at its right end, nudged apart where lines converge."""
    fig = ax.figure
    fontsize = fontsize or mpl.rcParams["legend.fontsize"]
    min_gap_pt = min_gap_pt or fontsize * 1.15
    bold = bold or [False] * len(lines)
    fig.canvas.draw()
    height_pt = ax.get_window_extent().height * 72 / fig.dpi
    ends = []
    for line, name, b in zip(lines, names, bold):
        xs, ys = line.get_xdata(), line.get_ydata()
        xy = (xs[-1], ys[-1])
        frac = ax.transAxes.inverted().transform(ax.transData.transform(xy))[1]
        ends.append([frac * height_pt, xy, line, name, b])
    ends.sort(key=lambda e: e[0])
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + min_gap_pt)
    for pos, xy, line, name, b in ends:
        frac = ax.transAxes.inverted().transform(ax.transData.transform(xy))[1]
        ax.annotate(name, xy=xy, xytext=(4, pos - frac * height_pt), textcoords="offset points",
                    va="center", ha="left", fontsize=fontsize, color=TEXT,
                    fontweight="bold" if b else "normal", annotation_clip=False)


def pareto(xs, ys, better_x: str = "lower", better_y: str = "higher") -> list[int]:
    """Indices of points no other point beats on both axes, ordered along x."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    cx = xs if better_x == "lower" else -xs
    cy = -ys if better_y == "higher" else ys
    front, best = [], np.inf
    for i in np.lexsort((cy, cx)):
        if cy[i] < best:
            front.append(int(i))
            best = cy[i]
    return sorted(front, key=lambda i: xs[i])


def tradeoff(ax, points: Mapping, *, ours=None, better_x: str = "lower", better_y: str = "higher",
             frontier: bool = True, labels: bool = True, xlabel: str | None = None,
             ylabel: str | None = None, logx: bool = False, arrows: bool = True):
    """Each method as a point on two measures that pull against each other.

    ``points`` maps name -> (x, y). The dashed line joins the methods no
    other method beats on both measures. With ``arrows`` each axis label ends
    in the arrow the tables use for the better direction.
    """
    theme = current().theme
    sizes = current().sizes
    names = list(points)
    xs = np.array([points[n][0] for n in names], dtype=float)
    ys = np.array([points[n][1] for n in names], dtype=float)
    front = pareto(xs, ys, better_x, better_y) if frontier else []
    if logx:
        ax.set_xscale("log")
    if len(front) > 1:
        ax.plot(xs[front], ys[front], linestyle=(0, (3, 2)), color=REFERENCE, linewidth=0.8, zorder=1)
    on, off = theme.grey(0.35), theme.grey(0.72)
    for i, name in enumerate(names):
        mine = _is_ours(name, ours)
        color = theme.ours if mine else (on if i in front else off)
        ax.plot([xs[i]], [ys[i]], "o", color=color, markersize=5.5 if mine else 4.2,
                markeredgecolor="white", markeredgewidth=0.6, zorder=4 if mine else 3)
        if labels:
            ax.annotate(name, xy=(xs[i], ys[i]), xytext=(4, 3), textcoords="offset points",
                        fontsize=sizes["small"] + 0.5, color=TEXT, fontweight="bold" if mine else "normal")
    ax.grid(axis="x", visible=True)
    if xlabel:
        ax.set_xlabel(xlabel + (_arrow(better_x, xlabel) if arrows else ""))
    if ylabel:
        ax.set_ylabel(ylabel + (_arrow(better_y, ylabel) if arrows else ""))
    return front


_CJK_TEXT = re.compile("[\u1100-\u11ff\u2e80-\u9fff\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]")


def _arrow(better: str, label: str = "") -> str:
    # A label holding $...$ is set entirely in the math fonts, which have no
    # CJK characters; for such a label the arrow is the plain character,
    # which the CJK fallback fonts have.
    if _CJK_TEXT.search(label):
        return " ↑" if better == "higher" else " ↓"
    return r" $\uparrow$" if better == "higher" else r" $\downarrow$"


def heatmap(ax, values, rows: Sequence[str], cols: Sequence[str], *, better: str = "higher",
            fmt: str = "{:.1f}", center: float | None = None, mark: str | None = None,
            colorbar: bool = False, label: str | None = None):
    """Values over two factors, shaded in the accent hue.

    ``center`` switches to a diverging scale around that value (for signed
    changes). ``mark`` is ``"column"`` or ``"row"`` to set the best value of
    each column or row in bold, as in a table.
    """
    theme = current().theme
    sizes = current().sizes
    data = np.asarray(values, dtype=float)
    if center is None:
        cmap = theme.cmap()
        lo, hi = np.nanmin(data), np.nanmax(data)
        if better == "lower":
            cmap = cmap.reversed()
    else:
        cmap = theme.diverging()
        span = np.nanmax(np.abs(data - center)) or 1.0
        lo, hi = center - span, center + span
        if better == "lower":
            cmap = cmap.reversed()
    image = ax.imshow(data, cmap=cmap, vmin=lo, vmax=hi, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(len(cols)), cols)
    ax.set_yticks(range(len(rows)), rows)
    ax.tick_params(length=0)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    best = np.zeros_like(data, dtype=bool)
    if mark in ("column", "row"):
        axis = 0 if mark == "column" else 1
        target = np.nanmax(data, axis=axis, keepdims=True) if better == "higher" else np.nanmin(data, axis=axis, keepdims=True)
        best = data == target
    for (r, c), v in np.ndenumerate(data):
        if not np.isfinite(v):
            continue
        fill = mpl.colors.to_hex(cmap((v - lo) / (hi - lo) if hi > lo else 0.5))
        ink = TEXT if contrast(TEXT, fill) >= contrast("#FFFFFF", fill) else "#FFFFFF"
        ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=sizes["small"] + 0.5,
                color=ink, fontweight="bold" if best[r, c] else "normal")
    if colorbar:
        bar = ax.figure.colorbar(image, ax=ax, fraction=0.05, pad=0.02)
        bar.outline.set_visible(False)
        bar.ax.tick_params(labelsize=sizes["tick"], length=2)
        if label:
            bar.set_label(label)
    return image


# ---- one row per method: the runs, the mean, the spread ----------------------
# The three kinds below share a layout: one row per method in the order given,
# top to bottom, the method's name on the left (bold for ours), values on a
# horizontal scale. Ours wears the accent, every compared method one grey;
# the rows are named, so the methods need no colors of their own.

ROW_GREY = 0.55   # lightness of the marks of compared methods
FEW_RUNS = 10     # below this a summary of the runs says too little (rule of thumb)


# ---- sections: a second level of grouping --------------------------------------
# Rows (or bars) that belong together, such as the configurations of one model
# or the variants of one ablated part, form a section: a little space before
# it, its name beside (or under) its members, and a light band behind it, as
# a section row is shaded in a table. The three cues agree: an enclosing
# region is among the strongest grouping cues, and two-level structures were
# read best when every group was enclosed and the cues did not compete (Bae &
# Watson 2014). band="alternate" shades every other section instead, as zebra
# rows do; band=None keeps only the space and the names.

SECTION_GAP = 0.7   # extra space before each section after the first, in rows
BANDS = ("alternate", "all", None)


def _sections(names: Sequence[str], sections) -> list[tuple[str, list[str]]]:
    """The sections as (name, members) in order, each member given once.

    Without ``sections``, names that are (section, member) pairs give them:
    the sections in the order they first appear."""
    if not sections and names and all(isinstance(n, tuple) and len(n) == 2 for n in names):
        sections = {}
        for n in names:
            sections.setdefault(n[0], []).append(n)
    if not sections:
        return []
    listed = [n for members in sections.values() for n in members]
    missing = [n for n in names if n not in listed]
    unknown = [n for n in listed if n not in names]
    twice = sorted({n for n in listed if listed.count(n) > 1})
    if missing or unknown or twice:
        raise ValueError("sections must list every name once: "
                         + "; ".join(f"{what}: {', '.join(map(str, items))}" for what, items in
                                     (("missing", missing), ("not in the data", unknown), ("listed twice", twice))
                                     if items))
    return [(str(sec), list(members)) for sec, members in sections.items()]


def _places(names: Sequence[str], groups) -> tuple[dict, list]:
    """Positions 0, 1, 2, ... in reading order, with a gap before each
    section after the first; and each section's (name, first, last)."""
    if not groups:
        return {n: float(i) for i, n in enumerate(names)}, []
    places, spans, at = {}, [], 0.0
    for k, (sec, members) in enumerate(groups):
        at += SECTION_GAP if k else 0.0
        first = at
        for n in members:
            places[n] = at
            at += 1.0
        spans.append((sec, first, at - 1.0))
    return places, spans


def _band_spans(spans, band: str | None):
    if band not in BANDS:
        raise ValueError("band must be 'alternate', 'all' or None")
    if band is None:
        return []
    # Alternate bands reach halfway into the gaps, so shaded and unshaded
    # sections meet there; with a band on every section the gaps stay white.
    reach = 0.5 + (SECTION_GAP / 2 if band == "alternate" else 0.0)
    return [(lo - reach, hi + reach) for k, (_, lo, hi) in enumerate(spans) if band == "all" or k % 2 == 1]


def _shown(name) -> str:
    """The label of a row or column: the member of a (section, member) pair."""
    return str(name[1]) if isinstance(name, tuple) and len(name) == 2 else str(name)


def _label_width_pt(texts) -> float:
    texts = [t for t in texts if t.get_text()]
    if not texts:
        return 0.0
    fig = texts[0].figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    return max(t.get_window_extent(renderer).width for t in texts) * 72 / fig.dpi


def _row_sections(ax, spans, ys_of, band) -> None:
    """Bands behind row sections and each section's name left of its rows."""
    theme = current().theme
    for lo, hi in _band_spans(spans, band):
        ax.axhspan(ys_of(hi), ys_of(lo), color=theme["band"], linewidth=0, zorder=0)
    if not spans:
        return
    left = _label_width_pt(ax.get_yticklabels()) + mpl.rcParams["ytick.major.pad"] + 6
    for sec, lo, _ in spans:
        ax.annotate(sec, xy=(0, ys_of(lo)), xycoords=("axes fraction", "data"), xytext=(-left, 0),
                    textcoords="offset points", ha="right", va="center", fontweight="bold",
                    fontsize=mpl.rcParams["ytick.labelsize"], color=TEXT, annotation_clip=False)


def _column_sections(ax, spans, band) -> None:
    """Bands behind column sections and each section's name under its tick labels."""
    theme = current().theme
    for lo, hi in _band_spans(spans, band):
        ax.axvspan(lo, hi, color=theme["band"], linewidth=0, zorder=0)
    if not spans:
        return
    texts = [t for t in ax.get_xticklabels() if t.get_text()]
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    below = max(t.get_window_extent(renderer).height for t in texts) * 72 / fig.dpi if texts else 0.0
    below += mpl.rcParams["xtick.major.pad"] + 2
    size = mpl.font_manager.FontProperties(size=mpl.rcParams["xtick.labelsize"]).get_size_in_points()
    for sec, lo, hi in spans:
        ax.annotate(sec, xy=((lo + hi) / 2, 0), xycoords=("data", "axes fraction"), xytext=(0, -below),
                    textcoords="offset points", ha="center", va="top", fontweight="bold",
                    fontsize=size, color=TEXT, annotation_clip=False)
    ax.xaxis.labelpad += size * 1.4


def _rows(ax, names, ours, sections=None, band: str | None = "all") -> dict:
    """One row per name, top to bottom; with ``sections``, grouped as given."""
    groups = _sections(names, sections)
    order = [n for _, members in groups for n in members] if groups else list(names)
    places, spans = _places(order, groups)
    top = max(places.values()) if places else 0.0
    ys = {n: top - places[n] for n in order}
    ax.set_yticks(list(ys.values()), [_shown(n) for n in ys])
    for name, label in zip(ys, ax.get_yticklabels()):
        if _is_ours(name, ours):
            label.set_fontweight("bold")
    ax.set_ylim(-0.6, top + 0.6)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    _row_sections(ax, spans, lambda place: top - place, band)
    return ys


def _row_color(name, ours) -> str:
    theme = current().theme
    return theme.ours if _is_ours(name, ours) else theme.grey(ROW_GREY)


def _label_row(ax, x, y, text, bold):
    return ax.annotate(_signed(text), xy=(x, y), xytext=(5, 0), textcoords="offset points", va="center",
                       ha="left", fontsize=current().sizes["small"] + 0.5, color=TEXT,
                       fontweight="bold" if bold else "normal")


def _fit_x(ax, lo, hi, room=0.16):
    span = (hi - lo) or abs(hi) or 1.0
    ax.set_xlim(lo - span * 0.06, hi + span * room)


def _swarm(values, close) -> np.ndarray:
    """Vertical slots for dots: a dot within ``close`` of one already placed
    moves to the next free slot above or below, so no run hides another."""
    slots = np.zeros(len(values))
    placed = []
    order = [0] + [s for k in range(1, 50) for s in (k, -k)]
    for i in np.argsort(values, kind="stable"):
        used = {slot for v, slot in placed if abs(v - values[i]) < close}
        slot = next(s for s in order if s not in used)
        placed.append((values[i], slot))
        slots[i] = slot
    return slots


SWARM_MAX = 30   # up to this many runs move apart one by one; more get a fixed jitter


def _strip(ax, values, y, color, close, height=0.36, alpha=1.0, size=3.4, edge="white"):
    """The runs of one row as dots, spread up and down so none hides another."""
    if len(values) <= SWARM_MAX:
        slots = _swarm(values, close)
        offsets = slots * min(0.11, height / max(1, np.abs(slots).max()))
    else:
        offsets = np.random.default_rng(len(values)).uniform(-height, height, len(values))
    ax.plot(values, y + offsets, "o", linestyle="none", markersize=size, markerfacecolor=color,
            markeredgecolor=edge, markeredgewidth=0.4 if edge != "none" else 0, alpha=alpha, zorder=3)


def dots(ax, runs: Mapping, *, ours=None, mean: bool = True, values: bool = True,
         fmt: str = "{:.1f}", unit: str = "", xlabel: str | None = None, sections=None,
         band: str | None = "all"):
    """Every run as a dot, one row per method, with the mean marked.

    For a handful of runs per method (seeds, participants), where a box plot
    or a density would summarize too few points. ``runs`` maps name ->
    per-run values. Dots that would cover each other move up or down within
    their row. The mean is a short vertical bar and is printed at the end of
    the row. Give the number of runs in the caption.
    """
    sizes = current().sizes
    names = list(runs)
    data = {n: np.asarray(runs[n], dtype=float) for n in names}
    data = {n: v[np.isfinite(v)] for n, v in data.items()}
    every = np.concatenate([v for v in data.values() if len(v)]) if names else np.array([0.0])
    lo, hi = float(every.min()), float(every.max())
    close = ((hi - lo) or 1.0) * 0.018
    ys = _rows(ax, names, ours, sections, band)
    printed = []
    for name in names:
        v, y, color = data[name], ys[name], _row_color(name, ours)
        if not len(v):
            continue
        _strip(ax, v, y, color, close)
        if mean:
            m = float(v.mean())
            ax.plot([m, m], [y - 0.3, y + 0.3], color=color if _is_ours(name, ours) else EDGE,
                    linewidth=1.6, solid_capstyle="butt", zorder=4)
            if values:
                printed.append(_label_row(ax, float(v.max()), y, fmt.format(m) + unit, _is_ours(name, ours)))
    _fit_x(ax, lo, hi)
    if xlabel:
        ax.set_xlabel(xlabel)
    _fit_rows(ax)
    _keep_inside(ax, printed)
    return ys


def _estimate(value):
    """A tuple (mean, low, high) as given; a list or array of runs through mean_ci."""
    if isinstance(value, tuple):
        if len(value) != 3:
            raise ValueError("an estimate is a tuple (mean, low, high)")
        return tuple(float(x) for x in value)
    m, lo, hi = mean_ci(value)
    return float(m), float(lo), float(hi)


def means(ax, data: Mapping, *, ours=None, show: str = "interval", points: bool | None = None,
          values: bool = True, fmt: str = "{:.1f}", unit: str = "", xlabel: str | None = None,
          sections=None, band: str | None = "all"):
    """The level of each method: its mean and the uncertainty of that mean.

    ``data`` maps name -> a list of per-run values (the 95% t-interval is
    computed with ``mean_ci``) or a tuple (mean, low, high). ``show``:

    - ``"interval"``: a point at the mean and a line over the 95% interval.
    - ``"gradient"``: the row is shaded by how plausible each value is for
      the mean, full inside the 95% interval and fading outside it along a
      normal curve fitted to the interval, after the gradient plots of
      Correll & Gleicher (2014).

    ``points``: draw the runs themselves, faintly, under the estimate. The
    default draws them whenever runs are given: readers shown only the
    interval of a mean overstate how often one method beats another, and the
    runs beside it bring their estimates back near the truth (Hofman et al.
    2020; Zhang et al. 2023). A tuple has no runs to draw.

    Not bars: with a bar, values inside it read as likelier than values
    above it. Say in the caption what the interval is and over how many runs.
    """
    if show not in ("interval", "gradient"):
        raise ValueError("show must be 'interval' or 'gradient'")
    names = list(data)
    est = {n: _estimate(data[n]) for n in names}
    runs = {n: np.asarray(data[n], dtype=float) for n in names if not isinstance(data[n], tuple)}
    runs = {n: v[np.isfinite(v)] for n, v in runs.items()}
    if points is None:
        points = bool(runs)
    ys = _rows(ax, names, ours, sections, band)
    printed = []
    lo_all, hi_all = math.inf, -math.inf
    if points and runs:
        every = np.concatenate([v for v in runs.values() if len(v)])
        close = ((every.max() - every.min()) or 1.0) * 0.012
        for name, v in runs.items():
            if len(v):
                _strip(ax, v, ys[name], _row_color(name, ours), close, height=0.3, alpha=0.45,
                       size=2.4, edge="none")
                lo_all, hi_all = min(lo_all, float(v.min())), max(hi_all, float(v.max()))
    for name in names:
        m, lo, hi = est[name]
        y, color, mine = ys[name], _row_color(name, ours), _is_ours(name, ours)
        if show == "gradient" and hi > lo:
            se = (hi - lo) / (2 * 1.959964)
            xs = np.linspace(m - 4 * se, m + 4 * se, 121)
            tail = np.array([math.erfc(abs(x - m) / (se * math.sqrt(2))) for x in xs])  # two-sided p
            alpha = np.clip(tail / 0.05, 0, 1)
            rgb = mpl.colors.to_rgb(color)
            cells = [[(xs[i], y - 0.2), (xs[i + 1], y - 0.2), (xs[i + 1], y + 0.2), (xs[i], y + 0.2)]
                     for i in range(len(xs) - 1)]
            faces = [(*rgb, 0.85 * (alpha[i] + alpha[i + 1]) / 2) for i in range(len(xs) - 1)]
            ax.add_collection(mpl.collections.PolyCollection(cells, facecolors=faces, edgecolors="none",
                                                             zorder=2))
            lo_all, hi_all = min(lo_all, xs[0]), max(hi_all, xs[-1])
            end = m + 2.8 * se  # past the visible part of the fade
        else:
            if hi > lo:
                ax.plot([lo, hi], [y, y], color=color, linewidth=1.2, solid_capstyle="round", zorder=2)
            lo_all, hi_all = min(lo_all, lo), max(hi_all, hi)
            end = hi
        ax.plot([m], [y], "o", markersize=4.2, markerfacecolor=color if show == "interval" else "white",
                markeredgecolor=color if show == "interval" else EDGE, markeredgewidth=0.6, zorder=3)
        if values:
            if points and name in runs and len(runs[name]):
                end = max(end, float(runs[name].max()))
            printed.append(_label_row(ax, end, y, fmt.format(m) + unit, mine))
    _fit_x(ax, lo_all, hi_all)
    if xlabel:
        ax.set_xlabel(xlabel)
    _fit_rows(ax)
    _keep_inside(ax, printed)
    return est


def distributions(ax, runs: Mapping, *, ours=None, kind: str = "box", points: bool = False,
                  values: bool = True, fmt: str = "{:.1f}", unit: str = "", xlabel: str | None = None,
                  bins="auto", sections=None, band: str | None = "all"):
    """How the runs of each method spread, one row per method.

    For many runs per method (test items, users, long sweeps). No kind is
    read best for everything, so choose by what the reader should judge
    (Lotteraner et al. 2026; Newburger et al. 2023):

    - ``"box"``: the median and the comparison of groups. The box spans the
      middle half of the runs, the dark line is the median, whiskers reach
      the furthest run within 1.5 box lengths, and runs beyond them are
      dots; say so in the caption. A box hides two peaks.
    - ``"strip"``: the range and the spread. Every run is a dot, the median
      a short bar.
    - ``"violin"``: the shape, such as two peaks. A smoothed density of the
      runs with the median marked.
    - ``"histogram"``: counts in each row, on bins shared by all rows.

    ``points`` draws the runs as faint dots over a box or violin. The median
    is printed at the end of each row. A method with fewer than about ten
    runs gets a warning: draw every run with ``dots`` instead.
    """
    if kind not in ("box", "strip", "violin", "histogram"):
        raise ValueError("kind must be 'box', 'strip', 'violin' or 'histogram'")
    theme = current().theme
    names = list(runs)
    data = {n: np.asarray(runs[n], dtype=float) for n in names}
    data = {n: v[np.isfinite(v)] for n, v in data.items()}
    for name, v in data.items():
        if len(v) < FEW_RUNS:
            warnings.warn(f"{name}: {len(v)} runs are too few to summarize; draw every run with pv.dots",
                          stacklevel=2)
    ys = _rows(ax, names, ours, sections, band)
    printed = []
    every = np.concatenate([v for v in data.values() if len(v)])
    lo, hi = float(every.min()), float(every.max())
    fill = {n: theme.fills[1] if _is_ours(n, ours) else theme.grey(0.88) for n in names}
    line = {n: theme.ours if _is_ours(n, ours) else EDGE for n in names}
    order = [n for n in names if len(data[n])]
    positions = [ys[n] for n in order]
    close = ((hi - lo) or 1.0) * 0.012
    if kind == "strip":
        for name in order:
            _strip(ax, data[name], ys[name], line[name] if _is_ours(name, ours) else theme.grey(ROW_GREY),
                   close, height=0.3, alpha=0.6, size=2.4, edge="none")
            med = float(np.median(data[name]))
            ax.plot([med, med], [ys[name] - 0.34, ys[name] + 0.34], color=TEXT, linewidth=1.4, zorder=4)
    elif kind == "box":
        parts = ax.boxplot([data[n] for n in order], positions=positions, orientation="horizontal",
                           widths=0.5, patch_artist=True, manage_ticks=False, showfliers=not points,
                           medianprops={"color": TEXT, "linewidth": 1.4},
                           whiskerprops={"linewidth": 0.7}, capprops={"linewidth": 0.7},
                           flierprops={"marker": "o", "markersize": 2.2, "markeredgewidth": 0,
                                       "markerfacecolor": EDGE})
        for name, box in zip(order, parts["boxes"]):
            box.set(facecolor=fill[name], edgecolor=line[name], linewidth=0.7)
        for k, name in enumerate(order):
            for artist in (parts["whiskers"][2 * k], parts["whiskers"][2 * k + 1],
                           parts["caps"][2 * k], parts["caps"][2 * k + 1]):
                artist.set_color(line[name])
    elif kind == "violin":
        parts = ax.violinplot([data[n] for n in order], positions=positions, orientation="horizontal",
                              widths=0.75, showextrema=False, showmedians=False)
        for name, body in zip(order, parts["bodies"]):
            body.set(facecolor=fill[name], edgecolor=line[name], linewidth=0.7, alpha=1.0)
        for name in order:
            med = float(np.median(data[name]))
            ax.plot([med, med], [ys[name] - 0.22, ys[name] + 0.22], color=TEXT, linewidth=1.4, zorder=3)
    else:
        edges = np.histogram_bin_edges(every, bins=bins)
        counts = {n: np.histogram(data[n], bins=edges)[0] for n in order}
        top = max(c.max() for c in counts.values()) or 1
        for name in order:
            base = ys[name] - 0.38
            ax.stairs(base + 0.76 * counts[name] / top, edges, baseline=base, fill=True,
                      facecolor=fill[name], edgecolor=line[name], linewidth=0.6, zorder=2)
            med = float(np.median(data[name]))
            ax.plot([med, med], [base, base + 0.76], color=TEXT, linewidth=1.2, zorder=3)
    if points and kind in ("box", "violin"):
        for name in order:
            _strip(ax, data[name], ys[name], EDGE, close, height=0.2, alpha=0.35, size=1.8, edge="none")
    if values:
        for name in order:
            printed.append(_label_row(ax, hi if kind == "histogram" else float(data[name].max()), ys[name],
                                      fmt.format(float(np.median(data[name]))) + unit, _is_ours(name, ours)))
    _fit_x(ax, lo, hi)
    if xlabel:
        ax.set_xlabel(xlabel)
    _fit_rows(ax)
    _keep_inside(ax, printed)
    return ys


# ---- many items, one value each ------------------------------------------------

MARKERS = ("o", "s", "^", "D", "v", "P")


def ranked(ax, data, *, ours=None, better: str = "higher", sort: str | None = "ours", values: bool = False,
           fmt: str = "{:.1f}", xlabel: str | None = None, legend: bool = True, sections=None,
           band: str | None = "all"):
    """A dot chart (Cleveland 1984): one row per item, such as a language or
    a class, and one dot per system on a shared scale.

    For more items than bars can hold, and in place of a radar chart.
    ``data`` maps item -> value (one system) or item -> {system: value}, or
    is a DataFrame with items as rows. ``sort`` orders the rows best first
    by ``"ours"`` (or the first system when none is ours), by the
    ``"mean"`` of the systems, or keeps the given order with None. The axis
    need not start at zero: a dot is read by its position, not its length.
    Each system has its own marker as well as its shade, and a thin line
    joins the dots of one row so the gap between systems reads per item.
    ``sections`` groups the items, such as languages by family; rows are
    sorted within each section.
    """
    first = next(iter(data.values())) if isinstance(data, Mapping) and data else None
    if first is not None and not isinstance(first, Mapping):
        data = {k: {"": v} for k, v in data.items()}
    items, systems, matrix = _table(data)
    if len(systems) > len(MARKERS):
        raise ValueError(f"{len(systems)} systems are too many to tell apart in one dot chart; "
                         f"split them over panels (at most {len(MARKERS)})")
    sign = 1 if better == "higher" else -1
    if sort == "ours":
        key_col = next((j for j, s in enumerate(systems) if _is_ours(s, ours)), 0)
        order = np.argsort(-sign * matrix[:, key_col], kind="stable")
    elif sort == "mean":
        order = np.argsort(-sign * np.nanmean(matrix, axis=1), kind="stable")
    elif sort is None:
        order = np.arange(len(items))
    else:
        raise ValueError("sort must be 'ours', 'mean' or None")
    items = [items[i] for i in order]
    matrix = matrix[order]
    groups = _sections(items, sections)
    if groups:
        # Keep the sort within each section.
        rank = {n: k for k, n in enumerate(items)}
        groups = [(sec, sorted(members, key=rank.get)) for sec, members in groups]
        reorder = [rank[n] for _, members in groups for n in members]
        items = [items[k] for k in reorder]
        matrix = matrix[reorder]
    colors = _series_colors(systems, ours, "gray", marks="line")
    if not any(_is_ours(s, ours) for s in systems) and len(systems) > 1:
        colors = dict(zip(systems, current().theme.others(len(systems), lo=0.25, hi=0.72)))
    where = _rows(ax, items, ours, dict(groups) or None, band)
    ys = np.array([where[n] for n in items])
    for y, row in zip(ys, matrix):
        finite = row[np.isfinite(row)]
        if len(finite) > 1:
            ax.plot([finite.min(), finite.max()], [y, y], color=REFERENCE, linewidth=0.8, zorder=2)
    handles = []
    printed = []
    for j, system in enumerate(systems):
        mine = _is_ours(system, ours)
        (h,) = ax.plot(matrix[:, j], ys, MARKERS[j], linestyle="none", markersize=4.6 if mine else 3.8,
                       markerfacecolor=colors[system], markeredgecolor="white", markeredgewidth=0.5,
                       zorder=4 if mine else 3)
        handles.append(h)
    if values:
        for y, row in zip(ys, matrix):
            j = next((j for j, s in enumerate(systems) if _is_ours(s, ours)), 0)
            if np.isfinite(row[j]):
                printed.append(_label_row(ax, float(np.nanmax(row)), y, fmt.format(row[j]), _is_ours(systems[j], ours)))
    ax.grid(axis="y", visible=True, color="#EDEDED", linewidth=0.5)
    lo, hi = float(np.nanmin(matrix)), float(np.nanmax(matrix))
    _fit_x(ax, lo, hi, room=0.16 if values else 0.06)
    if xlabel:
        ax.set_xlabel(xlabel + _arrow(better, xlabel))
    if legend and len(systems) > 1:
        legend_obj = _fit_legend(ax, handles, systems, frameon=False,
                                 handlelength=1.0, borderaxespad=0)
        for text in legend_obj.get_texts():
            if _is_ours(text.get_text(), ours):
                text.set_fontweight("bold")
    _fit_rows(ax)
    _keep_inside(ax, printed)
    return items


# ---- a measure against scale, with a fitted power law -----------------------------


def power_fit(x, y) -> tuple[float, float]:
    """(a, b) of y = a * x**b, fitted by least squares on log10 of both."""
    lx, ly = np.log10(np.asarray(x, dtype=float)), np.log10(np.asarray(y, dtype=float))
    b, log_a = np.polyfit(lx, ly, 1)
    return float(10 ** log_a), float(b)


def scaling(ax, data: Mapping, *, ours=None, fit: bool = True, upto: float | None = None,
            extend: float | None = None, xlabel: str | None = None, ylabel: str | None = None,
            better: str | None = None):
    """A measure against model size, data or compute, both axes logarithmic.

    ``data`` maps name -> (x, y). With ``fit``, each series gets the power
    law y = a x^b fitted on its points with x up to ``upto`` (all points by
    default): a solid line over the points it was fitted on, dashed beyond
    them to the largest x or to ``extend``. Points used in the fit are
    filled; points held out are hollow, so the reader sees how far the
    extrapolation was checked. Names sit at the line ends. Returns the
    fitted (a, b) per name; say in the caption which points were fitted.
    """
    sizes = current().sizes
    names = list(data)
    colors = _series_colors(names, ours, "gray", marks="line")
    ax.set_xscale("log")
    ax.set_yscale("log")
    fits, ends = {}, []
    for name in names:
        x, y = (np.asarray(v, dtype=float) for v in data[name])
        mine = _is_ours(name, ours)
        color = colors[name]
        used = x <= upto if upto is not None else np.ones_like(x, dtype=bool)
        ax.plot(x[used], y[used], "o", linestyle="none", markersize=4.2 if mine else 3.6, markerfacecolor=color,
                markeredgecolor="white", markeredgewidth=0.5, zorder=4)
        if (~used).any():
            ax.plot(x[~used], y[~used], "o", linestyle="none", markersize=4.2 if mine else 3.6,
                    markerfacecolor="white", markeredgecolor=color, markeredgewidth=0.9, zorder=4)
        last = (x.max(), y[np.argmax(x)])
        if fit and used.sum() >= 2:
            a, b = power_fit(x[used], y[used])
            fits[name] = (a, b)
            inside = np.geomspace(x[used].min(), x[used].max(), 50)
            ax.plot(inside, a * inside ** b, color=color, linewidth=1.5 if mine else 1.0, zorder=3)
            far = max(x.max(), extend or 0)
            if far > x[used].max():
                beyond = np.geomspace(x[used].max(), far, 30)
                ax.plot(beyond, a * beyond ** b, color=color, linewidth=1.5 if mine else 1.0, linestyle=(0, (3, 2)),
                        zorder=3)
            last = (far, a * far ** b)
        ends.append((name, last, color, mine))
    ax.grid(axis="both", visible=True, which="major")
    lo, hi = ax.get_ylim()
    if hi / lo < 30:
        # Less than about a decade and a half: label the steps between powers of ten too.
        ax.yaxis.set_major_locator(mpl.ticker.LogLocator(subs=(1.0, 1.5, 2.0, 3.0, 5.0, 7.0)))
        ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    lines = []
    for _, (lx, ly), _, _ in ends:
        (h,) = ax.plot([lx], [ly], linestyle="none")
        lines.append(h)
    label_ends(ax, lines, names, bold=[e[3] for e in ends], fontsize=sizes["legend"])
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel + (_arrow(better, ylabel) if better else ""))
    return fits


# ---- points of a learned space ---------------------------------------------------


def embedding(ax, points, labels: Sequence[str], *, most: int | None = None, size: float = 2.0,
              alpha: float = 0.7, names: bool = True):
    """A 2-D map of points (t-SNE, UMAP, PCA), colored by class and each
    class named on the map.

    Classes take the theme's distinct colors in order of size; past ``most``
    (by default as many as the theme has colors), the smallest classes are
    folded into one grey "Other" class with a warning. Each class name sits
    at the median of its points, so no legend has to be matched by color.
    The axes have no ticks: in t-SNE and UMAP maps, distances between
    clusters and cluster sizes do not carry meaning, so say in the caption
    what the map can and cannot show.
    """
    ctx = current()
    theme = ctx.theme
    xy = np.asarray(points, dtype=float)
    labels = np.asarray([str(x) for x in labels])
    if xy.shape != (len(labels), 2):
        raise ValueError("points must have shape (n, 2), one row per label")
    classes, sizes_ = np.unique(labels, return_counts=True)
    classes = list(classes[np.argsort(-sizes_, kind="stable")])
    room = _palette_size(theme)
    most = min(most or room, room)
    other = ctx.say("other")
    if len(classes) > most:
        folded = classes[most - 1:]
        warnings.warn(f"{len(classes)} classes need more colors than can be told apart; "
                      f"the {len(folded)} smallest are drawn as {other!r}", stacklevel=2)
        keep = classes[:most - 1]
        labels = np.where(np.isin(labels, keep), labels, other)
        classes = keep + [other]
    palette = theme.categorical(len([c for c in classes if c != other]))
    colors = dict(zip([c for c in classes if c != other], palette))
    colors[other] = theme.grey(0.75)
    for c in [other] + [c for c in classes if c != other][::-1]:
        if c not in colors or not (labels == c).any():
            continue
        mask = labels == c
        ax.scatter(xy[mask, 0], xy[mask, 1], s=size ** 2, color=colors[c], alpha=alpha, linewidths=0,
                   zorder=2 if c == other else 3, rasterized=len(xy) > 5000)
    if names:
        for c in classes:
            mask = labels == c
            # "Other" gathers several clusters, so its median names none of them.
            if not mask.any() or c == other:
                continue
            mx, my = np.median(xy[mask], axis=0)
            # A white ground, not an outline effect: an outline turns the text into paths in the PDF.
            ax.text(mx, my, c, ha="center", va="center", fontsize=ctx.sizes["legend"], color=TEXT, zorder=5,
                    bbox={"boxstyle": "round,pad=0.12", "facecolor": "white", "edgecolor": "none", "alpha": 0.8})
        if other in classes:
            from matplotlib.lines import Line2D

            mark = Line2D([], [], marker="o", linestyle="none", markersize=size * 1.6, markerfacecolor=colors[other],
                          markeredgewidth=0)
            ax.legend([mark], [other], loc="lower right", frameon=False, handletextpad=0.2, borderaxespad=0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.set_aspect("equal", adjustable="datalim")
    for spine in ax.spines.values():
        spine.set_visible(False)
    return colors


GREYS_APART = 4  # greys a reader can tell apart in small marks (rule of thumb)


def _palette_size(theme) -> int:
    """How many distinct colors the theme can give, ours' hue excluded."""
    if theme.mode != "color":
        return GREYS_APART
    n = 1
    while n < 32:
        try:
            theme.categorical(n + 1)
        except ValueError:
            return n
        n += 1
    return n
