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

family: $(REF)
	$(PY) tools/author_em.py

# 1.117 is a reproducible delta from the SHA-pinned immutable 1.116 archive.
# Only the author SVG for italic em and its derived LSB change.
release: family
	$(PY) tools/check_author_em.py
	$(PY) tools/check_family.py
	$(PY) tools/quality_family.py
	$(PY) tools/family_proof.py
	$(PY) tools/author_em_proof.py
	$(PY) tools/optical_review.py
	$(PY) tools/package_release.py $(if $(filter 1,$(BROWSER)),--browser,)
	$(PY) tools/package_renamed_copy.py
	$(PY) tools/check_author_em.py --root fonts --report docs/qa/author-em-final.json
	$(PY) tools/readme_header.py

quality:
	$(PY) tools/check_author_em.py
	$(PY) tools/check_family.py
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
