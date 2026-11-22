r"""Values over two factors at once.

    uv run python examples/figures/heatmap.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where heatmap.pdf goes (default examples/build/figs). The
numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/heatmap}
      \caption{\textbf{Larger models gain more from more data.} Accuracy (\%)
        by model size and training tokens; the best value of each column is bold.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

SIZES = ["125M", "350M", "1.3B"]  # rows
TOKENS = ["10B", "30B", "100B", "300B"]  # columns
ACCURACY = [  # accuracy (%), one row per model size
    [41.2, 44.0, 45.1, 45.6],
    [45.8, 49.3, 51.7, 52.4],
    [48.1, 53.9, 57.6, 59.8],
]

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.5)
# mark="column" sets the best value of each column in bold, as a table would.
pv.heatmap(ax, ACCURACY, SIZES, TOKENS, mark="column")
ax.set_xlabel("Training tokens")
ax.set_ylabel("Model size")
pv.save(fig, str(out_dir / "heatmap"))
