r"""Where a model puts its inputs: a 2-D map of the embeddings by class.

    uv run python examples/figures/embedding.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where embedding.pdf goes (default examples/build/figs). The
points are drawn from fixed distributions for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/embedding}
      \caption{\textbf{Utterances of the same speaker group together.}
        t-SNE map of 1,000 speaker embeddings (perplexity 30). Distances
        between groups and their sizes carry no meaning in this map.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

rng = np.random.default_rng(9)
CENTRES = {"Speaker A": (0, 0), "Speaker B": (6, 2), "Speaker C": (-5, 5), "Speaker D": (3, -6)}
points, labels = [], []
for name, (cx, cy) in CENTRES.items():
    n = int(rng.integers(180, 280))
    angle = rng.uniform(0, np.pi)
    stretch = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]) @ np.diag([1.6, 0.8])
    points.append(rng.normal(0, 1, (n, 2)) @ stretch.T + (cx, cy))
    labels += [name] * n

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.75)
pv.embedding(ax, np.concatenate(points), labels)
pv.save(fig, str(out_dir / "embedding"))
