"""Thang Tier 1–5 là mặc định của mẫu và `init` (SPR-35 TK4; FR5.1–FR5.4, SC5).

Hồ sơ mới mang `tier_scale: 2` và `roles` ghi số 1–4; hồ sơ không có `tier_scale` giữ luật `T1`–`T3`;
luật `tier-label-legacy` (Ghi chú) chỉ xét tài liệu `tier_scale: 2` tạo từ ngày hiệu lực.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import _common as c
import check
import init
from conftest import REPO, write_lf

DATE = "2026-03-02"
NEW_DATE = "2026-01-01"  # ngày hiệu lực giả lập, trước DATE: hồ sơ `init --date 2026-03-02` là hồ sơ mới
TEMPLATE_DIR = REPO / "templates" / "sprint"
TEMPLATES = ("SPEC", "PLAN", "PROGRESS", "REPORT", "SPRINT", "TASK")
ROLE_TABLE = {  # FR5.1
    "researcher": 1, "qa": 2, "implementer": 2, "analyst": 3, "architect": 3, "tech-reviewer": 3,
    "business-reviewer": 4, "gate-delegate": 4, "advisor": 4,
}
CARD_TIERS = {**ROLE_TABLE, "dual-review": 3, "backend": 3, "data": 3, "frontend": 3, "security": 3}
SHAPES = {"medium": [], "tiny": ["--tiny"], "small": ["--size", "small"], "large": ["--size", "large"]}
OLD_TIERS = {"analyst": "T1", "implementer": "T2", "tech-reviewer": "T1"}  # nhãn cũ của khối `roles` mẫu TASK.md


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(tmp_path.parent / (tmp_path.name + "-state")))


def _scaffold(root: Path, *extra: str) -> list[Path]:
    root.mkdir(exist_ok=True)
    assert init.main([str(root), "--apply", "--date", DATE, "--sprint", "order-lookup", "--title", "Order lookup", *extra]) == 0
    return sorted((root / "docs" / "plans" / f"{DATE}-order-lookup").glob("*.md"))


def _fm(path: Path) -> dict:
    return c.parse_frontmatter(path.read_text(encoding="utf-8")).data


def _rules(folder: Path) -> set:
    return {f.rule for f in check.check_paths([folder]).findings}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_init_new_sprint_has_tier_scale_2(tmp_path, shape):
    docs = _scaffold(tmp_path, *SHAPES[shape])
    assert docs and all(_fm(p).get("tier_scale") == 2 for p in docs)


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_init_new_sprint_passes_check_clean(tmp_path, shape):
    _scaffold(tmp_path, *SHAPES[shape])
    assert check.check_paths([tmp_path]).findings == []


@pytest.mark.parametrize("name", TEMPLATES)
def test_template_roles_use_tier_numbers(name):
    data = _fm(TEMPLATE_DIR / f"{name}.md")
    assert data["tier_scale"] == 2
    assert data["roles"] and all(type(v[0]) is int and v[0] in {1, 2, 3, 4} for v in data["roles"].values())


@pytest.mark.parametrize("name", TEMPLATES)
def test_template_role_tiers_match_role_table(name):
    data = _fm(TEMPLATE_DIR / f"{name}.md")
    assert all(v[0] == ROLE_TABLE[role] for role, v in data["roles"].items())


@pytest.mark.parametrize("name", TEMPLATES)
def test_template_tier_scale_sits_above_first_gate_or_roles(name):
    head = (TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8").split("---", 2)[1]
    keys = re.findall(r"^([a-z_0-9-]+):", head, re.M)
    anchor = "gate_1" if "gate_1" in keys else "roles"
    assert keys.index("tier_scale") == keys.index(anchor) - 1


@pytest.mark.parametrize("name", TEMPLATES)
def test_template_bodies_have_no_legacy_tier_labels(name):
    body = (TEMPLATE_DIR / f"{name}.md").read_text(encoding="utf-8").split("---", 2)[2]
    assert not re.search(r"\bT[123]\b", body)


def test_role_cards_tier_is_number_matching_role_table():
    seen = {}
    for card in (REPO / "roles").rglob("*.md"):
        if card.name == "README.md":
            continue
        tier = _fm(card).get("tier")
        assert type(tier) is int, card
        seen[card.stem] = tier
    assert seen == CARD_TIERS


def _legacy_doc(root: Path, monkeypatch, *, scale: bool = True, created: str | None = None,
                label_line: str = "Việc này do Implementer T2 làm.") -> Path:
    """`TASK.md` mới dựng bằng `init`, thêm một dòng thân; `scale=False` đưa về hồ sơ cũ (không `tier_scale`, `roles` kiểu `T1`–`T3`)."""
    monkeypatch.setattr(c, "NAMING_EFFECTIVE_DATE", NEW_DATE)
    task = next(p for p in _scaffold(root, "--tiny") if p.name == "TASK.md")
    text = task.read_text(encoding="utf-8")
    if not scale:
        text = text.replace("tier_scale: 2\n", "", 1)
        for role, label in OLD_TIERS.items():
            text = re.sub(rf"(  {role}: \[)\d", rf"\g<1>{label}", text, count=1)
    if created:
        text = text.replace(f"created: {DATE}", f"created: {created}", 1)
    write_lf(task, text.rstrip("\n") + f"\n\n{label_line}\n")
    return task


def test_legacy_doc_without_tier_scale_unchanged(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch, scale=False)
    assert "tier_scale" not in task.read_text(encoding="utf-8")
    assert _rules(task.parent) == set()


def test_tier_label_legacy_note_on_scale2_doc(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch)
    assert _rules(task.parent) == {"tier-label-legacy"}
    finding = next(f for f in check.check_paths([task.parent]).findings if f.rule == "tier-label-legacy")
    assert finding.level == check.GHI


def test_tier_label_legacy_note_only_from_effective_date(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch, created="2025-12-31")
    assert _rules(task.parent) == set()


def test_tier_label_legacy_silent_before_placeholder_date(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch)
    monkeypatch.setattr(c, "NAMING_EFFECTIVE_DATE", c.NAMING_DATE_PLACEHOLDER)
    assert _rules(task.parent) == set()


def test_tier_label_legacy_ignores_scale1_docs(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch, scale=False)
    assert "tier-label-legacy" not in _rules(task.parent)


def test_tier_label_legacy_ignores_code_spans(tmp_path, monkeypatch):
    note = "Nhãn cũ `T2` chỉ nhắc trong dấu code.\n\n```\nT3 trong khối code\n```\n\n<!-- T1 trong comment -->"
    task = _legacy_doc(tmp_path, monkeypatch, label_line=note)
    assert _rules(task.parent) == set()


def test_tier_label_legacy_missing_created_is_silent(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch)
    write_lf(task, task.read_text(encoding="utf-8").replace(f"created: {DATE}\n", "", 1))
    assert "tier-label-legacy" not in _rules(task.parent)


def test_tier_5_assigned_to_agent_is_roles_invalid(tmp_path, monkeypatch):
    task = _legacy_doc(tmp_path, monkeypatch, label_line="Không còn nhãn cũ.")
    write_lf(task, task.read_text(encoding="utf-8").replace("  implementer: [2,", "  implementer: [5,", 1))
    assert "roles-invalid" in _rules(task.parent)


def test_tiers_example_is_schema_3_with_five_tiers():
    data = json.loads((REPO / "tiers" / "tiers.example.json").read_text(encoding="utf-8"))
    assert data["schema"] == 3 and data["tier_scale"] == 2
    assert list(data["tiers"]) == ["1", "2", "3", "4", "5"]
    assert data["tiers"]["5"]["models"] == {} and data["tiers"]["5"]["effort"] is None
