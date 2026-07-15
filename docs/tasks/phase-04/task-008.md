# Task 008: Aggregate results and generate figures

## Source

- `docs/spec.md`, sections 6, 7, 8, 9.5, and 12 Steps 8 and 9
- Depends on `task-005`; should be updated after `task-006` and `task-007`

## Objective

Create machine-readable summaries and figures that reports can consume without hand-copying metrics.

## Scope

- Implement result collection from official outputs and wrapper metadata.
- Produce `results/summaries/experiments.csv`.
- Produce `results/summaries/experiments.json`.
- Generate figures under `results/figures/`.
- Keep aggregation tolerant of `FAILED` and `NOT_RUN` experiments.
- Preserve enough provenance to trace report numbers back to raw logs.

## Deliverables

- `scripts/collect_results.py`
- `scripts/make_figures.py`
- `results/summaries/experiments.csv`
- `results/summaries/experiments.json`
- `results/figures/`

## Validation

- Aggregation is deterministic.
- JSON and CSV contain the same experiment rows.
- Figures are regenerated from summaries, not manually edited.
- Missing metrics are represented explicitly, not guessed.

## Out of scope

- Manually entering metric values into Markdown.
- Generating figures from unverified assumptions.
