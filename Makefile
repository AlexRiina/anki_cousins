.PHONY: clean test build build_test

plugin.zip:
	python setup.py sdist --format zip
	unzip -j $$(ls -t dist/*.zip | head -1) '*/src/*' -d dist/plugin
	zip plugin.zip -j -r dist/plugin
	# Test to confirm some files look right
	unzip -l plugin.zip '__init__.py'
	unzip -l plugin.zip 'main.py'

clean:
	rm -r build dist **/*.egg-info plugin.zip || true
	pyclean .

build:
	pip install .

build_test:
	pip install .[test]

test:
	flake8 src
	mypy src
	python -m doctest src/settings.py
	black --check .
