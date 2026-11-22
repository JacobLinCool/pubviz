r"""Which parts of an image a model's prediction rests on.

    uv run python examples/figures/overlay.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where overlay.pdf goes (default examples/build/figs). The
image and the maps are drawn by this script for illustration.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/overlay}
      \caption{\textbf{Ours weighs the object; the baseline also weighs the
        background.} Grad-CAM maps on one test image, each scaled to its
        own maximum.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

H, W = 96, 128
y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
image = np.stack([0.5 + 0.3 * y, 0.6 + 0.2 * x, 0.7 - 0.2 * y], axis=-1)
body = (x - 0.42) ** 2 / 0.03 + (y - 0.55) ** 2 / 0.06 < 1
image[body] = [0.75, 0.45, 0.25]


def bump(cx, cy, s):
    return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s ** 2))


# Coarse maps, as a network's last feature map gives them.
MAPS = {"Baseline": (0.7 * bump(0.42, 0.55, 0.15) + 0.6 * bump(0.85, 0.2, 0.12))[::8, ::8],
        "Ours": bump(0.42, 0.55, 0.13)[::8, ::8]}

pv.use(layout)
fig, axes = pv.figure("column", ratio=0.42, ncols=2)
for ax, (name, weight) in zip(axes, MAPS.items()):
    pv.overlay(ax, image, weight, colorbar=False)
    ax.set_xlabel(name, fontweight="bold" if name == "Ours" else "normal")
pv.save(fig, str(out_dir / "overlay"))
