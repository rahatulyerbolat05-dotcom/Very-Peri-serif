# Very Peri Serif: build from the sources in data/ and tools/.
#   make            both styles, then fonts/ttf otf webfonts, docs/qa and the download in dist/
#   make regular    the Regular only (build/release, test copy in dist/test)
#   make quality    independent acceptance, FontBakery Universal and Hyperglot on build/release
#   make clean      remove build/
# Requires Python 3.12, requirements.txt + requirements-quality.txt, and git.

PY  := python3 -I
BROWSER ?= 0
REF := reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf

.PHONY: all release family italic regular reference quality contour-audit clean

all: release

$(REF):
	bash tools/fetch_reference.sh

reference: $(REF)

regular: $(REF)
	$(PY) tools/build_regular_release.py
	$(PY) tools/make_test_copy.py

italic: regular
	$(PY) tools/italic_caps.py
	$(PY) tools/italic_lower.py
	$(PY) tools/italic_features.py

family: italic
	$(PY) tools/build_family.py

release: family
	$(PY) tools/check_italic_el_alternate.py --formats ttf,woff2
	$(PY) tools/check_exact_node_reduction.py
	$(PY) tools/check_family.py
	$(PY) tools/check_curve_finish.py
	$(PY) tools/check_ya_revision.py
	$(PY) tools/check_ghe_width.py
	$(PY) tools/check_tail_joins.py --formats ttf,woff2
	$(PY) tools/check_italic_che.py --formats ttf,woff2
	$(PY) tools/quality_family.py
	$(PY) tools/family_proof.py
	$(PY) tools/el_alternate_proof.py
	$(PY) tools/node_reduction_proof.py
	$(PY) tools/curve_finish_proof.py
	$(PY) tools/ya_revision_proof.py
	$(PY) tools/ghe_width_proof.py
	$(PY) tools/italic_tail_loop_proof.py
	$(PY) tools/italic_che_proof.py
	$(PY) tools/family_curve_audit.py --root build/release --output docs/qa/curve-inventory.json
	$(PY) tools/optical_review.py
	$(PY) tools/package_release.py $(if $(filter 1,$(BROWSER)),--browser,)
	$(PY) tools/package_renamed_copy.py
	$(PY) tools/check_final_freeze.py
	$(PY) tools/check_italic_el_alternate.py --root fonts
	$(PY) tools/check_tail_joins.py --root fonts
	$(PY) tools/check_italic_che.py --root fonts
	$(PY) tools/italic_tail_loop_proof.py
	$(PY) tools/check_contour_geometry.py
	$(PY) tools/contour_audit.py
	$(PY) tools/readme_header.py

quality:
	$(PY) tools/check_italic_el_alternate.py --formats ttf,woff2
	$(PY) tools/check_family.py
	$(PY) tools/check_curve_finish.py
	$(PY) tools/check_ya_revision.py
	$(PY) tools/check_ghe_width.py
	$(PY) tools/check_tail_joins.py --formats ttf,woff2
	$(PY) tools/check_italic_che.py --formats ttf,woff2
	$(PY) tools/quality_family.py

# Published files only: no outline changes, font rebuild or release packaging.
# A successful scan means complete parsing, not that the candidates are accepted.
contour-audit:
	$(PY) tools/check_contour_geometry.py
	$(PY) tools/contour_audit.py
	$(PY) tools/contour_audit_proof.py
	$(if $(filter 1,$(BROWSER)),node tools/check_contour_audit_browser.cjs,@:)

clean:
	rm -rf build
