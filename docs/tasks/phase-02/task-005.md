# Task 005: Run the first smoke test

## Source

- `docs/spec.md`, section 5 Phase 1 and section 12 Step 4
- Depends on `task-003` and `task-004`

## Objective

Run the smallest official Tab-PE demo that can validate installation, data access, execution, output writing, and metric extraction.

## Scope

- Select the shortest official tabular demo based on `task-001` findings.
- Run only one smoke experiment first.
- Confirm data download or data generation.
- Confirm checkpoint behavior when available.
- Confirm synthetic CSV or equivalent synthetic output.
- Confirm official metric output.
- Record runtime and environment metadata.

## Deliverables

- `results/raw/<smoke-experiment>/`
- `results/synthetic/` output where applicable
- `results/checkpoints/` output where applicable
- `results/summaries/experiments.csv`
- `results/summaries/experiments.json`
- Updated `docs/reproduction-log.md`

## Validation

- The smoke run exits successfully or is recorded as `FAILED` with logs.
- No XOR, SCM, or real-data batch run starts until the smoke result is understood.
- Reported metrics can be traced to official output.

## Out of scope

- Claiming paper-level reproduction from a smoke run alone.
- Running all demos in one batch.
