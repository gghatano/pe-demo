# エンジニアリングノート

第三者がこのページだけで環境を再構築できることを目指す。

## 環境

| 項目 | 値 |
|---|---|
| OS | Windows 11 Pro (10.0.26200) |
| CPU | AMD Ryzen 5 7640HS (6C/12T) |
| RAM | 25.8 GB |
| Python | 3.12.13（uv 管理） |
| uv | 0.11.26 |
| DPSDA commit | `9078c67995499e6769113780200bbf1d788d3d60`（2026-07-01） |
| パッケージ | `private-evolution` 0.0.1（当該 SHA の Git 依存） |

## 環境再構築

```bash
uv sync            # 依存を uv.lock から再現（--frozen でも可）
uv run python -c "from pe.api import TabularAPI"   # import 確認
```

公式デモスクリプトはインストール対象パッケージに含まれない（`pyproject.toml` の
`packages.find` で `example*` を除外）。そのため DPSDA を同一 SHA で
`external/DPSDA` にチェックアウトして実行する（`external/` は gitignore）。

```bash
git clone --filter=blob:none https://github.com/microsoft/DPSDA.git external/DPSDA
git -C external/DPSDA checkout 9078c67995499e6769113780200bbf1d788d3d60
```

## パッケージ / 実行方法

- 実験ラッパー: `scripts/run_experiment.py`（無改変の公式スクリプトを実行し、
  メタデータ・実行時間・成果物・最終指標を記録）。Smoke 用は `scripts/run_smoke.py`。
- 集計: `scripts/collect_results.py` → `results/summaries/experiments.{csv,json}` と
  `results/summaries/iterations/*.csv`。
- 図: `scripts/make_figures.py` → `results/figures/*.png`。
- HTML: `scripts/build_site.py` → `htmls/*.html`（Markdown から生成、直接編集禁止）。
  ビルダー本体 `ark/` は [gghatano/synth-report-kit](https://github.com/gghatano/synth-report-kit)（MIT）を取り込んだもの。
- Pages 公開: `.github/workflows/deploy-pages.yml`（GitHub Actions）。`main` への push で
  Markdown から HTML を生成し Pages へデプロイする。事前に Settings → Pages → Source を
  「GitHub Actions」に設定する必要がある。

## Windows / 環境依存の問題と対処

以下は公式アルゴリズム・プライバシー・評価には影響しない最小限の対処である。

1. **`azure` の import 失敗**: `from pe.api import TabularAPI` が text/LLM 経路
   (`pe.llm.azure_openai` → `azure.identity`) を eager import する。`pe/__init__.py`
   は `openai`/`transformers` 等を `generalimport` で optional 化するが `azure` を
   含まない。`[tabular]` のみでは失敗するため **`azure-identity` を追加**した
   （公式 `[text]`/`[image]` extras にも含まれる依存）。未使用の Azure-OpenAI 経路を
   満たすのみで、Tab-PE・DP・評価には無影響。

2. **`tabpfn` のライセンスゲート**: XOR デモは `tabpfn` を分類器に固定するが、
   `tabpfn` は重みダウンロードに対話的なライセンス受諾 + `TABPFN_TOKEN` を要求する。
   非対話環境では取得できないため、XOR の分類器精度は `NOT_RUN` とし、生成のみを
   分類器コールバックを外した deviation スクリプトで実行した。他 5 デモが使う
   `tabicl` は HuggingFace Hub から重みを取得し、ライセンスゲートなしで CPU 実行可能。

3. **`CSVPrint` の per-iteration CSV が空**: 公式 `CSVPrint` は指標名でファイルを作る
   が、表形式指標名にフィルタ辞書由来の `:` が含まれ、Windows のファイル名に使えない
   ため 0 バイトになる。per-iteration の時系列は代わりに `log.txt` を解析して
   `results/summaries/iterations/*.csv` に抽出した。

4. **`ot` の SyntaxWarning**: `pe` 依存の `POT` が docstring 中の `\d` で警告を出すが
   実行に影響なし。

## データダウンロード / seed / checkpoint

- データは `toan-vt/cloud-data-store@main` から取得（未固定参照。§データ参照）。
- PE 生成自体はシードされず**非決定的**。WSD のサンプリングのみ `seed=42`。
- 各反復で `checkpoint/` にチェックポイントを保存し、`checkpoint_path` から再開可能。
  再開時の privacy accounting の扱いは **UNCONFIRMED**。

## 結果の監査（元ログへの追跡、#19）

公開している数値は `results/summaries/*.json` と、そこから集計した `experiments.json` に由来する。
一方、根拠となる元ログ・合成 CSV・checkpoint は容量のため `.gitignore` 対象（`results/raw/`,
`results/logs/`, `results/synthetic/`, `results/checkpoints/`, `results/figures/`）で、clean clone
直後には存在しない。この追跡性を `scripts/audit_results.py` で担保する。

```bash
uv run python scripts/audit_results.py            # 監査マニフェストを生成
uv run python scripts/audit_results.py --verify   # 完全性を検査（不一致で非ゼロ終了）
```

- 生成すると `results/summaries/audit_manifest.json`（追跡対象）に、各サマリごとの元ログパス・
  サイズ・**SHA-256**・生成コマンド・再現判定・指標照合結果を記録する。
- 指標照合：ログを `parse_final_metrics` で再解析し、サマリの `final_metrics`（新ランナー）または
  `experiments.json` の公開行（console ログ実行の Adult/Breast Cancer 等）と一致するか検査する。
  現状 **47/47 が一致**（Adult・Breast Cancer・SCM 3 prior・Person Activity を含む）。
- `--verify` はローカルにログがある前提で、SHA-256 と指標の不一致を検出する（CI では `results/raw`
  が無いため未実行）。ログが欠落しているエントリは、マニフェストの `command` を再実行して再生成する。
  ログはタイムスタンプを含むためバイト一致はしない：第三者検証は「コマンド再実行 → 解析指標の突合」
  で行い、SHA-256 は当方が保存したログの完全性を固定する用途である。
- 非 Git 管理の成果物（大容量）の理由・保存場所・再生成手順は上記のとおり。合成 CSV・checkpoint は
  各サマリの `command`（seed 付き）で再生成できる。
