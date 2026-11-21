"""SPR-35 TK5: new blocks and columns of the sprint templates (FR1.1-FR1.7, SC4) and their label keys.

The templates are the contract with `check`: a new column or section must not change how a rule reads a table
(the `vr-result-not-pass` rule finds the Result column by its header), and the optional sections must not become
required headings.
"""

from __future__ import annotations

import json
import re
import shutil

import pytest

import check
from conftest import REPO, write_lf
from test_check import rules_of
from test_check_result_cell import TABLE, build

TEMPLATES = REPO / "templates" / "sprint"
LABELS = REPO / "labels"
NEW_KEYS = {
    "heading.continuation": ("Tiếp nối", "Continuation"),
    "heading.after_gate_2": ("Sau Cổng 2", "After Gate 2"),
    "field.inherits": ("Kế thừa", "Inherits"),
    "field.read_order": ("Đọc theo thứ tự", "Read in this order"),
    "field.source_of_truth": ("Nguồn sự thật", "Source of truth"),
    "field.where_now": ("Đang ở", "Where things stand"),
    "field.next_task": ("Việc kế", "Next task"),
    "field.do_not_redo": ("Đừng làm lại", "Do not redo"),
    "field.env_traps": ("Bẫy môi trường mới gặp", "Environment traps found"),
    "field.execution_env": ("Môi trường thực thi", "Execution environment"),
    "column.threshold": ("Ngưỡng", "Threshold"),
    "column.measure_env": ("Môi trường đo", "Measuring environment"),
    "column.if_unmeasurable": ("Khi không đo được", "If it cannot be measured"),
    "column.consequence": ("Hệ quả cho thực thi", "Consequence for execution"),
    "column.environment": ("Môi trường", "Environment"),
    "column.checkpoint": ("Mốc", "Checkpoint"),
    "column.checked_at": ("Thời điểm", "Checked at"),
}
VIETNAMESE = re.compile("[À-ỹ]")  # any letter outside ASCII in the Latin blocks Vietnamese uses
HARNESS_NAMES = re.compile(r"claude|codex|antigravity|subagent", re.IGNORECASE)


def read(name: str) -> str:
    return (TEMPLATES / name).read_bytes().decode("utf-8")


def section(text: str, heading: str, level: str = "## ") -> str:
    """Body of the first `<level>...<heading>...` section (up to the next heading of the same or higher level)."""
    lines = text.split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith(level) and heading in ln)
    end = len(lines)
    depth = len(level.strip())
    for j in range(start + 1, len(lines)):
        if re.match(r"#{1,%d} " % depth, lines[j]):
            end = j
            break
    return "\n".join(lines[start + 1:end])


def table_header(text: str, anchor: str) -> list:
    """Cells of the first table header row that follows the first line containing `anchor`."""
    lines = text.split("\n")
    start = next(i for i, ln in enumerate(lines) if anchor in ln)
    row = next(ln for ln in lines[start:] if ln.startswith("|"))
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def roles_block(text: str) -> str:
    return text.split("roles:\n", 1)[1].split("\ncreated:", 1)[0]


# --- FR1.1: Tiếp nối ------------------------------------------------------------------------------------


def test_progress_template_has_continuation_block_with_six_fields():
    text = read("PROGRESS.md")
    assert text.index("> **Kết luận:**") < text.index("## Tiếp nối") < text.index("## 1. Bảng trạng thái việc")
    body = section(text, "Tiếp nối")
    for label in ("Đọc theo thứ tự", "Nguồn sự thật", "Đang ở", "Việc kế", "Đừng làm lại", "Bẫy môi trường mới gặp"):
        assert f"**{label}:**" in body, label
    for word in ("SPEC", "PLAN", "REPORT", "Git"):  # source-of-truth order
        assert word in body, word


def test_sprint_template_has_three_continuation_lines():
    text = read("SPRINT.md")
    body = section(text, "PROGRESS")
    for label in ("Đang ở", "Việc kế", "Đừng làm lại"):
        assert len(re.findall(rf"^- \*\*{label}:\*\*", body, flags=re.M)) == 1, label
    assert "**Đọc theo thứ tự:**" not in body  # the small size keeps three lines, not six


# --- FR1.2, FR1.3: SPEC ---------------------------------------------------------------------------------


def test_spec_template_sc_table_has_six_columns():
    assert table_header(read("SPEC.md"), "SPEC có 1 **success criterion**") == [
        "Mã", "Tiêu chí", "Cách đo", "Ngưỡng", "Môi trường đo", "Khi không đo được"]


def test_spec_template_has_inherits_line():
    body = section(read("SPEC.md"), "1. Bối cảnh")
    assert re.search(r"^- \*\*Kế thừa:\*\*", body, flags=re.M)
    assert "Không có." in body.split("**Kế thừa:**", 1)[1].split("\n", 1)[0]


def test_spec_template_cq_table_has_consequence_column():
    header = table_header(read("SPEC.md"), "SPEC có 1 **clarification question**")
    assert "Hệ quả cho thực thi" in header and header[0] == "Mã" and header[-1] == "Người quyết · trạng thái"
    assert "KHI trượt THÌ" in section(read("SPEC.md"), "3. Yêu cầu chức năng")  # FR1.3: the FR note


# --- FR1.4: PLAN ----------------------------------------------------------------------------------------


def test_plan_template_has_execution_env_box():
    body = section(read("PLAN.md"), "Ràng buộc chung")
    assert "**Môi trường thực thi:**" in body
    box = body.split("**Môi trường thực thi:**", 1)[1]
    for word in ("được ghi", "không được đụng", "ngoài sandbox", "nạp bộ skill", "shell", "đúng mã"):
        assert word in box, word
    text = read("PLAN.md")
    assert text.index("## Việc") < text.index("## Sau Cổng 2") < text.index("## Rủi ro")


def test_plan_template_after_gate_2_is_optional_for_check(tmp_path):
    root = tmp_path / "sprint"  # the four files of a medium sprint, without the SPRINT.md and TASK.md templates
    root.mkdir()
    for name in ("SPEC.md", "PLAN.md", "PROGRESS.md", "REPORT.md"):
        shutil.copyfile(TEMPLATES / name, root / name)
    plan = root / "PLAN.md"
    text = plan.read_bytes().decode("utf-8")
    assert "## Sau Cổng 2" in text
    with_section = check.check_paths([root])
    assert rules_of(with_section) == set(), [f.render() for f in with_section.findings]
    start = text.index("## Sau Cổng 2")
    write_lf(plan, text[:start] + text[text.index("## Rủi ro"):])
    without = check.check_paths([root])
    assert rules_of(without) == set(), [f.render() for f in without.findings]


# --- FR1.5: REPORT --------------------------------------------------------------------------------------


def test_report_template_vr_table_has_nine_columns_and_result_header():
    text = read("REPORT.md")
    header = table_header(text, "REPORT có 1 **verification result**")
    assert len(header) == 9
    assert header.count("Kết quả") == 1  # the header the vr-result-not-pass rule reads: same words
    assert header[:4] == ["Mã", "Kiểm cái gì", "Lệnh / thao tác", "Kết quả"]
    assert {"Môi trường", "Mốc", "Thời điểm"} <= set(header)
    assert header[-1] == "Bằng chứng"  # the last cell stays the evidence/reason cell the rule reads for "Không áp dụng"
    summary = text.split("## Tóm tắt cho người không chuyên", 1)[1].split("\n## ", 1)[0]
    assert summary.count("Gợi ý") == 3  # three prompts in the comment for the plain-language summary


def nine_column(text: str, new_after_evidence: bool = False) -> str:
    """Rewrite the six-column VR table of a build() fixture into the nine-column shape of the template."""
    header = TABLE["vi"]["header"]
    out = []
    for line in text.split("\n"):
        if line == header:
            new = "| Môi trường | Mốc | Thời điểm |"
            out.append(header + new[1:] if new_after_evidence else header.replace("| Người kiểm | Bằng chứng |", "| Người kiểm " + new + " Bằng chứng |"))
        elif line == "|---|---|---|---|---|---|":
            out.append("|---|---|---|---|---|---|---|---|---|")
        elif line.startswith("| VR1 "):
            cells = " máy dev | `abc1234` | 2026-11-21 10:00 +07 |"
            out.append(line + cells if new_after_evidence else line.replace("| QA · agent-f | ", "| QA · agent-f |" + cells + " "))
        else:
            out.append(line)
    return "\n".join(out)


@pytest.mark.parametrize("result,fires", [("Chưa chạy", True), ("Đạt", False)])
def test_vr_result_rule_still_fires_with_new_columns(tmp_path, result, fires):
    root, _ = build(tmp_path, "vi", result)
    path = root / "REPORT.md"
    before = path.read_bytes().decode("utf-8")
    wide = nine_column(before)
    assert wide != before and "| Thời điểm |" in wide and "| `abc1234` |" in wide
    write_lf(path, wide)
    report = check.check_paths([root])
    assert ("vr-result-not-pass" in rules_of(report)) is fires, [f.render() for f in report.findings]


def test_vr_not_applicable_without_reason_still_fires_with_new_columns(tmp_path):
    """The template order keeps the evidence/reason cell last, so a bare "Không áp dụng" is still reported."""
    root, _ = build(tmp_path, "vi", "Không áp dụng", last="")
    path = root / "REPORT.md"
    write_lf(path, nine_column(path.read_bytes().decode("utf-8")))
    report = check.check_paths([root])
    assert "vr-result-not-pass" in rules_of(report), [f.render() for f in report.findings]


def test_known_limit_new_columns_after_evidence_hide_missing_reason(tmp_path):
    """Records a LIMIT of `check`, not a requirement: with the three new columns AFTER the evidence column the rule reads the
    last cell as the reason, so a bare "Không áp dụng" goes unreported. This is why the template puts them before it."""
    root, _ = build(tmp_path, "vi", "Không áp dụng", last="")
    path = root / "REPORT.md"
    write_lf(path, nine_column(path.read_bytes().decode("utf-8"), new_after_evidence=True))
    report = check.check_paths([root])
    assert "vr-result-not-pass" not in rules_of(report), [f.render() for f in report.findings]


# --- FR1.6, FR1.7 ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["SPEC.md", "PLAN.md", "PROGRESS.md", "REPORT.md", "SPRINT.md"])
def test_templates_roles_have_gate_delegate(name):
    assert re.search(r"^  gate-delegate: \[4, [\w-]+\]$", roles_block(read(name)), flags=re.M)


def test_new_label_keys_exist_in_vi_and_en():
    vi = json.loads((LABELS / "vi.json").read_text(encoding="utf-8"))
    en = json.loads((LABELS / "en.json").read_text(encoding="utf-8"))
    for key, (vi_label, en_label) in NEW_KEYS.items():
        assert vi.get(key) == vi_label, key
        assert en.get(key) == en_label, key
        assert not VIETNAMESE.search(en[key]), key
    assert set(vi) == set(en)


def test_new_template_text_names_no_harness():
    for name in ("SPEC.md", "PLAN.md", "PROGRESS.md", "REPORT.md", "SPRINT.md"):
        assert not HARNESS_NAMES.search(read(name)), name
