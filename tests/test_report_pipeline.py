"""Tests for the report numeric pipeline: log parsing, iteration extraction, and
the strict-validity / POSIX-path invariants of the tracked summary JSONs (issue #45).

Fixture-based and fast — no network, no PE run. Guards the regressions we actually
hit: `float('inf')` serialized as bare `Infinity` (#38), and OS-native backslash
paths in provenance JSON (#44).
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_smoke import parse_final_metrics  # noqa: E402
from collect_results import extract_iterations  # noqa: E402

PREFIX = "07/19/2026 08:44:21 AM [pe] [INFO ]  "


def _log(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "log.txt"
    p.write_text("\n".join(PREFIX + ln for ln in body.strip().splitlines()) + "\n",
                 encoding="utf-8")
    return p


FINAL_BODY = """
Tabular classifier test accuracy: 80.94%
Tabular classifier test (macro) F1 score: 70.78
Tabular classifier test AUC: 84.94
1way-wsd_1000samples_42seed_{'PE.VARIATION_API_FOLD_ID':-1}: 0.029
2way-wsd_1000samples_42seed_{'PE.VARIATION_API_FOLD_ID':-1}: 0.053
3way-wsd_1000samples_42seed_{'PE.VARIATION_API_FOLD_ID':-1}: 0.076
DP epsilon=1.0, delta=4.13121706102112e-06, noise_multiplier=3.92, num_iterations=29.
"""


def test_parse_final_metrics_basic(tmp_path):
    fm = parse_final_metrics(_log(tmp_path, FINAL_BODY))
    assert fm["classifier_test_acc"] == 80.94
    assert fm["classifier_test_f1"] == 70.78
    assert fm["classifier_test_auc"] == 84.94
    assert fm["wsd_1way"] == 0.029
    assert fm["wsd_2way"] == 0.053
    assert fm["wsd_3way"] == 0.076
    assert fm["dp"]["epsilon"] == 1.0
    assert fm["dp"]["noise_multiplier"] == 3.92
    assert fm["dp"]["accounted_num_iterations"] == 29
    # dp must stay JSON-serializable with a strict parser (no bare Infinity/NaN).
    json.loads(json.dumps(fm))


def test_parse_final_metrics_last_wins(tmp_path):
    body = """
Tabular classifier test accuracy: 60.00%
Tabular classifier test accuracy: 82.50%
"""
    fm = parse_final_metrics(_log(tmp_path, body))
    assert fm["classifier_test_acc"] == 82.50


def test_parse_final_metrics_epsilon_inf_is_string(tmp_path):
    body = """
Tabular classifier test accuracy: 82.47%
DP epsilon=inf, delta=4.1e-06, noise_multiplier=0.0, num_iterations=29.
"""
    fm = parse_final_metrics(_log(tmp_path, body))
    # kept as the string "inf" so json.dumps does not emit the invalid token Infinity
    assert fm["dp"]["epsilon"] == "inf"
    assert "Infinity" not in json.dumps(fm)


def test_parse_final_metrics_missing_file(tmp_path):
    assert parse_final_metrics(tmp_path / "does_not_exist.txt") == {}


def test_extract_iterations_attributes_and_skips(tmp_path):
    # iter 0 metrics (before any marker); markers 1-2 with metrics only after 2;
    # marker 3 with no following metrics -> skipped.
    body = """
Tabular classifier test accuracy: 50.00%
Tabular classifier test (macro) F1 score: 40.00
1way-wsd_1000samples_42seed_x: 0.30
PE iteration 1
PE iteration 2
Tabular classifier test accuracy: 70.00%
Tabular classifier test (macro) F1 score: 65.00
1way-wsd_1000samples_42seed_x: 0.10
PE iteration 3
"""
    rows = extract_iterations(_log(tmp_path, body))
    iters = {r["iteration"]: r for r in rows}
    assert set(iters) == {0, 2}  # 1 and 3 carry no metrics -> not emitted
    assert iters[0]["test_acc"] == 50.0 and iters[0]["wsd_1way"] == 0.30
    assert iters[2]["test_acc"] == 70.0 and iters[2]["test_f1"] == 65.0


def test_extract_iterations_empty(tmp_path):
    assert extract_iterations(_log(tmp_path, "some line with no metrics")) == []


def test_tracked_summaries_are_strict_json():
    """Every tracked summary JSON parses with a strict parser and contains no bare
    Infinity/NaN tokens (the #38 regression)."""
    files = glob.glob(str(REPO_ROOT / "results" / "summaries" / "*.json"))
    assert files, "expected tracked summary JSONs"
    for f in files:
        text = Path(f).read_text(encoding="utf-8")
        json.loads(text)  # raises on invalid JSON
        for bad in ("Infinity", "NaN"):
            assert bad not in text, f"{Path(f).name} contains bare {bad}"


def test_tracked_summaries_use_posix_paths():
    """Provenance path fields carry no OS-native backslashes (the #44 regression)."""
    for f in glob.glob(str(REPO_ROOT / "results" / "summaries" / "*.json")):
        rec = json.loads(Path(f).read_text(encoding="utf-8"))
        records = rec if isinstance(rec, list) else [rec]
        for r in records:
            if not isinstance(r, dict):
                continue
            for key in ("_source_json", "copied_to", "console_log"):
                if isinstance(r.get(key), str):
                    assert "\\" not in r[key], f"{Path(f).name}:{key} has a backslash"
            art = r.get("artifacts")
            if isinstance(art, dict) and isinstance(art.get("log_relpath"), str):
                assert "\\" not in art["log_relpath"], f"{Path(f).name}:log_relpath has a backslash"
