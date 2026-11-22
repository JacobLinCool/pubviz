# Figures

Every figure follows the same four steps.

```python
import pubviz as pv

pv.use("main.pubviz.json")      # the layout file the paper's compile writes
fig, ax = pv.figure("column")    # the printed width
pv.bars(ax, scores, ours="Ours", ylabel="Accuracy (%)")
pv.save(fig, "figs/scores")      # figs/scores.pdf; prints any problem it finds
```

## Setup and size

- `pv.use(layout, theme=None, font="sans", language=None, words=None)`.
  `layout` is the paper's `<jobname>.pubviz.json`, or a preset before the
  paper compiles: `neurips`, `iclr`, `icml`, `cvpr`, `acl`, `ieee`, `acm`,
  `acm-small`, `lncs`, `elsevier`, `article`. With a preset, give the
  paper's accent too: `pv.use("icml", theme="blue")`. Switch to the layout
  file once the paper compiles, because templates change from year to year.
  `font="body"` sets figure text in the paper's face, for figures with a lot
  of math.
- `pv.figure(which="column", ratio=0.62, height=None, nrows=1, ncols=1, **kw)`.
  `which` is `"column"`, `"text"` (a `figure*` across both columns), a
  fraction of the text width such as `0.48` (a subfigure), or inches (> 1).
  `ratio` is height over width. Other keywords go to `plt.subplots`
  (`sharex=True`, `height_ratios=[3, 1]`). Kinds with one row per item make
  the figure taller when the rows would not fit; the width never changes.
- `pv.save(fig, stem, formats=("pdf",))` writes `stem.pdf` with its fonts
  embedded, at the built size. Fix every problem it prints.
- `pv.panel_labels(axes)` writes (a), (b), … at the top left of each panel.
- `pv.mean_ci(runs)` gives `(mean, low, high)`: the mean over the first axis
  (seeds) and its 95% t-interval.

## Arguments most kinds share

- `ours=` names the proposed method (a name, a list of names, or a
  `(section, member)` pair). It gets the accent and a bold name; the others
  get greys. Without `ours`, methods get distinct colors.
- `better="higher"` or `"lower"`: which way is better, where a kind sorts or
  marks by it.
- `values=True` and `fmt="{:.1f}"`: the printed values and their format.
- `xlabel=`, `ylabel=`: axis titles with units. Never `ax.set_title`.

## Groups (`sections`)

`bars` (its benchmarks), `deltas`, `dots`, `means`, `distributions`,
`ranked` and `ratings` (their rows) take a second level of grouping:

```python
pv.deltas(ax, changes, sections={"Data": ["no mixing", "half data"],
                                 "Model": ["no adapter", "larger batch"]})
# or name rows as (section, member) pairs, so a member name can repeat:
pv.means(ax, {("Base", "1 pass"): runs_a, ("Ours", "1 pass"): runs_b,
              ("Ours", "3 passes"): runs_c}, ours=("Ours", "3 passes"))
```

Each section gets a gap before it, its name beside or under its members,
and a light band behind it. `band="all"` (the default) shades every
section, `band="alternate"` every other one, `band=None` none.

## Results of experiments

| Kind | Data | Notes |
| --- | --- | --- |
| `pv.bars(ax, data, ours=, errors=, ylabel=)` | `{method: {benchmark: score}}` or a DataFrame, methods as rows | Bars start at zero: for amounts measured from zero. `errors` has the same shape; say in the caption what they are. |
| `pv.deltas(ax, data, better="higher", ours=, unit="", xlabel=)` | `{variant: change}` or `{variant: (change, low, high)}` | The interval is of the change itself. Sorted best first; `key=True` names the colors above the plot. |
| `pv.curves(ax, x, series, ours=, labels="end", xlabel=, ylabel=)` | `x` of shape `(n,)`; `{name: values}` of shape `(n,)` or `(seeds, n)` | With seeds: the mean and a 95% band. Lines are named at their ends. |
| `pv.tradeoff(ax, points, ours=, better_x="lower", better_y="higher", xlabel=, ylabel=, logx=False)` | `{method: (x, y)}` | A dashed frontier joins the methods no other beats on both. Axis titles get the better-direction arrows. |
| `pv.heatmap(ax, values, rows, cols, better="higher", mark=None, center=None)` | a 2-D array, `rows` × `cols` | `mark="column"` or `"row"` sets each best in bold; `center=0` for signed changes. |
| `pv.dots(ax, runs, ours=, xlabel=)` | `{method: [per-run values]}` | For under ten runs: every run, the mean as a short bar. |
| `pv.means(ax, data, ours=, show="interval", xlabel=)` | `{method: [per-run values]}` or `{method: (mean, low, high)}` | `show="gradient"` shades how plausible each value is for the mean. Draws the runs faintly when given. Not bars. |
| `pv.distributions(ax, runs, ours=, kind="box", points=False, xlabel=)` | `{method: [many per-run values]}` | `kind`: `"box"` (medians, comparing groups), `"strip"` (range), `"violin"` (shape, two peaks), `"histogram"`. |
| `pv.ranked(ax, data, ours=, better="higher", sort="ours", xlabel=)` | `{item: value}` or `{item: {system: value}}` or a DataFrame, items as rows | Many items such as languages or classes; in place of a radar chart. |
| `pv.scaling(ax, data, ours=, upto=None, extend=None, xlabel=, ylabel=)` | `{name: (x, y)}` | Log axes and a power-law fit on points with x up to `upto`; hollow points were held out. Returns the fitted `(a, b)` per name. |
| `pv.ratings(ax, data, levels, ours=, neutral="split")` | `{system: [count per level]}`, `levels` from worst to best | MOS, Likert, or `["Loss", "Tie", "Win"]`. `neutral="aside"` sets the middle level apart. |

## What a model does

| Kind | Data | Notes |
| --- | --- | --- |
| `pv.confusion(ax, counts, labels, normalize="row")` | a square array of counts, true class by row | Rows as shares (each class's recall); `"column"` for precision, `"none"` for counts. |
| `pv.attention(ax, weights, x_labels, y_labels)` | an array, output items by input items | Say in the caption which layer and head the weights come from. |
| `pv.roc(ax, data, ours=)` | `{method: (labels, scores)}` | AUC beside each name. Add `pv.precision_recall` when positives are rare. |
| `pv.precision_recall(ax, data, ours=)` | `{method: (labels, scores)}` | AP beside each name; the dashed line is the share of positives. |
| `pv.det(ax, data, ours=, lim=(0.1, 40))` | `{method: (labels, scores)}`, 1 for a target trial | Normal-deviate axes; the EER is marked and printed. |
| `pv.reliability(ax, data, ours=, bins=10, counts_ax=None)` | `{method: (labels, probabilities)}` | ECE beside each name. Pass a second axes as `counts_ax` to show the cases per bin. |
| `fig, axes = pv.images(grid, which="text", ours=, zoom=None, error=None)` | `{example: {method: image}}`, images in [0, 1], all one size | Makes its own figure. `zoom=(x, y, w, h)` enlarges one region under every image; `error="Reference"` adds a row of differences from that column. |
| `pv.overlay(ax, image, weight, scale=None)` | an image and a weight map | The image in grey; a signed map in green and red. Say whether maps share a scale. |
| `pv.spectrogram(ax, audio, sr, mel=0, f0=None)` | samples and rate, or `level=` in dB with its `hop` | White for quiet to near black for loud; keep one `floor` for spectrograms that are compared. |
| `pv.waveform(ax, audio, sr)` | samples and rate | Put it above a spectrogram: `pv.figure(nrows=2, sharex=True, height_ratios=[1, 3])`. |
| `pv.embedding(ax, points, labels, most=None)` | an `(n, 2)` array and a class per point | Each class named on the map; small classes fold into "Other". |

Weights over the words of a sentence stay text in the paper: `pv.pvshade(tokens,
weights)` returns LaTeX built from `\pvshade{t}{word}` (unsigned) or
`\pvshade*{t}{word}` (signed). Use `join=""` for Chinese or Japanese.

## Multi-panel figures

```python
fig, axes = pv.figure("text", ratio=0.3, ncols=3, sharey=True)
for ax, (name, data) in zip(axes, panels.items()):
    pv.curves(ax, steps, data, ours="Ours", xlabel="Step")
axes[0].set_ylabel("Reward")
pv.panel_labels(axes)
pv.save(fig, "figs/panels")
```

Panels that share a quantity share its axis. Panels read left to right in
the order the text discusses them.

## Words in figures

The layout file carries the paper's language, so the words a kind writes
itself (the key of `deltas`, the axis titles of `confusion` and `roc`)
follow it. Without a layout file, `pv.use(..., language="ja")` picks a
built-in language (`en`, `zh-tw`, `zh-cn`, `ja`, `ko`). For another
language, pass `words={"better": ..., "worse": ..., "crosses": ...}`; the
same dictionary replaces default axis titles (see `pv.style.LABELS`).
In a CJK label write `L`, not `$L$`: matplotlib sets a label holding `$...$`
in math fonts, which have no CJK characters.
