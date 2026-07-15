# Tab-PE reproduction task index

This directory breaks down `docs/spec.md` into executable tasks.

## Phase 01: Research and design

- `phase-01/task-001.md`: Investigate the official DPSDA Tab-PE implementation.
- `phase-01/task-002.md`: Define reproducibility, result, and report contracts.

## Phase 02: Environment and smoke execution

- `phase-02/task-003.md`: Build the uv-managed Python environment.
- `phase-02/task-004.md`: Implement experiment wrappers and logging conventions.
- `phase-02/task-005.md`: Run the first smoke test.

## Phase 03: Official demo reproduction

- `phase-03/task-006.md`: Reproduce the XOR stress test.
- `phase-03/task-007.md`: Reproduce SCM and real-data official demos.

## Phase 04: Reporting and final review

- `phase-04/task-008.md`: Aggregate results and generate figures.
- `phase-04/task-009.md`: Build Markdown and HTML reports.
- `phase-04/task-010.md`: Perform final reproducibility review.

## Global rules

- Do not implement algorithmic changes during the initial reproduction phase.
- Treat `content/*.md` as the report source of truth.
- Generate HTML from Markdown; do not edit generated HTML directly.
- Separate `REPRODUCED`, `PARTIALLY_REPRODUCED`, `EXECUTED`, `FAILED`, and `NOT_RUN`.
- Record commands, environment details, commit SHAs, seeds, runtimes, and failures.

## GitHub issue map

- Parent orchestration issue: #1
- Official implementation research: #3
- uv environment and Smoke Test: #2
- XOR official reproduction: #5
- SCM and real-data official demos: #4
- Aggregation, Markdown, HTML, and final review: #6

The parent issue (#1) is the source for priority, dependencies, and sub-agent delegation order.
