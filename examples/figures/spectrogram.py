r"""A sound over time: its waveform, its spectrogram and its pitch.

    uv run python examples/figures/spectrogram.py [layout] [out_dir]

layout: a venue preset or the .pubviz.json file your paper writes (default
ieee). out_dir: where spectrogram.pdf goes (default examples/build/figs).
The sound is synthesized by this script: a vowel glide, a hiss, a vowel.

    \begin{figure}[t]
      \centering
      \includegraphics[width=\linewidth]{figs/spectrogram}
      \caption{\textbf{The pitch contour follows the rise and fall of the
        synthesized phrase.} Waveform (top) and 80-band mel spectrogram
        (bottom; dB relative to the loudest bin, down to $-80$~dB) with the
        estimated F0.}
    \end{figure}
"""

import sys
from pathlib import Path

import numpy as np

import pubviz as pv

layout = sys.argv[1] if len(sys.argv) > 1 else "ieee"
out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "examples/build/figs")

SR = 16000
t = np.arange(int(1.2 * SR)) / SR
voiced = (t < 0.55) | (t > 0.75)
f0 = np.where(voiced, 115 + 45 * np.sin(np.pi * t / 1.2) - 20 * (t > 0.75), np.nan)
# Formants glide from /a/ to /i/ in the first vowel and stay at /u/ in the second.
glide = np.clip(t / 0.55, 0, 1)
first = np.stack([700 - 430 * glide, 1220 + 1070 * glide, 2600 + 400 * glide])
second = np.array([300.0, 870.0, 2240.0])[:, None] * np.ones_like(t)
formants = np.where(t < 0.6, first, second)


def resonance(f, centre, width=90.0):
    return 1 / (1 + ((f - centre) / width) ** 2)


phase = 2 * np.pi * np.cumsum(np.nan_to_num(f0)) / SR
audio = np.zeros_like(t)
for k in range(1, 40):
    fk = k * np.nan_to_num(f0)
    gain = sum(resonance(fk, formants[i], 60 + 30 * i) for i in range(3)) / k ** 1.2
    audio += np.where(voiced & (fk < SR / 2), gain * np.sin(k * phase), 0)
rng = np.random.default_rng(2)
hiss = np.diff(rng.normal(0, 1, len(t) + 1)) * 0.08
audio += np.where((t > 0.58) & (t < 0.72), hiss, 0) + rng.normal(0, 0.002, len(t))
fade = np.minimum(1, np.minimum(t, t[-1] - t) / 0.03)
audio *= fade / np.max(np.abs(audio))

pv.use(layout)
fig, (wave, spec) = pv.figure("column", ratio=0.78, nrows=2, sharex=True, height_ratios=[1, 3])
pv.waveform(wave, audio, SR)
frames = np.arange(0, len(t), 160)
pv.spectrogram(spec, audio, SR, mel=80, f0=(t[frames], f0[frames]))
pv.save(fig, str(out_dir / "spectrogram"))
