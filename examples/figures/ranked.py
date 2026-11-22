r"""One score per language for each system: too many groups for bars.

    uv run python examples/figures/ranked.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where ranked.pdf goes (default examples/build/figs). The
scores are made up for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/ranked}
      \caption{\textbf{Ours gains most on the languages where the baselines
        are weakest.} Accuracy on each language of the test set, sorted by
        ours.}
    \end{figure}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Accuracy (%) per language: Ours, Prior, Baseline.
SCORES = {
    "English": (88.1, 87.4, 86.9), "German": (84.0, 82.7, 81.2), "French": (84.6, 83.9, 82.5),
    "Spanish": (85.2, 84.1, 83.0), "Chinese": (80.3, 77.2, 74.8), "Japanese": (78.9, 75.0, 72.6),
    "Korean": (77.5, 73.1, 70.4), "Arabic": (76.2, 71.5, 68.0), "Hindi": (74.8, 69.6, 65.9),
    "Turkish": (75.6, 71.8, 69.3), "Finnish": (77.0, 74.2, 72.1), "Swahili": (68.4, 60.2, 55.7),
    "Yoruba": (62.1, 52.8, 48.3),
}
DATA = {lang: dict(zip(("Ours", "Prior", "Baseline"), v)) for lang, v in SCORES.items()}

pv.use(layout)
fig, ax = pv.figure("column", ratio=0.95)
pv.ranked(ax, DATA, ours="Ours", xlabel="Accuracy (%)")
pv.save(fig, str(out_dir / "ranked"))
