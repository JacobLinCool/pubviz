"""The agent skill in skills/pubviz stays true to the library it describes."""

import re
from pathlib import Path

import pytest

import pubviz as pv
from test_figures import KINDS

SKILL = Path(__file__).resolve().parent.parent / "skills" / "pubviz"
FILES = sorted(SKILL.rglob("*.md"))


def frontmatter() -> dict[str, str]:
    text = (SKILL / "SKILL.md").read_text()
    head = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert head, "SKILL.md starts with YAML frontmatter"
    return dict(line.split(": ", 1) for line in head.group(1).splitlines())


def test_frontmatter_follows_the_agent_skills_format():
    fields = frontmatter()
    # The name is the folder's, in lowercase letters and hyphens.
    assert fields["name"] == SKILL.name and re.fullmatch(r"[a-z0-9-]{1,64}", fields["name"])
    assert 0 < len(fields["description"]) <= 1024
    assert len(fields["compatibility"]) <= 500


def test_every_figure_kind_is_described():
    figures = (SKILL / "references" / "figures.md").read_text()
    for kind in KINDS + ["waveform"]:
        assert hasattr(pv, kind) and f"pv.{kind}(" in figures, kind


def slug(heading: str) -> str:
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def test_links_between_skill_files_resolve():
    for path in FILES:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if target.startswith("http"):
                continue
            name, _, anchor = target.partition("#")
            linked = (path.parent / name) if name else path
            assert linked.exists(), (path.name, target)
            if anchor:
                headings = re.findall(r"^#+ (.+)$", linked.read_text(), re.M)
                assert anchor in {slug(h) for h in headings}, (path.name, target)


def latex_examples() -> list[str]:
    blocks = []
    for name in ("tables.md", "diagrams.md"):
        text = (SKILL / "references" / name).read_text()
        blocks += [b for b in re.findall(r"```latex\n(.*?)```", text, re.S) if r"\begin{table}" in b
                   or r"\begin{figure" in b]
    return blocks


def test_latex_examples_compile_at_their_printed_size(tmp_path, latex):
    examples = latex_examples()
    assert len(examples) == 3
    doc = tmp_path / "skill.tex"
    doc.write_text("\\documentclass[conference]{IEEEtran}\n\\usepackage[diagrams]{pubviz}\n"
                   "\\begin{document}\n" + "\n".join(examples) + "\n\\clearpage\n\\end{document}\n")
    log = latex(doc)
    assert "wider than the line" not in log


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_made_up_api(path):
    # Every pv.<name> the skill mentions exists in the library.
    for name in set(re.findall(r"\bpv\.([a-z_]+)", path.read_text())):
        assert hasattr(pv, name), (path.name, name)
