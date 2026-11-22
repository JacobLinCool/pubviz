r"""How many runs of each method spread: box plots, violins or histograms.

    uv run python examples/figures/distributions.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where distributions.pdf and its strip, violin and histogram
versions go (default examples/build/figs). The numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/distributions}
      \caption{\textbf{Ours is faster on most requests, with a shorter tail.}
        Latency of 400 requests per method. Boxes span the middle half, the
        line and number are the median, whiskers reach 1.5 box lengths and
        dots are requests beyond them.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Latency (ms) of 400 requests per method, drawn from a fixed generator. The
# baseline has a second, slow mode that a box plot hides and a violin shows.
rng = np.random.default_rng(3)
RUNS = {
    "Ours": rng.lognormal(3.0, 0.25, 400),
    "Cache": rng.lognormal(3.15, 0.3, 400),
    "Baseline": np.concatenate([rng.lognormal(3.1, 0.2, 280), rng.lognormal(3.9, 0.15, 120)]),
}

pv.use(layout)
for kind, stem in [("box", "distributions"), ("strip", "distributions-strip"),
                   ("violin", "distributions-violin"), ("histogram", "distributions-histogram")]:
    fig, ax = pv.figure("column", ratio=0.36)
    pv.distributions(ax, RUNS, ours="Ours", kind=kind, fmt="{:.0f}", xlabel="Latency (ms)")
    pv.save(fig, str(out_dir / stem))
