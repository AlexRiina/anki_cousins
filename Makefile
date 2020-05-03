.PHONY: clean dist test build build_test

dist:
	python setup.py sdist --format=zip

clean:
	rm -r build
	rm -r dist
	pyclean .

build:
	pip install .

build_test:
	pip install .[test]

test:
	black --check .
	flake8 --select=F,E .
	mypy main.py
