r"""How precise a detector stays as it finds more of the positives.

    uv run python examples/figures/precision_recall.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where precision_recall.pdf goes (default
examples/build/figs). The scores are the same made-up ones as roc.py.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/precision_recall}
      \caption{\textbf{With 5\% positives, every method loses most of its
        precision before it finds half of them.} Precision--recall curves on
        the test set; average precision (AP) is in the legend, and the
        dashed line is the precision of guessing.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

rng = np.random.default_rng(11)
labels = rng.random(4000) < 0.05
DATA = {name: (labels, rng.normal(0, 1, 4000) + gap * labels)
        for name, gap in {"Ours": 2.2, "Prior": 1.7, "Baseline": 1.2}.items()}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.86)
pv.precision_recall(ax, DATA, ours="Ours")
pv.save(fig, str(out_dir / "precision_recall"))
