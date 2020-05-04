.PHONY: clean dist test build build_test

dist:
	python setup.py sdist --format=zip

clean:
	rm -r build dist || true
	pyclean .

build:
	pip install .

build_test:
	pip install .[test]

test:
	black --check .
	flake8 --select=F,E *.py
	mypy main.py interface.py
