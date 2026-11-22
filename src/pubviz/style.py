"""Matplotlib setup: figure size, fonts and colors that match the paper.

    import pubviz as pv

    pv.use("paper/main.pubviz.json")      # or a preset such as "neurips"
    fig, ax = pv.figure("column")
    ...
    pv.save(fig, "figs/results")

Build every figure at the width it will be printed at and include it with
``width=\\linewidth``. Text sizes are set from the body font size, so a figure
built for a 9 pt ACM paper and one built for an 11 pt ACL paper both print
their labels about two points below the body text.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

import matplotlib as mpl

from .layout import Layout, resolve
from .theme import NEG_DEFAULT, POS_DEFAULT, Theme

SANS = ["Helvetica Neue", "Helvetica", "Arial", "TeX Gyre Heros", "Nimbus Sans", "Liberation Sans", "DejaVu Sans"]
# Body font groups. Each stack runs from the closest match to one that ships
# with matplotlib, so a figure always renders.
SERIF = {
    "times": ["Times New Roman", "TeX Gyre Termes", "Nimbus Roman", "STIXGeneral"],
    "cm": ["CMU Serif", "Latin Modern Roman", "cmr10"],
    "libertine": ["Linux Libertine O", "Libertinus Serif", "Linux Libertine", "STIXGeneral"],
    "palatino": ["Palatino", "TeX Gyre Pagella", "URW Palladio L", "STIXGeneral"],
    "serif": ["STIXGeneral", "DejaVu Serif"],
}
MATH = {"times": "stix", "cm": "cm", "libertine": "stix", "palatino": "stix", "serif": "stix"}
# Words the figures write themselves. A layout file carries the words of the
# paper's language (language=... in pubviz.sty, including languages defined
# there with \pvdefinelanguage); these built-in sets serve when there is none.
WORDS = {
    "en": {"better": "better", "worse": "worse", "crosses": "interval crosses zero"},
    "zh-tw": {"better": "較好", "worse": "較差", "crosses": "區間跨過零"},
    "zh-cn": {"better": "较好", "worse": "较差", "crosses": "区间跨过零"},
    "ja": {"better": "良い", "worse": "悪い", "crosses": "区間が0をまたぐ"},
    "ko": {"better": "좋음", "worse": "나쁨", "crosses": "구간이 0을 포함"},
}
# Axis titles and reference labels that some kinds write when the caller
# gives none. Each can be overridden by the kind's own argument (xlabel=...);
# a language without a set here falls back to English.
LABELS = {
    "en": {
        "true": "True class", "predicted": "Predicted class", "share": "Share of row (%)",
        "time": "Time (s)", "frequency": "Frequency (kHz)", "mel": "Mel band", "level": "Level (dB)",
        "fpr": "False positive rate", "tpr": "True positive rate", "chance": "chance",
        "recall": "Recall", "precision": "Precision", "positives": "share of positives",
        "false_alarm": "False alarm rate (%)", "miss": "Miss rate (%)", "eer": "EER",
        "confidence": "Predicted probability", "observed": "Observed frequency",
        "calibrated": "calibrated", "cases": "Cases",
        "responses": "Responses (%)", "fit": "fit", "extrapolated": "extrapolated",
        "other": "Other", "weight": "Weight",
    },
    "zh-tw": {
        "true": "真實類別", "predicted": "預測類別", "share": "佔該列比例（%）",
        "time": "時間（秒）", "frequency": "頻率（kHz）", "mel": "梅爾頻帶", "level": "強度（dB）",
        "fpr": "偽陽性率", "tpr": "真陽性率", "chance": "隨機",
        "recall": "召回率", "precision": "精確率", "positives": "正例比例",
        "false_alarm": "誤報率（%）", "miss": "漏報率（%）", "eer": "EER",
        "confidence": "預測機率", "observed": "實際比例",
        "calibrated": "完全校準", "cases": "樣本數",
        "responses": "回答（%）", "fit": "擬合", "extrapolated": "外推",
        "other": "其他", "weight": "權重",
    },
    "zh-cn": {
        "true": "真实类别", "predicted": "预测类别", "share": "占该行比例（%）",
        "time": "时间（秒）", "frequency": "频率（kHz）", "mel": "梅尔频带", "level": "强度（dB）",
        "fpr": "假阳性率", "tpr": "真阳性率", "chance": "随机",
        "recall": "召回率", "precision": "精确率", "positives": "正例比例",
        "false_alarm": "误报率（%）", "miss": "漏报率（%）", "eer": "EER",
        "confidence": "预测概率", "observed": "实际比例",
        "calibrated": "完全校准", "cases": "样本数",
        "responses": "回答（%）", "fit": "拟合", "extrapolated": "外推",
        "other": "其他", "weight": "权重",
    },
    "ja": {
        "true": "正解クラス", "predicted": "予測クラス", "share": "行内の割合（%）",
        "time": "時間（秒）", "frequency": "周波数（kHz）", "mel": "メル帯域", "level": "レベル（dB）",
        "fpr": "偽陽性率", "tpr": "真陽性率", "chance": "偶然",
        "recall": "再現率", "precision": "適合率", "positives": "正例の割合",
        "false_alarm": "誤警報率（%）", "miss": "見逃し率（%）", "eer": "EER",
        "confidence": "予測確率", "observed": "実際の割合",
        "calibrated": "完全に較正", "cases": "件数",
        "responses": "回答（%）", "fit": "当てはめ", "extrapolated": "外挿",
        "other": "その他", "weight": "重み",
    },
    "ko": {
        "true": "실제 클래스", "predicted": "예측 클래스", "share": "행 내 비율(%)",
        "time": "시간(초)", "frequency": "주파수(kHz)", "mel": "멜 대역", "level": "레벨(dB)",
        "fpr": "거짓 양성률", "tpr": "참 양성률", "chance": "무작위",
        "recall": "재현율", "precision": "정밀도", "positives": "양성 비율",
        "false_alarm": "오경보율(%)", "miss": "미탐지율(%)", "eer": "EER",
        "confidence": "예측 확률", "observed": "실제 비율",
        "calibrated": "완전 보정", "cases": "사례 수",
        "responses": "응답(%)", "fit": "적합", "extrapolated": "외삽",
        "other": "기타", "weight": "가중치",
    },
}
# Fonts for Chinese, Japanese and Korean characters, which the Latin fonts
# lack. A figure falls back to the first installed font of its language, then
# to those of the other three, so any CJK character renders. Fonts with a bold
# weight come first, so the method marked as ours stays bold. For the
# CFF-based ones (PingFang, Hiragino, Noto and Source Han Sans CJK) poppler's
# pdffonts prints a font-type mismatch warning on the PDF matplotlib writes;
# qpdf --check finds no error. Heiti embeds as TrueType but has no bold, so it
# comes last. Variable fonts such as Noto Sans TC are left out: matplotlib
# loads their thinnest weight.
CJK = {
    "zh-tw": ["PingFang TC", "Microsoft JhengHei", "Noto Sans CJK TC", "Source Han Sans TC", "Heiti TC"],
    "zh-cn": ["PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", "Heiti SC"],
    "ja": ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans CJK JP", "Source Han Sans JP"],
    "ko": ["Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans CJK KR", "Source Han Sans KR"],
}


class _ExpectedWeight(logging.Filter):
    """matplotlib warns when a fallback font lacks bold and it takes the
    nearest weight. For the CJK fallbacks, which only draw CJK characters,
    that substitution is expected; other font warnings still show."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not ("Failed to find font weight" in message
                    and any(font in message for fonts in CJK.values() for font in fonts))


def cjk_fallbacks(language: str, installed: set[str]) -> list[str]:
    """The first installed CJK font for ``language``, then for each other CJK
    language: the chain matplotlib falls back along for characters the
    figure's main font lacks."""
    order = [language] + [lang for lang in CJK if lang != language] if language in CJK else list(CJK)
    chain = []
    for lang in order:
        font = next((f for f in CJK[lang] if f in installed), None)
        if font and font not in chain:
            chain.append(font)
    return chain
# OpenType files TeX Live ships, registered with matplotlib when the machine
# has no system copy, so "match the body font" works on a bare TeX install.
TEX_FONTS = {
    "cm": ["lmroman10-regular.otf", "lmroman10-bold.otf", "lmroman10-italic.otf"],
    "libertine": ["LinLibertine_R.otf", "LinLibertine_RB.otf", "LinLibertine_RI.otf"],
}


@dataclass
class Context:
    layout: Layout
    theme: Theme
    font: str
    sizes: dict
    language: str = "en"
    words: dict = None

    def __post_init__(self):
        if self.words is None:
            self.words = dict(WORDS.get(self.language, WORDS["en"]))
        # Axis titles a kind writes by default, in the paper's language; the
        # words given for a language (the key words) take precedence.
        self.words = {**LABELS["en"], **LABELS.get(self.language, {}), **self.words}

    def say(self, key: str) -> str:
        """The default figure text ``key`` (see ``LABELS``) in the paper's language."""
        return self.words[key]


_current: Context | None = None


def _installed() -> set[str]:
    import matplotlib.font_manager as fm

    return {f.name for f in fm.fontManager.ttflist}


def _register_tex_fonts(group: str) -> None:
    files = TEX_FONTS.get(group)
    if not files or not shutil.which("kpsewhich"):
        return
    import matplotlib.font_manager as fm

    for name in files:
        try:
            path = subprocess.run(["kpsewhich", name], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if path and os.path.exists(path):
            fm.fontManager.addfont(path)


def text_sizes(body_pt: float) -> dict[str, float]:
    """Figure text sizes from the body size: labels two points below the body,
    ticks and legends three below, value labels four below with a 5 pt floor."""
    return {
        "label": max(6.0, body_pt - 2),
        "tick": max(5.5, body_pt - 3),
        "legend": max(5.5, body_pt - 3),
        "small": max(5.0, body_pt - 4),
    }


def use(layout: str | Layout = "article", theme: Theme | str | None = None, font: str = "sans",
        language: str | None = None, words: dict | None = None) -> Context:
    """Set matplotlib up for one paper.

    ``layout``: a preset name (``"neurips"``, ``"ieee"``...), the
    ``.pubviz.json`` file the LaTeX package writes, or a ``Layout``.
    ``theme``: a ``Theme``, an accent preset name or hex, or None to take the
    theme from the layout file (or the default theme).
    ``font``: ``"sans"`` for a clean sans-serif in every figure (the default;
    it stays readable at tick-label sizes), or ``"body"`` to match the
    paper's text font.
    ``language``: the language of the words a figure writes itself, such as
    the key of ``deltas``: ``"en"``, ``"zh-tw"``, ``"zh-cn"``, ``"ja"``,
    ``"ko"``, or any other name given with ``words``. None takes it from the
    layout file (or English). ``words``: ``better``, ``worse`` and
    ``crosses`` for a language without a built-in set; a layout file carries
    them for any language defined in LaTeX. It may also replace any of the
    axis titles in ``LABELS`` that kinds such as ``confusion`` write by
    default, which otherwise come in English for such a language. CJK
    characters fall back to the fonts in ``CJK``.
    """
    global _current
    lay, record = resolve(layout)
    if theme is None:
        theme = Theme(record.get("accent", "amber"), record.get("mode", "color"),
                      record.get("pos", POS_DEFAULT), record.get("neg", NEG_DEFAULT)) if record else Theme()
    elif isinstance(theme, str):
        theme = Theme(theme)
    if font not in ("sans", "body"):
        raise ValueError("font must be 'sans' or 'body'")
    language = language or record.get("language", "en")
    if words is None and "words" in record and (language == record.get("language")):
        given = record["words"]
        words = {"better": given["better"], "worse": given["worse"], "crosses": given["crosses_zero"]}
    if words is None:
        if language not in WORDS:
            raise ValueError(f"no words for language {language!r}: give words=, or use one of {', '.join(WORDS)}")
        words = WORDS[language]
    missing = {"better", "worse", "crosses"} - set(words)
    if missing:
        raise ValueError(f"words is missing {', '.join(sorted(missing))}")

    mpl.use("Agg")
    group = lay.family if font == "body" else "sans"
    if group in TEX_FONTS and not (set(SERIF[group][:-1]) & _installed()):
        _register_tex_fonts(group)
    sizes = text_sizes(lay.font_size)
    serif = SERIF.get(group, SERIF["serif"])
    others = theme.others(4)
    families = ["sans-serif" if group == "sans" else "serif"]
    log = logging.getLogger("matplotlib.font_manager")
    if not any(isinstance(f, _ExpectedWeight) for f in log.filters):
        log.addFilter(_ExpectedWeight())
    installed = _installed()
    families += cjk_fallbacks(language, installed)
    if language in CJK and not any(f in installed for f in CJK[language]):
        print(f"pubviz: no font for {language} found (tried {', '.join(CJK[language])}); "
              "its characters will not render as intended", file=sys.stderr)
    mpl.rcParams.update({
        "font.family": families,
        "font.sans-serif": SANS,
        "font.serif": serif,
        "mathtext.fontset": "stixsans" if group == "sans" else MATH.get(group, "stix"),
        "axes.formatter.use_mathtext": group == "cm",
        "axes.unicode_minus": True,
        # arXiv rejects Type 3 fonts; 42 embeds the outlines.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "font.size": sizes["label"],
        "axes.labelsize": sizes["label"],
        "axes.titlesize": sizes["label"],
        "legend.fontsize": sizes["legend"],
        "legend.title_fontsize": sizes["legend"],
        "xtick.labelsize": sizes["tick"],
        "ytick.labelsize": sizes["tick"],
        "figure.dpi": 200,
        "savefig.dpi": 600,
        "savefig.transparent": False,
        "axes.prop_cycle": mpl.cycler(color=[theme.strong, *others]),
        "axes.edgecolor": "#333333",
        "axes.labelcolor": "#1A1A1A",
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "text.color": "#1A1A1A",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": "#E3E3E3",
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.2,
        "lines.markersize": 3.5,
        "patch.linewidth": 0.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "legend.frameon": False,
        "legend.handlelength": 1.4,
        "legend.columnspacing": 1.0,
        "legend.borderaxespad": 0.3,
        "figure.constrained_layout.use": True,
    })
    _current = Context(lay, theme, font, sizes, language, dict(words))
    return _current


def current() -> Context:
    """The active context; ``use()`` with defaults if none was set."""
    return _current or use()


def width(which: str | float = "column") -> float:
    """``"column"``, ``"text"``, a fraction of the text width, or inches (> 1)."""
    lay = current().layout
    if which == "column":
        return lay.column
    if which == "text":
        return lay.text
    value = float(which)
    return lay.text * value if value <= 1 else value


def figure(which: str | float = "column", ratio: float = 0.62, height: float | None = None,
           nrows: int = 1, ncols: int = 1, **kwargs):
    """A figure at its printed width. ``ratio`` is height over width."""
    import matplotlib.pyplot as plt

    current()
    w = width(which)
    h = height if height is not None else w * ratio
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), **kwargs)
    # Remember the intended width so check() can tell a deliberate fraction of
    # the text width (a subfigure) from a figure resized by accident.
    fig._pubviz_width = w
    return fig, axes


def panel_labels(axes, labels=None) -> None:
    """Label panels (a), (b), ... at the top-left so the text can cite Fig. 2b."""
    import numpy as np

    flat = list(np.ravel(np.asarray(axes, dtype=object)))
    labels = labels or [f"({chr(ord('a') + i)})" for i in range(len(flat))]
    for ax, text in zip(flat, labels):
        ax.annotate(text, xy=(0, 1), xycoords="axes fraction", xytext=(0, 3), textcoords="offset points",
                    ha="left", va="bottom", fontweight="bold", fontsize=mpl.rcParams["axes.labelsize"])


def check(fig) -> list[str]:
    """Problems that make a figure print badly. Empty when the figure is fine."""
    ctx = current()
    problems = []
    w = fig.get_size_inches()[0]
    allowed = {round(ctx.layout.column, 2), round(ctx.layout.text, 2)}
    intended = getattr(fig, "_pubviz_width", None)
    if intended is not None and abs(w - intended) > 0.005:
        problems.append(f"width changed from {intended:.2f} in to {w:.2f} in after pv.figure()")
    elif intended is None and round(w, 2) not in allowed:
        problems.append(
            f"width {w:.2f} in is neither the column ({ctx.layout.column:.2f}) nor the text width "
            f"({ctx.layout.text:.2f}); LaTeX will rescale it and its text with it"
        )
    for ax in fig.axes:
        if ax.get_title():
            problems.append(f"axes title {ax.get_title()!r}: the caption is the title, remove it")
    fig.canvas.draw()
    tiny = sorted({round(t.get_fontsize(), 1) for t in fig.findobj(mpl.text.Text)
                   if t.get_visible() and t.get_text().strip() and t.get_fontsize() < 5})
    if tiny:
        problems.append(f"text below 5 pt does not survive print: sizes {tiny}")
    problems += _text_clashes(fig)
    return problems


def _drawn_texts(fig) -> list:
    """The texts a reader sees: tick labels inside the view, axis labels,
    annotations and legend entries."""
    texts = []
    for ax in fig.axes:
        for axis, limits in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = sorted(limits)
            slack = (hi - lo) * 1e-6
            for tick in axis.get_major_ticks():
                if lo - slack <= tick.get_loc() <= hi + slack and tick.label1.get_visible():
                    texts.append(tick.label1)
            texts.append(axis.label)
        texts += list(ax.texts)
        if ax.get_legend() is not None:
            texts += list(ax.get_legend().get_texts())
    for legend in fig.legends:
        texts += list(legend.get_texts())
    texts += list(fig.texts)
    return [t for t in texts if t.get_visible() and t.get_text().strip()]


def _text_clashes(fig) -> list[str]:
    """Texts that cover each other, or that run off the figure."""
    renderer = fig.canvas.get_renderer()
    boxes = [(t.get_text(), t.get_window_extent(renderer)) for t in _drawn_texts(fig)]
    problems = []
    edge = fig.bbox
    off = [text for text, b in boxes
           if b.x0 < edge.x0 - 1 or b.x1 > edge.x1 + 1 or b.y0 < edge.y0 - 1 or b.y1 > edge.y1 + 1]
    if off:
        problems.append("text runs off the figure: " + ", ".join(repr(t) for t in off[:4]))
    clashes = []
    for i, (a, box_a) in enumerate(boxes):
        for b, box_b in boxes[i + 1:]:
            width = min(box_a.x1, box_b.x1) - max(box_a.x0, box_b.x0)
            height = min(box_a.y1, box_b.y1) - max(box_a.y0, box_b.y0)
            if width > 1 and height > 1:
                clashes.append(f"{a!r} and {b!r}")
    if clashes:
        problems.append("texts overlap: " + "; ".join(clashes[:4]))
    return problems


def save(fig, stem: str, formats=("pdf",), close: bool = True) -> list[str]:
    """Write ``stem.pdf`` (and any other formats) at the built size and report problems.

    No ``bbox_inches="tight"``: trimming changes the printed width.
    """
    import matplotlib.pyplot as plt

    parent = os.path.dirname(stem)
    if parent:
        os.makedirs(parent, exist_ok=True)
    paths = []
    for ext in formats:
        path = f"{stem}.{ext}"
        fig.savefig(path, format=ext)
        paths.append(path)
    problems = check(fig)
    if close:
        plt.close(fig)
    for problem in problems:
        print(f"pubviz: {stem}: {problem}", file=sys.stderr)
    return paths
