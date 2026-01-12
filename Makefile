PY=python3
.PHONY: clean distclean build config test run

config:
	$(PY) -m venv .venv
	.venv/bin/pip install --upgrade pip setuptools wheel build
	.venv/bin/pip install -e .

clean:
	rm -rf dist build *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete

distclean: clean
	rm -rf .venv .venv_test .pytest_cache .mypy_cache .cache

build:
	$(PY) -m pip install --upgrade build setuptools wheel
	$(PY) -m build

test:
	$(PY) -m unittest discover -s tests -p "test_*.py"

run:
	$(PY) -m edu_tools.cli