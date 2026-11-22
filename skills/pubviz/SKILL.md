---
name: pubviz
description: Make the tables, figures and diagrams of a research paper with pubviz, so they share one accent color, survive grey printing and fit the venue's column. Use when writing or revising the results tables of a LaTeX paper (marking best and second-best values, changes against a baseline, a key under the table), when drawing matplotlib figures for a paper (benchmark bars, ablation changes, training curves, scaling laws, trade-offs, seeds and intervals, human ratings, confusion matrices, ROC, PR and DET curves, calibration, image grids, spectrograms, attention maps, embeddings), when drawing a method or architecture diagram in TikZ, or when choosing which table or figure a result needs.
license: MIT
compatibility: Needs Python 3.10 or newer with pip or uv, and LaTeX (TeX Live 2023-11 or newer, or Overleaf).
---

# pubviz

pubviz gives every table, figure and diagram of a paper one look, inside any
venue's template. Two parts work together:

- `pubviz.sty`, a LaTeX package: it marks the best values of a results table,
  writes a key under it, and adds TikZ styles for diagrams. Each compile also
  writes `<jobname>.pubviz.json`, a layout file with the column width, text
  width, font size, colors and language of that document.
- `pubviz`, a Python library: it reads the layout file and draws matplotlib
  figures at their printed width, with text sized for the venue, in the same
  colors as the tables.

All colors come from one accent. The accent means "ours" in figures and
"best" in tables; grey means a method compared with; green and red mean a
change that helps or hurts. Every color cue has a second cue (bold, a sign,
a name), so a grey print or a color-blind reader loses nothing.

## Set up

1. Install the library:

   ```sh
   pip install pubviz            # or: uv add pubviz
   pip install "pubviz[pandas]"  # to pass DataFrames
   ```

2. Put `pubviz.sty` of the same version next to the paper's main `.tex`
   (on Overleaf, upload it to the project):

   ```sh
   v=$(python -c "import pubviz; print(pubviz.__version__)")
   curl -fsSLo pubviz.sty "https://raw.githubusercontent.com/JacobLinCool/pubviz/v$v/latex/pubviz.sty"
   ```

   If the paper already has a `pubviz.sty`, its version is on the
   `\ProvidesExplPackage{pubviz}{date}{version}` line; keep the library at
   that version, or update both together.

3. Load it after the venue's own packages:

   ```latex
   \usepackage{pubviz}              % tables and colors
   % or
   \usepackage[diagrams]{pubviz}    % the same, plus the diagram styles (loads TikZ)
   ```

## Workflow

1. **Read the paper first.** Find the main `.tex`, the document class, any
   `\pvsetup{...}` already set (accent, `mode`, `language`), the figure
   folder, and where the results live (logs, CSV, JSON). Every number in an
   exhibit comes from those results. Never type a number from memory, round
   it by eye, or leave made-up demo data in a script.
2. **Choose the exhibit.** Write the one sentence the reader should take
   away, then follow the questions in
   [references/choosing.md](references/choosing.md). It leads to a table, a
   figure kind or a diagram.
3. **Tables** go in a `pvtable` environment with `\pvkey` after it; see
   [references/tables.md](references/tables.md).
4. **Compile once.** Next to the PDF there is now `<jobname>.pubviz.json`
   (in the output directory when one is set).
5. **Figures**: one script per figure beside the paper, such as
   `figs/ablation.py` writing `figs/ablation.pdf`; see
   [references/figures.md](references/figures.md).

   ```python
   import pubviz as pv

   pv.use("main.pubviz.json")       # before the first compile: a preset, pv.use("neurips")
   fig, ax = pv.figure("column")     # "text" for a figure* across both columns
   pv.deltas(ax, {name: pv.mean_ci(runs) for name, runs in changes.items()},
             xlabel="Accuracy change (points)")
   pv.save(fig, "figs/ablation")     # writes figs/ablation.pdf, fonts embedded
   ```

6. **Include** each figure at the width it was built for:

   ```latex
   \begin{figure}[t]        % figure* for a figure built with "text"
     \centering
     \includegraphics[width=\linewidth]{figs/ablation}
     \caption{\textbf{The adapter matters most; data mixing does not clearly help.}
       Accuracy change against the full model, with 95\% intervals of the change
       over five seeds.}
     \label{fig:ablation}
   \end{figure}
   ```

7. **Diagrams** are drawn in `pvdiagram`; see
   [references/diagrams.md](references/diagrams.md).
8. **Compile again and look at the PDF.**

## Rules

- **One exhibit, one point.** The caption opens with that point in bold,
  then gives what the reader needs to trust it: the number of runs or
  items, what an interval or band is, which points a fit used. When two
  points need two layouts, make two exhibits.
- **The caption never explains colors.** `\pvkey` under a table and the
  legend or line names of a figure show each mark beside its meaning.
- **Mark the proposed method**, so it gets the accent: `ours=` in every
  figure kind, `\pvours` in a table. Do not pick colors by hand.
- **Write which way is better where the measure is named**: `\pvup` and
  `\pvdown` in table headers, `better=` (or `better_x=`, `better_y=`) in
  figures.
- **Build at the printed size.** Make figures only with `pv.figure`, do not
  change their size afterwards, do not save with `bbox_inches="tight"`, and
  include them with `width=\linewidth`. The library sizes the text from the
  venue's body font.
- **No axes titles.** The caption is the title; use `pv.panel_labels(axes)`
  to name panels (a), (b) so the text can cite Fig. 2b.
- **Show the uncertainty of repeated runs**, and say how many runs in the
  caption. A claim that one method beats another is drawn as the difference
  with its own interval (`pv.deltas`), not as two intervals side by side.
- **Grey printing.** For a venue that prints in black and white, set
  `\pvsetup{mode=gray}` (or `mode=plain` for bold and underline only).
  Figures take the mode from the layout file.
- **Other languages.** `\usepackage[language=zh-tw]{pubviz}` (also `zh-cn`,
  `ja`, `ko`, or `\pvdefinelanguage`) writes the key in that language, and
  figures follow it through the layout file. Linux needs a CJK font, such as
  the `fonts-noto-cjk` package, for CJK text in figures.

## Check before handing over

- `pv.save` prints `pubviz: <file>: <problem>` for a width changed after
  `pv.figure`, an axes title, text smaller than 5 pt, and texts that overlap
  or run off the figure. Fix every one; `pv.style.check(fig)` returns the
  same list, empty when the figure is fine.
- Read the LaTeX log: `pvdiagram` warns when a diagram is wider than the
  line it sits in, and a key or table option error stops the compile with
  a message that names it.
- Look at the PDF: the marked values are the best ones in the direction of
  each arrow, the key lists only marks the table shows, and nothing in a
  figure is cut off or covered.

## More

- The evidence behind each rule and each answer of the tree:
  [guide](https://github.com/JacobLinCool/pubviz/blob/main/docs/guide.md) and
  [decision tree](https://github.com/JacobLinCool/pubviz/blob/main/docs/decision-tree.md).
- One runnable script per figure kind, with the LaTeX that includes it in
  its docstring:
  [examples/figures](https://github.com/JacobLinCool/pubviz/tree/main/examples/figures).
- Every option of the LaTeX package:
  [README, Options](https://github.com/JacobLinCool/pubviz#options).
