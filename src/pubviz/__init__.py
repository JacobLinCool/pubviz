"""pubviz: figures and tables for research papers that share one color theme.

    import pubviz as pv

    pv.use("paper/main.pubviz.json")   # the layout file pubviz.sty writes
    fig, ax = pv.figure("column")
    pv.bars(ax, scores, ours="Ours", ylabel="Accuracy (%)")
    pv.save(fig, "paper/figs/scores")
"""

from .color import contrast, hex_to_oklch, lightness, oklch_to_hex, to_gray
from .layout import PRESETS as LAYOUTS
from .layout import Layout
from .classifiers import det, precision_recall, reliability, roc
from .matrices import attention, confusion
from .pictures import images, overlay, spectrogram, waveform
from .plots import (bars, curves, deltas, distributions, dots, embedding, heatmap, label_ends, mean_ci,
                    means, pareto, power_fit, ranked, scaling, tradeoff)
from .ratings import ratings
from .style import current, figure, panel_labels, save, use, width
from .table import pvtable
from .text import pvshade
from .theme import PRESETS as ACCENTS
from .theme import Theme

__all__ = [
    "ACCENTS", "LAYOUTS", "Layout", "Theme",
    "attention", "bars", "confusion", "contrast", "current", "curves", "deltas", "det", "distributions",
    "dots", "embedding", "figure", "heatmap", "hex_to_oklch", "images", "label_ends", "lightness",
    "mean_ci", "means", "oklch_to_hex", "overlay", "panel_labels", "pareto", "power_fit",
    "precision_recall", "pvshade", "pvtable", "ranked", "ratings", "reliability", "roc", "save",
    "scaling", "spectrogram", "to_gray", "tradeoff", "use", "waveform", "width",
]
__version__ = "0.1.0"
