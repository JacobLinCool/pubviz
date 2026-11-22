r"""How loss falls with model size, and how far the fitted trend was checked.

    uv run python examples/figures/scaling.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where scaling.pdf goes (default examples/build/figs). The
losses are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/scaling}
      \caption{\textbf{Ours falls faster with size.} Validation loss
        against parameters. Lines are power laws fitted on the filled
        points (up to 1B parameters); hollow points were held out, and
        dashes extend the fit beyond the data.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

PARAMS = np.array([2e7, 6e7, 1.5e8, 4e8, 1e9, 3e9])
rng = np.random.default_rng(4)
DATA = {
    "Ours": (PARAMS, 9.1 * PARAMS ** -0.088 * np.exp(rng.normal(0, 0.006, 6))),
    "Baseline": (PARAMS, 8.2 * PARAMS ** -0.072 * np.exp(rng.normal(0, 0.006, 6))),
}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.72)
pv.scaling(ax, DATA, ours="Ours", upto=1e9, extend=1e10, xlabel="Parameters", ylabel="Validation loss",
           better="lower")
pv.save(fig, str(out_dir / "scaling"))
