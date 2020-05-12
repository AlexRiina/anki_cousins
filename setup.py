from setuptools import setup, find_packages


setup(
    name="anki_cousins",
    version="0.1",
    tests_require=["PyQt5-stubs" "anki", "black", "flake8", "isort", "mypy"],
    packages=find_packages("src"),
    package_dir={"": "src"},
)
