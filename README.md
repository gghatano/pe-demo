# pe-demo — Tab-PE official demo reproduction

Reproduction追試 of the official Microsoft [DPSDA](https://github.com/microsoft/DPSDA)
**Tabular Private Evolution (Tab-PE)** demos.

The goal of the first phase is *reproduction of the official demos*, not new
methods or algorithmic changes. See [`docs/spec.md`](docs/spec.md) for the full
specification and [`docs/research/official-implementation.md`](docs/research/official-implementation.md)
for the pinned upstream commit and code inventory.

## Environment

Managed with [`uv`](https://docs.astral.sh/uv/). The environment pins the DPSDA
dependency at commit `9078c67995499e6769113780200bbf1d788d3d60`.

```bash
uv sync
```

## Documentation

- `docs/spec.md` — project specification.
- `docs/plans/experiment-plan.md` — execution order and contracts.
- `docs/research/official-implementation.md` — upstream code investigation.
- `docs/reproduction-log.md` — decisions and execution evidence.
- [`docs/findings.md`](docs/findings.md) — 横断的な知見と課題（未対応 Issue のまとめ）。
- `docs/tasks/` — task breakdown mapped to GitHub issues.
- [`docs/guides/new-dataset-checklist.md`](docs/guides/new-dataset-checklist.md) — 新規データへ Tab-PE を適用する際の適用可否チェックリストと標準タスクリスト。
