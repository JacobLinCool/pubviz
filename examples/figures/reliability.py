r"""Whether a model's confidence matches how often it is right.

    uv run python examples/figures/reliability.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where reliability.pdf goes (default examples/build/figs).
The predictions are drawn from fixed distributions for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/reliability}
      \caption{\textbf{After temperature scaling, confidence matches
        accuracy.} Top: accuracy of the top prediction in ten bins of
        confidence, 5,000 test images. Bottom: how many predictions fall in
        each bin.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Confidence of the top class, and whether it was right: the baseline is
# right less often than it claims, the scaled model about as often.
rng = np.random.default_rng(8)
conf = {"Ours (scaled)": 0.35 + 0.65 * rng.beta(4, 1.4, 5000), "Baseline": 0.35 + 0.65 * rng.beta(6, 1.0, 5000)}
truth = {"Ours (scaled)": lambda p: p, "Baseline": lambda p: p ** 2.2}
DATA = {name: (rng.random(5000) < truth[name](p), p) for name, p in conf.items()}

pv.use(layout)
fig, (ax, counts) = pv.figure("column", ratio=1.15, nrows=2, sharex=True, height_ratios=[3, 1])
pv.reliability(ax, DATA, ours="Ours (scaled)", counts_ax=counts)
pv.save(fig, str(out_dir / "reliability"))
