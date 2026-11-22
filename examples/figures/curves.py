r"""How a measure moves over training, with the spread over seeds.

    uv run python examples/figures/curves.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where curves.pdf goes (default examples/build/figs). The
curves are made up for illustration and seeded, so every run draws the same
figure.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/curves}
      \caption{\textbf{Ours reaches the final reward of the best baseline in
        less than half the steps.} Mean of three seeds with 95\% intervals.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

steps = np.arange(0, 2001, 25)
rng = np.random.default_rng(7)


def seeds(rate, top, n=3):
    """n runs of a made-up reward curve rising toward top, shape (n, len(steps))."""
    mean = top * (1 - np.exp(-steps / rate))
    return mean + rng.normal(0, 0.012, (n, len(steps))).cumsum(axis=1) * 0.15


# Reward over training, one row per seed. A single run is a plain array of
# len(steps); it draws a line without a band (say "single seed" in the caption).
REWARD = {"Base": seeds(900, 0.62), "Prior A": seeds(700, 0.70), "Ours": seeds(350, 0.74)}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.62)
pv.curves(ax, steps, REWARD, ours="Ours", xlabel="Training step", ylabel="Reward")
pv.save(fig, str(out_dir / "curves"))
