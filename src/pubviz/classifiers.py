"""How a classifier or detector behaves across every threshold.

- ``roc``               True against false positive rate, with the chance line.
- ``precision_recall``  Precision against recall, with the line a classifier
  that guesses reaches: the share of positives.
- ``det``               Miss against false alarm rate on normal-deviate
  scales, as in speaker verification, with the equal error rate.
- ``reliability``       Observed frequency against predicted probability,
  with the line of a perfectly calibrated model.

Each takes, per method, the true labels (1 for the positive class) and the
scores the method gave, computes the curve and prints its summary (area,
average precision, equal error rate or calibration error) beside the name.
Ours wears the accent and every compared method a grey; the legend sits
where the curves are not.
"""

from __future__ import annotations

from collections.abc import Mapping
from statistics import NormalDist

import numpy as np

from .plots import REFERENCE, _is_ours, _series_colors
from .style import current

DASH = (0, (3, 2))


def _counts(labels, scores):
    """True and false positives at each distinct threshold, highest first."""
    y = np.asarray(labels).astype(bool)
    s = np.asarray(scores, dtype=float)
    if y.shape != s.shape:
        raise ValueError("labels and scores must have the same length")
    if y.all() or not y.any():
        raise ValueError("the labels need both classes")
    order = np.argsort(-s, kind="mergesort")
    s, y = s[order], y[order]
    last = np.r_[np.nonzero(np.diff(s))[0], len(s) - 1]
    tp = np.cumsum(y)[last].astype(float)
    fp = np.cumsum(~y)[last].astype(float)
    return tp, fp, float(y.sum()), float((~y).sum())


def rates(labels, scores):
    """False positive rate, true positive rate and the area under the ROC curve."""
    tp, fp, pos, neg = _counts(labels, scores)
    fpr = np.r_[0.0, fp / neg]
    tpr = np.r_[0.0, tp / pos]
    return fpr, tpr, float(np.trapezoid(tpr, fpr))


def _draw(ax, curves: Mapping, ours, style: str = "line"):
    names = list(curves)
    colors = _series_colors(names, ours, "gray", marks="line")
    order = [n for n in names if not _is_ours(n, ours)] + [n for n in names if _is_ours(n, ours)]
    handles = {}
    for name in order:
        x, y, text = curves[name]
        mine = _is_ours(name, ours)
        kwargs = {"color": colors[name], "linewidth": 1.6 if mine else 1.0, "zorder": 4 if mine else 3}
        if style == "step":
            (line,) = ax.step(x, y, where="post", **kwargs)
        else:
            (line,) = ax.plot(x, y, **kwargs)
        handles[name] = (line, f"{name} ({text})")
    return [handles[n][0] for n in names], [handles[n][1] for n in names]


def _legend(ax, handles, labels, names, ours, reference=None):
    """The legend where the curves leave room ("best"), with the dashed
    reference line as its last entry; ours in bold."""
    if reference is not None:
        handles = [*handles, reference[0]]
        labels = [*labels, reference[1]]
    legend = ax.legend(handles, labels, loc="best", frameon=True, framealpha=0.9, edgecolor="none",
                       handlelength=1.4, borderaxespad=0.4)
    for text, name in zip(legend.get_texts(), names):
        if _is_ours(name, ours):
            text.set_fontweight("bold")
    return legend


def _unit_square(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.0)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(axis="both", visible=True)


def roc(ax, data: Mapping, *, ours=None, fmt: str = "{:.3f}", xlabel: str | None = None,
        ylabel: str | None = None, legend: bool = True):
    """ROC curves: one per method, from ``data`` mapping name -> (labels, scores).

    Both axes run from 0 to 1 at the same scale; the dashed diagonal is what
    a classifier that guesses reaches. The area under each curve (AUC) is
    printed beside its name. When positives are rare, a large area can hide
    many false positives among few true ones: show ``precision_recall`` too.
    """
    ctx = current()
    curves = {}
    for name, (labels, scores) in data.items():
        fpr, tpr, area = rates(labels, scores)
        curves[name] = (fpr, tpr, "AUC " + fmt.format(area))
    (chance,) = ax.plot([0, 1], [0, 1], linestyle=DASH, color=REFERENCE, linewidth=0.8, zorder=1)
    handles, labels = _draw(ax, curves, ours)
    _unit_square(ax)
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("fpr"))
    ax.set_ylabel(ylabel if ylabel is not None else ctx.say("tpr"))
    if legend:
        _legend(ax, handles, labels, list(data), ours, (chance, ctx.say("chance")))
    return {n: c[2] for n, c in curves.items()}


def precision_recall(ax, data: Mapping, *, ours=None, fmt: str = "{:.3f}", xlabel: str | None = None,
                     ylabel: str | None = None, legend: bool = True):
    """Precision–recall curves, from ``data`` mapping name -> (labels, scores).

    The dashed line is the share of positives: the precision of a classifier
    that guesses, which is not 0.5 when the classes are unbalanced. Average
    precision (AP, the area under the steps) is printed beside each name.
    """
    ctx = current()
    curves = {}
    shares = set()
    for name, (labels, scores) in data.items():
        tp, fp, pos, neg = _counts(labels, scores)
        precision = np.r_[1.0, tp / (tp + fp)]
        recall = np.r_[0.0, tp / pos]
        ap = float(np.sum(np.diff(recall) * precision[1:]))
        curves[name] = (recall, precision, "AP " + fmt.format(ap))
        shares.add(round(pos / (pos + neg), 6))
    for share in shares:
        guess = ax.axhline(share, linestyle=DASH, color=REFERENCE, linewidth=0.8, zorder=1)
    handles, labels = _draw(ax, curves, ours, style="step")
    _unit_square(ax)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("recall"))
    ax.set_ylabel(ylabel if ylabel is not None else ctx.say("precision"))
    if legend:
        text = ctx.say("positives") + (f" ({min(shares):.2f})" if len(shares) == 1 else "")
        _legend(ax, handles, labels, list(data), ours, (guess, text))
    return {n: c[2] for n, c in curves.items()}


DET_TICKS = (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 40)  # percent


def det(ax, data: Mapping, *, ours=None, fmt: str = "{:.2f}", lim=(0.1, 40), xlabel: str | None = None,
        ylabel: str | None = None, legend: bool = True):
    """DET curves (Martin et al. 1997): miss rate against false alarm rate,
    both on a normal-deviate scale, from ``data`` mapping name ->
    (labels, scores) with 1 for a target trial.

    On these scales the curves of normally distributed scores are straight
    lines, and the low error rates where systems differ spread out. The
    dashed diagonal joins the points where both rates are equal; the equal
    error rate (EER) is marked on each curve and printed beside its name.
    ``lim`` is the range of both axes in percent.
    """
    ctx = current()
    probit = NormalDist().inv_cdf
    lo, hi = lim[0] / 100, lim[1] / 100

    def scale(p):
        return np.array([probit(min(max(v, lo / 4), 1 - lo / 4)) for v in np.atleast_1d(p)])

    curves, eers = {}, {}
    for name, (labels, scores) in data.items():
        fpr, tpr, _ = rates(labels, scores)
        miss = 1 - tpr
        k = int(np.argmin(np.abs(miss - fpr)))
        eer = float((miss[k] + fpr[k]) / 2)
        eers[name] = eer
        curves[name] = (scale(fpr), scale(miss), "EER " + fmt.format(100 * eer) + "%")
    a, b = scale([lo])[0], scale([hi])[0]
    ax.plot([a, b], [a, b], linestyle=DASH, color=REFERENCE, linewidth=0.8, zorder=1)
    handles, labels = _draw(ax, curves, ours)
    for line, eer in zip(handles, eers.values()):
        point = scale([eer])[0]
        ax.plot([point], [point], "o", markersize=3.6, color=line.get_color(), markeredgecolor="white",
                markeredgewidth=0.5, zorder=5)
    ticks = [t for t in DET_TICKS if lim[0] <= t <= lim[1]]
    for setter in (ax.set_xticks, ax.set_yticks):
        setter(scale([t / 100 for t in ticks]), [f"{t:g}" for t in ticks])
    ax.set_xlim(a, b)
    ax.set_ylim(a, b)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(axis="both", visible=True)
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("false_alarm"))
    ax.set_ylabel(ylabel if ylabel is not None else ctx.say("miss"))
    if legend:
        _legend(ax, handles, labels, list(data), ours)
    return eers


def reliability(ax, data: Mapping, *, ours=None, bins: int = 10, fmt: str = "{:.3f}", counts_ax=None,
                xlabel: str | None = None, ylabel: str | None = None, legend: bool = True):
    """Reliability diagrams, from ``data`` mapping name -> (labels, probabilities).

    Cases are put into ``bins`` equal-width bins of predicted probability;
    each point is a bin's mean prediction against how often its cases were
    positive, so a calibrated model lies on the dashed diagonal. Bins with no
    cases are left out. The expected calibration error (ECE: the gap between
    the two, weighted by the cases in each bin) is printed beside each name.
    A bin with few cases gives a noisy point: pass ``counts_ax`` (a second
    axes, for instance under this one) to show how many cases each bin holds.
    For a model's confidence in its top class, pass whether each top-class
    prediction was correct as the labels and the confidence as the
    probabilities.
    """
    ctx = current()
    edges = np.linspace(0, 1, bins + 1)
    curves, held = {}, {}
    for name, (labels, probs) in data.items():
        y = np.asarray(labels, dtype=float)
        p = np.asarray(probs, dtype=float)
        which = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
        n = np.bincount(which, minlength=bins).astype(float)
        mean_p = np.bincount(which, weights=p, minlength=bins)
        mean_y = np.bincount(which, weights=y, minlength=bins)
        used = n > 0
        conf, freq = mean_p[used] / n[used], mean_y[used] / n[used]
        ece = float(np.sum(n[used] * np.abs(conf - freq)) / n.sum())
        curves[name] = (conf, freq, "ECE " + fmt.format(ece))
        held[name] = n
    (diagonal,) = ax.plot([0, 1], [0, 1], linestyle=DASH, color=REFERENCE, linewidth=0.8, zorder=1)
    handles, labels = _draw(ax, curves, ours)
    for line in handles:
        line.set_marker("o")
        line.set_markersize(2.8)
    _unit_square(ax)
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("confidence"))
    ax.set_ylabel(ylabel if ylabel is not None else ctx.say("observed"))
    if legend:
        _legend(ax, handles, labels, list(data), ours, (diagonal, ctx.say("calibrated")))
    if counts_ax is not None:
        names = list(data)
        colors = _series_colors(names, ours, "gray", marks="line")
        width = 1 / bins / max(1, len(names))
        for i, name in enumerate(names):
            offset = edges[:-1] + width * i
            counts_ax.bar(offset, held[name], width=width * 0.9, align="edge", color=colors[name], linewidth=0)
        counts_ax.set_xlim(0, 1)
        counts_ax.set_ylabel(ctx.say("cases"))
        counts_ax.set_xlabel(ax.get_xlabel())
        ax.set_xlabel("")
    return {n: c[2] for n, c in curves.items()}
