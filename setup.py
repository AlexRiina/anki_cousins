from setuptools import setup


setup(
    name="anki_cousins",
    py_modules=["main", "__init__"],
    version="0.1",
    tests_requirements=["anki", "isort", "mypy", "black", "flake8"],
)
