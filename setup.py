from setuptools import find_packages, setup

setup(
    name="anki_cousins",
    version="0.6.1",  # update in manifest too
    tests_require=["PyQt5-stubs" "anki", "black", "flake8", "isort", "mypy"],
    packages=["src"],
)
