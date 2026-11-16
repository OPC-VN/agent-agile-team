"""Locale rules of check.py (SPR-33 TK4): locale-invalid, locale-differs, locale-label-mixed and the `locale` key.

All three rules fire only for a document with an EXPLICIT `locale` key (GC4): an old record without the key keeps
byte-identical findings. Rule messages stay Vietnamese (output only); rule keys and severities are asserted exactly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import REPO, write_lf
import _labels as lab
import check
from test_check import make_sprint, rules_of

NEW_RULES = ("locale-invalid", "locale-differs", "locale-label-mixed")


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def set_locale(path: Path, value, english: bool = False) -> None:
    """Add (or replace) the `locale` frontmatter line after `doc:`; english=True also rewrites the labels."""
    text = re.sub(r"^locale:.*\n", "", read(path), count=1, flags=re.M)
    if english:
        text = lab.translate(text, "en")
    if value is not None:
        text = re.sub(r"^(doc:.*\n)", lambda m: m.group(1) + f"locale: {value}\n", text, count=1, flags=re.M)
    write_lf(path, text)


def retranslate(path: Path, locale: str) -> None:
    write_lf(path, lab.translate(read(path), locale))


def tag_all(root: Path, value: str, english: bool = False) -> None:
    for path in sorted(root.glob("*.md")):
        set_locale(path, value, english)


def findings(report, rule: str) -> list:
    return [f for f in report.findings if f.rule == rule]


def test_new_rules_are_registered_with_the_right_severity():
    assert check.RULES["locale-invalid"][0] == "Phải sửa"
    assert check.RULES["locale-differs"][0] == "Nên sửa"
    assert check.RULES["locale-label-mixed"][0] == "Ghi chú"
    assert "locale" in check.KNOWN_KEYS


def test_locale_key_has_a_row_in_the_keys_table_of_templates_readme():
    text = (REPO / "templates" / "README.md").read_text(encoding="utf-8")
    assert re.search(r"^\| `locale` \|", text, re.M)


# --- the key itself ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value, english", [("vi", False), ("en", True)])
def test_clean_set_with_explicit_locale_stays_clean(tmp_path, value, english):
    root = make_sprint(tmp_path)
    tag_all(root, value, english)
    report = check.check_paths([root])
    assert [f.render() for f in report.findings] == []
    assert report.exit_code == 0
    assert "frontmatter-key-unknown" not in rules_of(report)


# --- locale-invalid ------------------------------------------------------------------------------------------


def test_locale_invalid_fires_on_unshipped_value(tmp_path):
    root = make_sprint(tmp_path)
    set_locale(root / "SPEC.md", "fr")
    hits = findings(check.check_paths([root]), "locale-invalid")
    assert len(hits) == 1
    assert hits[0].level == "Phải sửa"
    assert hits[0].path.name == "SPEC.md"


def test_locale_invalid_fires_on_non_string_value(tmp_path):
    root = make_sprint(tmp_path)
    set_locale(root / "SPEC.md", "[vi]")
    assert len(findings(check.check_paths([root]), "locale-invalid")) == 1


def test_locale_invalid_is_blocking(tmp_path):
    root = make_sprint(tmp_path)
    set_locale(root / "SPEC.md", "xx")
    assert check.check_paths([root]).exit_code != 0


@pytest.mark.parametrize("value", ["vi", "en"])
def test_locale_invalid_silent_on_shipped_values(tmp_path, value):
    root = make_sprint(tmp_path)
    tag_all(root, value, english=value == "en")
    assert "locale-invalid" not in rules_of(check.check_paths([root]))


def test_locale_invalid_silent_without_key(tmp_path):
    root = make_sprint(tmp_path)
    assert not rules_of(check.check_paths([root])) & set(NEW_RULES)


# --- locale-differs ------------------------------------------------------------------------------------------


def test_locale_differs_fires_when_documents_disagree(tmp_path):
    root = make_sprint(tmp_path)
    tag_all(root, "vi")
    set_locale(root / "REPORT.md", "en", english=True)
    hits = findings(check.check_paths([root]), "locale-differs")
    assert len(hits) == 1
    assert hits[0].level == "Nên sửa"
    assert hits[0].path.name == "REPORT.md"


def test_locale_differs_silent_when_all_agree(tmp_path):
    root = make_sprint(tmp_path)
    tag_all(root, "en", english=True)
    assert "locale-differs" not in rules_of(check.check_paths([root]))


def test_locale_differs_ignores_documents_without_the_key(tmp_path):
    root = make_sprint(tmp_path)
    set_locale(root / "SPEC.md", "vi")
    assert "locale-differs" not in rules_of(check.check_paths([root]))


def test_locale_differs_is_per_folder(tmp_path):
    a = make_sprint(tmp_path / "a")
    b = make_sprint(tmp_path / "b")
    tag_all(a, "vi")
    tag_all(b, "en", english=True)
    assert "locale-differs" not in rules_of(check.check_paths([a, b]))


def test_locale_differs_does_not_count_an_invalid_value(tmp_path):
    root = make_sprint(tmp_path)
    set_locale(root / "SPEC.md", "vi")
    set_locale(root / "PLAN.md", "fr")
    rules = rules_of(check.check_paths([root]))
    assert "locale-invalid" in rules
    assert "locale-differs" not in rules


# --- locale-label-mixed --------------------------------------------------------------------------------------


def test_label_mixed_fires_for_english_labels_in_a_vi_document(tmp_path):
    root = make_sprint(tmp_path)
    tag_all(root, "vi")
    retranslate(root / "SPEC.md", "en")
    hits = findings(check.check_paths([root]), "locale-label-mixed")
    assert [h.path.name for h in hits] == ["SPEC.md"]
    assert hits[0].level == "Ghi chú"


def test_label_mixed_fires_for_vietnamese_labels_in_an_en_document(tmp_path):
    root = make_sprint(tmp_path)
    tag_all(root, "en", english=True)
    retranslate(root / "PLAN.md", "vi")
    hits = findings(check.check_paths([root]), "locale-label-mixed")
    assert [h.path.name for h in hits] == ["PLAN.md"]
    assert hits[0].level == "Ghi chú"


def test_label_mixed_is_a_note_only(tmp_path):
    root = make_sprint(tmp_path)
    tag_all(root, "vi")
    retranslate(root / "SPEC.md", "en")
    report = check.check_paths([root])
    assert "locale-label-mixed" in rules_of(report)
    assert report.exit_code == 0


def test_label_mixed_silent_for_vi_document_with_english_words(tmp_path):
    root = make_sprint(tmp_path)
    tag_all(root, "vi")
    spec = root / "SPEC.md"
    write_lf(spec, read(spec) + "\nTrang này dùng Scope, Status và Owner như từ thường.\n")
    assert "locale-label-mixed" not in rules_of(check.check_paths([root]))


def test_label_mixed_does_not_count_labels_shared_by_both_locales(tmp_path):
    """SPEC, PLAN, PROGRESS, REPORT, Timeline and Review & Retro read the same in vi and en."""
    root = make_sprint(tmp_path)
    tag_all(root, "en", english=True)
    assert "locale-label-mixed" not in rules_of(check.check_paths([root]))


# --- GC4: an old record stays byte-identical -----------------------------------------------------------------


def test_old_record_without_locale_key_gets_no_locale_finding(tmp_path):
    root = make_sprint(tmp_path)
    spec = root / "SPEC.md"
    write_lf(spec, read(spec) + "\nScope: Owner, Status.\n")
    retranslate(root / "PLAN.md", "en")  # a mixed record without the key
    assert not rules_of(check.check_paths([root])) & set(NEW_RULES)


def test_adding_the_key_to_a_clean_set_adds_no_finding(tmp_path):
    a = make_sprint(tmp_path / "a")
    b = make_sprint(tmp_path / "b")
    tag_all(b, "vi")
    fa = [(f.path.name, f.rule) for f in check.check_paths([a]).findings]
    fb = [(f.path.name, f.rule) for f in check.check_paths([b]).findings]
    assert fa == fb == []
