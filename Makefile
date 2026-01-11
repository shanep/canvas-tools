.PHONY: clean distclean build

clean:
	rm -rf dist build *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

distclean: clean
	rm -rf .venv .venv_test .pytest_cache .mypy_cache .cache

build:
	python -m pip install --upgrade build setuptools wheel
	python -m build
