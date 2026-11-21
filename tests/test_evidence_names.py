"""Tên file hồ sơ viết hoa trong máy kiểm (SPR-35 TK3; FR3.2, FR3.3, SC3).

`check` nhận biên bản cổng hai tên (`GATE-<N>-VERDICT.md` mới, `gate-<N>-verdict.md` cũ); luật `evidence-name` (Ghi chú) chỉ
áp cho hồ sơ tạo từ `NAMING_EFFECTIVE_DATE`. Tra tên bằng liệt kê thư mục: Windows không phân biệt hoa thường, nên
`Path.exists` với kiểu chữ khác sẽ xanh giả ở máy và đỏ ở CI Linux.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from conftest import write_lf
import _common as c
import check
from test_check import _new_delegated_plan, _rewrite, make_sprint

NEW_DATE = "2026-11-21"  # ngày hiệu lực dùng trong test (hằng của nhánh là giá trị giữ chỗ 9999-12-31)
PLAN_QUOTE = "duyệt thay: chọn phương án a — xem mục Bản ghi duyệt thay"


@pytest.fixture
def effective(monkeypatch):
    """Ngày hiệu lực giả lập: hồ sơ `created` từ đó trở đi là hồ sơ mới."""
    monkeypatch.setattr(c, "NAMING_EFFECTIVE_DATE", NEW_DATE)


def _verdict_names(root: Path) -> list:
    return sorted(n for n in os.listdir(root / "evidence") if n.lower().endswith("-verdict.md"))


def _rename_verdict(root: Path, number: int, name: str) -> None:
    """Đổi tên biên bản cổng qua tên trung gian: đúng trên cả hệ file không phân biệt hoa thường."""
    evidence = root / "evidence"
    old = next(n for n in os.listdir(evidence) if n.lower() == f"gate-{number}-verdict.md")
    tmp = evidence / "tmp-rename.md"
    (evidence / old).rename(tmp)
    tmp.rename(evidence / name)
    assert name in os.listdir(evidence)


def _signer(root: Path) -> list:
    return [f for f in check.check_paths([root]).findings if f.rule == "gate-signer-independence"]


def _notes(root: Path, **kw) -> list:
    return [f for f in check.check_paths([root], **kw).findings if f.rule == "evidence-name"]


def _new_record_with(root: Path, *names: str) -> None:
    """Hồ sơ mới (`created` từ ngày hiệu lực) với các file kèm rỗng trong `evidence/`."""
    _rewrite(root / "PROGRESS.md", "created: 2026-02-01", f"created: {NEW_DATE}")
    (root / "evidence").mkdir(exist_ok=True)
    for name in names:
        write_lf(root / "evidence" / name, "nội dung\n")


# --- Biên bản cổng hai tên (FR3.2) --------------------------------------------------------------------------


def test_gate_verdict_upper_name_accepted(tmp_path):
    root = make_sprint(tmp_path)
    _new_delegated_plan(root)
    _rename_verdict(root, 1, "GATE-1-VERDICT.md")
    assert _verdict_names(root) == ["GATE-1-VERDICT.md"]
    assert _signer(root) == []


def test_gate_verdict_legacy_name_still_accepted(tmp_path):
    root = make_sprint(tmp_path)
    _new_delegated_plan(root)
    assert _verdict_names(root) == ["gate-1-verdict.md"]
    assert _signer(root) == []
    assert _notes(root) == []


def test_gate_verdict_missing_message_names_upper_file(tmp_path):
    root = make_sprint(tmp_path)
    _new_delegated_plan(root, verdict=False)
    hits = _signer(root)
    assert len(hits) == 1 and "evidence/GATE-1-VERDICT.md" in hits[0].message, [f.render() for f in hits]


def test_gate_verdict_upper_name_first_line_mismatch_names_found_file(tmp_path):
    root = make_sprint(tmp_path)
    _new_delegated_plan(root)
    _rename_verdict(root, 1, "GATE-1-VERDICT.md")
    write_lf(root / "evidence" / "GATE-1-VERDICT.md", "duyệt thay: kết luận khác\n")
    hits = _signer(root)
    assert len(hits) == 1 and "evidence/GATE-1-VERDICT.md" in hits[0].message and "dòng đầu" in hits[0].message


def test_both_names_present_prefers_upper_and_notes(tmp_path, effective):
    """Có cả hai tên: dùng tên mới (dòng đầu tên cũ sai cũng không báo), và báo `evidence-name` ở hồ sơ mới.
    Ở hệ file không phân biệt hoa thường không thể có hai file cùng tên khác kiểu chữ: bỏ qua ca này ở đó."""
    root = make_sprint(tmp_path)
    _new_delegated_plan(root)
    _new_record_with(root)
    write_lf(root / "evidence" / "GATE-1-VERDICT.md", PLAN_QUOTE + "\n")
    if len(os.listdir(root / "evidence")) < 2:
        pytest.skip("hệ file không phân biệt hoa thường: không dựng được hai tên")
    write_lf(root / "evidence" / "gate-1-verdict.md", "duyệt thay: kết luận cũ khác\n")
    assert _signer(root) == []
    notes = _notes(root)
    assert len(notes) == 1 and "gate-1-verdict.md" in notes[0].message, [f.render() for f in notes]


def test_verdict_lookup_uses_directory_listing(tmp_path, monkeypatch):
    """Giả `os.listdir` trả tên chữ thường: hỏi tên chữ hoa phải rơi về nhánh tên cũ và trả đúng tên đã liệt kê.
    Một cài đặt dùng `Path.exists`/`is_file` với tên chữ hoa sẽ trả tên chữ hoa ở Windows (xanh giả)."""
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    write_lf(evidence / "gate-1-verdict.md", "x\n")
    real = os.listdir
    monkeypatch.setattr(check.os, "listdir", lambda p=".": ["gate-1-verdict.md"] if Path(p) == evidence else real(p))
    found = check._find_verdict(evidence, 1)
    assert found is not None and found.name == "gate-1-verdict.md"
    monkeypatch.setattr(check.os, "listdir", lambda p=".": ["GATE-1-VERDICT.md", "gate-1-verdict.md"] if Path(p) == evidence else real(p))
    assert check._find_verdict(evidence, 1).name == "GATE-1-VERDICT.md"  # tên mới trước
    monkeypatch.setattr(check.os, "listdir", lambda p=".": ["Gate-1-Verdict.md"] if Path(p) == evidence else real(p))
    assert check._find_verdict(evidence, 1) is None  # kiểu chữ lẫn không phải tên nào trong hai tên
    assert check._find_verdict(tmp_path / "không-có", 1) is None


def test_find_verdict_matches_gate_number(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    write_lf(evidence / "GATE-2-VERDICT.md", "x\n")
    assert check._find_verdict(evidence, 1) is None
    assert check._find_verdict(evidence, 2).name == "GATE-2-VERDICT.md"


# --- Luật `evidence-name` (FR3.3) ---------------------------------------------------------------------------


def test_evidence_name_note_only_from_effective_date(tmp_path, effective):
    old = make_sprint(tmp_path / "old")
    (old / "evidence").mkdir()
    write_lf(old / "evidence" / "gate-1-verdict.md", "x\n")
    assert _notes(old) == []  # created 2026-02-01 < ngày hiệu lực
    new = make_sprint(tmp_path / "new")
    _new_record_with(new, "gate-1-verdict.md", "analysis.md", "tk3-report.md", "REPORT-TK3.md")
    notes = _notes(new)
    flagged = " ".join(f.message for f in notes)
    assert len(notes) == 3, [f.render() for f in notes]
    assert "gate-1-verdict.md" in flagged and "analysis.md" in flagged and "tk3-report.md" in flagged
    assert "REPORT-TK3.md" not in flagged
    assert all(f.path.name == "PROGRESS.md" for f in notes)


def test_evidence_name_note_reported_at_created_line(tmp_path, effective):
    root = make_sprint(tmp_path)
    _new_record_with(root, "claims.md")
    notes = _notes(root)
    assert len(notes) == 1
    text = (root / "PROGRESS.md").read_text(encoding="utf-8").split("\n")
    assert text[notes[0].line - 1].startswith("created:")


def test_evidence_name_default_effective_date_is_placeholder():
    """Trong nhánh, ngày hiệu lực là hằng giữ chỗ (chốt ở TK19): chưa hồ sơ nào là hồ sơ mới."""
    assert c.NAMING_DATE_PLACEHOLDER == "9999-12-31"
    assert c.NAMING_EFFECTIVE_DATE == c.NAMING_DATE_PLACEHOLDER


def test_evidence_name_note_does_not_change_exit_code(tmp_path, effective, capsys):
    clean = make_sprint(tmp_path / "a")
    flagged = make_sprint(tmp_path / "b")
    _new_record_with(flagged, "gate-1-verdict.md")
    assert check.RULES["evidence-name"][0] == "Ghi chú"
    code_clean = check.main([str(clean)])
    code_flagged = check.main([str(flagged)])
    out = capsys.readouterr().out
    assert "evidence-name" in out
    assert code_clean == code_flagged == 0


def test_evidence_name_runs_without_include_evidence(tmp_path, effective):
    root = make_sprint(tmp_path)
    _new_record_with(root, "gate-1-verdict.md")
    assert len(_notes(root, include_evidence=False)) == 1
    assert len(_notes(root, include_evidence=True)) == 1


@pytest.mark.parametrize("bad", ["hôm qua", "21/11/2026", "2026-11-21T09:00", "2026-13-45x"], ids=["words", "dmy", "datetime", "garbage"])
def test_evidence_name_malformed_created_is_silent(tmp_path, effective, bad):
    """`created` sai định dạng: coi là hồ sơ cũ, không báo (hồ sơ cũ yên được ưu tiên)."""
    root = make_sprint(tmp_path)
    _rewrite(root / "PROGRESS.md", "created: 2026-02-01\n", f"created: {bad}\n")
    (root / "evidence").mkdir()
    write_lf(root / "evidence" / "gate-1-verdict.md", "x\n")
    assert _notes(root) == []


def test_evidence_name_missing_created_is_silent(tmp_path, effective):
    root = make_sprint(tmp_path)
    _rewrite(root / "PROGRESS.md", "created: 2026-02-01\n", "")
    (root / "evidence").mkdir()
    write_lf(root / "evidence" / "gate-1-verdict.md", "x\n")
    assert _notes(root) == []


def test_handoff_md_at_sprint_root_is_not_flagged(tmp_path, effective):
    root = make_sprint(tmp_path)
    _new_record_with(root, "GATE-1-VERDICT.md")
    write_lf(root / "HANDOFF.md", "# Bàn giao\n\nKhông có frontmatter.\n")
    report = check.check_paths([root])
    assert [f.render() for f in report.findings if f.path.name == "HANDOFF.md"] == []
    assert [f for f in report.findings if f.rule == "evidence-name"] == []


# --- Bảng tên (`EVIDENCE_NAMES`) ----------------------------------------------------------------------------


def test_evidence_names_table_shape():
    assert set(c.EVIDENCE_NAMES) == {"gate_verdict", "task_report", "plan_review", "research", "analysis", "claims"}
    for key, (new, old) in c.EVIDENCE_NAMES.items():
        assert isinstance(new, str) and isinstance(old, str), key
        re.compile(new)
        re.compile(old)


@pytest.mark.parametrize("name", ["tk6a-report.md", "TK3B-report.md", "TK2-REPORT.md", "tkP-report.md", "tk3.1-report.md", "tk2_report.md"])
def test_task_report_legacy_shapes_from_corpus(name):
    """Bốn dạng tên báo cáo việc có thật trong kho (cộng hai dạng gần) khớp mẫu tên cũ bằng `re.fullmatch`, và không khớp mẫu mới."""
    new, old = c.EVIDENCE_NAMES["task_report"]
    assert re.fullmatch(old, name), name
    assert not re.fullmatch(new, name), name


@pytest.mark.parametrize("name", ["REPORT-TK6a.md", "REPORT-TK3.md", "REPORT-TK10.1.md", "REPORT-TK8b.md"])
def test_task_report_new_name_accepts_letter_suffix(name):
    new, _ = c.EVIDENCE_NAMES["task_report"]
    assert re.fullmatch(new, name), name


@pytest.mark.parametrize("name", ["REPORT-TK6A.md", "REPORT-TK6ab.md", "report-tk6a.md", "REPORT-TK.md"])
def test_task_report_new_name_rejects_other_shapes(name):
    new, _ = c.EVIDENCE_NAMES["task_report"]
    assert not re.fullmatch(new, name), name


def test_gate_verdict_patterns_only_gates_one_and_two():
    new, old = c.EVIDENCE_NAMES["gate_verdict"]
    assert re.fullmatch(new, "GATE-2-VERDICT.md") and re.fullmatch(old, "gate-1-verdict.md")
    assert not re.fullmatch(new, "GATE-3-VERDICT.md") and not re.fullmatch(old, "gate-3-verdict.md")
    assert not re.fullmatch(new, "gate-1-verdict.md") and not re.fullmatch(old, "GATE-1-VERDICT.md")


def test_evidence_name_no_evidence_dir_or_subfolder_is_silent(tmp_path, effective):
    """Hồ sơ mới không có `evidence/` thì thôi; thư mục con tên kiểu cũ trong `evidence/` không phải file kèm, không báo."""
    root = make_sprint(tmp_path)
    _rewrite(root / "PROGRESS.md", "created: 2026-02-01", f"created: {NEW_DATE}")
    assert _notes(root) == []
    (root / "evidence" / "gate-1-verdict.md").mkdir(parents=True)
    assert _notes(root) == []


@pytest.mark.parametrize("key,name", [
    ("research", "RESEARCH-TK3-api.md"), ("research", "RESEARCH-chủ-đề.md"), ("research", "RESEARCH-Topic_X.md"),
    ("plan_review", "PLAN-REVIEW-v1-huong-B.md"), ("plan_review", "PLAN-REVIEW-Advisor.md"), ("plan_review", "PLAN-REVIEW-tech-reviewer.md"),
])
def test_new_topic_part_is_not_restricted_in_case_or_charset(tmp_path, effective, key, name):
    """NAMING mục 0 chỉ quy định tiền tố viết hoa: phần chủ đề/vai tự do, không bị ghi chú là kiểu cũ."""
    new, _ = c.EVIDENCE_NAMES[key]
    assert re.fullmatch(new, name), name
    root = make_sprint(tmp_path)
    _new_record_with(root, name)
    assert _notes(root) == []


@pytest.mark.parametrize("key,name", [
    ("research", "research-api.md"), ("research", "Research-api.md"), ("research", "research.md"),
    ("plan_review", "plan-review-opus.md"), ("plan_review", "Plan-Review-1.md"), ("plan_review", "plan-review.md"),
])
def test_legacy_prefix_case_still_flagged(tmp_path, effective, key, name):
    new, old = c.EVIDENCE_NAMES[key]
    assert re.fullmatch(old, name) and not re.fullmatch(new, name), name
    root = make_sprint(tmp_path)
    _new_record_with(root, name)
    assert len(_notes(root)) == 1
