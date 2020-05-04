.PHONY: clean test build build_test

plugin.zip:
	zip plugin.zip -j -r src

clean:
	rm -r build dist **/*.egg-info plugin.zip || true
	pyclean .

build:
	pip install .

build_test:
	pip install .[test]

test:
	black --check .
	flake8 src
	mypy src
