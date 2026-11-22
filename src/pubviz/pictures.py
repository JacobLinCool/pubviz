"""Results that are pictures or signals.

- ``images``       A grid of images: one row per example, one column per
  method, every image the same size, with an optional zoomed crop of the
  same region under each.
- ``overlay``      A weight map, such as a saliency map, laid over an image.
- ``spectrogram``  A sound's energy over time and frequency, in decibels,
  with an optional pitch contour.
- ``waveform``     A sound's amplitude over time, to put above a spectrogram.
"""

from __future__ import annotations

from collections.abc import Mapping

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects

from .color import oklch_to_hex, to_gray
from .plots import EDGE, TEXT, _is_ours
from .style import current

# ---- images -----------------------------------------------------------------

FRAME = "#FFFFFF"   # outline of the zoomed region: white with a dark edge reads on any image
GAP_IN = 0.03       # gap between images, inches


def _grey(image: np.ndarray) -> np.ndarray:
    """Luminance of an RGB image (Rec. 709 weights); a 2-D image as it is."""
    if image.ndim == 3:
        return image[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    return image


def _show(ax, image, cmap="gray"):
    image = np.asarray(image)
    if image.ndim == 2:
        ax.imshow(image, cmap=cmap, interpolation="nearest")
    else:
        ax.imshow(image, interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(False)


def _outline(ax, box):
    x, y, w, h = box
    for width, color in ((1.6, EDGE), (0.8, FRAME)):
        ax.add_patch(mpl.patches.Rectangle((x - 0.5, y - 0.5), w, h, fill=False, edgecolor=color,
                                           linewidth=width, zorder=5))


def images(grid: Mapping, *, which="text", ours=None, zoom=None, error: str | None = None, heat=None,
           alpha: float = 0.6):
    """A grid of images for comparing methods on the same examples.

    ``grid`` maps row name -> {column name: image}; rows are examples (or
    settings) and columns are methods, usually input, baselines, ours and
    the reference. A single mapping {column name: image} gives one row.
    Images are arrays of shape (h, w) or (h, w, 3) with values in [0, 1],
    all of one size, and are drawn at one scale with equal gaps; column
    names go on top (ours in bold) and row names on the left.

    ``zoom`` is a region (x, y, width, height) in pixels: it is outlined on
    every image and shown enlarged under it, the same region for every
    method, so the details are compared like for like. ``error`` names the
    reference column (the ground truth): under each other image a map of its
    absolute difference from the reference is added, white for none and dark
    for large, on one scale per example. ``heat`` maps a row name to
    {column name: weight map} to lay with ``overlay``.

    Returns the figure and the grid of image axes. Say in the caption how
    the examples were chosen.
    """
    import matplotlib.pyplot as plt

    from .style import width as text_width

    ctx = current()
    sizes = ctx.sizes
    if grid and all(isinstance(v, np.ndarray) for v in grid.values()):
        grid = {"": grid}
    rows = list(grid)
    cols = []
    for r in rows:
        for c in grid[r]:
            if c not in cols:
                cols.append(c)
    first = np.asarray(grid[rows[0]][cols[0]])
    h, w = first.shape[:2]
    for r in rows:
        for c in cols:
            if c in grid[r] and np.asarray(grid[r][c]).shape[:2] != (h, w):
                raise ValueError("every image must have the same size; crop or resize them first")
    total = text_width(which)
    line = (sizes["label"] * 1.45 + 3) / 72  # one line of label text, its offset and a little air
    left = line if any(rows) else 0.0
    top = line
    cell = (total - left - GAP_IN * (len(cols) - 1)) / len(cols)
    image_h = cell * h / w
    crop_h = cell * zoom[3] / zoom[2] if zoom else 0.0
    if error is not None and error not in cols:
        raise ValueError(f"error names the reference column; {error!r} is not one of {cols}")
    error_h = image_h if error is not None else 0.0
    row_h = image_h + (GAP_IN + crop_h if zoom else 0.0) + (GAP_IN + error_h if error is not None else 0.0)
    height = top + len(rows) * row_h + GAP_IN * (len(rows) - 1)
    fig = plt.figure(figsize=(total, height))
    # The grid is placed by hand; a placeholder engine keeps the default
    # constrained layout from taking over when the figure is saved.
    fig.set_layout_engine("none")
    fig._pubviz_width = total
    axes = np.empty((len(rows), len(cols)), dtype=object)
    for i, r in enumerate(rows):
        y_top = height - top - i * (row_h + GAP_IN)
        for j, c in enumerate(cols):
            x0 = left + j * (cell + GAP_IN)
            ax = fig.add_axes([x0 / total, (y_top - image_h) / height, cell / total, image_h / height])
            axes[i, j] = ax
            if c not in grid[r]:
                ax.set_axis_off()
                continue
            image = np.asarray(grid[r][c])
            weight = (heat or {}).get(r, {}).get(c)
            if weight is not None:
                overlay(ax, image, weight, alpha=alpha, colorbar=False)
            else:
                _show(ax, image)
            if i == 0:
                # Column names as plain text, not axes titles: the caption is the figure's title.
                ax.annotate(str(c), xy=(0.5, 1), xycoords="axes fraction", xytext=(0, 2), textcoords="offset points",
                            ha="center", va="bottom", fontsize=sizes["label"], color=TEXT,
                            fontweight="bold" if _is_ours(c, ours) else "normal")
            if j == 0 and r:
                ax.annotate(str(r), xy=(0, 0.5), xycoords="axes fraction", xytext=(-2, 0), textcoords="offset points",
                            ha="right", va="center", rotation=90, fontsize=sizes["label"], color=TEXT)
            if zoom:
                _outline(ax, zoom)
                x, y, zw, zh = zoom
                crop_ax = fig.add_axes([x0 / total, (y_top - image_h - GAP_IN - crop_h) / height,
                                        cell / total, crop_h / height])
                crop = image[y:y + zh, x:x + zw]
                if weight is not None:
                    big = _resize(np.asarray(weight, dtype=float), image.shape[:2])
                    overlay(crop_ax, crop, big[y:y + zh, x:x + zw], alpha=alpha, colorbar=False,
                            scale=(float(np.nanmin(weight)), float(np.nanmax(weight))))
                else:
                    _show(crop_ax, crop)
                for spine in crop_ax.spines.values():
                    spine.set_visible(True)
                    spine.set_edgecolor(EDGE)
                    spine.set_linewidth(0.8)
            if error is not None:
                below = image_h + (GAP_IN + crop_h if zoom else 0.0) + GAP_IN
                err_ax = fig.add_axes([x0 / total, (y_top - below - error_h) / height, cell / total, error_h / height])
                if c == error:
                    err_ax.set_axis_off()
                else:
                    diffs = {k: _grey(np.abs(np.asarray(v, dtype=float) - np.asarray(grid[r][error], dtype=float)))
                             for k, v in grid[r].items() if k != error}
                    top_err = max(float(d.max()) for d in diffs.values()) or 1.0
                    _show(err_ax, diffs[c])
                    err_ax.images[0].set(cmap=level_map(), clim=(0.0, top_err))
                    for spine in err_ax.spines.values():
                        spine.set_visible(True)
                        spine.set_edgecolor(EDGE)
                        spine.set_linewidth(0.5)
    return fig, axes


def _resize(weight: np.ndarray, shape) -> np.ndarray:
    """Nearest-neighbour resize, enough to cut a crop from a coarse map."""
    rows = (np.arange(shape[0]) * weight.shape[0] / shape[0]).astype(int)
    cols = (np.arange(shape[1]) * weight.shape[1] / shape[1]).astype(int)
    return weight[np.ix_(rows, cols)]


def overlay(ax, image, weight, *, alpha: float = 0.6, colorbar: bool = True, label: str | None = None,
            scale=None):
    """A weight map laid over an image, such as a saliency or attention map.

    The image is drawn in grey, so the only color on it is the map's. An
    unsigned map (no weight below zero) uses the accent scale, light for low
    weights and dark for high; a signed map uses ``pos`` for positive and
    ``neg`` for negative weights, since showing only the size of a signed
    map hides where its sign flips. Opacity grows with the size of the
    weight (up to ``alpha``), so small weights leave the image visible. A map
    coarser than the image is stretched over it. ``scale`` fixes the
    (low, high) ends; by default they are the map's range (symmetric around
    zero for a signed map), so say in the caption whether maps share a scale.
    """
    ctx = current()
    image = np.asarray(image, dtype=float)
    weight = np.asarray(weight, dtype=float)
    signed = bool(np.nanmin(weight) < 0)
    if scale is not None:
        lo, hi = scale
    elif signed:
        hi = float(np.nanmax(np.abs(weight)))
        lo = -hi
    else:
        lo, hi = float(np.nanmin(weight)), float(np.nanmax(weight))
    t = np.clip((weight - lo) / ((hi - lo) or 1.0), 0, 1)
    _show(ax, _grey(image))
    cmap = ctx.theme.diverging() if signed else ctx.theme.cmap()
    rgba = cmap(t)
    rgba[..., 3] = alpha * (np.abs(2 * t - 1) if signed else t)
    h, w = image.shape[:2]
    shown = ax.imshow(rgba, extent=(-0.5, w - 0.5, h - 0.5, -0.5), interpolation="bilinear", zorder=2)
    if colorbar:
        mappable = mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(lo, hi), cmap=cmap)
        bar = ax.figure.colorbar(mappable, ax=ax, fraction=0.05, pad=0.02)
        bar.outline.set_visible(False)
        bar.ax.tick_params(labelsize=ctx.sizes["tick"], length=2)
        bar.set_label(label if label is not None else ctx.say("weight"))
    return shown


# ---- sound ------------------------------------------------------------------

FLOOR_DB = -80.0     # quietest level shown, relative to the loudest bin
INK_DARK = 0.18      # lightness of the loudest bin


def level_map(dark: float = INK_DARK):
    """The scale of ``spectrogram`` and of error maps: white to near black in
    equal lightness steps, so louder (or larger) is darker in color and in grey."""
    from matplotlib.colors import ListedColormap

    return ListedColormap([oklch_to_hex(0.985 + (dark - 0.985) * i / 255, 0.0, 0.0) for i in range(256)],
                          name="pubviz-level")


def _hz_to_mel(f):
    return 2595.0 * np.log10(1.0 + np.asarray(f, dtype=float) / 700.0)


def _mel_to_hz(m):
    return 700.0 * (10 ** (np.asarray(m, dtype=float) / 2595.0) - 1.0)


def mel_filters(sr: int, n_fft: int, bands: int, fmax: float | None = None) -> np.ndarray:
    """Triangular filters equally spaced on the mel scale (HTK formula), shape (bands, n_fft // 2 + 1)."""
    fmax = fmax or sr / 2
    points = _mel_to_hz(np.linspace(0, _hz_to_mel(fmax), bands + 2))
    freqs = np.linspace(0, sr / 2, n_fft // 2 + 1)
    out = np.zeros((bands, len(freqs)))
    for b in range(bands):
        lo, mid, hi = points[b], points[b + 1], points[b + 2]
        rise = (freqs - lo) / (mid - lo)
        fall = (hi - freqs) / (hi - mid)
        out[b] = np.clip(np.minimum(rise, fall), 0, None)
    return out


def power_spectrum(audio, sr: int, n_fft: int | None = None, hop: int | None = None) -> tuple[np.ndarray, int, int]:
    """|STFT|^2 with a Hann window: 25 ms frames every 10 ms by default."""
    x = np.asarray(audio, dtype=float)
    n_fft = n_fft or int(2 ** np.ceil(np.log2(0.025 * sr)))
    hop = hop or int(round(0.010 * sr))
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    frames = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(frames)[:, None]
    spec = np.fft.rfft(x[idx] * np.hanning(n_fft), axis=1)
    return (np.abs(spec) ** 2).T, n_fft, hop


def spectrogram(ax, audio=None, sr: int = 16000, *, level=None, hop: int | None = None,
                n_fft: int | None = None, mel: int = 0, floor: float = FLOOR_DB, fmax: float | None = None,
                f0=None, colorbar: bool = True, xlabel: str | None = None, ylabel: str | None = None):
    """A spectrogram: energy over time and frequency, louder darker.

    Give ``audio`` (samples) and ``sr`` to compute it (Hann window, 25 ms
    frames every 10 ms unless ``n_fft`` and ``hop`` say otherwise), or a
    computed ``level`` in dB of shape (frequency bins or mel bands, frames),
    such as a model's predicted mel spectrogram, with the ``hop`` it used.

    Levels are in dB relative to the loudest bin, shown down to ``floor``
    (−80 dB); keep one floor for spectrograms that are compared. ``mel`` is
    the number of mel bands (0 for a linear frequency axis); the axis is then
    labelled in kHz at the band of each frequency. The scale runs from white
    (quiet) to near black (loud) in even lightness steps, so it prints in
    grey unchanged. ``f0`` is a pitch contour (times in s, Hz), with NaN
    where unvoiced, drawn in the accent.
    """
    ctx = current()
    sizes = ctx.sizes
    if level is None:
        if audio is None:
            raise ValueError("give audio or level")
        power, n_fft, hop = power_spectrum(audio, sr, n_fft, hop)
        if mel:
            power = mel_filters(sr, n_fft, mel, fmax) @ power
        db = 10 * np.log10(np.maximum(power, 1e-12))
        db -= db.max()
    else:
        db = np.asarray(level, dtype=float)
        db = db - np.nanmax(db)
        hop = hop or int(round(0.010 * sr))
        if mel == 0 and n_fft is None:
            n_fft = 2 * (db.shape[0] - 1)
    bins, frames = db.shape
    duration = frames * hop / sr
    top = (fmax or sr / 2) / 1000
    image = ax.imshow(np.maximum(db, floor), origin="lower", aspect="auto", cmap=level_map(), vmin=floor, vmax=0,
                      interpolation="nearest",
                      extent=(0, duration, -0.5, bins - 0.5) if mel else (0, duration, 0, sr / 2000))
    ax.grid(False)
    if mel:
        mel_top = _hz_to_mel(fmax or sr / 2)
        ticks = [k for k in (0.25, 0.5, 1, 2, 4, 8, 16) if k * 1000 < (fmax or sr / 2)]
        where = [float(_hz_to_mel(k * 1000) / mel_top * bins - 0.5) for k in ticks]
        ax.set_yticks(where, [f"{k:g}" for k in ticks])
    else:
        ax.set_ylim(0, top)
    if f0 is not None:
        times, hz = (np.asarray(v, dtype=float) for v in f0)
        y = hz / 1000 if not mel else _hz_to_mel(hz) / _hz_to_mel(fmax or sr / 2) * bins - 0.5
        ax.plot(times, y, color=ctx.theme.ours, linewidth=1.3, zorder=4,
                path_effects=[patheffects.Stroke(linewidth=2.6, foreground="white"), patheffects.Normal()])
    ax.set_xlabel(xlabel if xlabel is not None else ctx.say("time"))
    ax.set_ylabel(ylabel if ylabel is not None else ctx.say("frequency"))
    if colorbar:
        bar = ax.figure.colorbar(image, ax=ax, fraction=0.05, pad=0.02)
        bar.outline.set_visible(False)
        bar.ax.tick_params(labelsize=sizes["tick"], length=2)
        bar.set_label(ctx.say("level"))
    return image


def waveform(ax, audio, sr: int = 16000, *, xlabel: str | None = None, ylabel: str | None = None):
    """A sound's amplitude over time, as a thin dark line; set above a
    spectrogram with ``pv.figure(nrows=2, sharex=True, height_ratios=...)``.
    The amplitude axis has no ticks or title: it is relative, so name the
    panel in the caption."""
    x = np.asarray(audio, dtype=float)
    t = np.arange(len(x)) / sr
    ax.plot(t, x, color=to_gray(EDGE), linewidth=0.35)
    peak = float(np.max(np.abs(x))) or 1.0
    ax.set_ylim(-peak * 1.05, peak * 1.05)
    ax.set_xlim(0, len(x) / sr)
    ax.set_yticks([])
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
