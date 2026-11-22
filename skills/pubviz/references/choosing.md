# Choosing the exhibit

Start from the one sentence the reader should take away, then answer the
questions in order. Each answer ends at a table, a figure kind or a diagram.
The numbers in brackets are the notes of the
[decision tree](https://github.com/JacobLinCool/pubviz/blob/main/docs/decision-tree.md),
which give the studies and arguments behind each answer.

## 1. What should the reader take away?

- **How the method works** → a diagram, `pvdiagram` [1]. See
  [diagrams.md](diagrams.md).
- **Exact values, or many measures per method** → a table, `pvtable` [2].
  Go to section 2.
- **A shape or a comparison** → ask what each number is:
  - one measured amount (a count, a share, one run) → section 3;
  - an estimate from repeated runs (seeds, people, test items) → section 4;
  - answers on an ordered rating scale (MOS, Likert, win / tie / loss) →
    diverging stacked bars, `pv.ratings` [3];
  - a series over steps or time → lines named at their ends, and panels if
    there are many, `pv.curves` [4];
  - a measure against model size, data or compute → log axes and a fitted
    power law, `pv.scaling` [5];
  - two measures that pull against each other (quality and cost, accuracy
    and latency) → points and their frontier, `pv.tradeoff` [6].
- **What the model does with its inputs** → section 5.

## 2. Tables

- Is the claim a change from one baseline?
  - **Yes** → the signed change beside each value: `\pvbaseline` on the
    reference row and `delta=absolute` (or `relative`) [7].
  - **No** → does the pattern across cells matter more than the best one?
    - **Yes** → shading by value, `heat=group` (or `heat=table`) [8].
    - **No** → best and second best marked, `ranks=2` (the default), with
      `\pvkey` under the table [9].

## 3. One measured amount

- Are the differences small next to the values?
  - **Yes**, bars from zero would hide them → draw the differences
    themselves, `pv.deltas` [10].
  - **No** → how many factors?
    - one, a few items → bars from zero, `pv.bars` [11];
    - one, many items (languages, classes, tasks) → a dot per item, sorted,
      `pv.ranked` [12]; never a radar chart;
    - two, both ordered (sizes, rates, steps) → `pv.heatmap` [13];
    - two kinds, a few of each → grouped bars from zero, `pv.bars` [11];
    - two kinds, many of each → a table (section 2).

## 4. An estimate from repeated runs

- What is the claim about?
  - **A difference between methods** → the difference with its own
    interval, `pv.deltas` [14], never two intervals side by side:
    - both methods ran on the same seeds or items (paired): take the
      difference per run, then `pv.mean_ci(differences)`;
    - they did not (independent): the difference of the means, with a
      margin of √(w₁² + w₂²) from the two 95% margins, an approximation.
  - **The level of each method** → a point and its interval, or a gradient
    of the mean's uncertainty, with the runs drawn faintly, `pv.means` [15];
    not a bar.
  - **How the runs spread** → how many runs per group?
    - a handful, under ten → every run as a dot with the mean marked,
      `pv.dots` [16];
    - many → `pv.distributions` [17], with `kind=` chosen by what the
      reader judges: `"box"` for medians and comparing groups, `"strip"`
      for the range and spread, `"violin"` for shape such as two peaks,
      `"histogram"` for counts in ranges.

## 5. What the model does

- What should the reader see of the model?
  - **Which classes it mixes up** → a confusion matrix with each row as
    shares of its true class, `pv.confusion` [18].
  - **Its errors at every threshold** → `pv.roc`; add `pv.precision_recall`
    when positives are rare; `pv.det` for verification and detection
    (speaker verification, keyword spotting) [19].
  - **Whether its probabilities can be trusted** → a reliability diagram
    with the cases per bin, `pv.reliability` [20].
  - **Where it places its inputs** → a map of points with each class named
    on it, `pv.embedding` [21]; say in the caption that distances between
    t-SNE or UMAP clusters carry no meaning.
  - **Its outputs**:
    - images → an image grid with one region enlarged, `pv.images` [22];
    - sounds → a spectrogram in dB with the pitch on top,
      `pv.spectrogram` [23].
  - **What its outputs rest on** → weights over what?
    - another sequence (attention, alignment) → `pv.attention` [24];
    - an image (saliency) → the map over the image in grey,
      `pv.overlay` [25];
    - the words of a text → shaded words, `\pvshade` or `pv.pvshade` [26].

## Groups within an exhibit

When methods come in groups (prior work and ours, each model with several
settings, benchmarks by domain), keep one exhibit and group its rows:
`\pvsection{...}` in a table, `sections=` in `bars`, `deltas`, `dots`,
`means`, `distributions`, `ranked` and `ratings`. See
[figures.md](figures.md#groups-sections).
