# Task 001: Investigate official DPSDA Tab-PE implementation

## Source

- `docs/spec.md`, sections 2, 3, 4, 5, 7, and 12

## Objective

Identify how the official Microsoft DPSDA repository implements and exposes Tabular Private Evolution, before writing experiment code or running large demos.

## Scope

- Inspect `microsoft/DPSDA` at a fixed commit SHA.
- Locate Tab-PE related package code.
- Locate `example/tabular/` scripts and their CLI options.
- Identify supported Python versions and installation method.
- Identify default parameters, random seed handling, output paths, checkpoints, and evaluation metrics.
- Map the official code paths to the paper concepts where possible.
- Separate confirmed code facts from interpretation.

## Deliverables

- `docs/research/official-implementation.md`

The document must include:

- Repository URL and fixed commit SHA.
- Relevant source file paths.
- Installation decision: package release vs pinned Git dependency.
- Script inventory for XOR, SCM, Adult, Breast Cancer, Artificial Characters, and Person Activity.
- Input data sources and download behavior.
- Output files and directories.
- Metrics emitted by official code.
- Privacy parameters and accounting entry points.
- Open questions and unresolved risks.

## Validation

- Every implementation claim cites a source path or command output.
- No experiment wrapper is implemented before the script inventory is complete.
- Any uncertainty is explicitly marked as `UNCONFIRMED`.

## Out of scope

- Running full experiments.
- Comparing against non-official baselines.
- Modifying official algorithms.
