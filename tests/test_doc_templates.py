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


# --- SPR-35 TK6: add-on templates (FR2.1-FR2.5, FR3.1, FR3.4) ---------------------------------------------

TEMPLATES_ROOT = REPO / "templates"
ADDONS = {
    "HANDOFF.md": TEMPLATES_ROOT / "sprint" / "HANDOFF.md",
    "ANALYSIS.md": TEMPLATES_ROOT / "sprint" / "ANALYSIS.md",
    "CLAIMS.md": TEMPLATES_ROOT / "sprint" / "CLAIMS.md",
    "ROADMAP.md": TEMPLATES_ROOT / "registry" / "ROADMAP.md",
}


def addon(name: str) -> str:
    return ADDONS[name].read_bytes().decode("utf-8")


def templates_readme() -> str:
    return (TEMPLATES_ROOT / "README.md").read_bytes().decode("utf-8")


def test_addon_templates_exist():
    for name, path in ADDONS.items():
        assert path.is_file(), name


def test_addon_templates_pass_check(tmp_path):
    """Each add-on template, alone in its folder, gives no Chặn and no Phải sửa (`check` knows the names `handoff` and `roadmap` since TK6.1, so no Ghi chú either; pinned in test_addon_docs.py).

    ANALYSIS.md and CLAIMS.md carry no `doc:` key, so `check` reads no document kind from their frontmatter and applies
    only the general rules on codes; their structure is pinned by test_addon_headings_follow_spec."""
    for name, path in ADDONS.items():
        root = tmp_path / name.replace(".", "_")
        root.mkdir()
        shutil.copyfile(path, root / name)
        report = check.check_paths([root])
        bad = [f.render() for f in report.findings if f.level in ("Chặn", "Phải sửa")]
        assert bad == [], (name, bad)


def test_handoff_has_give_and_return_parts():
    text = addon("HANDOFF.md")
    headings = [ln[3:].strip() for ln in text.split("\n") if ln.startswith("## ")]
    assert headings == ["Giao", "Trả"]
    give = section(text, "Giao")
    assert len(re.findall(r"^[1-7]\. ", give, flags=re.M)) == 7  # seven numbered cells
    back = section(text, "Trả")
    for label in ("Đã đổi gì", "Cách chạy", "Hoàn tác", "Bằng chứng"):
        assert f"**{label}:**" in back, label
    assert "Giao → làm → Trả" in text.split("## Giao", 1)[0]  # three-line diagram in the head comment
    assert "Trước khi giao" in text.split("## Giao", 1)[0]


def test_handoff_give_part_at_most_40_lines():
    assert len(section(addon("HANDOFF.md"), "Giao").strip("\n").split("\n")) <= 40


FIXED_CHECK_BLOCK = [
    "Bốn kết quả: Đạt · Không đạt · Chưa chạy · Không áp dụng (kèm lý do); hai kết quả cuối không bao giờ là Đạt.",
    "Bằng chứng = lệnh + kết quả + commit + máy và giờ.",
    "Viết test hỏng trước khi viết mã.",
    "Chứng minh đang chạy đúng mã (đường thư mục và commit).",
    "Chạy cả bộ test trước khi báo xong.",
    "Gặp việc không đảo ngược, secret, ngoài phạm vi thư mục được ghi, hay giả định của kế hoạch sai: dừng, ghi lý do vào phần Trả, không đoán.",
]


def fixed_check_block(text: str) -> list:
    lines = text.split("\n")
    start = next(i for i, ln in enumerate(lines) if "Khối kiểm" in ln and ln.startswith("1") is False and "**" in ln)
    block = []
    for ln in lines[start + 1:]:
        if not ln.startswith(">"):
            if block:
                break
            continue
        block.append(ln)
    return block


def test_handoff_check_block_at_most_10_lines():
    block = fixed_check_block(addon("HANDOFF.md"))
    assert 1 <= len(block) <= 10
    assert [ln[1:].strip() for ln in block] == FIXED_CHECK_BLOCK


def test_addon_templates_name_no_harness_tool():
    for name in ADDONS:
        assert not HARNESS_NAMES.search(addon(name)), name


def test_addon_headings_follow_spec():
    analysis = [ln[3:].strip() for ln in addon("ANALYSIS.md").split("\n") if ln.startswith("## ")]
    assert len(analysis) == 6
    for word, heading in zip(("Kết luận", "nguồn", "an toàn", "Đánh giá", "tiên quyết", "khuyến nghị"), analysis):
        assert word.lower() in heading.lower(), (word, heading)
    claims = addon("CLAIMS.md")
    assert table_header(claims, "## Khẳng định đã kiểm") == ["Số", "Khẳng định", "Bằng chứng"]
    assert "## Chưa kiểm" in claims.split(chr(10))
    assert table_header(claims, "## Chưa kiểm")[0] == "Số"
    roadmap = addon("ROADMAP.md")
    assert re.search(r"^doc: roadmap$", roadmap, flags=re.M)
    assert len([ln for ln in roadmap.split("\n") if ln.startswith("## ")]) == 7


def test_init_does_not_scaffold_addons(tmp_path):
    import init
    for flags in ([], ["--sprint", "alpha", "--size", "medium"], ["--sprint", "beta", "--size", "small"],
                  ["--sprint", "gamma", "--tiny"]):
        extra = ["--title", "Goal"] if flags else []
        assert init.main([str(tmp_path), "--apply", "--date", "2026-11-21", *flags, *extra]) == 0
    names = {p.name for p in tmp_path.rglob("*") if p.is_file()}
    assert {"REQUESTS.md", "SPRINTS.md", "SPECS.md", "TASK.md", "SPRINT.md", "SPEC.md", "PLAN.md", "PROGRESS.md",
            "REPORT.md"} <= names  # the run really scaffolded files, so the disjoint check below is not vacuous
    assert names.isdisjoint(ADDONS), names & set(ADDONS)


def test_templates_readme_lists_every_template_file():
    readme = templates_readme()
    for folder in ("sprint", "registry", "project"):
        for path in sorted((TEMPLATES_ROOT / folder).iterdir()):
            assert f"`{folder}/{path.name}`" in readme, f"{folder}/{path.name}"


def naming_rows() -> list:
    readme = templates_readme()
    rows = []
    for ln in readme.split("\n"):
        if ln.startswith("|") and "`" in ln:
            rows.append(ln)
    return rows


def cells(row: str) -> list:
    return [c.strip() for c in row.strip().strip("|").split("|")]


OLD_NAMES = {
    "gate_verdict": "`gate-<N>-verdict.md`",
    "task_report": "`tk<n>-report.md`, `TK<n>-REPORT.md`",
    "plan_review": "`<vai>-plan-review.md`, `plan-review.md`, `plan-review-<vai>.md`",
    "research": "`research.md`, `research-<chủ-đề>.md`",
    "analysis": "`analysis.md`",
    "claims": "`claims.md`",
}


def test_naming_table_matches_evidence_names():
    import _common
    rows = naming_rows()
    for key in _common.EVIDENCE_NAMES:
        hit = [ln for ln in rows if f"`{key}`" in ln]
        assert len(hit) == 1, key
        key_cell, new, old, where = cells(hit[0])
        assert new == f"`{_common.EVIDENCE_NAME_FORMS[key]}`", key
        assert old == OLD_NAMES[key], key
        assert where == "`evidence/`", key


def test_naming_table_handoff_and_roadmap_rows_are_separate():
    rows = naming_rows()
    handoff = [cells(ln) for ln in rows if ln.startswith("| (ngoài `EVIDENCE_NAMES`) | `HANDOFF.md`")]
    roadmap = [cells(ln) for ln in rows if ln.startswith("| (ngoài `EVIDENCE_NAMES`) | `ROADMAP.md`")]
    assert len(handoff) == 1 and len(roadmap) == 1
    assert handoff[0][2] == "Không có" and "CQ7" not in handoff[0][2]
    assert handoff[0][3] == "gốc thư mục sprint"
    assert roadmap[0][2] == "Không có" and roadmap[0][3] == "gốc thư mục hồ sơ chương trình"
    assert not any("`HANDOFF.md`, `ROADMAP.md`" in ln for ln in rows)


def test_naming_table_distinguishes_brief_and_handoff():
    readme = templates_readme()
    row = next(ln for ln in readme.split("\n") if ln.startswith("| `sprint/BRIEF.md`"))
    assert "HANDOFF.md" in row and "người" in row.lower()
    assert "core.md" in readme and "VERIFICATION" in readme and "HANDOFF" in readme


MAPPING_ROWS = {
    "PLAN": "`PLAN.md`",
    "CHANGESET": "diff và commit Git của nhánh sprint; REPORT mục \"Cách dùng, đã đổi gì, cách hoàn tác\" tóm tắt",
    "VERIFICATION": "PROGRESS (nhật ký kiểm) và REPORT mục \"Kết quả kiểm định\" (bảng `VR`); báo cáo việc `REPORT-TK<n>.md` làm nguồn",
    "HANDOFF": "REPORT mục \"Cách dùng, đã đổi gì, cách hoàn tác\" khi không giao ra ngoài phiên; `HANDOFF.md` phần Trả khi giao cho phiên hoặc agent khác",
}


def test_core_mapping_table_rows_exact():
    lines = templates_readme().split(chr(10))
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| Artifact của `core.md`"))
    rows = {}
    for ln in lines[start + 2:]:
        if not ln.startswith("|"):
            break
        c = cells(ln)
        rows[c[0]] = c[1]
    assert rows == MAPPING_ROWS


def test_mapping_outside_agile_and_banned_names():
    """FR3.4: outside agile VERIFICATION.md and HANDOFF.md stay in use; SUMMARY.md, NOTES.md, BRIEF-<x>.md are not scaffolded."""
    readme = templates_readme()
    assert "KHI việc chạy ngoài agile THÌ `VERIFICATION.md` và `HANDOFF.md` vẫn được dùng" in readme
    assert "tên `SUMMARY.md`, `NOTES.md`, `BRIEF-<x>.md` không dựng" in readme


def test_ledger_template_names_task_md():
    text = (TEMPLATES_ROOT / "registry" / "LEDGER.md").read_bytes().decode("utf-8")
    assert "`SPRINT.md` hoặc `TASK.md`" in text


ADDON_LABELS = {
    "heading.handoff_give": "Giao",
    "heading.handoff_return": "Trả",
    "heading.analysis_sources": "Bảng nguồn",
    "heading.analysis_source_safety": "Kiểm an toàn nguồn",
    "heading.analysis_assessment": "Đánh giá từng thay đổi",
    "heading.analysis_prerequisites": "Điều kiện tiên quyết",
    "heading.analysis_options": "Phương án và khuyến nghị",
    "heading.claims_checked": "Khẳng định đã kiểm",
    "heading.claims_unchecked": "Chưa kiểm",
    "heading.roadmap_goal": "Mục tiêu và xong khi",
    "heading.roadmap_slices": "Bảng lát",
    "heading.roadmap_shared_contract": "Hợp đồng dùng chung",
    "heading.roadmap_decisions": "Quyết định còn hiệu lực",
    "heading.roadmap_lessons": "Bài học áp lát sau",
    "heading.roadmap_entry": "Điểm vào cho phiên mới",
    "heading.roadmap_risks": "Rủi ro chương trình",
}


def test_addon_heading_labels_in_vi_and_en():
    vi = json.loads((LABELS / "vi.json").read_text(encoding="utf-8"))
    en = json.loads((LABELS / "en.json").read_text(encoding="utf-8"))
    for key, vi_label in ADDON_LABELS.items():
        assert vi.get(key) == vi_label, key
        assert key in en and not VIETNAMESE.search(en[key]), key
    for name, keys in (("ANALYSIS.md", [k for k in ADDON_LABELS if "analysis" in k]),
                       ("ROADMAP.md", [k for k in ADDON_LABELS if "roadmap" in k])):
        text = addon(name)
        for key in keys:
            assert ADDON_LABELS[key] in text, (name, key)
    assert set(vi) == set(en)


def readme_section(number: int) -> str:
    parts = re.split(r"(?m)^## ", templates_readme())
    return next(part for part in parts if part.startswith(f"{number}. "))


def test_readme_section_2_example_uses_numeric_tier_scale():
    """Section 2 shows `roles` values on the Tier 1-5 numeric scale, not the old `T1`-`T3` labels."""
    section = readme_section(2)
    assert re.search(r"\bT[123]\b", section) is None
    assert "analyst: [3, agent-a]" in section


def test_readme_section_6_sprints_source_names_task_md():
    """The SPRINTS open block is read from every state document `index` reads, `TASK.md` included."""
    row = next(ln for ln in readme_section(6).split(chr(10)) if ln.startswith("| SPRINTS |"))
    assert "`TASK.md`" in row and "`SPRINT.md`" in row and "`PROGRESS.md`" in row

