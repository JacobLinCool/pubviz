"""Page geometry of a venue: how wide a figure may be and how big its text is.

The most reliable source is the paper itself. ``pubviz.sty`` writes
``<jobname>.pubviz.json`` on every compile with the column width, the text
width, the body font size, the font families and the color theme, so

    use("paper/main.pubviz.json")

sizes figures for whatever template the paper uses, including one this module
has never heard of. The named presets below are for starting before the paper
compiles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    """Column and text width in inches, body font size in points, font family."""

    column: float
    text: float
    font_size: float = 10.0
    family: str = "times"  # times | cm | libertine | palatino | serif | sans
    name: str = "custom"

    @property
    def twocolumn(self) -> bool:
        return self.text - self.column > 0.5


# How each preset was obtained (2026-11-21):
#   measured: compiled the class from TeX Live 2026 with pubviz and read the
#             layout file it wrote.
#   style:    read \textwidth, \columnsep and the font size from the venue's
#             official style file; column = (text - columnsep) / 2.
# Venues change their templates. When the paper compiles, prefer its own
# layout file over these numbers.
PRESETS: dict[str, Layout] = {
    # measured
    "article": Layout(4.77377, 4.77377, 10, "cm", "article"),
    "ieee": Layout(3.48692, 7.13990, 10, "times", "ieee"),  # IEEEtran conference and journal
    "acm": Layout(3.33676, 7.00560, 9, "libertine", "acm"),  # acmart sigconf
    "acm-small": Layout(5.47699, 5.47699, 10, "libertine", "acm-small"),  # acmart acmsmall
    "lncs": Layout(4.80315, 4.80315, 10, "cm", "lncs"),  # Springer llncs
    "elsevier": Layout(3.48692, 7.22292, 10, "cm", "elsevier"),  # elsarticle 5p
    # style
    "neurips": Layout(5.5, 5.5, 10, "times", "neurips"),  # neurips_2025.sty
    "iclr": Layout(5.5, 5.5, 10, "times", "iclr"),  # iclr2026_conference.sty
    "icml": Layout(3.25, 6.75, 10, "times", "icml"),  # icml2025.sty
    "cvpr": Layout(3.28125, 6.875, 10, "times", "cvpr"),  # cvpr.sty (author kit)
    "acl": Layout(7.7 / 2.54, 16.0 / 2.54, 11, "times", "acl"),  # acl.sty, A4 with 2.5 cm margins
}


def family_of(latex_family: str) -> str:
    """Map a LaTeX font family code (``ptm``, ``ntxtlf``, ``lmr``...) to a font group."""
    code = latex_family.lower()
    if code.startswith(("ptm", "ntx", "qtm", "stix", "txr", "tempora", "times", "nimbusserif")):
        return "times"
    if code.startswith(("cmr", "lmr")):
        return "cm"
    if "libertin" in code or code.startswith("lbt"):
        return "libertine"
    if code.startswith(("ppl", "qpl", "zpl", "pagella", "palatino", "tgpagella")):
        return "palatino"
    if code.startswith(("phv", "qhv", "cmss", "lmss", "helvet")):
        return "sans"
    return "serif"


def from_file(path: str | Path) -> tuple[Layout, dict]:
    """Read a ``.pubviz.json`` file. Returns the layout and the raw record,
    which also carries the theme (``accent``, ``mode``, ``pos``, ``neg``)."""
    path = Path(path)
    record = json.loads(path.read_text())
    layout = Layout(
        column=float(record["columnwidth_in"]),
        text=float(record["textwidth_in"]),
        font_size=float(record["font_size_pt"]),
        family=family_of(str(record.get("rmfamily", ""))),
        name=path.name.removesuffix(".pubviz.json"),
    )
    return layout, record


def resolve(layout: str | Path | Layout) -> tuple[Layout, dict]:
    """A preset name, a layout file, or a Layout to a Layout (and the raw record if any)."""
    if isinstance(layout, Layout):
        return layout, {}
    text = str(layout)
    if text in PRESETS:
        return PRESETS[text], {}
    path = Path(text)
    if path.suffix == ".json" or path.exists():
        return from_file(path)
    raise ValueError(
        f"unknown layout {text!r}: give a preset ({', '.join(PRESETS)}) "
        "or the path of a .pubviz.json file written by pubviz.sty"
    )
