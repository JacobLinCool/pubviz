r"""How much each change helps or hurts, with the interval of the change.

    uv run python examples/figures/deltas.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where deltas.pdf goes (default examples/build/figs). The
numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/deltas}
      \caption{\textbf{The adapter matters most; data mixing does not clearly help.}
        Accuracy change against the full model with 95\% intervals of the
        change over five seeds.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Accuracy of each variant minus the full model, one number per seed (the same
# five seeds for both). The interval of these differences is the interval of
# the change itself; two separate intervals of the variants are not.
CHANGES = {
    "without adapter": [-3.9, -2.6, -3.4, -2.9, -3.5],
    "without warm-up": [-1.4, -0.3, -1.2, -0.6, -0.9],
    "without data mixing": [0.9, -0.4, 0.6, -0.3, 0.3],
    "larger batch": [1.1, 0.4, 1.2, 0.5, 0.9],
}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.42)
# mean_ci gives (mean, low, high) over the seeds: a 95% t-interval. The key
# above the plot names each color beside its mark, so the caption need not.
pv.deltas(ax, {name: pv.mean_ci(runs) for name, runs in CHANGES.items()},
          xlabel="Accuracy change (points)")
pv.save(fig, str(out_dir / "deltas"))
