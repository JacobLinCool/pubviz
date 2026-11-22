r"""Which method wins, benchmark by benchmark: grouped bars.

    uv run python examples/figures/bars.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where bars.pdf and bars-sections.pdf go (default
examples/build/figs). The numbers are made up for illustration.

Five groups of four bars need the full text width, so in a two-column paper
the figure spans both columns. The legend names every color, so the caption
states only the finding and the setup:

    \begin{figure*}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/bars}
      \caption{\textbf{Ours scores highest on four of five benchmarks.}
        Accuracy on each benchmark; illustrative numbers.}
    \end{figure*}
"""

import sys
from pathlib import Path

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

# Accuracy (%) of each method on each benchmark. Methods keep this order in
# every group and in the legend.
SCORES = {
    "Base": {"MMLU": 55.2, "GSM8K": 41.0, "HumanEval": 30.5, "ARC": 61.3, "BBH": 44.8},
    "Prior A": {"MMLU": 60.1, "GSM8K": 52.4, "HumanEval": 38.2, "ARC": 66.0, "BBH": 50.3},
    "Prior B": {"MMLU": 61.8, "GSM8K": 49.9, "HumanEval": 41.7, "ARC": 64.2, "BBH": 52.9},
    "Ours": {"MMLU": 64.5, "GSM8K": 58.3, "HumanEval": 40.9, "ARC": 69.4, "BBH": 57.1},
}

pv.use(layout)
fig, ax = pv.figure("text", ratio=0.26)
pv.bars(ax, SCORES, ours="Ours", ylabel="Accuracy (%)")
pv.save(fig, str(out_dir / "bars"))
# The same scores with the benchmarks grouped by what they test: a gap before
# each section, its name under its benchmarks, a light band behind every
# other section.
fig, ax = pv.figure("text", ratio=0.26)
pv.bars(ax, SCORES, ours="Ours", ylabel="Accuracy (%)",
        sections={"Knowledge": ["MMLU", "ARC"], "Reasoning": ["GSM8K", "BBH"], "Code": ["HumanEval"]})
pv.save(fig, str(out_dir / "bars-sections"))
