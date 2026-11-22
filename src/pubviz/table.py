"""Write results held in Python as a ``pvtable`` for LaTeX.

The LaTeX package does the comparing (best, second, changes, heat), so this
module only formats numbers and puts the markers where the package looks for
them. Hand-written and generated tables therefore follow the same rules.

    from pubviz.table import pvtable
    print(pvtable(scores, ours="Ours", baseline="Base", lower=["WER"]))
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping

_SPECIAL = re.compile(r"(?<!\\)([&%#_])")


def _escape(text: str) -> str:
    return _SPECIAL.sub(r"\\\1", text)


def _rows(data) -> tuple[list[str], list[str], dict]:
    if hasattr(data, "to_dict") and hasattr(data, "index"):
        rows = [str(r) for r in data.index]
        cols = [str(c) for c in data.columns]
        table = {str(r): {str(c): data.loc[r, c] for c in data.columns} for r in data.index}
        return rows, cols, table
    rows = [str(r) for r in data]
    cols: list[str] = []
    for r in data:
        for c in data[r]:
            if str(c) not in cols:
                cols.append(str(c))
    table = {str(r): {str(c): v for c, v in data[r].items()} for r in data}
    return rows, cols, table


def _format(value, digits: int, percent: bool, missing: str) -> str:
    if value is None:
        return missing
    if isinstance(value, str):
        return value
    if isinstance(value, tuple) and len(value) == 2:  # (mean, spread)
        mean, spread = value
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (mean, spread)):
            return missing
        return f"${mean:.{digits}f} \\pm {spread:.{digits}f}$"
    if isinstance(value, float) and math.isnan(value):
        return missing
    text = f"{value:.{digits}f}"
    return text + "\\%" if percent else text


def pvtable(data, *, by: str = "column", ours: str | Iterable[str] = (), baseline: str | None = None,
            norank: Iterable[str] = (), lower: Iterable[str] = (), higher: Iterable[str] = (),
            digits: int | Mapping[str, int] = 1, percent: bool | Iterable[str] = False,
            sections: Mapping[str, Iterable[str]] | None = None, corner: str = "",
            colspec: str | None = None, options: str = "", escape: bool = True,
            missing: str = "--", key: bool = False) -> str:
    """A ``pvtable`` environment as a string.

    ``data`` maps row -> {column: value} or is a DataFrame. Values are numbers,
    ``(mean, spread)`` pairs, strings (kept as written) or None/NaN (missing).

    ``by="column"``: rows are methods and columns are metrics; the best value
    of each column is marked. ``by="row"``: rows are metrics and columns are
    methods. ``ours``, ``baseline`` and ``norank`` name methods; ``lower`` and
    ``higher`` name metrics whose direction differs from the table default.
    ``digits`` and ``percent`` apply to every metric or to the named ones.
    ``sections`` groups rows under headed bands: {"Coding": ["A", "B"], ...}.
    ``key`` adds ``\\pvkey`` after the table: a line per mark the table shows,
    each opening with the mark itself.
    """
    rows, cols, table = _rows(data)
    ours = {ours} if isinstance(ours, str) else set(ours)
    norank, lower, higher = set(norank), set(lower), set(higher)
    pct = set(cols if by == "column" else rows) if percent is True else set(percent or ())
    esc = _escape if escape else (lambda s: s)

    def method_label(name: str) -> str:
        marks = ("\\pvours " if name in ours else "") + ("\\pvbaseline " if name == baseline else "") \
            + ("\\pvnorank " if name in norank else "")
        return marks + esc(name)

    def metric_label(name: str) -> str:
        arrow = " \\pvdown" if name in lower else (" \\pvup" if name in higher else "")
        return esc(name) + arrow

    def digits_for(metric: str) -> int:
        return digits.get(metric, 1) if isinstance(digits, Mapping) else digits

    head_cells = [corner] + [method_label(c) if by == "row" else metric_label(c) for c in cols]
    lines = ["\\toprule", " & ".join(head_cells) + " \\\\", "\\midrule"]
    order: list[tuple[str | None, str]] = []
    if sections:
        seen = set()
        for title, members in sections.items():
            members = [m for m in members if m in table]
            for i, m in enumerate(members):
                order.append((title if i == 0 else None, m))
                seen.add(m)
        order += [(None, r) for r in rows if r not in seen]
    else:
        order = [(None, r) for r in rows]
    for title, r in order:
        if title is not None:
            lines.append(f"\\pvsection{{{esc(title)}}} \\\\")
        label = metric_label(r) if by == "row" else method_label(r)
        cells = []
        for c in cols:
            metric = r if by == "row" else c
            cells.append(_format(table[r].get(c), digits_for(metric), metric in pct, missing))
        lines.append(" & ".join([label, *cells]) + " \\\\")
    lines.append("\\bottomrule")
    opts = [f"by={by}"]
    if baseline is not None and "delta" not in options:
        opts.append("delta=absolute")
    if options:
        opts.append(options)
    spec = colspec or ("l" + "c" * len(cols))
    body = "\n".join("  " + line for line in lines)
    after = "\\pvkey\n" if key else ""
    return f"\\begin{{pvtable}}[{', '.join(opts)}]{{{spec}}}\n{body}\n\\end{{pvtable}}\n{after}"
