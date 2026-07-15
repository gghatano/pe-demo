# Task 002: Define reproducibility, result, and report contracts

## Source

- `docs/spec.md`, sections 2, 6, 8, 9, 10, 11, and 12

## Objective

Define the repository contracts that later experiment code, result aggregation, and reports must follow.

## Scope

- Create a reproducibility checklist.
- Define the canonical `results/` layout.
- Define experiment metadata fields.
- Define reproduction status semantics.
- Define report page inventory and page ownership.
- Define generated-vs-source file rules.
- Define `.gitignore` rules for caches, large outputs, environments, and generated artifacts.

## Deliverables

- `docs/plans/experiment-plan.md`
- `docs/reproduction-log.md`
- `.gitignore`
- Placeholder directories where useful, using `.gitkeep` only when the directory must exist before generation.

## Required metadata fields

- Experiment name.
- Official script path.
- Official commit SHA.
- Command.
- Python version.
- uv version.
- Dependency lock hash or `uv.lock` commit.
- OS.
- CPU.
- Memory when available.
- Random seed.
- Privacy parameters.
- Dataset name and source.
- Runtime.
- Output files.
- Reproduction status.
- Failure reason when applicable.

## Validation

- The contract distinguishes source reports from generated HTML.
- The contract allows failed and skipped experiments to be recorded.
- The result layout is compatible with official outputs without destructive rewrites.

## Out of scope

- Implementing the final HTML builder.
- Producing final figures.
- Recording metrics that have not been generated yet.
