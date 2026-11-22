# Diagrams

`\usepackage[diagrams]{pubviz}` adds TikZ styles in the paper's colors and
print mode, and the `pvdiagram` environment. It loads the TikZ libraries
`positioning`, `fit`, `backgrounds`, `arrows.meta` and `calc`. `pvdiagram`
draws at the printed size and warns in the log when the diagram is wider
than the line it sits in (the column, or the text width in a `figure*`).
Never scale a diagram down to fit: shorten labels, move blocks closer, or
stack the layout instead.

Place each node relative to another (`right=of a`, `above=4mm of b`), so
changing one gap or label moves the rest with it.

## What to draw

- **A pipeline** (steps in order): left to right; past about five steps,
  group them into stages. Plain text at the ends names what goes in and
  what comes out. Solid arrows for the main flow; a path used only in
  training, or a signal that goes back (a gradient, a reward), is dashed,
  and the caption says what dashed means.
- **An architecture** (parts of a model): inside one stack, bottom to top
  with the input at the bottom; between modules (encoder, decoder), left to
  right. A box is a layer, `pv op` (⊕) an add, a group box marked N× a layer
  repeated N times. Residual paths run around the side.
- **The contribution** stands out by role: every block white and only the
  part the paper adds in the accent (`pv new`). When the whole structure is
  the point, fill by kind instead (`pv kinds` in the `pvdiagram` options):
  one light fill per kind of layer, and the new part gets a thick accent
  border. Same kind, same fill, in every diagram of the paper.

## Block style

| Style | Draws |
| --- | --- |
| `pv block` | a layer or a step: a rounded white box |
| `pv new` | the part the paper adds: accent fill (or a thick accent border with `pv kinds`), bold label |
| `pv kinds`, `pv kind=1`…`6` | one light fill per kind of layer |
| `pv group` | a box around blocks that belong together, with `fit=(a)(b)` |
| `pv op`, `pv wave` | an add (⊕); a positional encoding (∿) |
| `pv flow`, `pv line` | an arrow; a line; both with rounded corners |
| `pv label`, `pv note` | text outside blocks; small grey text on an edge, such as a tensor shape |

```latex
\begin{figure}[t]
  \centering
  \begin{pvdiagram}
    \node[pv block] (emb) {Embedding};
    \node[pv block, above=of emb] (attn) {Attention};
    \node[pv block, pv new, above=of attn] (ffn) {Gated FFN};
    \node[pv block, above=of ffn] (head) {Output head};
    \draw[pv flow] (emb) -- (attn);
    \draw[pv flow] (attn) -- (ffn);
    \draw[pv flow] (ffn) -- (head);
    \begin{scope}[on background layer]
      \node[pv group, fit=(attn)(ffn), inner xsep=4mm, inner ysep=2.5mm] (layer) {};
    \end{scope}
    \node[pv label, right=1mm of layer] {$N\times$};
  \end{pvdiagram}
  \caption{\textbf{Ours replaces the feed-forward block with a gated one.} ...}
\end{figure}
```

## Light style

For a model drawn as stages rather than as every layer, and for pipelines.
A stack of layers is a small picture, flows are thin grey links, and parts
that belong together sit in a light region with no border.

| Style | Draws |
| --- | --- |
| `pv stack`, `pv layers=n` | a stack of n layers as a small picture; a node, so `right=of` and `.east` work |
| `pv link` | a thin grey arrow with an open head and rounded corners |
| `pv region`, `pv region=pv-fill-3` | a light region behind parts that belong together; tinted with the accent for the part the paper adds |
| `pv title`, `\pvnote{...}` | a stage title, and a small grey line under it |
| `pv emph` | an edge, a label or a stack in the accent; near black with a heavier line in grey and plain print |
| `\pvrepeat` | a loop sign, for a part that runs more than once |

```latex
\begin{figure*}[t]
  \centering
  \begin{pvdiagram}[node distance=6mm and 14mm]
    \node[pv stack] (enc) {};
    \node[pv title, above=2.5mm of enc] (t) {Encoder\\\pvnote{12 layers, frozen}};
    \node[pv stack, pv emph, right=of enc] (ad) {};
    \node[pv title, anchor=north] at (ad |- t.north) {Adapter\\\pvnote{\pvrepeat\ shared, 3 steps}};
    \node[pv stack, right=of ad] (dec) {};
    \node[pv title, anchor=north] at (dec |- t.north) {Decoder\\\pvnote{6 layers}};
    \begin{scope}[on background layer]
      \node[pv region=pv-fill-3, fit=(ad), inner sep=2.5mm] {};
    \end{scope}
    \node[pv label, inner sep=3pt, left=5mm of enc] (in) {Speech};
    \node[pv label, inner sep=3pt, right=5mm of dec] (out) {Text};
    \draw[pv link] (in) -- (enc);
    \draw[pv link] (enc) -- (ad);
    \draw[pv link, pv emph] (ad) -- (dec);
    \draw[pv link] (dec) -- (out);
  \end{pvdiagram}
  \caption{\textbf{A shared adapter between a frozen encoder and the decoder.} ...}
\end{figure*}
```

- Keep a title on every picture, and put the titles of one row on one line:
  place the first with `above=`, the others at `(node |- first.north)` with
  `anchor=north`, since a note with `\pvrepeat` is taller.
- The layers a stack shows are a picture, not a count: write the real count
  in the note, as some readers take four drawn layers to mean four.
- Keep each region in one piece, with its titles outside it.
- A branching line is drawn whole from its start for each branch, so every
  turn is rounded.

## Larger examples

[`transformer.tex`](https://github.com/JacobLinCool/pubviz/blob/main/examples/diagrams/transformer.tex)
(block style, fits one IEEE or ACM column),
[`looped.tex`](https://github.com/JacobLinCool/pubviz/blob/main/examples/diagrams/looped.tex),
[`asr.tex`](https://github.com/JacobLinCool/pubviz/blob/main/examples/diagrams/asr.tex) and
[`retrieval.tex`](https://github.com/JacobLinCool/pubviz/blob/main/examples/diagrams/retrieval.tex)
(light style).
