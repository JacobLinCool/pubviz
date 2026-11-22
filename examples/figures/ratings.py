r"""How listeners rated each system, and how often they preferred ours.

    uv run python examples/figures/ratings.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where ratings.pdf and ratings-preference.pdf go (default
examples/build/figs). The counts are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/ratings}
      \caption{\textbf{Listeners rated ours good or excellent about as often
        as the recordings.} Answers on a five-point quality scale, 20
        listeners by 30 sentences per system; the numbers are the shares
        below and above ``Fair''.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

SCALE = ["Bad", "Poor", "Fair", "Good", "Excellent"]
# Number of answers at each level, 600 per system.
ANSWERS = {
    "Recording": [4, 12, 60, 230, 294],
    "Ours": [7, 25, 92, 260, 216],
    "Prior": [21, 74, 182, 225, 98],
    "Baseline": [48, 131, 210, 160, 51],
}
# Side-by-side preference of ours against each other system, 300 judgments each.
PREFERENCE = {"vs Baseline": [41, 52, 207], "vs Prior": [78, 85, 137], "vs Recording": [131, 102, 67]}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.42)
pv.ratings(ax, ANSWERS, SCALE, ours="Ours")
pv.save(fig, str(out_dir / "ratings"))
# Win / tie / loss: the tie is set aside, so wins and losses share one baseline.
fig, ax = pv.figure("column", ratio=0.34)
pv.ratings(ax, PREFERENCE, ["Ours worse", "No preference", "Ours better"], neutral="aside")
pv.save(fig, str(out_dir / "ratings-preference"))
