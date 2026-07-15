# Task 003: Build the uv-managed Python environment

## Source

- `docs/spec.md`, sections 4 and 12
- Depends on `task-001`

## Objective

Create a reproducible Python environment for official Tab-PE demos.

## Scope

- Decide Python version from official package metadata and observed compatibility.
- Create `pyproject.toml`.
- Pin dependencies in `uv.lock`.
- Prefer `private-evolution[tabular]` unless official reproduction requires a pinned DPSDA Git dependency.
- Document any Python 3.12 incompatibility and selected fallback version.
- Verify `uv sync` reconstructs the environment.

## Deliverables

- `pyproject.toml`
- `uv.lock`
- Updated `docs/reproduction-log.md`
- Updated `content/engineering-notes.md` once report pages exist

## Validation

- `uv sync` succeeds on a clean checkout.
- `uv run python --version` reports the expected version.
- `uv run python -c "import private_evolution"` or the official equivalent succeeds.
- The installed official implementation version or commit SHA is recorded.

## Out of scope

- Running large experiments.
- Applying unofficial patches to the Tab-PE algorithm.
