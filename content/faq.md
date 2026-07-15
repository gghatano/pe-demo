# FAQ

回答はコードまたは論文から確認できたもののみを記す。未確認は「未確認」と明記する。

## Tab-PE は何を「進化」させているのか

合成データ集団（各ラベルごとの行の集合）を進化させている。各反復で最近傍
ヒストグラムのスコアに基づき選択し、`variation_api` で列を摂動 (mutation) して
次世代を生成する（`pe/api/tabular/tabular_api.py`, `pe/runner/pe.py`）。

## private data は各反復でどう参照されるか

各反復で、合成サンプルに対する非公開サンプルの最近傍ヒストグラムを計算する
（`NearestNeighbors.compute_histogram`）。この集計値にのみ Gaussian ノイズを加えて
DP を保証し、生の非公開行は合成側へ直接渡さない。

## DP budget は反復間でどう配分されるか

per-step の ε 分割ではなく、Gaussian mechanism の √合成
（`mu = sqrt(num_steps)/noise_multiplier`）で会計する。`noise_multiplier` は
`(epsilon, delta, num_steps)` から解析的に逆算される（`pe/dp/gaussian.py`）。
会計上の `num_steps` は `len(num_samples_schedule) - 1`。

## mutation とは何か

`variation_api` による列単位の摂動。categorical は確率 `mutation_rate` で再サンプル、
数値列は `±mutation_rate × range` の一様摂動＋クリップ。`mutation_rate` は反復とともに
0.5 → 0.01 へ多項式減衰する（`gamma=0.2`）。

## crossover とは何か

`CompositePopulation` による複数集団の組合せが該当し得るが、論文の crossover 概念
との厳密な対応は **未確認**。

## marginal-based method との違いは何か

Tab-PE は marginal を直接最適化するのではなく、最近傍ヒストグラム＋選択＋変異の
進化で marginal を含む分布を近づける。厳密な位置づけは論文本文の確認が必要（**未確認**）。

## なぜ XOR で差が出るのか

XOR は高次相関のストレステストで、低次 marginal だけでは表現できない相関の再現力を
測る意図と解釈される。ただし本フェーズでは XOR の分類器精度は `NOT_RUN` のため、
XOR 固有の差の定量化は行っていない（**未確認**）。

## checkpoint から再開すると privacy accounting はどうなるか

`checkpoint_path` から再開できるが、再開時に会計がどう扱われるか（追加消費の有無）は
コード上未検証で **未確認**。

## 「実行できた」と「再現した」は何が違うのか

`EXECUTED` は公式コードの実行に成功したこと。`REPRODUCED` は公式論文/README に
比較可能な数値があり合理的範囲で一致したこと。本フェーズは比較対象値を用いていない
ため、成功実験はすべて `EXECUTED` である。
