.PHONY: clean dist

dist:
	python setup.py sdist --format=zip

clean:
	rm -r dist	
