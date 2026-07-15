# 詳細結果

数値はすべて `results/summaries/`（`experiments.csv` と
`iterations/*.csv`）から生成しており、手入力していない。

## 実験別サマリ

<!-- INCLUDE:experiments_table -->

## 反復に伴う精度の推移

synthetic-train → real-test の分類器精度は、PE の反復とともに上昇する。Breast
Cancer は約 52% から **91.86%** まで改善し、進化が有効に機能している。SCM(rff) と
Artificial Characters は高次 marginal の難しい設定で、それぞれ約 **61%**・**52%**
で頭打ちとなる。

<!-- INCLUDE:figure:accuracy_vs_iteration -->

## 反復に伴う marginal 距離の推移

k-way Wasserstein marginal 距離は、次数が上がるほど大きくなる（高次相関ほど
一致が難しい）。反復を通じて概ね横ばい〜微減で推移する。

<!-- INCLUDE:figure:wsd_vs_iteration -->

## 最終反復の指標

| 実験 | test acc (%) | macro F1 | AUC | 1/2/3-way WSD | 5/6/7-way WSD |
|---|---|---|---|---|---|
| Breast Cancer | 91.86 | 91.44 | 98.73 | 0.1644 / 0.2767 / 0.3749 | — |
| SCM (rff) | 61.08 | 61.03 | 64.14 | — | 0.1460 / 0.1860 / 0.2243 |
| Artificial Characters | 51.60 | 50.92 | —(多クラス) | — | 0.1519 / 0.1862 / 0.2175 |
| XOR (1/2 feature) | NOT_RUN | — | — | — | —(WSD なし) |

## DP 会計（ログ実測値）

| 実験 | epsilon | delta | noise_multiplier | 会計上の num_iterations |
|---|---|---|---|---|
| Breast Cancer | 1.0 | 4.1971e-4 | 12.266 | 19 |
| SCM (rff) | 1.0 | 2.7307e-6 | 15.021 | 14 |
| Artificial Characters | 1.0 | 1.5754e-5 | 13.573 | 14 |
| XOR (1 feature) | 1.0 | 2.7307e-6 | 17.499 | 19 |

> 図はビルド時に `results/figures/*.png` を base64 で埋め込んでいる。図は
> `results/summaries/iterations/*.csv`（追跡対象）から `make_figures.py` で
> 再生成でき、公式ログに存在しない値は推測生成していない。
