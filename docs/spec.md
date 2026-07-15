# Tab-PE 公式デモ再現追試プロジェクト仕様書

## 1. プロジェクト概要

本プロジェクトでは、Microsoft が公開している Private Evolution（PE）の公式実装 `microsoft/DPSDA` に含まれる、表形式データ向け手法 **Tabular Private Evolution（Tab-PE）** の公式デモを再現実行する。

第一段階の目的は、新規手法の追加評価や独自改良ではない。

以下を達成することを目的とする。

1. 公式実装を再現可能な環境で動作させる
2. 公式Tab-PEデモを可能な範囲で実行する
3. 各実験の条件・実行方法・結果を記録する
4. Tab-PEの処理構造と実験コードの関係を理解する
5. Markdownを一次成果物として実験結果を整理する
6. Markdownから閲覧性の高いHTMLレポートを生成する
7. 後続の比較実験・追加データセット実験に拡張可能な構成とする

公式リポジトリ：

* https://github.com/microsoft/DPSDA

Tab-PE論文：

* Differentially Private Synthetic Data via APIs 4: Tabular Data
* arXiv: https://arxiv.org/abs/2606.08259

参考レポート構成：

* https://github.com/gghatano/tpdp2026-binagg

本プロジェクトでは、上記 `tpdp2026-binagg` の構成を参考に、

> 実験コード
> ↓
> results 配下に生データ・集計結果・図を保存
> ↓
> content 配下のMarkdownに分析結果を記録
> ↓
> MarkdownからHTMLレポートを生成

という構成を採用する。

---

# 2. 最重要方針

## 2.1 最初は「公式デモの再現」に限定する

初期フェーズでは独自アルゴリズムを実装しない。

Tab-PE本体を再実装するのではなく、公式実装を利用する。

原則として、

* 公式パッケージ
* 公式サンプルコード
* 公式データ取得処理
* 公式評価コード

を可能な限りそのまま利用する。

コード変更が必要な場合は、

1. なぜ変更が必要だったか
2. 公式コードから何を変更したか
3. 結果への影響があるか

を必ず記録する。

---

## 2.2 再現性を優先する

実験結果だけでなく、

* OS
* Pythonバージョン
* uvバージョン
* Python依存パッケージ
* DPSDA / private-evolution のバージョン
* Git commit SHA
* 実行コマンド
* random seed
* CPU情報
* メモリ
* 実行時間

を可能な範囲で記録する。

公式リポジトリを直接利用する場合は、実験時点のcommit SHAを固定・記録する。

単に最新mainブランチを参照するだけの状態にはしない。

---

## 2.3 MarkdownをSingle Source of Truthとする

レポート本文は `content/*.md` を一次成果物とする。

HTMLを直接編集してはならない。

HTMLは必ずMarkdownから生成する。

実験結果の数値は、可能な限り手入力せず、

* JSON
* CSV

などの機械可読な実験結果からレポート生成処理が参照できる設計とする。

---

# 3. エージェント実行方針

本プロジェクトはメインエージェントが統括し、必要に応じて最大3つのサブエージェントを並列利用する。

ただし、並列化そのものを目的にしない。

依存関係がある作業は直列化する。

## Agent A：公式実装調査

担当：

* DPSDAリポジトリ構造調査
* Tab-PE関連コード特定
* `example/tabular/` 調査
* 各デモの入力・出力調査
* CLIオプション調査
* デフォルトパラメータ調査
* 評価指標調査
* データ取得方法調査
* 論文と公式コードの対応関係整理

成果物：

`docs/research/official-implementation.md`

調査結果には必ずソースコードパスを記載する。

例：

```text
example/tabular/adult.py
private_evolution/...
```

推測とコードから確認できた事実を明確に分離する。

---

## Agent B：再現環境・実験実装

担当：

* uv環境構築
* 公式パッケージ導入
* 公式デモ実行
* 実行ラッパースクリプト整備
* seed管理
* 実行時間計測
* 結果保存
* エラーログ保存

成果物：

* `pyproject.toml`
* `uv.lock`
* `scripts/`
* `results/`
* `docs/reproduction-log.md`

---

## Agent C：分析・レポート

担当：

* 実験結果集計
* 表・グラフ生成
* Markdownレポート作成
* HTMLビルダー作成
* レポート間の整合性確認

成果物：

* `content/*.md`
* `htmls/*.html`
* `scripts/build_html.py`

---

## メインエージェント

メインエージェントは以下を担当する。

* タスク分解
* サブエージェントへの指示
* 成果物レビュー
* 実験結果の整合性確認
* 再現失敗時の原因分析
* 公式結果との比較
* 最終レポート品質確認

サブエージェントの出力を無批判に採用してはならない。

特に数値結果については、

* 実行ログ
* CSV / JSON
* Markdown記載値

の一致を確認する。

---

# 4. 開発環境

## 4.1 Python環境

パッケージ管理には `uv` を使用する。

基本構築：

```bash
uv venv --python 3.12
```

依存関係は `pyproject.toml` で管理する。

原則として、

```bash
uv sync
```

で環境を再現できる状態にする。

Python 3.12で公式実装に互換性問題が発生する場合は、公式実装の対応Pythonバージョンを確認し、適切なバージョンへ変更する。

その場合、理由を `engineering-notes.md` に記録する。

---

## 4.2 Tab-PE導入

第一候補：

```bash
uv add "private-evolution[tabular]"
```

ただし、公式デモを正確に再現するためにGitHubリポジトリ版が必要な場合は、公式リポジトリを特定commitで固定して利用する。

例：

```bash
uv add "private-evolution[tabular] @ git+https://github.com/microsoft/DPSDA.git@<COMMIT_SHA>"
```

実際の導入方法は公式コードを調査した上で決定する。

最終的な環境は `uv.lock` に固定する。

---

# 5. 対象実験

公式 `example/tabular/` のデモを対象とする。

## Phase 1：Smoke Test

最初に、最も短時間で完了する実験を1つ選択する。

目的：

* インストール成功確認
* データダウンロード確認
* Tab-PE実行確認
* checkpoint生成確認
* synthetic CSV生成確認
* 評価処理確認

ここで問題があれば、他の実験へ進まない。

---

## Phase 2：XOR Stress Test

公式のXORデータ実験を再現する。

対象：

```bash
python xor_stress_test.py --num-features 1
python xor_stress_test.py --num-features 2
```

環境・計算時間に問題がなければ、

```text
num-features = 1 ～ 7
```

を段階的に実行する。

ただし、初期再現では公式READMEに明示された実行例を優先する。

記録項目：

* num-features
* privacy parameters
* population size
* iterations
* random seed
* classifier accuracy
* Wasserstein-style marginal distance
* runtime

XORについては、Tab-PEが高次相関を扱う実験であることを踏まえ、結果の意味を整理する。

ただし独自条件追加は第二段階とし、初回追試では公式条件再現を優先する。

---

## Phase 3：SCM

公式SCMデモを再現する。

対象：

```bash
python scm.py --prior-function rff
```

可能であれば、

```text
tree
nn
rff
```

を実行する。

記録項目：

* prior function
* dataset parameters
* privacy parameters
* classifier accuracy
* marginal distance
* runtime

各prior functionの役割は、コードおよび論文を確認して説明する。

推測のみで説明しない。

---

## Phase 4：実データ

以下の公式デモを順次実行する。

```bash
python artificial_characters.py
python person_activity.py
python adult.py
python breast_cancer.py
```

優先順位：

1. Breast Cancer
2. Adult
3. Artificial Characters
4. Person Activity

ただし、公式コードの計算量を事前確認し、実行時間が極端に長い場合は順序を変更してよい。

実行前に各データセットについて以下を記録する。

* データセット名
* 行数
* 列数
* categorical / numerical columns
* target
* train/test split
* データ取得元

---

# 6. 実験結果

公式Tabular Exampleの出力構造を尊重する。

可能な限り以下を保存する。

```text
results/
├── raw/
│   ├── xor/
│   ├── scm/
│   ├── adult/
│   ├── breast_cancer/
│   ├── artificial_characters/
│   └── person_activity/
│
├── synthetic/
│
├── checkpoints/
│
├── summaries/
│   ├── experiments.csv
│   └── experiments.json
│
├── logs/
│
└── figures/
```

公式実装が独自のディレクトリ構造を要求する場合、公式出力を破壊的に変更しない。

必要であれば、

```text
results/raw/
```

に公式出力をそのまま保存し、

```text
results/summaries/
```

に統合結果を生成する。

---

# 7. 最低限記録する評価指標

公式コードで取得できる指標を優先する。

最低限：

## Utility

* classifier accuracy

可能であれば、

* real train → real test
* synthetic train → real test

の関係を明確にする。

どのデータを学習に使い、どのデータを評価に使った値かを曖昧に記載しない。

---

## Statistical similarity

公式実装の

* Wasserstein-style marginal distance

を記録する。

具体的な計算方法についてコードを確認し、

* 何次元のmarginalか
* numerical / categoricalの扱い
* aggregation方法

を調査する。

---

## Privacy

各実験について、

* ε
* δ
* DP mechanism
* privacy accounting

を確認できる範囲で記録する。

「DPである」という説明のみで終わらせず、公式コード上でどのパラメータがどこに渡されているかを確認する。

---

## Performance

* wall-clock time
* iteration数
* CPU
* memory

を可能な範囲で記録する。

---

# 8. 再現判定

各実験に以下のステータスを設定する。

```text
REPRODUCED
PARTIALLY_REPRODUCED
EXECUTED
FAILED
NOT_RUN
```

定義：

### REPRODUCED

公式論文または公式READMEに比較対象となる数値が存在し、合理的な範囲で一致した。

### PARTIALLY_REPRODUCED

実行には成功したが、一部結果が一致しない、または公式結果の一部のみ確認できた。

### EXECUTED

公式コードの実行には成功したが、比較可能な公式数値がなく、再現性の判定はできない。

### FAILED

実行を試みたが失敗した。

### NOT_RUN

リソース制約などにより実行していない。

「実行できた」と「論文結果を再現した」を混同しないこと。

---

# 9. レポート構成

`tpdp2026-binagg` の構成を参考に、以下の多ページ構成とする。

```text
content/
├── index.md
├── method-tabpe.md
├── experiments.md
├── data-notes.md
├── results-detail.md
├── engineering-notes.md
└── faq.md
```

---

## 9.1 `index.md`

メインレポート。

構成：

```text
# Tab-PE 公式実装 再現追試

## Abstract

## 1. はじめに

## 2. 目的

## 3. Tab-PE概要

## 4. 再現方法

## 5. 実験

## 6. 結果

## 7. 考察

## 8. 再現性評価

## 9. 制約

## 10. 結論

## References
```

本文は単なる実行ログにしない。

最初に、

> 何を確認したかったか

を示し、

最後に、

> 何が再現でき、何が未確認なのか

を明確にする。

---

## 9.2 `method-tabpe.md`

内容：

* Private Evolution概要
* Tab-PE概要
* Initialization
* Scoring
* Selection
* Variation
* Crossover
* Mutation
* Iterative evolution
* Differential Privacy
* 従来PEとの差分

論文とコードを対応付ける。

可能であれば、

```text
論文上の処理
↓
公式コード上のclass/function
```

という対応表を作る。

---

## 9.3 `experiments.md`

内容：

* 公式デモ一覧
* 実行条件
* CLI
* パラメータ
* 実験順序
* 再現判定

各実験について再実行可能なコマンドを記載する。

---

## 9.4 `data-notes.md`

内容：

* 各データセット概要
* ダウンロード元
* train/test split
* metadata
* categorical / numerical
* target
* 前処理

公式処理を可能な限り正確に記録する。

---

## 9.5 `results-detail.md`

詳細結果。

以下を掲載する。

* 実験別結果
* accuracy
* marginal distance
* runtime
* iteration推移
* 図表

可能であれば、

```text
iteration
↓
utility / distance
```

の変化を可視化する。

ただし、公式ログに存在しない値を推測して生成しない。

---

## 9.6 `engineering-notes.md`

内容：

* uv環境構築
* Python version
* package version
* commit SHA
* 実行方法
* OS依存問題
* Windows / Linux差異
* データダウンロード問題
* checkpoint / resume
* エラーと解決方法
* 再現時の注意点

第三者がこのページだけを見ても環境を再構築できる状態を目指す。

---

## 9.7 `faq.md`

実験中に生じた疑問を記録する。

例：

* Tab-PEは何を進化させているのか
* private dataは各iterationでどのように参照されるか
* DP budgetはiteration間でどう配分されるか
* crossoverとは何か
* mutationとは何か
* marginal-based methodとの違いは何か
* なぜXORで差が出るのか
* checkpointから再開するとprivacy accountingはどうなるか

回答はコードまたは論文から確認する。

未確認の場合は「未確認」と明記する。

---

# 10. HTMLレポート

`tpdp2026-binagg` を参考に、MarkdownからHTMLを生成する。

出力：

```text
htmls/
├── index.html
├── method-tabpe.html
├── experiments.html
├── data-notes.html
├── results-detail.html
├── engineering-notes.html
├── faq.html
└── .nojekyll
```

HTMLは直接編集しない。

---

## UI構成

上部：

```text
Tab-PE 公式実装 再現追試

[📄 レポート]
[🧩 Tab-PE]
[🧪 実験]
[🔬 データ]
[📈 詳細結果]
[🛠 エンジニアリング]
[❓ QA]
```

本文：

```text
左：目次
右：本文
```

レスポンシブ対応する。

スマートフォンでは1カラムにする。

---

## HTML要件

* UTF-8
* GitHub Pagesで表示可能
* Markdown tables対応
* fenced code対応
* 数式対応
* MathJax対応
* h2/h3から目次自動生成
* 相対画像パス対応
* 図のbase64埋め込み
* 上部タブ
* active tab表示
* レスポンシブ対応

ページ構成は `PAGES` のような単一設定で管理する。

---

# 11. 推奨リポジトリ構成

```text
.
├── README.md
├── spec.md
├── pyproject.toml
├── uv.lock
│
├── content/
│   ├── index.md
│   ├── method-tabpe.md
│   ├── experiments.md
│   ├── data-notes.md
│   ├── results-detail.md
│   ├── engineering-notes.md
│   └── faq.md
│
├── docs/
│   ├── plans/
│   │   └── experiment-plan.md
│   ├── research/
│   │   └── official-implementation.md
│   └── reproduction-log.md
│
├── scripts/
│   ├── run_smoke.py
│   ├── run_xor.py
│   ├── run_scm.py
│   ├── run_real_datasets.py
│   ├── collect_results.py
│   ├── make_figures.py
│   └── build_html.py
│
├── results/
│   ├── raw/
│   ├── synthetic/
│   ├── checkpoints/
│   ├── summaries/
│   ├── logs/
│   └── figures/
│
├── data/
│   └── cache/
│
└── htmls/
```

生成物・キャッシュについて適切に `.gitignore` を設定する。

ただし、レポート再現に必要な小容量の集計結果はGit管理対象としてよい。

---

# 12. 実装順序

以下の順番を厳守する。

## Step 1

公式DPSDAのTab-PE実装を調査する。

まだ実験を大量実行しない。

---

## Step 2

`docs/research/official-implementation.md` を作る。

以下を確定する。

* インストール方法
* Python version
* 実行対象スクリプト
* パラメータ
* 出力ファイル
* 評価指標

---

## Step 3

uv環境を構築する。

```bash
uv sync
```

だけで再構築可能にする。

---

## Step 4

Smoke Testを1件実施する。

成功するまで他の大規模実験へ進まない。

---

## Step 5

XOR実験を実施する。

まず公式README記載条件。

その後、計算資源に問題がなければ公式stress test範囲を実施する。

---

## Step 6

SCM実験を実施する。

---

## Step 7

実データ実験を実施する。

---

## Step 8

結果を

```text
results/summaries/experiments.csv
results/summaries/experiments.json
```

に統合する。

---

## Step 9

図表を生成する。

---

## Step 10

`content/*.md` を更新する。

結果をMarkdownへ手入力でコピーするのではなく、可能な範囲で結果ファイルから数値を読み取る。

---

## Step 11

HTMLを生成する。

```bash
uv run python scripts/build_html.py
```

---

## Step 12

最終レビューを行う。

確認項目：

```text
[ ] uv syncで環境再構築できる
[ ] 公式コードとの差分が記録されている
[ ] commit SHAが記録されている
[ ] 実行コマンドが記録されている
[ ] random seedが記録されている
[ ] 実験結果CSV/JSONが存在する
[ ] Markdownと結果ファイルの数値が一致する
[ ] HTMLがMarkdownから生成される
[ ] HTMLを直接編集していない
[ ] 再現と単なる実行成功を区別している
[ ] 失敗した実験も記録している
```

---

# 13. 自律実行ルール

作業途中で軽微な問題が発生しても、原則としてユーザーへの確認待ちで停止しない。

以下の順で対処する。

1. 公式READMEを確認
2. 公式ドキュメントを確認
3. 公式コードを確認
4. GitHub Issueを確認
5. 最小限の修正で回避
6. 修正内容を記録

不明点が残っても、実行可能な他タスクを継続する。

ただし、

* 公式アルゴリズムを変更する
* privacy guaranteeに影響する
* 評価方法を変更する
* 結果の意味が変わる

変更は勝手に行わない。

必要な場合は、公式実験と変更実験を明確に分離する。

---

# 14. 完了条件

本フェーズは、以下が揃った時点で完了とする。

1. uvで環境を再構築できる
2. Tab-PE公式デモが少なくとも1件正常実行できる
3. XOR公式デモを実行している
4. 可能な範囲でSCM・実データデモを実行している
5. synthetic dataが保存されている
6. accuracy等の公式評価結果が保存されている
7. 実験条件・実行ログが保存されている
8. Markdownレポートが完成している
9. HTMLレポートが生成できる
10. 再現できた内容と未再現の内容が明確になっている

---

# 15. 本フェーズでは行わないこと

以下は初回フェーズのスコープ外とする。

* AIMとの本格比較
* MSTとの比較
* PrivBayesとの比較
* SDV系モデルとの比較
* 独自データセット適用
* 独自XOR条件設計
* ε sweep
* サンプル数 sweep
* 次元数 sweep
* Tab-PEアルゴリズム改良

これらは公式デモの再現性を確認した後のPhase 2として実施する。

まず、

> 公式Tab-PE実装を理解し、再現可能な実験・評価・レポート基盤を作る

ことを優先する。
