"""`TASK.md` thay `SPRINT.md` ở cỡ rất nhỏ (SPR-35 TK2; FR4, SC2): `init --tiny`, `check`, `index`, `agile_state`.

`TASK.md` là bí danh của loại `sprint` cỡ `tiny` (`doc: task`); `SPRINT.md` cỡ rất nhỏ của hồ sơ cũ không đổi kết quả.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from conftest import REPO, SCRIPTS, write_lf
import _common as c
import agile_state as st
import check
import index
import init

DATE = "2026-03-02"
SAMPLES_PLANS = REPO / "samples" / "order-desk" / "docs" / "plans"
LEGACY_TWO_PART = SAMPLES_PLANS / "2026-01-23-rename-submit-button" / "SPRINT.md"
LEGACY_FOUR_PART = SAMPLES_PLANS / "2026-01-20-fix-not-found-text" / "SPRINT.md"
VIET_LETTER = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")


def names_in(folder: Path) -> list:
    return sorted(p.name for p in folder.iterdir())


def new_task(root: Path, slug: str = "fix-typo", *extra: str, title: str = "Sửa chữ") -> Path:
    assert init.main([str(root), "--apply", "--date", DATE, "--sprint", slug, "--title", title, *extra]) == 0
    return root / "docs" / "plans" / f"{DATE}-{slug}"


def as_task(text: str) -> str:
    """Bản `TASK.md` của một `SPRINT.md` hai phần cỡ rất nhỏ (đổi `doc`, hậu tố `id`, nhãn tiêu đề cấp 1)."""
    for old, new in (("-sprint\ndoc: sprint\n", "-task\ndoc: task\n"), ("— Sprint gộp (SPRINT)", "— Việc đơn lẻ (TASK)")):
        assert old in text, old
        text = text.replace(old, new, 1)
    return text


def legacy_two_part() -> str:
    return LEGACY_TWO_PART.read_text(encoding="utf-8")


def put(folder: Path, name: str, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    write_lf(path, text)
    return path


def rules_of(report) -> set:
    return {f.rule for f in report.findings}


def serious(report) -> list:
    return [f.render() for f in report.findings if f.level in ("Chặn", "Phải sửa")]


# --- init ---------------------------------------------------------------------------------------------------


def test_init_tiny_creates_only_task_md(tmp_path):
    folder = new_task(tmp_path, "fix-typo", "--tiny")
    assert names_in(folder) == ["TASK.md"]
    data = c.parse_frontmatter((folder / "TASK.md").read_text(encoding="utf-8")).data
    assert data["doc"] == "task" and data["id"].endswith("-task") and data["size"] == "tiny"
    assert data["status"] == "drafting"
    assert serious(check.check_paths([tmp_path])) == []


@pytest.mark.parametrize("locale", ["vi", "en"])
def test_init_tiny_task_md_h1_has_title(tmp_path, locale):
    title = "Order typo" if locale == "en" else "Sửa chữ báo lỗi"
    folder = new_task(tmp_path, "fix-typo", "--tiny", "--locale", locale, title=title)
    lines = (folder / "TASK.md").read_text(encoding="utf-8").split("\n")
    h1 = next(line for line in lines[lines.index("---", 1):] if line.startswith("# "))
    assert title in h1
    assert "Tên mục tiêu" not in h1 and "Sprint goal name" not in h1
    if locale == "en":
        assert not (set(h1.lower()) & VIET_LETTER), h1


def test_init_small_still_creates_sprint_md(tmp_path):
    folder = new_task(tmp_path, "tweak-flow", "--size", "small")
    assert names_in(folder) == ["SPRINT.md"]
    assert c.parse_frontmatter((folder / "SPRINT.md").read_text(encoding="utf-8")).data["doc"] == "sprint"


# --- check: TASK.md --------------------------------------------------------------------------------------------


def test_check_task_md_two_parts_is_clean(tmp_path):
    put(tmp_path, "TASK.md", as_task(legacy_two_part()))
    assert rules_of(check.check_paths([tmp_path])) == set()


def test_check_task_md_id_uses_doc_name(tmp_path):
    text = as_task(legacy_two_part())
    put(tmp_path / "ok", "TASK.md", text)
    assert "frontmatter-value" not in rules_of(check.check_paths([tmp_path / "ok"]))
    put(tmp_path / "bad", "TASK.md", text.replace("id: SPR-04-task", "id: SPR-04-sprint", 1))
    hits = [f for f in check.check_paths([tmp_path / "bad"]).findings if f.rule == "frontmatter-value"]
    assert len(hits) == 1 and "SPR-04-task" in hits[0].message, [f.render() for f in hits]


def test_legacy_tiny_sprint_md_two_parts_unchanged(tmp_path):
    put(tmp_path, "SPRINT.md", legacy_two_part())
    assert check.check_paths([tmp_path]).findings == []


def test_legacy_tiny_sprint_md_four_parts_unchanged(tmp_path):
    put(tmp_path, "SPRINT.md", LEGACY_FOUR_PART.read_text(encoding="utf-8"))
    assert check.check_paths([tmp_path]).findings == []


def test_task_md_with_size_small_is_mismatch(tmp_path):
    put(tmp_path, "TASK.md", as_task(legacy_two_part()).replace("size: tiny", "size: small", 1))
    assert rules_of(check.check_paths([tmp_path])) == {"sprint-size-mismatch"}


def test_task_md_four_parts_is_mismatch(tmp_path):
    text = (LEGACY_FOUR_PART.read_text(encoding="utf-8")
            .replace("id: SPR-02-sprint\ndoc: sprint\n", "id: SPR-02-task\ndoc: task\n", 1)
            .replace("— Sprint gộp (SPRINT)", "— Việc đơn lẻ (TASK)", 1))
    put(tmp_path, "TASK.md", text)
    assert rules_of(check.check_paths([tmp_path])) == {"sprint-size-mismatch"}


def test_task_md_beside_sprint_md_is_mismatch_once(tmp_path):
    put(tmp_path, "TASK.md", as_task(legacy_two_part()))
    put(tmp_path, "SPRINT.md", legacy_two_part())
    hits = [f for f in check.check_paths([tmp_path]).findings if f.rule == "sprint-size-mismatch"]
    assert len(hits) == 1, [f.render() for f in hits]


def test_task_md_beside_four_files_is_mismatch_once(tmp_path):
    folder = tmp_path / "work"
    first = new_task(tmp_path / "gen", "order-lookup")  # bốn file cỡ vừa
    for path in first.glob("*.md"):
        put(folder, path.name, path.read_text(encoding="utf-8"))
    put(folder, "TASK.md", as_task(legacy_two_part()).replace("SPR-04", "SPR-01"))  # cùng sprint với bốn file
    hits = [f for f in check.check_paths([folder]).findings if f.rule == "sprint-size-mismatch"]
    assert len(hits) == 1, [f.render() for f in hits]


def test_task_md_beside_another_sprints_file_is_still_one_mismatch(tmp_path):
    """Khác mã sprint vẫn báo: luật đếm mọi tài liệu sprint trong thư mục (chỉ thư mục mẫu của plugin được miễn)."""
    put(tmp_path, "TASK.md", as_task(legacy_two_part()))
    put(tmp_path, "SPRINT.md", legacy_two_part().replace("SPR-04", "SPR-09"))
    hits = [f for f in check.check_paths([tmp_path]).findings if f.rule == "sprint-size-mismatch"]
    assert len(hits) == 1, [f.render() for f in hits]


def _plugin_template_dir(tmp_path, monkeypatch, name: str = "sprint") -> Path:
    templates = tmp_path / "plugin" / "templates"
    monkeypatch.setattr(c, "TEMPLATES", templates)
    return templates / name


def test_plugin_template_folder_is_exempt_from_beside_rule(tmp_path, monkeypatch):
    folder = _plugin_template_dir(tmp_path, monkeypatch)
    put(folder, "TASK.md", as_task(legacy_two_part()))
    put(folder, "SPRINT.md", legacy_two_part())
    assert "sprint-size-mismatch" not in rules_of(check.check_paths([folder]))


def test_folder_named_like_the_template_folder_is_not_exempt(tmp_path, monkeypatch):
    """Miễn theo đường `resolve()`, không theo tên thư mục: `.../sprint` ở chỗ khác vẫn bị báo."""
    _plugin_template_dir(tmp_path, monkeypatch)
    other = tmp_path / "elsewhere" / "templates" / "sprint"
    put(other, "TASK.md", as_task(legacy_two_part()))
    put(other, "SPRINT.md", legacy_two_part())
    assert "sprint-size-mismatch" in rules_of(check.check_paths([other]))


def test_template_folder_exemption_compares_resolved_paths(tmp_path, monkeypatch):
    """Đường tới thư mục mẫu qua `..` (hoa/thường hay lối vòng) vẫn là cùng thư mục sau `resolve()`."""
    folder = _plugin_template_dir(tmp_path, monkeypatch)
    put(folder, "TASK.md", as_task(legacy_two_part()))
    put(folder, "SPRINT.md", legacy_two_part())
    detour = tmp_path / "plugin" / "x" / ".." / "templates" / "sprint"
    assert "sprint-size-mismatch" not in rules_of(check.check_paths([detour]))
    upper = tmp_path / "plugin" / "TEMPLATES" / "SPRINT"
    if upper.exists():  # hệ không phân biệt hoa/thường (Windows): cùng một thư mục
        assert "sprint-size-mismatch" not in rules_of(check.check_paths([upper]))


def test_task_md_missing_result_part_is_flagged(tmp_path):
    text = as_task(legacy_two_part())
    text = text[:text.index("## 2. Kết quả")]
    put(tmp_path, "TASK.md", text)
    hits = [f for f in check.check_paths([tmp_path]).findings if f.rule == "heading-missing"]
    assert any("Kết quả" in f.message for f in hits), [f.render() for f in check.check_paths([tmp_path]).findings]


def test_task_md_without_vr_row_is_flagged(tmp_path):
    text = "\n".join(line for line in as_task(legacy_two_part()).split("\n") if not line.startswith("| VR1"))
    put(tmp_path, "TASK.md", text)
    assert "report-sc-without-vr" in rules_of(check.check_paths([tmp_path]))


def test_task_md_with_doc_sprint_is_flagged(tmp_path):
    put(tmp_path, "TASK.md", as_task(legacy_two_part()).replace("doc: task", "doc: sprint", 1))
    hits = [f for f in check.check_paths([tmp_path]).findings if f.rule == "frontmatter-value" and "doc" in f.message]
    assert len(hits) == 1 and hits[0].level == "Phải sửa", [f.render() for f in check.check_paths([tmp_path]).findings]


def test_sprint_md_with_doc_task_is_flagged(tmp_path):
    put(tmp_path, "SPRINT.md", legacy_two_part().replace("doc: sprint", "doc: task", 1))
    hits = [f for f in check.check_paths([tmp_path]).findings if f.rule == "frontmatter-value" and "doc" in f.message]
    assert len(hits) == 1 and hits[0].level == "Phải sửa", [f.render() for f in check.check_paths([tmp_path]).findings]


def test_evidence_beside_task_md_is_skipped(tmp_path):
    put(tmp_path, "TASK.md", as_task(legacy_two_part()))
    put(tmp_path / "evidence", "x.md", "---\nid: evidence-note\ndoc: spec\n---\n\n# ghi chú\n")
    assert check.check_paths([tmp_path]).findings == []
    assert check.check_paths([tmp_path], include_evidence=True).findings != []


def test_registry_rule_reads_task_md(tmp_path):
    """Dòng sổ tập trung đòi cho sprint chỉ có `TASK.md`, như cho `SPRINT.md`."""
    root = tmp_path / "proj"
    put(root / "docs" / "plans" / "2026-02-01-fix", "TASK.md", as_task(legacy_two_part()).replace("status: done", "status: verifying", 1))
    write_lf(root / ".agile.json", json.dumps({"schema": 1, "ledger": {"project": "order-desk"}}))
    store = tmp_path / "store"
    store.mkdir()
    head = "| Sprint | Trạng thái | Cập nhật | Hồ sơ | Link |\n|---|---|---|---|---|\n"
    write_lf(store / "order-desk.md", "# Sổ\n\n## Sprint\n\n" + head + "| SPR-09 | verifying | 2026-02-02 | order-desk:x | y |\n")
    env = {"AGENT_AGILE_LEDGER": f"{store.as_posix()}/{{project}}.md"}
    hits = [f for f in check.check_paths([root], env=env).findings if f.rule == "ledger-missing-row"]
    assert len(hits) == 1 and hits[0].path.name == "TASK.md" and "SPR-04" in hits[0].message, [f.render() for f in hits]


# --- index và agile_state ----------------------------------------------------------------------------------


def test_index_open_block_reads_task_md(tmp_path):
    init.main([str(tmp_path), "--apply", "--date", DATE])
    new_task(tmp_path, "fix-typo", "--tiny")
    task = tmp_path / "docs" / "plans" / f"{DATE}-fix-typo" / "TASK.md"
    write_lf(task, task.read_text(encoding="utf-8").replace("status: drafting", "status: verifying", 1))
    assert index.main([str(tmp_path)]) == 0
    got = (tmp_path / "docs" / "plans" / "SPRINTS.md").read_text(encoding="utf-8")
    assert f"| SPR-01 | {DATE} | Sửa chữ | đang kiểm định | 0 |" in got


def test_agile_state_status_lists_task_md(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    write_lf(root / ".agile.json", json.dumps({"schema": 1}))
    fm = "---\nid: SPR-05-task\ndoc: task\ntitle: Nho\nsprint: SPR-05\nstatus: in_progress\n---\n\n# x\n"
    put(root / "docs" / "plans" / "2026-01-01-nho", "TASK.md", fm)
    status = st.build_status(root, "s1")
    assert [s["sprint"] for s in status["open_sprints"]] == ["SPR-05"]
    assert "open sprint: SPR-05 [in_progress] Nho" in st.render_status(status)


def test_agile_state_names_match_common():
    """`agile_state.py` là file sàn cứng, nạp `_common` trễ: giữ bộ ba tên viết thẳng; test này giữ nó khớp `_common.STATE_DOC_NAMES`."""
    tree = ast.parse((SCRIPTS / "agile_state.py").read_text(encoding="utf-8"))
    literals = [tuple(e.value for e in node.elts) for node in ast.walk(tree)
                if isinstance(node, ast.Tuple) and node.elts and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts)
                and "PROGRESS.md" in {e.value for e in node.elts}]
    assert literals and all(lit == c.STATE_DOC_NAMES for lit in literals), literals


def test_task_md_without_frontmatter_is_frontmatter_missing(tmp_path):
    """A `TASK.md` of an unrelated project is a standard document now: no frontmatter gives Phải sửa, exit 1 (chosen, see CHANGELOG)."""
    write_lf(tmp_path / "TASK.md", "# Todo\n\nbuy milk\n")
    report = check.check_paths([tmp_path])
    found = [f for f in report.findings if f.rule == "frontmatter-missing"]
    assert [f.level for f in found] == [check.PHAI]
    assert check.main([str(tmp_path)]) == 1


def test_task_md_with_foreign_frontmatter_is_frontmatter_syntax(tmp_path):
    """Frontmatter outside the supported YAML subset gives Chặn, exit 2 (chosen, see CHANGELOG)."""
    write_lf(tmp_path / "TASK.md", "---\ntitle: [a, {b: c}]\n---\n\n# T\n")
    report = check.check_paths([tmp_path])
    found = [f for f in report.findings if f.rule == "frontmatter-syntax"]
    assert [f.level for f in found] == [check.CHAN]
    assert check.main([str(tmp_path)]) == 2
