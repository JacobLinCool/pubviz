# Tables

Write the table body as usual inside `pvtable`, and put `\pvkey` after it.
pubviz finds the numbers, marks the best and second best in each column,
greys missing values and writes the key from what the table shows.

```latex
\begin{table}[t]
  \centering\small
  \caption{\textbf{Ours improves every metric over the base model.}
    Accuracy on the test set; word error rate and real-time factor on ...}
  \label{tab:main}
  \begin{pvtable}[delta=absolute]{lccc}
    \toprule
    Method & Acc \pvup & WER \pvdown & RTF \pvdown \\
    \midrule
    \pvbaseline Base & 70.1 & 12.4 & 0.31 \\
    Prior A & 72.3 & 11.9 & 0.35 \\
    \pvours Ours & $74.0 \pm 0.4$ & 10.2 & 0.28 \\
    \bottomrule
  \end{pvtable}
  \pvkey[baseline=Base]
\end{table}
```

## What pubviz reads from the body

- **Numbers.** A cell holding a number, optionally signed, with `\%`, or as
  `$mean \pm spread$`, takes part. Anything else stays as written. Braces
  keep a number out: `{2024}`.
- **Headers.** Rows above the first `\midrule` (or `\hline`) are headers.
  For a table without one, set `header=`.
- **Direction.** `\pvup` or `\pvdown` (or `$\uparrow$`, `$\downarrow$`) where
  a measure is named sets which way is better; otherwise `better=` decides.
- **What is compared.** `by=column` (the default) compares within each
  column, for methods listed down the table. `by=row` compares within each
  row, for methods listed across; the method marks then go in the header.
- **Methods.** `\pvours` (bold), `\pvbaseline` (the reference for changes),
  `\pvnorank` (shown, never ranked, such as an oracle or an upper bound).
- **Missing values.** `-`, `--`, `n/a` or `\pvna` become a grey dash.
- **Sections.** `\pvsection{Coding} \\` starts a full-width band.
- **Sub-labels.** `\pvlabel{RepoFix}{harness v2.4}` adds a small grey line
  under a label.

Numbers pubviz cannot read, so they are left out of the ranking without a
warning: a thousands separator (`1,234`), a Unicode `±`, a subscripted
spread (`$70.0_{\pm 0.4}$`), a footnote mark or `*` after the number, and a
number already set in `\textbf`. Write `1234`, `\pm`, and no bold by hand.
A `\multicolumn` in a body row is kept as text.

## Choosing the options

| Claim | Options |
| --- | --- |
| which method is best on each measure | the defaults: `ranks=2`, best filled and bold, second filled |
| a change from one baseline | `\pvbaseline` on its row, `delta=absolute` or `relative`; `show=delta` for the change alone |
| a pattern across a grid | `heat=group` (within each column or row) or `heat=table` (one scale) |
| many methods across many benchmarks | `by=column`, `\pvsection` bands for families of methods |
| methods as columns, benchmarks as rows | `by=row`, method marks in the header |

Other options: `ranks=0` to `3`; `ties=shared` (after a tie for best, the
next is third) or `dense`; `fill=chip`, `cell` or `none`; `align=c`, `l`,
`r`; `label-cols=1`; `missing=\textendash`. Set them for one table in
`\begin{pvtable}[...]`, or for the paper in `\pvsetup{...}`.

## The key

`\pvkey` writes one line per mark the table shows, each opening with the
mark itself, so the caption never describes colors. It lists only what is
there; the note on ties appears only after a tie.

- `\pvkey[baseline=Base]` names the reference of the changes.
- `\pvkey[ours={Our method}]` adds a line for the `\pvours` row; a row named
  "Ours" needs none.
- `\pvkey[best={Best reported score}]` changes one word for one key;
  `\pvsetup{key/best={...}}` for the paper.
- `\usepackage[language=zh-tw]{pubviz}` (`zh-cn`, `ja`, `ko`) writes the key
  in that language. Define another with
  `\pvdefinelanguage{de}{best=Beste, second=Zweitbeste, ...}` and
  `\pvsetup{language=de}`; words left out stay English.
- `\pvkey` must come after a `pvtable`; placed before any, it stops the
  compile with an error.

## Colors and print

```latex
\usepackage[theme=blue]{pubviz}   % amber (default), blue, teal, green, red, purple, gray
\pvsetup{accent=1A73D5}           % or any hex value or xcolor color
\pvsetup{mode=gray}               % color | gray | plain (bold and underline, no fills)
```

Use one accent per paper; the figures take it from the layout file.

## Marks by hand

In a plain `tabular`: `\pvbest{..}`, `\pvsecond{..}`, `\pvthird{..}`,
`\pvheat{0.7}{..}`, `\pvdelta{+2.3}`, `\pvdelta[lower]{+0.4}`, `\pvna`,
`\pvsectionrow{<columns>}{<title>}`. To explain a mark in a caption above
its table, write `\pvbest{Best} in each row`.

## Tables from Python

For results that live in Python, `pv.pvtable` returns the LaTeX of a
`pvtable`, with the numbers formatted the same way every time:

```python
import pubviz as pv

latex = pv.pvtable(
    {"Base": {"Acc": 70.1, "WER": 12.4}, "Ours": {"Acc": (74.0, 0.4), "WER": 10.2}},
    ours="Ours", baseline="Base", lower=["WER"], digits=1, key=True,
    options="delta=absolute")
open("tables/main.tex", "w").write(latex)   # then \input{tables/main} inside a table float
```

`data` maps row to `{column: value}` or is a DataFrame. Values are numbers,
`(mean, spread)` pairs, strings (kept as written) or `None`/NaN (missing).
`sections={"Coding": ["A", "B"]}` adds bands; `by="row"` puts methods in
columns; `percent=` and `digits=` apply to all or to named measures.

When a table looks wrong, `\pvsetup{debug=true}` logs every rank, color and
key decision.
