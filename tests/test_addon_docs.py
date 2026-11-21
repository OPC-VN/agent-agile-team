"""SPR-35 TK6.1 (DN6): `check` recognises the names `handoff` and `roadmap` and applies no shape rule to them.

The two names live in their own set `ADDON_DOCS`, not in `DOC_KINDS`: a wider `DOC_KINDS` would give old records that
use these values new Phải sửa findings (SC3). Any other unknown `doc` value still gives the Ghi chú `doc-unknown`.
"""

from __future__ import annotations

import shutil

import pytest

import check
from conftest import REPO, write_lf
from test_check import rules_of

TEMPLATE_FILES = {
    "handoff": REPO / "templates" / "sprint" / "HANDOFF.md",
    "roadmap": REPO / "templates" / "registry" / "ROADMAP.md",
}


def doc_file(tmp_path, name: str, doc_value: str, body: str = "# Tiêu đề\n\nNội dung.\n"):
    path = tmp_path / name
    write_lf(path, f"---\nid: DOC-1\ndoc: {doc_value}\ntitle: t\n---\n\n{body}")
    return path


@pytest.mark.parametrize("value, name", [("handoff", "HANDOFF.md"), ("roadmap", "ROADMAP.md")])
def test_addon_doc_values_are_not_doc_unknown(tmp_path, value, name):
    doc_file(tmp_path, name, value)
    assert rules_of(check.check_paths([tmp_path])) == set()


def test_addon_templates_have_zero_findings(tmp_path):
    for value, path in TEMPLATE_FILES.items():
        root = tmp_path / value
        root.mkdir()
        shutil.copyfile(path, root / path.name)
        report = check.check_paths([root])
        assert [f.render() for f in report.findings] == [], value


@pytest.mark.parametrize("value", ["handoff-brief", "roadmap-draft", "analysis"])
def test_near_miss_doc_value_still_doc_unknown(tmp_path, value):
    doc_file(tmp_path, "HANDOFF.md", value)
    assert rules_of(check.check_paths([tmp_path])) == {"doc-unknown"}


def test_legacy_handoff_without_give_return_has_no_heading_missing(tmp_path):
    path = doc_file(tmp_path, "HANDOFF.md", "handoff", body="# Bàn giao cũ\n\nKhông có tiêu đề Giao hay Trả.\n")
    rules = rules_of(check.check_paths([tmp_path]))
    assert not rules & {"heading-missing", "frontmatter-key-missing", "doc-unknown"}
    doc = check.load_doc(path)
    assert doc.kind is None
    assert doc.doc_name == "handoff"


def test_addon_docs_not_in_doc_kinds():
    assert tuple(check.ADDON_DOCS) == ("handoff", "roadmap")
    assert set(check.ADDON_DOCS).isdisjoint(check.DOC_KINDS)
    for table in (check.REQUIRED_KEYS, check.REQUIRED_HEADINGS, check.KNOWN_NAMES):
        assert set(check.ADDON_DOCS).isdisjoint(table)


def test_doc_unknown_message_still_lists_doc_kinds(tmp_path):
    doc_file(tmp_path, "HANDOFF.md", "handoff-brief")
    findings = check.check_paths([tmp_path]).findings
    assert findings and all(check.DOC_KINDS[0] in f.message for f in findings if f.rule == "doc-unknown")
