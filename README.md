# Canvas Tools

Small CLI utilities for querying Canvas (courses, assignments, students, submissions).

## Quick Install

- From source (development):

```bash
python -m pip install --upgrade build setuptools wheel
python -m build
pip install dist/*.whl
```

### Using a virtual environment

It's recommended to use an isolated virtual environment for development and testing.

- Create and activate (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- Create and activate (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

- Then install dependencies and the package inside the venv:

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade build setuptools wheel
python -m build
pip install dist/*.whl
```

## Usage

Run the bundled CLI module or the installed console script.

- Module:

```bash
python -m canvas_tools.cli -c        # list active courses
python -m canvas_tools.cli -a <course_id>   # list assignments for course
python -m canvas_tools.cli -u <course_id>   # list users in course
python -m canvas_tools.cli -s <course_id> <assignment_id>  # list submissions
```

- Console script (after install):

```bash
canvas-tools -c
```

## Packaging & Publishing

- Build distributions:

```bash
python -m pip install --upgrade build twine setuptools wheel
python -m build
```

- Upload to TestPyPI for validation:

```bash
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

- When ready, upload to PyPI:

```bash
python -m twine upload dist/*
```

## Development notes

- Runtime dependencies are declared in `pyproject.toml` (`requests`, `python-dotenv`).
- The package exposes a console script entry point `canvas-tools` defined in `pyproject.toml`.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE).
