"""Markdown レポート → 自己完結 HTML(GitHub Pages 公開用)ビルダー。

情報系アカデミア向けの「論文体レポート＋補助タブ」サイトを、Markdown だけから生成する。
特定の研究テーマ（合成データ・特定ライブラリ等）には依存しない汎用ビルダー。

特徴:
- 本文中の画像(*.png)を base64 埋め込み(HTML 単体で配布・閲覧可能)
- 目次サイドバー + ヒーロー + ページ切替タブ
- ```mermaid を描画(抽出→div 注入→mermaid.js。codehilite に壊されない)
- ページ間 .md リンク→.html、その他リポジトリ相対→GitHub blob に書換
- 出典タグ [n](href="#refN")を上付きチップに、区分バッジ(📘/🔎/📑)を色分け
- 数式(MathJax v3 + arithmatex)。インライン `$...$`、表示 `$$...$$`

使い方(ライブラリとして):
    from ark.build_html import build
    build(root=Path("."), cfg={
        "repo_url": "https://github.com/OWNER/REPO",
        "upstream_url": "",
        "hero_title": "...",
        "outdir": "htmls",
        "pages": [{"md":"content/REPORT.md","out":"index.html","key":"report","nav":"📄 レポート","subtitle":"..."},
                  {"md":"content/faq.md","out":"faq.html","key":"faq","nav":"❓ FAQ","subtitle":"..."}],
    })

依存は markdown / pygments / pymdown-extensions のみ。
"""

from __future__ import annotations

import base64
import re
import shutil
from pathlib import Path

import markdown


def _embed_images(md_text: str, root: Path) -> str:
    def repl(m: re.Match) -> str:
        alt, path = m.group(1), m.group(2)
        img = root / path
        if not img.exists():
            return m.group(0)
        return f"![{alt}](data:image/png;base64,{base64.b64encode(img.read_bytes()).decode()})"
    return re.sub(r"!\[([^\]]*)\]\(([^)]+\.png)\)", repl, md_text)


def _extract_mermaid(md_text: str):
    blocks: list[str] = []

    def repl(m: re.Match) -> str:
        blocks.append(m.group(1).strip())
        return f"\n\nxMERMAIDBLOCKx{len(blocks) - 1}x\n\n"
    return re.sub(r"```mermaid\s*\n(.*?)```", repl, md_text, flags=re.DOTALL), blocks


def _inject_mermaid(html: str, blocks: list[str]) -> str:
    for i, src in enumerate(blocks):
        html = html.replace(f"<p>xMERMAIDBLOCKx{i}x</p>", f'<div class="mermaid">\n{src}\n</div>')
    return html


def _rewrite_links(html: str, pages: list[dict], repo_url: str) -> str:
    for p in pages:
        html = html.replace(f'href="{p["md"]}"', f'href="{p["out"]}"')
    site_files = {p["out"] for p in pages}

    def repl(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith(("http://", "https://", "#", "mailto:", "data:")) or href in site_files:
            return m.group(0)
        return f'href="{repo_url}/blob/main/{href}"'
    return re.sub(r'href="([^"]+)"', repl, html)


def _style_badges(html: str) -> str:
    # 📘 出典・根拠(青) / 🔎・💡 考察・ヒント・注意(琥珀) / ⚠️ 注意(琥珀) / 📑 凡例(青灰)
    mapping = {"📘": "badge-doc", "🔎": "badge-note", "💡": "badge-note",
               "⚠️": "badge-note", "📑": "badge-legend"}

    def repl(m: re.Match) -> str:
        return f'<blockquote class="{mapping[m.group(2)]}">{m.group(1)}<p>{m.group(2)}'
    return re.sub(r"<blockquote>(\s*)<p>(📘|🔎|💡|⚠️|📑)", repl, html)


CSS = """
:root { --fg:#1a1d24; --muted:#5b6470; --accent:#3949ab; --accent-soft:#eef1fb; --line:#e4e7ec; --bg:#fff; --code:#f6f8fa; --sidebar:#fafbfc; }
* { box-sizing: border-box; } html { scroll-behavior: smooth; }
body { font-family:-apple-system,"Segoe UI","Hiragino Sans","Yu Gothic UI","Meiryo",sans-serif; color:var(--fg); background:#f3f4f6; line-height:1.85; margin:0; }
.hero { background:linear-gradient(135deg,#1f2937 0%,#3949ab 130%); color:#fff; padding:36px 24px 0; }
.hero .inner { max-width:1180px; margin:0 auto; } .hero h1 { margin:0 0 .3em; font-size:1.8rem; border:none; color:#fff; }
.hero p { margin:.2em 0; opacity:.92; font-size:.94rem; } .hero a { color:#ffe; }
.nav { max-width:1180px; margin:16px auto 0; display:flex; gap:6px; }
.nav a { padding:9px 18px; border-radius:8px 8px 0 0; background:rgba(255,255,255,.14); color:#fff; text-decoration:none; font-size:.9rem; border:1px solid rgba(255,255,255,.25); border-bottom:none; }
.nav a.active { background:#f3f4f6; color:var(--accent); font-weight:600; } .nav a:hover:not(.active) { background:rgba(255,255,255,.26); }
.layout { max-width:1180px; margin:0 auto; display:grid; grid-template-columns:250px 1fr; gap:32px; padding:24px 24px 96px; }
nav.toc { position:sticky; top:18px; align-self:start; max-height:calc(100vh - 36px); overflow-y:auto; background:var(--sidebar); border:1px solid var(--line); border-radius:10px; padding:14px 16px; font-size:.86rem; }
nav.toc strong { display:block; margin-bottom:8px; color:var(--accent); } nav.toc ul { list-style:none; padding-left:0; margin:0; } nav.toc ul ul { padding-left:12px; }
nav.toc li { margin:3px 0; } nav.toc a { color:#34495e; text-decoration:none; display:block; padding:2px 0; } nav.toc a:hover { color:var(--accent); }
article { background:var(--bg); border:1px solid var(--line); border-radius:10px; padding:12px 40px 56px; box-shadow:0 1px 10px rgba(0,0,0,.04); min-width:0; }
article > h1:first-of-type { display:none; }
h2 { font-size:1.45rem; margin-top:2.2em; border-bottom:1px solid var(--line); padding-bottom:.3em; scroll-margin-top:16px; }
h3 { font-size:1.16rem; margin-top:1.7em; color:#222; scroll-margin-top:16px; } h4 { font-size:1.0rem; margin-top:1.3em; color:var(--accent); }
a { color:#1565c0; text-decoration:none; } a:hover { text-decoration:underline; }
a[href^="#ref"] { font-size:.72em; vertical-align:super; line-height:0; color:#1565c0; background:#eef4fb; border:1px solid #cfe0f3; border-radius:4px; padding:0 4px; margin:0 1px; text-decoration:none; white-space:nowrap; }
a[href^="#ref"]:hover { background:#d7e8fb; } :target { scroll-margin-top:18px; }
code { background:var(--code); padding:.15em .4em; border-radius:4px; font-size:.88em; font-family:"Cascadia Code",Consolas,"SF Mono",monospace; }
pre { background:var(--code); padding:15px 18px; border-radius:8px; overflow-x:auto; border:1px solid var(--line); } pre code { background:none; padding:0; }
table { border-collapse:collapse; width:100%; margin:1.2em 0; font-size:.9rem; display:block; overflow-x:auto; }
th,td { border:1px solid var(--line); padding:8px 11px; text-align:left; white-space:nowrap; } th { background:#f2f4f7; font-weight:600; } tr:nth-child(even) td { background:#fbfbfc; }
img { max-width:100%; height:auto; display:block; margin:1.2em auto; border:1px solid var(--line); border-radius:8px; }
.mermaid { background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; margin:1.4em 0; text-align:center; overflow-x:auto; }
blockquote { border-left:4px solid var(--accent); margin:1.2em 0; padding:.4em 1.2em; background:var(--accent-soft); color:#33404f; border-radius:0 6px 6px 0; }
blockquote.badge-doc { border-left-color:#1565c0; background:#eef4fb; color:#21303f; }
blockquote.badge-note { border-left-color:#b9770e; background:#fdf6e9; color:#3a2e12; }
blockquote.badge-legend { border-left-color:#607d8b; background:#eef1f3; color:#243; }
hr { border:none; border-top:1px solid var(--line); margin:2.2em 0; }
footer { max-width:1180px; margin:0 auto; padding:24px; color:var(--muted); font-size:.85rem; text-align:center; }
@media (max-width:860px) { .layout { grid-template-columns:1fr; } nav.toc { position:static; max-height:none; } article { padding:12px 20px 40px; } }
"""

MERMAID_JS = """
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });
</script>
"""

MATHJAX = """
<script>
  window.MathJax = {
    tex: { inlineMath: [["\\\\(", "\\\\)"]], displayMath: [["\\\\[", "\\\\]"]],
           processEscapes: true, processEnvironments: true },
    options: { ignoreHtmlClass: ".*|", processHtmlClass: "arithmatex" }
  };
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
"""


def _nav(active_key: str, pages: list[dict]) -> str:
    links = []
    for p in pages:
        cls = ' class="active"' if p["key"] == active_key else ""
        links.append(f'<a href="{p["out"]}"{cls}>{p["nav"]}</a>')
    return f'<nav class="nav">{"".join(links)}</nav>'


def _render(page: dict, pages: list[dict], cfg: dict, root: Path) -> str:
    md_text, blocks = _extract_mermaid(_embed_images((root / page["md"]).read_text(encoding="utf-8"), root))
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "codehilite", "sane_lists",
                                       "pymdownx.arithmatex"],
                           extension_configs={"codehilite": {"guess_lang": False}, "toc": {"toc_depth": "2-3"},
                                              "pymdownx.arithmatex": {"generic": True}})
    body = _style_badges(_rewrite_links(_inject_mermaid(md.convert(md_text), blocks), pages, cfg["repo_url"]))
    upstream = (f' · Upstream: <a href="{cfg["upstream_url"]}">{cfg["upstream_url"]}</a>'
                if cfg.get("upstream_url") else "")
    mermaid_js = MERMAID_JS if blocks else ""
    mathjax = MATHJAX if 'class="arithmatex"' in body else ""
    return f"""<!DOCTYPE html>
<html lang="ja"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg['hero_title']}</title><style>{CSS}</style>{mathjax}
</head><body>
<header class="hero"><div class="inner"><h1>{cfg['hero_title']}</h1><p>{page['subtitle']}</p></div>{_nav(page['key'], pages)}</header>
<div class="layout"><nav class="toc"><strong>目次</strong>{md.toc}</nav><article>{body}</article></div>
<footer>Source: <a href="{cfg['repo_url']}">{cfg['repo_url']}</a>{upstream}</footer>
{mermaid_js}
</body></html>"""


def build(root: Path, cfg: dict) -> list[Path]:
    """REPORT/EXPERIMENTS を htmls/ にビルドして書き出す。書いたファイルのパス一覧を返す。"""
    root = Path(root)
    outdir = root / cfg.get("outdir", "htmls")
    pages = [p for p in cfg["pages"] if (root / p["md"]).exists()]
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    (outdir / ".nojekyll").write_text("")
    written = []
    for p in pages:
        html = _render(p, pages, cfg, root)
        dest = outdir / p["out"]
        dest.write_text(html, encoding="utf-8")
        written.append(dest)
        print(f"wrote {outdir.name}/{p['out']} ({len(html.encode()) / 1024:.0f} KB)")
    return written
