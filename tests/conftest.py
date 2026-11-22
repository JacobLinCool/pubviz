import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LATEX_DIR = ROOT / "latex"
TEX_DIR = Path(__file__).resolve().parent / "tex"


def compile_tex(source: Path, outdir: Path, engine: str = "pdflatex") -> tuple[int, str]:
    """Compile ``source`` into ``outdir`` with pubviz.sty on the path.

    Returns the exit code and the log text, with long lines kept whole so
    log parsing does not depend on TeX's line wrapping.
    """
    if not shutil.which(engine):
        pytest.skip(f"{engine} not installed")
    env = dict(os.environ)
    env["TEXINPUTS"] = f"{LATEX_DIR}{os.pathsep}{source.parent}{os.pathsep}"
    env["max_print_line"] = "100000"
    proc = subprocess.run(
        [engine, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={outdir}", str(source)],
        cwd=source.parent, env=env, capture_output=True, text=True, timeout=300,
    )
    log = (outdir / (source.stem + ".log")).read_text(errors="replace")
    return proc.returncode, log


@pytest.fixture
def latex(tmp_path):
    def run(source, engine="pdflatex"):
        path = Path(source)
        if not path.is_absolute():
            path = TEX_DIR / path
        code, log = compile_tex(path, tmp_path, engine)
        assert code == 0, "LaTeX failed:\n" + "\n".join(l for l in log.splitlines() if l.startswith("!"))[:2000]
        return log

    run.outdir = tmp_path
    return run
