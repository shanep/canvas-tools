# Edu Tools

Small CLI utilities for querying Canvas (courses, assignments, students, submissions) and a helper to create/share Google Docs via a service account.

## Quickstart

- Create and configure environment variables in a `.env` file (see `.env.example`):
- Use the provided Makefile to set up a virtual environment, install dependencies, and the package itself.

```bash
make config
```

- Setup your terminal to use the virtual environment:

```bash
source .venv/bin/activate
```

## Usage

Run the bundled CLI module or the installed console script.

- Module:

```bash
cd src
python -m edu_tools.cli -h
```

- Console script (after install):

```bash
canvas-tools -h
```

## Development notes

- Runtime dependencies are declared in `pyproject.toml` (`requests`, `python-dotenv`, Google API clients).
- The package exposes a console script entry point `canvas-tools` defined in `pyproject.toml`.

## Project Structure

- `src/`: Contains the source code for the project.
- `tests/`: Contains the test files for the project.