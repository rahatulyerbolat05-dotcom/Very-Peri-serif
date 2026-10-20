# Very Peri Serif: build from the sources in data/ and tools/.
#   make            both styles, then fonts/ttf otf webfonts, docs/qa and the download in dist/
#   make regular    the Regular only (build/release, test copy in dist/test)
#   make quality    FontBakery (universal profile) on fonts/ttf, needs requirements-quality.txt
#   make clean      remove build/
# Requires Python 3.11+ with requirements.txt, and git for the Instrument Serif reference.

PY  := python3 -I
REF := reference/instrument-serif/fonts/ttf/InstrumentSerif-Regular.ttf

.PHONY: all release family italic regular reference quality clean

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
	$(PY) tools/italic_kern.py

family: italic
	$(PY) tools/build_family.py

release: family
	$(PY) tools/package_release.py

quality:
	mkdir -p build
	python3 -m fontbakery check-universal --skip-network --no-progress --no-colors \
	  --json build/fontbakery-universal.json fonts/ttf/VeryPeriSerif-Regular.ttf fonts/ttf/VeryPeriSerif-Italic.ttf

clean:
	rm -rf build
