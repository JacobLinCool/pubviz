r"""Which classes a classifier mixes up.

    uv run python examples/figures/confusion.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where confusion.pdf goes (default examples/build/figs). The
numbers are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/confusion}
      \caption{\textbf{Happy speech is most often taken for neutral.}
        Share of each true emotion (rows) given each predicted label;
        the diagonal is each class's recall. 1,240 test utterances.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

LABELS = ["Neutral", "Happy", "Sad", "Angry"]
# How many utterances of each true emotion (rows) got each predicted label (columns).
COUNTS = [
    [352, 41, 39, 18],
    [88, 201, 9, 22],
    [27, 4, 236, 3],
    [21, 19, 2, 158],
]

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.72)
# Rows as shares of each true class, so rare and common classes compare;
# the shading runs from 0 to 100% whatever the data.
pv.confusion(ax, COUNTS, LABELS)
pv.save(fig, str(out_dir / "confusion"))
