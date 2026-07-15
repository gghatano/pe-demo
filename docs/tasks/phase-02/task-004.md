# Task 004: Implement experiment wrappers and logging conventions

## Source

- `docs/spec.md`, sections 2, 6, 7, and 12
- Depends on `task-001` and `task-002`

## Objective

Provide thin wrappers around official demo scripts so runs are reproducible, logged, and summarized without changing official behavior.

## Scope

- Implement wrapper scripts under `scripts/`.
- Record command, environment, seed, runtime, exit code, stdout, and stderr.
- Preserve official output structure under `results/raw/` where required.
- Store normalized summaries under `results/summaries/`.
- Make wrapper behavior explicit and minimal.
- Add guardrails that prevent running non-smoke large experiments accidentally when a dry-run or explicit flag is expected.

## Deliverables

- `scripts/run_smoke.py`
- `scripts/run_xor.py`
- `scripts/run_scm.py`
- `scripts/run_real_datasets.py`
- `docs/reproduction-log.md` updates

## Validation

- Wrapper dry-runs print the exact underlying official command.
- Logs are written to `results/logs/`.
- Failures produce structured metadata rather than disappearing.
- Wrapper code does not modify official algorithm internals.

## Out of scope

- Aggregating final figures.
- HTML report generation.
