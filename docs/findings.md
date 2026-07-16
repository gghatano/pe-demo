# 知見と課題

このプロジェクトで得た知見と、残っている課題をテーマ別にまとめる。時系列の記録は
`docs/reproduction-log.md`、環境の詳細は `content/engineering-notes.md`、公式コードの
調査は `docs/research/official-implementation.md` にある。ここはそれらを横断して
「後から効く要点」だけを拾う。

## 知見

### 環境・ツールの落とし穴

- **公式デモスクリプトはインストールされない。** `pyproject.toml` の
  `packages.find` が `example*` を除外するため、`pe` を入れてもデモは実行できない。
  固定 SHA `9078c67` でリポジトリを checkout して回す必要がある。
- **`from pe.api import TabularAPI` が `azure` を要求する。** この import が text/LLM 経路
  (`pe.llm.azure_openai` → `azure.identity`) を eager import する。`pe/__init__.py` は
  `openai` 等を `generalimport` で optional 化するが `azure` を含まない。`[tabular]` だけでは
  失敗するので `azure-identity` を足した。未使用経路を満たすだけで、Tab-PE・DP・評価には無影響。
- **`tabpfn` はライセンスゲートで止まる。** 重みダウンロードに対話的なライセンス受諾＋
  `TABPFN_TOKEN`（外部アカウント登録）が要る。XOR デモだけがこれを分類器に固定する。
  他の 5 デモが使う `tabicl` は HuggingFace Hub からゲートなしで取得でき、CPU で動く。
  DPSDA を非対話環境で回すなら、分類器は `tabicl`/`xgboost` を前提にした方がよい。
- **Windows で公式 `CSVPrint` の per-iteration CSV が空になる。** 指標名にフィルタ辞書由来の
  `:` が入り、Windows のファイル名に使えず 0 バイトになる。反復系列は `log.txt` を
  パースして `results/summaries/iterations/*.csv` に抽出した。
- Python は DPSDA が `>=3.9`。tabpfn/tabicl/torch/POT 込みで **3.12.13** で通った。

### アルゴリズム・DP

- **DP 会計の反復数は「設定値 − 1」。** `PE.run` は `len(num_samples_schedule) - 1` を
  `num_steps` に渡す。公式デモの schedule 長は `num_iterations` なので、会計上は
  `num_iterations - 1`（例: XOR 20→19、SCM 15→14、Adult 30→29）。
- **保護対象は最近傍ヒストグラム。** Gaussian ノイズをそのヒストグラムに加える。合成は
  `mu = sqrt(num_steps)/noise_multiplier` の √合成（Gaussian-DP 系）で、per-step の ε 分割ではない。
- **PE 生成はシードされず非決定的。** WSD のサンプリングだけ `seed=42`。だから各実験は
  単一 run の値であり、run 間の揺れは測っていない（→ #22）。

### 結果から見えたこと

- **SCM は prior で下流精度が大きく変わる。** 同じ Tab-PE 設定・同じ `epsilon=1.0` でも
  `nn`(85.48%) > `tree`(66.68%) > `rff`(61.08%)。一方 5/6/7-way の marginal 距離は 3 prior で
  ほぼ同水準（差 0.01 未満）。距離が近くても下流 utility は元データの生成過程に強く依存する。
- **XOR は次数が上がると再現が難しくなる。** 特徴数 1→3 で分類精度が 99.80% → 96.85% と低下。
  AUC は 99.67 以上を維持。Tab-PE は高次相関を扱えているが、次数が上がるほどわずかに苦しくなる
  （分類器は tabpfn の代替として tabicl を使用）。
- **不均衡データでは accuracy と macro F1 が乖離する。** Adult は acc 80.94% に対し macro F1 70.78、
  Person Activity は acc 64.04% に対し macro F1 36.52。accuracy だけで再現度を語らない。
- **`EXECUTED` と `REPRODUCED` は別物。** 本フェーズは公式公表値と比較していないので、成功実験は
  すべて `EXECUTED`。「動いた」ことを「論文を再現した」と言い換えない（→ #20）。

### 再現性・レポート基盤

- **上流コードは固定できたが、入力データが固定できていない。** DPSDA は SHA を固定したが、
  データは第三者リポジトリ `toan-vt/cloud-data-store@main`（未固定参照）から取得している。
  厳密な再現にはデータ側の SHA か SHA-256 の固定・記録が要る（→ #19）。
- **レポートは追跡済みサマリから再生成できる。** 実験を再実行しなくても
  `collect_results.py` → `make_figures.py` → `build_site.py` で HTML を作れる。Actions は
  軽量依存（torch なし）でこの 3 段を回して Pages に公開する。
- **レポート生成キットは再利用した。** HTML ビルダー・Pages ワークフロー・執筆 skill は
  `gghatano/synth-report-kit`（MIT）から取り込んだ（`ark/`、`.claude/skills/`）。

## 課題（未対応・追跡中）

| 課題 | 対応 Issue | メモ |
|---|---|---|
| 乱数 seed を制御し複数試行で mean±std を出す | #22 | PE 非決定性への対応。#24 本実験の前提 |
| Adult 埋め込みの本実験（3 variant × ≥3 seed） | #24 | 実装・テストは完了。実行は #22 待ち |
| 公式公表値と対応付けて `REPRODUCED` 判定 | #20 | 論文・README の比較可能な数値を要調査 |
| 公開集計値を元ログ・合成 CSV まで追跡・監査 | #19 | provenance。入力データ SHA の固定もここで扱う |
| XOR を公式 `tabpfn` で verbatim 実行 | (#21 は tabicl 代替で達成済み) | `TABPFN_TOKEN` 待ち |
| 入力データ（cloud-data-store）の SHA/ハッシュ固定 | #19 関連 | 現状 `main` 参照で未固定。再現性の穴 |

## 非スコープ（本フェーズでは扱わない）

`docs/spec.md` §15 のとおり、AIM/MST/PrivBayes/SDV との比較、ε・サンプル数・次元数の sweep、
Tab-PE アルゴリズム改良は Phase 2 とする。新規データ適用は
`docs/guides/new-dataset-checklist.md` の手順に従う。
