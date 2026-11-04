# Tasks. Install just once: winget install Casey.Just
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    @just --list

# Style checks. Changes nothing.
lint:
    uv run ruff check .
    uv run ruff format --check .

# Tests. Anything marked slow is left out: uv run pytest -m slow
test:
    uv run pytest

# Build the wheel and the source archive into dist/.
build:
    uv build

# Everything the pull request checks run, plus the build.
typecheck:
    uv run mypy src/siftgrain_state

schemas:
    uv run python scripts/validate_schemas.py

check: lint test typecheck schemas build

# Apply the automatic fixes.
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Fetch pinned public source, inject faults and package local archives.
bench:
    uv run python benchmarks/run.py --fetch

viewer:
    uv run python scripts/build_demo.py
    uv run python scripts/build_state_demo.py
    npm test
