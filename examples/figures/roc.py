r"""How a detector trades true against false positives over every threshold.

    uv run python examples/figures/roc.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where roc.pdf goes (default examples/build/figs). The scores
are drawn from fixed normal distributions for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/roc}
      \caption{\textbf{Ours ranks positives above negatives more often.}
        ROC curves on the test set (5\% positives); the area under each
        curve is in the legend.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# 4,000 test cases, 5% positive; each method's score separates them by a different margin.
rng = np.random.default_rng(11)
labels = rng.random(4000) < 0.05
DATA = {name: (labels, rng.normal(0, 1, 4000) + gap * labels)
        for name, gap in {"Ours": 2.2, "Prior": 1.7, "Baseline": 1.2}.items()}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.86)
pv.roc(ax, DATA, ours="Ours")
pv.save(fig, str(out_dir / "roc"))
