# ark — 取り込み元の明記

`ark/`（`build_html.py`, `context.py`, `__init__.py`）は
[gghatano/synth-report-kit](https://github.com/gghatano/synth-report-kit)（MIT License,
"academic-report-kit"）から取り込んだ汎用の Markdown→HTML レポートビルダーである。

- Markdown だけから「論文体レポート＋補助タブ」の自己完結 HTML を生成する。
- 本文中の PNG を base64 埋め込み、mermaid 描画、MathJax、出典チップ／バッジに対応。
- pe-demo 側の呼び出しは `scripts/build_site.py`、ページ構成は同ファイルの `PAGES`。

依存: `markdown`, `pygments`, `pymdown-extensions`, `pyyaml`。
