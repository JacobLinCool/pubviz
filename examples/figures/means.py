r"""The level of each method with the uncertainty of its mean.

    uv run python examples/figures/means.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where means.pdf, means-gradient.pdf and means-sections.pdf
go (default examples/build/figs). The numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/means}
      \caption{\textbf{Ours has the highest mean accuracy.} Mean over ten
        seeds with its 95\% interval.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Accuracy (%) of ten seeds per method, drawn from a fixed generator.
rng = np.random.default_rng(7)
RUNS = {
    "Ours": list(rng.normal(78.6, 0.9, 10)),
    "Adapter": list(rng.normal(76.8, 1.1, 10)),
    "LoRA": list(rng.normal(75.6, 1.4, 10)),
    "Full fine-tune": list(rng.normal(76.2, 1.8, 10)),
}

pv.use(layout)
# A point and the 95% t-interval of the mean (a list of runs goes through
# mean_ci; a tuple (mean, low, high) is drawn as given). The runs themselves
# are drawn faintly underneath: the interval of a mean alone makes readers
# overstate how often one method beats another.
fig, ax = pv.figure("column", ratio=0.36)
pv.means(ax, RUNS, ours="Ours", xlabel="Accuracy (%)")
pv.save(fig, str(out_dir / "means"))
# The same estimates as gradients: full inside the interval, fading outside.
fig, ax = pv.figure("column", ratio=0.36)
pv.means(ax, RUNS, ours="Ours", show="gradient", xlabel="Accuracy (%)")
pv.save(fig, str(out_dir / "means-gradient"))

# Two levels: each model with its settings, given as (model, setting) pairs.
# Each model is a section: its name stands left of its rows, a gap comes
# before it, and every other section has a light band. Time (s) to solve a
# task, twelve tasks per setting.
rng = np.random.default_rng(3)
TIMES = {
    ("Prior", "3 passes"): list(rng.normal(41, 14, 12)),
    ("Ours", "1 pass"): list(rng.normal(16, 7, 12)),
    ("Ours", "2 passes"): list(rng.normal(26, 9, 12)),
    ("Ours", "3 passes"): list(rng.normal(37, 12, 12)),
    ("Ours", "5 passes"): list(rng.normal(42, 12, 12)),
    ("Ours", "10 passes"): list(rng.normal(40, 11, 12)),
}
fig, ax = pv.figure("column", ratio=0.5)
pv.means(ax, TIMES, ours=("Ours", "3 passes"), xlabel="Time to solve (s)")
pv.save(fig, str(out_dir / "means-sections"))
