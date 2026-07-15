# Task 006: Reproduce the XOR stress test

## Source

- `docs/spec.md`, section 5 Phase 2 and section 12 Step 5
- Depends on `task-005`

## Objective

Reproduce the official XOR stress-test examples in the order recommended by the specification.

## Scope

- Run official README examples first:
- `python xor_stress_test.py --num-features 1`
- `python xor_stress_test.py --num-features 2`
- If resource use is acceptable, extend gradually through `num-features = 1..7`.
- Record privacy parameters, population size, iterations, seed, classifier accuracy, marginal distance, and runtime.
- Explain the high-order correlation role of XOR using code and paper references.

## Deliverables

- `results/raw/xor/`
- `results/summaries/experiments.csv`
- `results/summaries/experiments.json`
- Updated `content/experiments.md`
- Updated `content/results-detail.md`
- Updated `content/method-tabpe.md` if XOR clarifies method behavior

## Validation

- Each feature count has a separate command, log, metadata row, and status.
- A run is marked `REPRODUCED` only if official comparable numbers exist and match within a documented tolerance.
- Resource-related skips are marked `NOT_RUN`, not silently omitted.

## Out of scope

- Designing new XOR conditions.
- Running epsilon, sample-size, or dimension sweeps outside official reproduction scope.
