"""Matrices of classes or tokens.

- ``confusion``  Which classes a classifier mixes up: true class by
  predicted class.
- ``attention``  How strongly each item of one sequence attends to, or is
  aligned with, each item of another (attention weights, a TTS or ASR
  alignment).

Both shade a cell darker for a larger value, in the accent hue, on a scale
that keeps lightness in one direction, so the order survives a grey print.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib as mpl
import numpy as np

from .color import contrast
from .plots import EDGE, TEXT, _fit_rows
from .style import current


def _ink(cmap, t: float) -> str:
    fill = mpl.colors.to_hex(cmap(min(max(t, 0.0), 1.0)))
    return TEXT if contrast(TEXT, fill) >= contrast("#FFFFFF", fill) else "#FFFFFF"


def _bare(ax) -> None:
    ax.tick_params(length=0)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)


def _turn_if_crowded(ax, angle: int) -> None:
    """Turn the x tick labels by ``angle`` when, set level, any two would touch."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in ax.get_xticklabels() if t.get_text()]
    gap = 2 * fig.dpi / 72
    if any(b.x0 < a.x1 + gap for a, b in zip(boxes, boxes[1:])):
        for t in ax.get_xticklabels():
            t.set(rotation=angle, ha="right" if angle < 90 else "center", rotation_mode="anchor" if angle < 90 else "default")


def confusion(ax, counts, labels: Sequence[str], *, normalize: str = "row", values: str | None = None,
              fmt: str = "{:.0f}", diagonal: bool = True, colorbar: bool = False,
              xlabel: str | None = None, ylabel: str | None = None):
    """A confusion matrix: one row per true class, one column per predicted class.

    ``counts`` holds how many cases of the row's class were predicted as the
    column's class. ``normalize``:

    - ``"row"`` (default): each row as shares of that class, so the diagonal
      is each class's recall and rows of rare and common classes compare.
    - ``"column"``: each column as shares of that prediction (precision).
    - ``"none"``: the counts.

    The shading runs from 0 to 100% whatever the data (from 0 to the largest
    count for ``"none"``), so the same shade means the same share in every
    figure. ``values`` prints ``"share"`` (percent), ``"count"``, ``"both"``
    (share over count) or ``"none"``; by default both up to six classes and
    the share beyond, where two numbers no longer fit a cell. A cell with no
    cases shows a dash. ``diagonal`` outlines the cells of correct
    predictions. Axis titles say which side is the true class and which the
    prediction, in the paper's language.
    """
    if normalize not in ("row", "column", "none"):
        raise ValueError("normalize must be 'row', 'column' or 'none'")
    if values is None:
        values = "both" if len(labels) <= 6 else "share"
    if values not in ("share", "count", "both", "none"):
        raise ValueError("values must be 'share', 'count', 'both' or 'none'")
    ctx = current()
    sizes = ctx.sizes
    counts = np.asarray(counts, dtype=float)
    n = len(labels)
    if counts.shape != (n, n):
        raise ValueError(f"counts must be {n} x {n} for {n} labels, got {counts.shape}")
    if normalize == "row":
        total = counts.sum(axis=1, keepdims=True)
        shown = np.divide(counts, total, out=np.zeros_like(counts), where=total > 0)
        lo, hi = 0.0, 1.0
    elif normalize == "column":
        total = counts.sum(axis=0, keepdims=True)
        shown = np.divide(counts, total, out=np.zeros_like(counts), where=total > 0)
        lo, hi = 0.0, 1.0
    else:
        shown = counts
        lo, hi = 0.0, float(counts.max()) or 1.0
    cmap = ctx.theme.cmap()
    image = ax.imshow(shown, cmap=cmap, vmin=lo, vmax=hi, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(n), labels)
    ax.set_yticks(range(n), labels)
    _bare(ax)
    _turn_if_crowded(ax, 45)
    size = sizes["small"] + (0.5 if n <= 6 else 0)
    for (r, c), v in np.ndenumerate(shown):
        if values == "none":
            break
        share = fmt.format(100 * v) if normalize != "none" else fmt.format(v)
        count = f"{counts[r, c]:.0f}"
        text = {"share": share, "count": count, "both": f"{share}\n({count})"}[values]
        if normalize == "none" and values in ("share", "both"):
            text = count
        if counts[r, c] == 0:
            text = "\u2013"
        ax.text(c, r, text, ha="center", va="center", fontsize=size, linespacing=0.95,
                color=_ink(cmap, (v - lo) / (hi - lo)), fontweight="bold" if (diagonal and r == c) else "normal")
    if diagonal:
        for i in range(n):
            ax.add_patch(mpl.patches.Rectangle((i - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=EDGE,
                                               linewidth=0.8, zorder=3))
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("predicted"))
    ax.set_ylabel(ylabel if ylabel is not None else ctx.say("true"))
    # Two lines of numbers per cell need about two and a half lines of room.
    _fit_rows(ax, n, lines=2.4 if values == "both" else 1.5)
    if colorbar:
        bar = ax.figure.colorbar(image, ax=ax, fraction=0.05, pad=0.02)
        bar.outline.set_visible(False)
        bar.ax.tick_params(labelsize=sizes["tick"], length=2)
        if normalize != "none":
            bar.set_ticks([0, 0.5, 1], labels=["0", "50", "100"])
            bar.set_label(ctx.say("share"))
    return image


def _thin(n: int, most: int) -> list[int]:
    step = max(1, int(np.ceil(n / most)))
    return list(range(0, n, step))


def attention(ax, weights, x_labels: Sequence[str] | None = None, y_labels: Sequence[str] | None = None, *,
              colorbar: bool = True, label: str | None = None, most: int = 40,
              xlabel: str | None = None, ylabel: str | None = None):
    """Weights between two sequences: one row per item of the output (or
    query) sequence, one column per item of the input (or key) sequence.

    No numbers are printed: the pattern, such as a diagonal alignment, is the
    point. The scale runs from 0 to the largest weight. ``x_labels`` and
    ``y_labels`` name the items (tokens, characters, frames); past ``most``
    items only every few are named. Say in the caption which layer and head,
    or which average of them, the weights come from; attention weights alone
    do not show which inputs the output depends on.
    """
    ctx = current()
    sizes = ctx.sizes
    data = np.asarray(weights, dtype=float)
    rows, cols = data.shape
    cmap = ctx.theme.cmap()
    image = ax.imshow(data, cmap=cmap, vmin=0.0, vmax=float(np.nanmax(data)) or 1.0, aspect="auto",
                      interpolation="nearest")
    _bare(ax)
    for labels, count, setter, axis in ((x_labels, cols, ax.set_xticks, "x"), (y_labels, rows, ax.set_yticks, "y")):
        if labels is None:
            continue
        if len(labels) != count:
            raise ValueError(f"{len(labels)} {axis} labels for {count} {'columns' if axis == 'x' else 'rows'}")
        keep = _thin(count, most)
        shown = [labels[i] for i in keep]
        setter(keep, shown)
        if axis == "x":
            _turn_if_crowded(ax, 90)
    if x_labels is None:
        ax.set_xticks([])
    if y_labels is None:
        ax.set_yticks([])
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if colorbar:
        bar = ax.figure.colorbar(image, ax=ax, fraction=0.05, pad=0.02)
        bar.outline.set_visible(False)
        bar.ax.tick_params(labelsize=sizes["tick"], length=2)
        bar.set_label(label if label is not None else ctx.say("weight"))
    return image
