r"""What each method gains on one measure and pays on another.

    uv run python examples/figures/tradeoff.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where tradeoff.pdf goes (default examples/build/figs). The
numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/tradeoff}
      \caption{\textbf{Ours moves the accuracy--latency frontier.} The dashed
        line joins methods that no other method beats on both measures.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Latency per sample (ms) and accuracy (%) of each method.
POINTS = {
    "Base": (12, 61.0),
    "Prior A": (31, 66.2),
    "Prior B": (18, 63.0),
    "Large": (85, 69.5),
    "Distilled": (8, 57.4),
    "Ours": (21, 68.3),
}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.66)
# The better directions decide the frontier and the arrows on the axis labels.
pv.tradeoff(ax, POINTS, ours="Ours", better_x="lower", better_y="higher",
            xlabel="Latency per sample (ms)", ylabel="Accuracy (%)")
pv.save(fig, str(out_dir / "tradeoff"))
