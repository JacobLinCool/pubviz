r"""The same examples as each method restores them, with one region enlarged.

    uv run python examples/figures/images.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where images.pdf goes (default examples/build/figs). The
images are drawn by this script: a scene with fine stripes, blurred to
stand in for the outputs of different methods.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/images}
      \caption{\textbf{Ours keeps the fine stripes that the others blur.}
        Two test images upscaled four times; the boxed region is enlarged
        under each image, and the bottom row is each output's absolute
        difference from the reference (darker is larger). The examples are
        the first two of the test set.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

H, W = 72, 96


def scene(seed: int) -> np.ndarray:
    """A sky gradient, a disc and a patch of fine diagonal stripes."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    image = np.stack([0.55 + 0.35 * y, 0.65 + 0.25 * y, 0.85 - 0.1 * y], axis=-1)
    cx, cy = rng.uniform(0.25, 0.4), rng.uniform(0.35, 0.65)
    disc = (x - cx) ** 2 + ((y - cy) * H / W) ** 2 < 0.03
    image[disc] = rng.uniform(0.2, 0.9, 3)
    patch = (x > 0.55) & (x < 0.9) & (y > 0.2) & (y < 0.75)
    stripes = 0.5 + 0.5 * np.sin(2 * np.pi * (x * W + y * H) / rng.uniform(3.2, 4.0))
    image[patch] = (0.25 + 0.6 * stripes[patch])[:, None] * np.array([0.9, 0.8, 0.6])
    return np.clip(image, 0, 1)


def blur(image: np.ndarray, sigma: float) -> np.ndarray:
    """A separable Gaussian blur."""
    if sigma <= 0:
        return image
    r = int(3 * sigma) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    out = image.copy()
    for axis in (0, 1):
        out = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, mode="valid"), axis, out)
    return out


def upscale_input(image: np.ndarray) -> np.ndarray:
    """The low-resolution input, shown at full size: every fourth pixel, repeated."""
    return np.repeat(np.repeat(image[::4, ::4], 4, axis=0), 4, axis=1)


GRID = {}
for row, seed in (("Image 1", 1), ("Image 2", 2)):
    truth = scene(seed)
    GRID[row] = {"Input": upscale_input(truth), "Bicubic": blur(truth, 1.6), "Prior": blur(truth, 1.0),
                 "Ours": blur(truth, 0.45), "Reference": truth}

pv.use(layout)
# One region, the same for every method, outlined and enlarged under each
# image; under that, each output's difference from the reference.
fig, axes = pv.images(GRID, which="column", ours="Ours", zoom=(56, 18, 28, 14), error="Reference")
pv.save(fig, str(out_dir / "images"))
