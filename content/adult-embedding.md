# Adult 埋め込みの精緻化（追加実験）

公式 Adult デモは既定の `TabularEmbedding`（数値は metadata の min-max、カテゴリは
one-hot、距離は L2）を使う。Adult 固有の性質——`capital-gain/loss` のゼロ集中、
`fnlwgt` が標本重みであること、`education` と `education-num` の重複——を距離へ反映すると
下流 utility や統計的 fidelity が改善するかを追加実験した。

> これは**公式再現条件の変更**である。公式 `adult`（`EXECUTED`）結果は置換せず、
> `adult_embedding_*` として独立に記録した。判定はすべて `EXECUTED`。設計と公開定数
> （domain bounds、`education→education-num` 対応表）は
> [`docs/research/adult-embedding.md`](https://github.com/gghatano/pe-demo/blob/main/docs/research/adult-embedding.md) 参照。

## 3 variant

- `official`: 公式 `TabularEmbedding` と数値一致（ベースライン）。
- `robust_numeric`: `fnlwgt` を log 化（重み 0.25）、`capital-gain/loss` を「ゼロか否か」＋
  「正値の log 量」に分解。数値変換の値域は**公開 domain bounds を固定使用**（秘密データから
  学習しない）。カテゴリ・`age`・`education-num`・`hours-per-week` は公式と同じ。
- `adult_semantic`: `robust_numeric` に加え、`education` の one-hot をやめ `education-num` を
  主表現とし、`education`/`education-num` の不整合に penalty 次元を追加。

生成・DP・population・分類器（`tabicl`）・WSD の定義は公式 `adult` と同一。変えたのは
埋め込みだけ。各 variant を seed `0,1,2` の **3 試行**（#22 の seed 制御）で実行した。

## Utility（下流分類）

平均±標準偏差（`results/summaries/adult_embedding_seed_aggregate.csv`）:

| variant | test acc (%) | macro F1 | AUC |
|---|---|---|---|
| official | 79.89 ± 0.58 | 70.58 ± 1.18 | 83.33 ± 0.86 |
| robust_numeric | 81.01 ± 1.30 | 71.19 ± 0.54 | 84.61 ± 1.34 |
| adult_semantic | 77.78 ± 1.84 | 62.58 ± 9.33 | 80.90 ± 2.84 |

![variant 別の精度 mean±std（seed 3 試行）](results/figures/adult_embedding_seed_stability.png)

*図 5: Adult 埋め込み variant 別の分類精度 mean±std（seed 0,1,2）。*

`official`(79.89%) と `robust_numeric`(81.01%) の差は約 1.1 点で、標準偏差（0.58〜1.30）と
同程度であり、**有意な改善とは言えない**。`adult_semantic` は精度が下がり（77.78%）、
macro F1 が **62.58 ± 9.33** と大きくばらつく（seed 1 で 49.44 まで崩壊）。→ 気を利かせた
埋め込みでも、下流 utility は**安定して改善しない**。

## Fidelity・意味的一貫性

最終合成 CSV に対する追加評価（低いほど良い。公式 TabICL 評価とは分離）:

| variant | capital-gain>0 比率差 | capital-loss>0 比率差 | education 不整合率 |
|---|---|---|---|
| official | 0.760 ± 0.012 | 0.805 ± 0.012 | 0.549 ± 0.044 |
| robust_numeric | 0.498 ± 0.008 | 0.521 ± 0.016 | 0.711 ± 0.024 |
| adult_semantic | 0.519 ± 0.012 | 0.535 ± 0.016 | 0.502 ± 0.072 |

![variant 別の fidelity/一貫性 mean±std](results/figures/adult_embedding_seed_fidelity.png)

*図 6: capital 比率差と education 不整合率（低いほど良い）。誤差バーは標準偏差。*

公式埋め込みは capital のゼロ集中を全く再現できていない（capital-gain>0 が実データ 9% に対し
合成 83%、比率差 0.76）。`robust_numeric`/`adult_semantic` はこれを **0.50 前後**まで下げた。
差（約 0.26）は標準偏差（≤0.02）よりはるかに大きく、**明確な改善**である。一方
`robust_numeric` は education 不整合を **悪化**させた（0.55→0.71）。capital 用の数値変換が
選択される合成サンプルを変え、education/education-num の同時分布を崩す副作用が出たと解釈できる。

## 仮説の判定

- **H1（capital をゼロ判定＋log 量に分解すると fidelity 改善）: 支持。**
  capital-gain/loss の比率差が 0.76/0.80 → 0.50/0.52 と、標準偏差を大きく超えて改善した。
- **H2（education 整合 penalty で意味的一貫性向上）: 未判定（弱い）。**
  `adult_semantic` の education 不整合は 0.549→0.502 と下がったが、改善幅は標準偏差（0.04〜0.07）
  の範囲内で有意とは言えない。しかも `adult_semantic` は utility を犠牲にし不安定。
- **H3（fnlwgt の寄与を下げると下流 utility 改善）: 未判定。**
  `robust_numeric` の精度は +1.1 点だが標準偏差内で、有意な改善ではない。

## 総括

気を利かせた埋め込みは、**狙った列（capital）の分布忠実度は明確に改善する**が、
**下流分類 utility は安定して改善しない**（`robust_numeric` は誤差内の微増、`adult_semantic`
はむしろ悪化・不安定）。accuracy 一つだけ見ると「変わらない」に見えるが、fidelity 軸では
確かに変わる。ここには trade-off がある。

- `robust_numeric`: capital 忠実度＋utility は改善方向だが、education 整合を悪化させる副作用。
- `adult_semantic`: education 整合をわずかに改善する代わりに utility を落とし、seed 感度が高い。

強い主張はしない。単一指標での優劣ではなく、utility・fidelity・意味的一貫性の trade-off として
読むべき結果である。tabicl が強力なため、埋め込みの改良が下流精度に表れにくい可能性も残る
（未確認）。
