from setuptools import setup, find_packages


setup(
    name="anki_cousins",
    version="0.1",
    tests_requirements=["anki", "isort", "mypy", "black", "flake8"],
    packages=find_packages("src"),
    package_dir={"": "src"},
)
