# Reproduction log

This log records decisions and execution evidence for the Tab-PE official demo reproduction.

## 2026-07-15: Development preparation

- Created task breakdown under `docs/tasks/` from `docs/spec.md`.
- Defined the initial experiment plan in `docs/plans/experiment-plan.md`.
- Created GitHub orchestration issue #1 and child issues #2 through #6.
- No official DPSDA code has been downloaded or executed yet.
- No Python dependencies have been installed yet.

## GitHub issue map

- #1: Orchestrator priority and dependency map.
- #3: Official DPSDA Tab-PE implementation research.
- #2: uv environment and Smoke Test.
- #5: XOR official reproduction.
- #4: SCM and real-data official demos.
- #6: Aggregation, Markdown, HTML, and final review.

## 2026-07-15: Official implementation research (#3)

- Investigated `microsoft/DPSDA` and pinned commit SHA
  `9078c67995499e6769113780200bbf1d788d3d60` (2026-07-01).
- Findings written to `docs/research/official-implementation.md`.
- Tab-PE demo scripts live in `example/tabular/` and are excluded from the
  installed package, so a repo checkout at the pinned SHA is required to run them.
- `pyproject.toml` declares `requires-python = ">=3.9"`; tabular extras are
  `tabicl`, `tabpfn`, `xgboost`, `numpy`, `POT`.
- All demos use `epsilon=1.0`, `delta = 1/n/ln(n)`, Gaussian mechanism on a
  nearest-neighbor histogram, with √-composition accounting.
- No experiments have been run yet.

## Pending decisions

- ~~Official DPSDA commit SHA.~~ Resolved: `9078c67995499e6769113780200bbf1d788d3d60`.
- Python version after checking official compatibility (blocked on `tabpfn`/`tabicl`
  platform support — see research doc §8; DPSDA itself allows `>=3.9`).
- Package source: released `private-evolution[tabular]` vs pinned Git dependency
  (research recommends the pinned Git SHA; scripts require a repo checkout anyway).
- First smoke-test script (candidate: `xor_stress_test.py --num-features 1`).

## Execution records

No experiments have been run yet.
