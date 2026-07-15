# Task 007: Reproduce SCM and real-data official demos

## Source

- `docs/spec.md`, section 5 Phases 3 and 4 and section 12 Steps 6 and 7
- Depends on `task-006`

## Objective

Run the official SCM and real-data demos after smoke and XOR execution are stable.

## Scope

- Run SCM first with `python scm.py --prior-function rff`.
- If feasible, run `tree`, `nn`, and `rff` prior functions.
- Run real-data demos in this priority order unless preflight cost analysis changes it:
- Breast Cancer.
- Adult.
- Artificial Characters.
- Person Activity.
- Before each real-data run, record row count, column count, categorical/numerical columns, target, train/test split, and data source.
- Record accuracy, marginal distance, privacy parameters, runtime, and failures.

## Deliverables

- `results/raw/scm/`
- `results/raw/breast_cancer/`
- `results/raw/adult/`
- `results/raw/artificial_characters/`
- `results/raw/person_activity/`
- Updated `results/summaries/experiments.csv`
- Updated `results/summaries/experiments.json`
- Updated `content/data-notes.md`
- Updated `content/experiments.md`
- Updated `content/results-detail.md`

## Validation

- Each dataset has pre-run metadata.
- Each prior function or dataset has an explicit reproduction status.
- Any order change is justified in `docs/reproduction-log.md`.

## Out of scope

- Adding non-official datasets.
- Comparing against AIM, MST, PrivBayes, or SDV.
