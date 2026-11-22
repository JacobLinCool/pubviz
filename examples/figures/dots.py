r"""Every run of each method, a handful per method, with the mean marked.

    uv run python examples/figures/dots.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where dots.pdf goes (default examples/build/figs). The
numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/dots}
      \caption{\textbf{Ours scores higher on every seed.} Accuracy of each of
        five seeds; the bar and the number are the mean.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Accuracy (%) of five seeds per method. With so few runs, every run is shown:
# a box plot or a density of five numbers would summarize too little.
RUNS = {
    "Ours": [78.4, 79.1, 77.9, 78.8, 79.4],
    "Adapter": [76.2, 77.5, 75.8, 76.9, 77.0],
    "LoRA": [75.1, 76.8, 74.2, 76.0, 75.5],
    "Full fine-tune": [77.0, 74.9, 76.3, 75.4, 77.8],
}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.42)
pv.dots(ax, RUNS, ours="Ours", xlabel="Accuracy (%)")
pv.save(fig, str(out_dir / "dots"))
