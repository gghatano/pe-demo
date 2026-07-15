# Experiment plan

This plan operationalizes `docs/spec.md`. The initial phase focuses on official Tab-PE reproduction only.

## Execution order

1. Investigate the official DPSDA implementation and pin the exact commit.
2. Define repository contracts for outputs, logs, summaries, and reports.
3. Build the uv environment from the official compatibility constraints.
4. Run one smoke test.
5. Run XOR official examples.
6. Run SCM demos.
7. Run real-data demos.
8. Aggregate summaries and figures.
9. Generate Markdown and HTML reports.
10. Perform final reproducibility review.

## Reproduction status

- `REPRODUCED`: Official paper or README has comparable numbers and the observed result matches within documented tolerance.
- `PARTIALLY_REPRODUCED`: Execution succeeds but only part of the official result is comparable or matching.
- `EXECUTED`: Official code executes, but no comparable official number exists.
- `FAILED`: Execution was attempted and failed.
- `NOT_RUN`: Execution was intentionally skipped, usually because of resource or dependency constraints.

## Result layout

```text
results/
├── raw/
├── synthetic/
├── checkpoints/
├── summaries/
├── logs/
└── figures/
```

Official outputs should be preserved under `results/raw/` when possible. Normalized experiment summaries belong under `results/summaries/`.

## Minimum experiment metadata

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

## Reporting rules

- Markdown under `content/` is the source of truth.
- HTML under `htmls/` is generated from Markdown.
- Report metrics should be read from CSV/JSON summaries where possible.
- Generated HTML should not be manually edited.
- Failed and skipped experiments must remain visible in the report.
