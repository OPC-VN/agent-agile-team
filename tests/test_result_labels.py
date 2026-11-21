"""SPR-34 TK2: the two result-cell words are in both label tables (pinned to literals)."""

from __future__ import annotations

import json

from conftest import REPO

LABELS = REPO / "labels"

EXPECTED = {
    "vi": {"status.not_run": "Chưa chạy", "status.not_applicable": "Không áp dụng"},
    "en": {"status.not_run": "Not run", "status.not_applicable": "Not applicable"},
}


def _raw(locale):
    return json.loads((LABELS / f"{locale}.json").read_text(encoding="utf-8"))


def test_result_words_pinned_vi():
    table = _raw("vi")
    for key, value in EXPECTED["vi"].items():
        assert table.get(key) == value, key


def test_result_words_pinned_en():
    table = _raw("en")
    for key, value in EXPECTED["en"].items():
        assert table.get(key) == value, key


def test_result_keys_in_both_tables():
    assert set(_raw("vi")) == set(_raw("en"))
