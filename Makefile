# Build the example paper for every venue, then the README gallery.
#
#   make test       run the Python and LaTeX tests
#   make examples   compile examples/venues/*.tex, draw their figures with
#                   examples/figures/*.py, compile again
#   make gallery    render the README and guide images to docs/img/*.png

VENUES := article ieee acm lncs elsevier
BUILD  := examples/build
TEX    := TEXINPUTS=$(CURDIR)/latex: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../build

.PHONY: test examples gallery report clean

test:
	uv run pytest -q

examples:
	@mkdir -p $(BUILD)
	@for v in $(VENUES); do \
	  echo "== $$v"; \
	  (cd examples/venues && $(TEX) $$v.tex > /dev/null) || { echo "LaTeX failed: $(BUILD)/$$v.log"; exit 1; }; \
	  for f in examples/figures/*.py; do \
	    uv run python $$f $(BUILD)/$$v.pubviz.json $(BUILD)/figs/$$v || exit 1; \
	  done; \
	  (cd examples/venues && $(TEX) $$v.tex > /dev/null && $(TEX) $$v.tex > /dev/null) || exit 1; \
	done

gallery: examples
	@mkdir -p docs/img $(BUILD)/gallery
	@for g in leaderboard modes themes figures figures-models venues diagram tokens; do \
	  (cd examples/gallery && TEXINPUTS=$(CURDIR)/latex: pdflatex -interaction=nonstopmode -halt-on-error \
	    -output-directory=../build/gallery $$g.tex > /dev/null) || { echo "LaTeX failed: $$g"; exit 1; }; \
	  pdftoppm -r 170 -png -singlefile $(BUILD)/gallery/$$g.pdf docs/img/$$g; \
	done
	@# The decision tree: one chart per page, rendered to docs/img/tree-<n>.png.
	@(cd examples/gallery && TEXINPUTS=$(CURDIR)/latex: pdflatex -interaction=nonstopmode -halt-on-error \
	  -output-directory=../build/gallery tree.tex > /dev/null) || { echo "LaTeX failed: tree"; exit 1; }
	@pdftoppm -r 170 -png $(BUILD)/gallery/tree.pdf docs/img/tree
	@# The diagrams in the light style, one per page: docs/img/diagrams-<n>.png.
	@(cd examples/gallery && TEXINPUTS=$(CURDIR)/latex: pdflatex -interaction=nonstopmode -halt-on-error \
	  -output-directory=../build/gallery diagrams.tex > /dev/null) || { echo "LaTeX failed: diagrams"; exit 1; }
	@pdftoppm -r 170 -png $(BUILD)/gallery/diagrams.pdf docs/img/diagrams
	@# One image per figure kind for the guide, as drawn for an IEEE column.
	@for f in examples/figures/*.py; do \
	  k=$$(basename $$f .py); \
	  pdftoppm -r 170 -png -singlefile $(BUILD)/figs/ieee/$$k.pdf docs/img/fig-$$k; \
	done
	@# Sections: a second level of grouping in a figure.
	@for k in means-sections bars-sections; do \
	  pdftoppm -r 170 -png -singlefile $(BUILD)/figs/ieee/$$k.pdf docs/img/fig-$$k; \
	done
	@ls docs/img

# The technical report: compute the checks, compile once for the layout file,
# draw its figures from the evidence, then compile with the bibliography.
REPORT := $(BUILD)/report
REPORTTEX := TEXINPUTS=$(CURDIR)/latex: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../examples/build/report
report:
	@mkdir -p $(REPORT)
	uv run python report/analysis.py > /dev/null
	(cd report && $(REPORTTEX) report.tex > /dev/null) || { echo "LaTeX failed: $(REPORT)/report.log"; exit 1; }
	uv run python report/figures.py $(REPORT)/report.pubviz.json $(REPORT)
	(cd report && $(REPORTTEX) report.tex > /dev/null) || exit 1
	(cd $(REPORT) && BIBINPUTS=$(CURDIR)/report: bibtex report > /dev/null) || exit 1
	@# Rerun until the floats and references settle (at most three passes).
	(cd report && for i in 1 2 3; do $(REPORTTEX) report.tex > /dev/null || exit 1; \
	  grep -q "Rerun to get" ../$(REPORT)/report.log || break; done) || exit 1
	@grep -c "Warning" $(REPORT)/report.log || true
	@pdfinfo $(REPORT)/report.pdf | grep Pages

clean:
	rm -rf $(BUILD)
