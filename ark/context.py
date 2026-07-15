"""作業ディレクトリと config.yaml の解決ヘルパ。

- root():    キット本体（ark/・scripts/・templates/）の場所。import 解決に使う固定パス。
- workdir(): 執筆物・成果物（content/・htmls/・config.yaml）の置き場。ARK_WORKDIR で差し替え可能。
- load_config(): workdir 直下の config.yaml を読む（無ければ既定値を返す）。

合成データ実験には依存しない。レポートの執筆とビルドに必要な最小限だけを提供する。
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# config.yaml が無くてもビルドできるよう、メタ情報の既定値を持つ。
DEFAULT_CONFIG: dict = {
    "report": {
        "hero_title": "検証レポート",
        "repo_url": "https://github.com/OWNER/REPO",
        "upstream_url": "",
    }
}


def root() -> Path:
    """キット本体（ark/・scripts/・templates/・content/）の場所。固定パス。"""
    return Path(__file__).resolve().parent.parent


def workdir() -> Path:
    """執筆物・成果物（content/・htmls/・config.yaml）の置き場。

    環境変数 ``ARK_WORKDIR`` で差し替えられる（既定はキット本体直下）。
    別リポジトリで使う場合はそのリポジトリ直下を指す。デモ生成物を隔離フォルダに
    集約したいときも ``ARK_WORKDIR`` を指定すればキット本体を汚さない。
    """
    w = Path(os.environ.get("ARK_WORKDIR") or root()).resolve()
    w.mkdir(parents=True, exist_ok=True)
    return w


def load_config(r: Path | None = None) -> dict:
    """workdir 直下の config.yaml を読む。無い／空のときは DEFAULT_CONFIG を返す。"""
    r = r or workdir()
    f = r / "config.yaml"
    if not f.exists():
        return {"report": dict(DEFAULT_CONFIG["report"])}
    cfg = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    # report セクションが欠けても落ちないよう既定値で補完する。
    return {"report": {**DEFAULT_CONFIG["report"], **(cfg.get("report") or {})}}
