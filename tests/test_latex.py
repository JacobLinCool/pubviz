"""Compile real documents and check what pubviz.sty decided."""

import json
import re
from pathlib import Path

import pytest

from pubviz.theme import derive_roles

ROLE = re.compile(r"pubviz roles \((\w+)\): (.*)")
RANK = re.compile(r"pubviz rank: table (\d+) row (\d+) col (\d+) value (\S+) rank (\d+) \((\w+)\)")


def ranks(log: str, table: int = 1) -> dict[tuple[int, int], int]:
    """Rank of each (row, column) in the given table, as the package logged it."""
    return {(int(r), int(c)): int(k) for t, r, c, _, k, _ in RANK.findall(log) if int(t) == table}


def test_latex_and_python_derive_the_same_colors(latex):
    log = latex("agreement.tex")
    lines = ROLE.findall(log)
    assert len(lines) == 26
    accents = ["E4AE1A", "1A73D5", "009A9A", "2E9E52", "DA4339", "8254C4", "717171",
               "FF0000", "00FF00", "0000FF", "F8DC8C", "101010", "FFFFFF"]
    expected_modes = [m for _ in accents for m in ("color", "gray")]
    for (mode, body), accent, want_mode in zip(lines, [a for a in accents for _ in (0, 1)], expected_modes):
        assert mode == want_mode
        got = dict(item.split("=") for item in body.split())
        want = derive_roles("#" + accent, gray=mode != "color")
        for name, value in got.items():
            key = name.replace("-", "")
            assert "#" + value == want[key], (accent, mode, name)


def test_ranks_by_row_with_shared_ties_and_direction(latex):
    log = latex("smoke.tex")
    r = ranks(log)
    # Row 3: 20.1 tied for best twice, so 13.6 is third, not second.
    assert r[(3, 2)] == 1 and r[(3, 5)] == 1 and r[(3, 6)] == 3
    # Row 4: only two values; missing cells do not count.
    assert r[(4, 2)] == 1 and r[(4, 6)] == 2 and (4, 3) not in r
    # Row 7 is marked \pvdown: the lowest latency wins.
    assert r[(7, 3)] == 1 and r[(7, 6)] == 2 and r[(7, 4)] == 5


def test_ranks_by_column_skip_unranked_rows(latex):
    log = latex("columns.tex")
    r = ranks(log)
    # Accuracy: the oracle (\pvnorank, row 6) is ignored, so Ours (row 5) is best.
    assert (6, 2) not in r
    assert r[(5, 2)] == 1 and r[(4, 2)] == 2
    # WER is marked with $\downarrow$ in the header.
    assert r[(5, 4)] == 1
    # Dense ties: two values tied for best, the next value is second.
    assert r[(3, 5)] == 1 and r[(4, 5)] == 1 and r[(5, 5)] == 2


@pytest.mark.parametrize("engine", ["pdflatex", "lualatex", "xelatex"])
def test_every_option_compiles(latex, engine):
    log = latex("options.tex", engine)
    assert "pubviz" in log


def test_heat_per_column_follows_direction(latex):
    log = latex("options.tex")
    tables = re.findall(r"pubviz table: (.*)", log)
    heat_table = next(t for t in tables if t.startswith("\\toprule M&Acc&Err"))
    # Acc rises a -> c, Err falls a -> c and is lower-is-better: both end on the darkest step.
    assert heat_table.count("{pv-heat-8}") == 2 and heat_table.count("{pv-heat-0}") == 2


@pytest.mark.parametrize("venue", ["article", "ieee", "acm", "lncs", "elsevier"])
def test_example_paper_in_each_venue(latex, venue):
    source = Path(__file__).resolve().parent.parent / "examples" / "venues" / f"{venue}.tex"
    log = latex(source)
    assert "Package pubviz Warning" not in log
    assert "Overfull \\hbox" not in log
    layout = (latex.outdir / f"{venue}.pubviz.json").read_text()
    assert '"columnwidth_in"' in layout


KEY = re.compile(r"pubviz key: table (\d+): (.*)")


def test_key_explains_the_marks_each_table_shows(latex):
    keys = {int(t): body.split(" | ") for t, body in KEY.findall(latex("key.tex"))}
    best = r"\__pv_key_cue:nn {1}{Best} in each row (lowest where lower is better); ties share a mark"
    second = r"\__pv_key_cue:nn {2}{Second best} in each row; none when first place is tied"
    missing = r"\__pv_na:  not reported"
    assert keys[1] == [best, second, missing]
    # Plain mode gives third place no mark, so the key has no line for it.
    assert keys[2] == [best, second, missing]
    assert keys[3] == [
        r"\__pv_key_cue:nn {1}{Best} in each column (lowest where lower is better)",
        r"\__pv_key_cue:nn {2}{Second best} in each column",
        r"Small numbers: change against Base, \__pv_delta_text:nn {1}{better} or \__pv_delta_text:nn {-1}{worse}",
    ]
    # In grey, color no longer tells better from worse, so the key does not say it does.
    assert keys[4][-1] == "Small numbers: change against the baseline"
    # Shading takes the fills: best stays bold, second has no mark and no line.
    # The words come from \pvsetup{key/best=...} here.
    assert keys[5] == [r"\__pv_key_cue:nn {1}{Top value} in each column",
                       r"Shading across the table: worse \__pv_key_ramp:  better"]
    # Tables 1-4 mark a method \pvours but set no words for it, so no line.
    assert not any("key_ours" in line for t in (1, 2, 3, 4) for line in keys[t])
    assert keys[6][-1] == r"\__pv_key_ours:n {This paper's method}"
    assert not any("key_ours" in line for line in keys[7])


def test_key_in_chinese(latex):
    log = latex("key-zh.tex", engine="xelatex")
    keys = {int(t): body.split(" | ") for t, body in KEY.findall(log)}
    assert keys[1] == [
        r"\__pv_key_cue:nn {1}{最佳} 每欄（越低越好者取最低）",
        r"\__pv_key_cue:nn {2}{次佳} 每欄",
        r"小字：相對基準的變化，\__pv_delta_text:nn {1}{較好}或\__pv_delta_text:nn {-1}{較差}",
    ]
    assert keys[2] == [r"\__pv_key_cue:nn {1}{最好} 每欄", r"整張表的底色：較差 \__pv_key_ramp:  較好"]
    # The figures write their own words in the same language.
    layout = json.loads((latex.outdir / "key-zh.pubviz.json").read_text())
    assert layout["language"] == "zh-tw"
    assert layout["words"] == {"better": "較好", "worse": "較差", "crosses_zero": "區間跨過零"}


def test_key_in_other_languages(latex):
    log = latex("key-lang.tex", engine="xelatex")
    keys = {int(t): body.split(" | ") for t, body in KEY.findall(log)}
    # Korean separates words with spaces and has no word before the baseline.
    assert keys[1] == [
        r"\__pv_key_cue:nn {1}{최고} 각 열 (낮을수록 좋은 열은 최솟값)",
        r"\__pv_key_cue:nn {2}{두 번째} 각 열",
        r"작은 숫자: 기준 대비 변화, \__pv_delta_text:nn {1}{좋음} 또는 \__pv_delta_text:nn {-1}{나쁨}",
    ]
    # A language defined in the document; the words it leaves out are English.
    assert keys[2] == [
        r"\__pv_key_cue:nn {1}{Beste} in jeder Spalte (lowest where lower is better)",
        r"\__pv_key_cue:nn {2}{Zweitbeste} in jeder Spalte",
        r"Kleine Zahlen: Änderung gegenüber der Basis, \__pv_delta_text:nn {1}{besser} oder \__pv_delta_text:nn {-1}{schlechter}",
    ]
    # Japanese: no spaces between words, full-width punctuation.
    assert keys[3] == [r"\__pv_key_cue:nn {1}{最良} 各列", r"表全体の濃淡：悪い \__pv_key_ramp:  良い"]
    layout = json.loads((latex.outdir / "key-lang.pubviz.json").read_text())
    assert layout["language"] == "ko"
    assert layout["words"] == {"better": "좋음", "worse": "나쁨", "crosses_zero": '0 "포함"'}


def test_unknown_language_is_an_error(tmp_path):
    from conftest import compile_tex

    doc = tmp_path / "lang.tex"
    doc.write_text("\\documentclass{article}\\usepackage[language=xx]{pubviz}\\begin{document}x\\end{document}\n")
    code, log = compile_tex(doc, tmp_path)
    assert code != 0 and "No language 'xx'" in log


def test_layout_file_is_json_with_the_words(latex):
    latex("key.tex")
    layout = json.loads((latex.outdir / "key.pubviz.json").read_text())
    assert layout["language"] == "en"
    assert layout["words"] == {"better": "better", "worse": "worse", "crosses_zero": "interval crosses zero"}


def test_table_options_set_that_tables_colors(latex):
    log = latex("key.tex")
    blue, amber = derive_roles("#1A73D5")["fill1"][1:], derive_roles("#E4AE1A")["fill1"][1:]
    assert f"fill-1={blue}" in log
    assert "pubviz roles (gray)" in log
    # After the table the document's own colors are back.
    assert f"fill-1 now: {amber}" in log


def test_key_before_any_table_is_an_error(tmp_path):
    from conftest import compile_tex

    doc = tmp_path / "early.tex"
    doc.write_text("\\documentclass{article}\\usepackage{pubviz}\\begin{document}\\pvkey\\end{document}\n")
    code, log = compile_tex(doc, tmp_path)
    assert code != 0 and "pvkey explains the pvtable before it" in log


@pytest.mark.parametrize("engine", ["pdflatex", "lualatex", "xelatex"])
def test_diagrams_compile_and_warn_when_too_wide(latex, engine):
    log = latex("diagram.tex", engine)
    warnings = re.findall(r"The diagram is ([\d.]+)pt wider than the line", log)
    assert len(warnings) == 1 and float(warnings[0]) > 0


def test_tikz_loads_only_with_the_diagrams_option(tmp_path):
    from conftest import compile_tex

    doc = tmp_path / "plain.tex"
    doc.write_text("\\documentclass{article}\\usepackage{pubviz}\\makeatletter"
                   "\\typeout{TIKZ=\\@ifpackageloaded{tikz}{yes}{no}}\\begin{document}x\\end{document}\n")
    code, log = compile_tex(doc, tmp_path)
    assert code == 0 and "TIKZ=no" in log


@pytest.mark.parametrize("engine", ["pdflatex", "lualatex", "xelatex"])
def test_token_shading_compiles_in_every_mode(latex, engine):
    log = latex("shade.tex", engine)
    assert "Warning" not in "\n".join(l for l in log.splitlines() if "pubviz" in l)


def test_python_writes_token_shading_latex_can_set(latex, tmp_path):
    import pubviz as pv

    body = pv.pvshade(["a_b", "{x}", "50%", "c^2", "~", "back\\slash"], [0.2, -0.5, 1.0, 0.0, 0.3, -0.1])
    doc = tmp_path / "tokens.tex"
    doc.write_text("\\documentclass{article}\\usepackage{pubviz}\\begin{document}\n" + body + "\\end{document}\n")
    latex(doc)


@pytest.mark.parametrize("engine", ["pdflatex", "lualatex", "xelatex"])
def test_light_diagrams_compile_in_every_mode_within_the_line(latex, engine):
    log = latex("diagrams-light.tex", engine)
    assert "wider than the line" not in log
