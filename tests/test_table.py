import math

from pubviz.table import pvtable


def test_markers_land_where_the_package_reads_them():
    data = {"Base": {"Acc": 70.1, "WER": 12.4}, "Ours": {"Acc": 74.0, "WER": 10.2}}
    tex = pvtable(data, ours="Ours", baseline="Base", lower=["WER"])
    assert "\\begin{pvtable}[by=column, delta=absolute]{lcc}" in tex
    assert "\\pvbaseline Base & 70.1 & 12.4 \\\\" in tex
    assert "\\pvours Ours & 74.0 & 10.2 \\\\" in tex
    assert "WER \\pvdown" in tex


def test_by_row_marks_methods_in_the_header():
    data = {"Speed": {"A": 1.0, "Ours": 2.0}}
    tex = pvtable(data, by="row", ours="Ours", sections={"Fast": ["Speed"]})
    assert " & A & \\pvours Ours \\\\" in tex
    assert "\\pvsection{Fast} \\\\" in tex


def test_missing_spread_and_percent():
    data = {"M": {"a": None, "b": (72.31, 0.42), "c": math.nan, "d": 46.5}}
    tex = pvtable(data, percent=["d"], digits=1)
    assert "M & -- & $72.3 \\pm 0.4$ & -- & 46.5\\% \\\\" in tex


def test_escape():
    tex = pvtable({"a_b & c": {"x%": 1.0}})
    assert "a\\_b \\& c" in tex and "x\\%" in tex


def test_generated_table_compiles_and_ranks(latex, tmp_path):
    data = {"Base": {"Acc": 70.1, "F1": 0.61}, "Prior": {"Acc": 72.3, "F1": 0.64},
            "Ours": {"Acc": 74.0, "F1": 0.66}}
    body = pvtable(data, ours="Ours", baseline="Base", digits={"Acc": 1, "F1": 2}, key=True)
    doc = tmp_path / "gen.tex"
    doc.write_text("\\documentclass{article}\\usepackage{pubviz}\\pvsetup{debug=true}"
                   "\\begin{document}\n" + body + "\\end{document}\n")
    log = latex(doc)
    assert "pubviz rank: table 1 row 4 col 2 value 74 rank 1" in log
    assert "pubviz rank: table 1 row 3 col 3 value 0.64 rank 2" in log
    assert "pubviz key: table 1: " in log
