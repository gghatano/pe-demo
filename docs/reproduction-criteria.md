# 再現判定の基準と対応付け（#20）

本追試の各実験を `REPRODUCED / PARTIALLY_REPRODUCED / EXECUTED / FAILED / NOT_RUN`
のいずれかに、根拠付きで判定するための基準と、公式（論文・README）との対応表をまとめる。
**判定基準は結果を見る前に定義する**（下記）。

## 1. 判定の定義と許容差（事前定義）

| 判定 | 条件 |
|---|---|
| `REPRODUCED` | 公式が公表した比較値が存在し、**設定が一致**（データ・split・ε・δ・iteration・sample 数・prior・分類器・指標）し、全対象指標が許容差内。 |
| `PARTIALLY_REPRODUCED` | 公式比較値が存在し、指標は許容差内だが、**明示できる設定差が 1 つ以上**ある（例：分類器の差し替え）。 |
| `EXECUTED` | 公式コードが正常終了し数値は得られたが、**対応する公式公表値が無い**ため数値比較ができない。 |
| `FAILED` | 実行が失敗した。 |
| `NOT_RUN` | 実行していない（例：ライセンス制約で未実行）。 |

指標ごとの許容差（`REPRODUCED`/`PARTIALLY` 判定に使用）:

- 下流分類 accuracy / macro F1 / AUC: **±1.0 ポイント**（生成の非決定性・seed 差を考慮）。
- k-way Wasserstein 周辺距離（WSD）: **相対 ±10%**。

## 2. 公式公表値の探索結果

比較の前提となる「公式が公表した数値」を探索した。結論として、**本デモに対応する公式公表値は
見つからなかった**。

- 公式リポジトリ `example/tabular/README.md` は各スクリプトの動作（データ取得・PE 実行・`log.txt`
  への accuracy / WSD 記録）を説明するのみで、**期待値（数値）を公表していない**。
- 論文 *Differentially Private Synthetic Data via APIs 4: Tabular Data*
  (arXiv:2606.08259) の要旨は「最良ベースライン AIM に対し分類精度を最大 10% 改善、実行は 28 倍
  高速」と述べるが、**本デモの各データセット別の accuracy/WSD 値を要旨では示していない**。また
  論文のベンチマークは標準的な DP 表形式ベンチであり、本リポジトリの利便デモ（breast_cancer,
  xor_stress_test, scm, artificial_characters 等）と 1:1 対応する保証がない。

したがって、**数値比較に基づく `REPRODUCED` は現時点で根拠づけられない**。これは
「比較値が存在しない実験を無理に `REPRODUCED` としない」という方針に従う判断である。

## 3. 実験 ↔ 公式の対応表

局所値は [reproduction-log](reproduction-log.md) / `results/summaries/` に基づく（判定は
`EXECUTED`）。「公式値」列はいずれも公表なし。

| 実験 | 公式参照 | 公式値 | 局所値（ε=1, tabicl 等） | 設定差 | 判定 |
|---|---|---|---|---|---|
| Breast Cancer | `example/tabular/breast_cancer.py` | 公表なし | acc 91.86 / F1 91.44 / AUC 98.73 | なし（無改変） | EXECUTED |
| Adult | `example/tabular/adult.py` | 公表なし | acc 80.94 / F1 70.78 / AUC 84.94 | なし（無改変） | EXECUTED |
| SCM (nn) | `scm.py --prior-function nn` | 公表なし | acc 85.48 / F1 85.46 / AUC 93.80 | なし | EXECUTED |
| SCM (tree) | `scm.py --prior-function tree` | 公表なし | acc 66.68 / F1 66.66 / AUC 72.61 | なし | EXECUTED |
| SCM (rff) | `scm.py --prior-function rff` | 公表なし | acc 61.08 / F1 61.03 / AUC 64.14 | なし | EXECUTED |
| Person Activity | `person_activity.py` | 公表なし | acc 64.04 / F1 36.52 | なし | EXECUTED |
| Artificial Characters | `artificial_characters.py` | 公表なし | acc 51.60 / F1 50.92 | なし | EXECUTED |
| XOR 1/2/3（生成） | `xor_stress_test.py --num-features k` | 公表なし | 生成のみ（分類器は下記） | 分類器を除去して生成 | EXECUTED |
| XOR 1/2/3（分類） | 同上（公式分類器 `tabpfn`） | 公表なし | tabicl 代替で 99.8 / 99.0 / 96.9 | **公式 tabpfn 未使用（要 TABPFN_TOKEN）→ tabicl 差し替え** | 公式分類器は NOT_RUN／代替は EXECUTED |

## 4. `REPRODUCED` 可能性の検討（完了条件）

最有力候補は **Breast Cancer**：公式スクリプトを無改変で実行でき、反復で 52%→92% と収束し
（進化が機能）、再実行間の揺れも小さいと見込まれる。しかし、

- 公式が期待値を公表していないため、**照合先が存在しない**。
- 論文の該当値が特定できれば、設定一致を確認のうえ `REPRODUCED`／`PARTIALLY_REPRODUCED` を
  判定できる余地がある。

よって現時点では **EXECUTED を維持**する。`REPRODUCED` へ引き上げるために必要なのは、
(a) 公式が公表した該当データセット・設定の数値、または (b) 論文のベンチ・ハーネスを同一条件で
再実行して比較値を得ること、のいずれかである。

## 5. 判定の一貫性

- `results/summaries/*.json` の `reproduction_status` は成功実験がすべて `EXECUTED`、失敗が
  `FAILED`、XOR の公式分類器が `NOT_RUN`。
- Markdown レポート（`content/index.md` §制約と再現性、`experiments.md`）および生成 HTML も
  同じく「すべて `EXECUTED`／`REPRODUCED` なし」と記述しており、**summary・Markdown・HTML で
  判定が一致**する。
