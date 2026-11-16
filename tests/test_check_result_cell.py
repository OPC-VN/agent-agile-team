"""Tests for the future rule `vr-result-not-pass` (SPR-34, RQ-137): a VR row whose Result cell says "not run" (or "not
applicable" with no reason) may not stand under `verdict: pass` / `gate_2: pass`.

Written before the rule exists (TK3): every negative fails because the rule key is absent; every control already passes
because it expects NO new key. Words are literals on purpose; nothing is read back from labels/*.json.

The fixtures are copies of tests/fixtures/valid (Vietnamese) and tests/fixtures/en/valid (English) whose REPORT.md
verification table and frontmatter are edited. Both valid fixtures are clean (empty rule set, exit 0).
"""

from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path

import pytest

import check
from conftest import write_lf
from test_check import FIXTURES, VALID as VI_VALID, rules_of, two_part_sprint

EN_VALID = FIXTURES / "en" / "valid"

# The valid fixtures are dated February 2026 and the sprint sample January 2026; date-gated rules start on 2026-11-13, so
# every cloned record is moved to 2026-11-14.. (order preserved) before the rule sees it.
DATES = {"2026-02-01": "2026-11-14", "2026-02-02": "2026-11-15", "2026-01-20": "2026-11-14"}


SUMMARY = {
    "vi": ("Tóm tắt cho người không chuyên", "Kế toán bấm một nút là có file danh sách đơn."),
    "en": ("Summary for non-specialists", "An accountant clicks one button and gets a file with the order list."),
}
ASK_COUNT = {"vi": "Số lượt Đức phải trả lời", "en": "Number of turns the human had to answer"}


def redate(text: str) -> str:
    for old, new in DATES.items():
        text = text.replace(old, new)
    return text
KEY = "vr-result-not-pass"

# (document language, words language, not-run word, not-applicable word): the four combinations of FR4.2.
COMBOS = [
    pytest.param("vi", "Chưa chạy", "Không áp dụng", id="vi-doc-vi-words"),
    pytest.param("en", "Not run", "Not applicable", id="en-doc-en-words"),
    pytest.param("en", "Chưa chạy", "Không áp dụng", id="en-doc-vi-words"),
    pytest.param("vi", "Not run", "Not applicable", id="vi-doc-en-words"),
]

# Table shape of the valid fixture REPORT.md, per document language.
TABLE = {
    "vi": {
        "header": "| Mã | Kiểm cái gì | Lệnh / thao tác | Kết quả | Người kiểm | Bằng chứng |",
        "result": "Kết quả",
        "pass": "Đạt",
        "code": "Mã",
        "row": "| VR1 (test xuất) | SC1, FR1.1 | `pytest` | Đạt | QA · agent-f | 4 passed |",
    },
    "en": {
        "header": "| Code | What is checked | Command / action | Result | Checked by | Evidence |",
        "result": "Result",
        "pass": "Pass",
        "code": "Code",
        "row": "| VR1 (export test) | SC1, FR1.1 | `pytest` | Pass | QA · agent-f | 4 passed |",
    },
}


def build(
    tmp_path: Path,
    doc: str,
    result: str,
    *,
    last: str = "4 passed",
    verdict: str | None = "pass",
    gate_2: str | None = "pending",
    close_gate_2: bool = False,
    header_result: str | None = None,
    first_header: str | None = None,
    result_last: bool = False,
    extra_rows: tuple[str, ...] = (),
) -> tuple[Path, int]:
    """Copy the valid fixture of `doc` into tmp_path, rewrite REPORT.md; return (root, 1-based line of the VR1 row)."""
    root = tmp_path / "sprint"
    shutil.copytree(VI_VALID if doc == "vi" else EN_VALID, root)
    for other in root.glob("*.md"):
        body = redate(other.read_bytes().decode("utf-8"))
        if other.name in ("SPEC.md", "PLAN.md"):  # plain-summary is date-gated: give the redated copy its section
            heading, sentence = SUMMARY[doc]
            body = body.replace("\n## ", f"\n## {heading}\n\n{sentence}\n\n## ", 1)
        write_lf(other, body)
    shape = TABLE[doc]
    path = root / "REPORT.md"
    text = path.read_bytes().decode("utf-8")
    assert shape["header"] in text and shape["row"] in text
    header = shape["header"].replace(f"| {shape['result']} |", f"| {header_result or shape['result']} |", 1)
    if first_header is not None:
        header = header.replace(f"| {shape['code']} |", f"| {first_header} |", 1)
    cells = [c.strip() for c in shape["row"].strip("|").split("|")]
    cells[3] = result
    cells[5] = last
    if result_last:
        header = "| " + " | ".join(c.strip() for c in header.strip("|").split("|")[:4]) + " |"
        cells = cells[:4]
    row = "| " + " | ".join(cells) + " |"
    # "|  |" for an empty last cell, so the row still ends with a pipe
    row = row.replace("|  |", "| |") if row.endswith("|  |") else row
    new = text.replace(shape["header"], header, 1).replace(shape["row"], "\n".join((row,) + extra_rows), 1)
    if result_last:
        new = new.replace("|---|---|---|---|---|---|", "|---|---|---|---|", 1)
    new = new.replace("verdict: pass", f"verdict: {verdict}" if verdict is not None else "@@DROP", 1)
    new = new.replace("gate_2: pending", f"gate_2: {gate_2}" if gate_2 is not None else "@@DROP", 1)
    new = new.replace("@@DROP\n", "")
    if close_gate_2:
        new = new.replace("gate_2_at: null", "gate_2_at: 2026-11-16 10:00 +07", 1)
        new = new.replace("gate_2_quote: null", 'gate_2_quote: "ok"', 1)
    new = new.rstrip("\n") + f"\n\n- **{ASK_COUNT[doc]}:** 0\n"  # report-missing-ask-count is date-gated too
    write_lf(path, new)
    row_line = new.split("\n").index(row) + 1
    return root, row_line


def run(root: Path):
    report = check.check_paths([root])
    return report, rules_of(report)


def hits(report) -> list:
    return [f for f in report.findings if f.rule == KEY]


# --- the fixtures themselves are the baseline ----------------------------------------------------------------


@pytest.mark.parametrize("doc", ["vi", "en"])
def test_unmodified_valid_fixture_is_clean_baseline(tmp_path, doc):
    root, _ = build(tmp_path, doc, TABLE[doc]["pass"])
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]
    assert report.exit_code == 0


# --- negatives: pass is claimed and a row is not run / not applicable without a reason -----------------------


@pytest.mark.parametrize("doc, word, _na", COMBOS)
def test_not_run_under_verdict_pass_fires_in_every_language_combination(tmp_path, doc, word, _na):
    root, line = build(tmp_path, doc, word)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    found = hits(report)
    assert len(found) == 1 and found[0].line == line
    assert "VR1" in found[0].message and word in found[0].message
    assert report.exit_code == 0  # a Should fix does not change the exit code


@pytest.mark.parametrize("doc, _word, na", COMBOS)
def test_bare_not_applicable_with_empty_last_cell_under_verdict_pass_fires(tmp_path, doc, _word, na):
    root, line = build(tmp_path, doc, na, last="")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    found = hits(report)
    assert len(found) == 1 and found[0].line == line
    assert "VR1" in found[0].message and na in found[0].message and "lý do" in found[0].message
    assert report.exit_code == 0


def test_not_run_and_missing_reason_messages_differ(tmp_path):
    a, _ = run(build(tmp_path / "a", "vi", "Chưa chạy")[0])
    b, _ = run(build(tmp_path / "b", "vi", "Không áp dụng", last="")[0])
    assert len(hits(a)) == 1 and len(hits(b)) == 1
    assert "lý do" not in hits(a)[0].message
    assert hits(a)[0].message != hits(b)[0].message


@pytest.mark.parametrize("doc, _word, na", COMBOS)
def test_bare_not_applicable_in_the_last_column_fires(tmp_path, doc, _word, na):
    """The Result cell is the last cell of the row: there is no other cell to carry a reason."""
    root, line = build(tmp_path, doc, na, result_last=True)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_one_finding_per_row_each_at_its_own_line(tmp_path):
    extra = ("| VR2 (export test 2) | SC1 | `pytest -k b` | Chưa chạy | QA · agent-f | |",)
    root, line = build(tmp_path, "vi", "Chưa chạy", extra_rows=extra)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert sorted(f.line for f in hits(report)) == [line, line + 1]


def test_gate_2_pass_alone_triggers_with_verdict_conditional_pass(tmp_path):
    root, line = build(tmp_path, "vi", "Chưa chạy", verdict="conditional_pass", gate_2="pass", close_gate_2=True)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_bold_not_run_fires(tmp_path):
    root, line = build(tmp_path, "vi", "**Chưa chạy**")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_not_run_followed_by_more_words_still_fires(tmp_path):
    """The next character is a space, so the leading word is complete."""
    root, line = build(tmp_path, "vi", "Chưa chạy đủ")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_english_not_run_with_a_colon_fires(tmp_path):
    root, line = build(tmp_path, "en", "Not run: no browser")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_nfd_encoded_not_run_fires(tmp_path):
    nfd = unicodedata.normalize("NFD", "Chưa chạy")
    assert nfd != "Chưa chạy"
    root, line = build(tmp_path, "vi", nfd)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


@pytest.mark.parametrize("doc, header", [("vi", "Kết quả và giới hạn"), ("en", "Result and limits")])
def test_result_header_with_a_tail_still_marks_the_column(tmp_path, doc, header):
    word = "Chưa chạy" if doc == "vi" else "Not run"
    root, line = build(tmp_path, doc, word, header_result=header)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_sprint_kind_document_with_a_vr_table_is_read(tmp_path):
    root = tmp_path / "sprint"
    root.mkdir()
    text = redate(two_part_sprint()).replace("verdict: pending", "verdict: pass", 1)
    assert "verdict: pass" in text and "| Chưa chạy |" in text
    write_lf(root / "SPRINT.md", text)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    row = "| VR1 (test câu báo lỗi) | SC1 | `pytest tests/test_ui.py` | Chưa chạy | Tech Reviewer · agent-d |"
    assert [f.line for f in hits(report)] == [text.split("\n").index(row) + 1]


def test_bare_not_applicable_token_with_empty_last_cell_fires(tmp_path):
    root, line = build(tmp_path, "vi", "NOT_APPLICABLE", last="")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


# --- controls: the same shapes that must stay silent ------------------------------------------------------------

# (key, value, expected exact rule set) for a not-run row. The valid fixture is clean, so the set is empty unless the value
# itself is already a finding of an existing rule (verified against the unmodified fixture).
VERDICT_CONTROLS = [
    ("verdict", "conditional_pass", set()),
    ("verdict", "fail", set()),
    ("verdict", "pending", set()),
    ("verdict", None, {"frontmatter-key-missing"}),
    ("verdict", "approved", {"frontmatter-value"}),
    ("verdict", "Đạt", {"frontmatter-value"}),
    ("gate_2", "conditional_pass", set()),
    ("gate_2", "fail", set()),
    ("gate_2", "pending", set()),
    ("gate_2", None, {"frontmatter-key-missing"}),
    ("gate_2", "approved", {"frontmatter-value"}),
    ("gate_2", "Đạt", {"frontmatter-value"}),
]


@pytest.mark.parametrize("doc, word, _na", COMBOS)
@pytest.mark.parametrize("key, value, expected", VERDICT_CONTROLS, ids=[f"{k}-{v}" for k, v, _ in VERDICT_CONTROLS])
def test_not_run_row_stays_silent_unless_pass_is_claimed(tmp_path, doc, word, _na, key, value, expected):
    if key == "verdict":
        root, _ = build(tmp_path, doc, word, verdict=value, gate_2="pending")
    else:
        root, _ = build(tmp_path, doc, word, verdict="pending", gate_2=value, close_gate_2=True)
    report, rules = run(root)
    assert rules == expected, [f.render() for f in report.findings]


@pytest.mark.parametrize("doc", ["vi", "en"])
@pytest.mark.parametrize(
    "cell",
    [
        "Not runnable",
        "Passed; not run on mac",
        "Đạt; bước 2 chưa chạy",
        "Chưa chứng minh",
        "N/A",
        "Skipped",
        "",
    ],
    ids=["not-runnable", "word-later-en", "word-later-vi", "unproven", "n-a", "skipped", "empty"],
)
def test_cells_that_are_not_a_leading_not_run_word_stay_silent_under_pass(tmp_path, doc, cell):
    root, _ = build(tmp_path, doc, cell)
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]
    assert report.exit_code == 0


@pytest.mark.parametrize("doc", ["vi", "en"])
@pytest.mark.parametrize(
    "cell, last",
    [
        ("Không áp dụng — no browser", ""),
        ("Not applicable: no browser", ""),
        ("NOT_APPLICABLE — reason", ""),
        ("Không áp dụng", "no browser on this host"),
        ("Not applicable", "no browser on this host"),
        ("NOT_APPLICABLE", "reason in the last cell"),
    ],
    ids=["vi-reason-in-cell", "en-reason-in-cell", "token-reason-in-cell", "vi-last-filled", "en-last-filled", "token-last-filled"],
)
def test_not_applicable_with_a_reason_stays_silent_under_pass(tmp_path, doc, cell, last):
    root, _ = build(tmp_path, doc, cell, last=last)
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]
    assert report.exit_code == 0


@pytest.mark.parametrize("doc, word, _na", COMBOS)
def test_table_without_a_result_column_gives_no_finding(tmp_path, doc, word, _na):
    root, _ = build(tmp_path, doc, word, header_result="Trạng thái" if doc == "vi" else "Status")
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]


@pytest.mark.parametrize("doc, word, _na", COMBOS)
def test_vr_table_that_check_does_not_register_gives_no_finding(tmp_path, doc, word, _na):
    """A second table whose first header cell is not Mã/Code is never read, even with a Result column and a VR code."""
    head = "| Mục | Kết quả |" if doc == "vi" else "| Item | Result |"
    extra = f"\n\nGhi chú ngoài bảng VR:\n\n{head}\n|---|---|\n| VR9 (khác) | {word} |\n"
    root, _ = build(tmp_path, doc, TABLE[doc]["pass"])
    path = root / "REPORT.md"
    text = path.read_bytes().decode("utf-8")
    write_lf(path, text.replace("\n## 2.", extra + "\n## 2.", 1))
    report, rules = run(root)
    assert KEY not in rules, [f.render() for f in report.findings]  # "contains": the extra table may raise baseline rules


@pytest.mark.parametrize("doc, word, _na", COMBOS)
def test_first_header_not_code_unregisters_the_main_table(tmp_path, doc, word, _na):
    """The registered table is the one whose first header cell is Mã/Code; rename it and the rule has nothing to read."""
    root, _ = build(tmp_path, doc, word, first_header="Mục" if doc == "vi" else "Item")
    _, rules = run(root)
    assert KEY not in rules  # "contains": the unregistered VR1 legitimately raises existing rules (report-sc-without-vr...)


@pytest.mark.parametrize("doc, word, _na", COMBOS)
def test_only_finding_of_this_rule_exits_zero(tmp_path, doc, word, _na):
    root, _ = build(tmp_path, doc, word)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert report.exit_code == 0


# --- normalisation and the cheap notes --------------------------------------------------------------------------


@pytest.mark.parametrize("cell", ["chưa chạy", "CHƯA CHẠY", "NOT RUN", "not run"], ids=["vi-lower", "vi-upper", "en-upper", "en-lower"])
def test_case_of_the_cell_does_not_matter(tmp_path, cell):
    root, line = build(tmp_path, "vi", cell)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


@pytest.mark.parametrize("header", ["**Kết quả**", "RESULT", "`Result`", "_Kết quả_"], ids=["bold", "upper", "code", "italic"])
def test_header_markup_and_case_are_normalised(tmp_path, header):
    root, line = build(tmp_path, "vi", "Chưa chạy", header_result=header)
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


@pytest.mark.parametrize("header", ["Resultant", "Kết quảx"])
def test_header_that_only_starts_with_the_word_is_not_the_result_column(tmp_path, header):
    root, _ = build(tmp_path, "vi", "Chưa chạy", header_result=header)
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]


def test_only_the_first_result_column_counts(tmp_path):
    """Two Result columns: the first holds a pass word, the second holds not-run; only the first is read, so silent."""
    root, _ = build(tmp_path, "vi", "Đạt")
    path = root / "REPORT.md"
    text = path.read_bytes().decode("utf-8")
    old = "| Kết quả | Người kiểm | Bằng chứng |"
    assert old in text
    text = text.replace(old, "| Kết quả | Kết quả lần 2 | Bằng chứng |", 1)
    old = "| Đạt | QA · agent-f | 4 passed |"
    assert old in text
    text = text.replace(old, "| Đạt | Chưa chạy | 4 passed |", 1)
    write_lf(path, text)
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]


def test_trailing_punctuation_after_bare_not_applicable_still_fires(tmp_path):
    root, line = build(tmp_path, "vi", "Không áp dụng.", last="")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


@pytest.mark.parametrize("name", ["SPEC.md", "PLAN.md"])
def test_spec_or_plan_kind_document_with_a_vr_table_is_not_read(tmp_path, name):
    root, _ = build(tmp_path, "vi", TABLE["vi"]["pass"])
    path = root / name
    text = path.read_bytes().decode("utf-8")
    table = (
        "\n\n| Mã | Kiểm cái gì | Lệnh / thao tác | Kết quả | Người kiểm | Bằng chứng |\n|---|---|---|---|---|---|\n"
        "| VR7 (ngoài REPORT) | SC1 | `pytest` | Chưa chạy | QA · agent-f | |\n"
    )
    write_lf(path, text.rstrip("\n") + table)
    _, rules = run(root)
    assert KEY not in rules  # "contains": the stray VR table may raise other existing rules in a SPEC/PLAN


def _rewrite_command_cell(root: Path, new_cell: str) -> None:
    path = root / "REPORT.md"
    text = path.read_bytes().decode("utf-8")
    old = "| `pytest` |"
    assert old in text
    write_lf(path, text.replace(old, f"| {new_cell} |", 1))


def test_pipe_inside_code_span_before_result_column_does_not_shift_it(tmp_path):
    root, line = build(tmp_path, "vi", "Chưa chạy")
    _rewrite_command_cell(root, "`a|b`")
    report, rules = run(root)
    assert rules == {KEY}, [f.render() for f in report.findings]
    assert [f.line for f in hits(report)] == [line]


def test_not_run_word_inside_a_code_span_with_pipe_is_not_the_result_cell(tmp_path):
    root, _ = build(tmp_path, "vi", TABLE["vi"]["pass"])
    _rewrite_command_cell(root, "`echo|Chưa chạy`")
    report, rules = run(root)
    assert rules == set(), [f.render() for f in report.findings]
