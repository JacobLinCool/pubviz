"""Text with each token shaded by a weight, for LaTeX.

    tex = pv.pvshade(["the", "film", "was", "not", "good"], [0.1, 0.3, 0.0, -0.8, 0.6])
    Path("figs/tokens.tex").write_text(tex)   # then \\input{figs/tokens} in the paper

The shading is drawn by ``\\pvshade`` in pubviz.sty, so the text stays text:
set in the paper's font, searchable, and in any script the paper can set.
"""

from __future__ import annotations

from collections.abc import Sequence

_LATEX = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "%": r"\%",
          "#": r"\#", "_": r"\_", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}"}


def _escape(token: str) -> str:
    """A token as literal text: every character LaTeX treats specially escaped."""
    return "".join(_LATEX.get(ch, ch) for ch in token)


def pvshade(tokens: Sequence[str], weights: Sequence[float], *, signed: bool | None = None, scale=None,
            join: str = " ", escape: bool = True, digits: int = 2) -> str:
    """LaTeX for a sentence whose tokens are shaded by ``weights``.

    Unsigned weights (all zero or more) use the accent scale, darker for
    larger, from 0 to the largest weight. Signed weights (``signed=True``, or
    any weight below zero) use ``\\pvshade*``: tints of ``pos`` and ``neg``,
    as strong as each weight's size relative to the largest size, and a line
    under the negative ones. ``scale`` fixes the weight that gets the full
    shade, so sentences shaded on one scale compare. ``join`` goes between
    tokens: a space for English, nothing for Chinese or Japanese. Name the
    method that gave the weights in the caption.
    """
    if len(tokens) != len(weights):
        raise ValueError("one weight per token")
    weights = [float(w) for w in weights]
    if signed is None:
        signed = any(w < 0 for w in weights)
    top = scale if scale is not None else max((abs(w) for w in weights), default=0.0)
    top = top or 1.0
    esc = _escape if escape else (lambda t: t)
    star = "*" if signed else ""
    parts = []
    for token, w in zip(tokens, weights):
        t = max(-1.0, min(1.0, w / top))
        if not signed:
            t = max(0.0, t)
        parts.append(f"\\pvshade{star}{{{t:.{digits}f}}}{{{esc(token)}}}")
    return join.join(parts) + "\n"
