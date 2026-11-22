r"""How often a verification system misses a target and accepts an impostor.

    uv run python examples/figures/det.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where det.pdf goes (default examples/build/figs). The
scores are drawn from fixed normal distributions for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/det}
      \caption{\textbf{Ours has fewer misses at every false alarm rate.}
        DET curves of speaker verification on 1,000 target and 9,000
        impostor trials; the dot on each curve is its equal error rate.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

rng = np.random.default_rng(5)
target = np.r_[np.ones(1000), np.zeros(9000)]
DATA = {name: (target, rng.normal(0, 1, 10000) + gap * target)
        for name, gap in {"Ours": 4.1, "x-vector": 3.5, "i-vector": 2.9}.items()}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.9)
pv.det(ax, DATA, ours="Ours")
pv.save(fig, str(out_dir / "det"))
