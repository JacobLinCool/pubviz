r"""Which source words each target word attends to.

    uv run python examples/figures/attention.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where attention.pdf goes (default examples/build/figs). The
weights are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/attention}
      \caption{\textbf{Cross-attention follows the word order except where
        German moves the verb.} Weights of the last decoder layer, averaged
        over heads, for one test sentence.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

SOURCE = ["I", "have", "seen", "the", "film", "today", "."]
TARGET = ["Ich", "habe", "heute", "den", "Film", "gesehen", "."]
# For each target word, the source word it mostly aligns with.
ALIGN = [0, 1, 5, 3, 4, 2, 6]

rng = np.random.default_rng(3)
logits = rng.normal(0, 0.6, (len(TARGET), len(SOURCE)))
for t, s in enumerate(ALIGN):
    logits[t, s] += 3.0
weights = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.62)
pv.attention(ax, weights, SOURCE, TARGET)
pv.save(fig, str(out_dir / "attention"))
