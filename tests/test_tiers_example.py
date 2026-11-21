"""Bảng tier mẫu schema 3 và ma trận vai × vendor mẫu: hình dạng, thang 1–5, khớp thẻ vai."""

from __future__ import annotations

import json
import re
from pathlib import Path

from conftest import REPO
import check

ROOT = REPO
EXAMPLE = ROOT / "tiers" / "tiers.example.json"
MATRIX = ROOT / "tiers" / "ROLE-MATRIX.example.md"
HARNESSES = ("claude", "codex", "antigravity")
MATRIX_COLUMNS = ("Vai", "Tier", "Vendor", "Model", "Effort", "Effort native", "Ghi chú")
ROLE_NAMES = {
    "analyst": "Analyst",
    "architect": "Architect",
    "implementer": "Implementer",
    "qa": "QA",
    "researcher": "Researcher",
    "business-reviewer": "Business Reviewer",
    "tech-reviewer": "Tech Reviewer",
    "gate-delegate": "Gate Delegate",
    "advisor": "Advisor",
}


def _load() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _card_tier(role: str) -> int:
    """Tier ghi ở dòng `tier: <số 1–5>` trong frontmatter của thẻ `roles/**/<role>.md` (số nguyên)."""
    card = next((ROOT / "roles").rglob(f"{role}.md"))
    for line in card.read_text(encoding="utf-8").splitlines()[1:12]:
        match = re.fullmatch(r"tier:\s*([1-5])\s*", line)
        if match:
            return int(match.group(1))
    raise AssertionError(f"thẻ {card} không có dòng tier")


def _effort_values(data: dict) -> list:
    """Mọi ô effort trong bảng (tier và vai), mở khối `{harness: số}` thành từng số."""
    values: list = []
    cells = [t.get("effort") for t in data["tiers"].values()]
    cells += [r.get("effort") for r in data.get("roles", {}).values()]
    for cell in cells:
        if cell is None:
            continue
        values.extend(cell.values() if isinstance(cell, dict) else [cell])
    return values


def _effort_ok(value: object) -> bool:
    """Effort hợp lệ là số nguyên 1–5; `bool` là con của `int` nên phải loại riêng."""
    return type(value) is int and 1 <= value <= 5


def _model_cells(data: dict) -> list:
    """Mọi ô model trong bảng (tier và vai)."""
    cells: list = []
    for entry in list(data["tiers"].values()) + list(data.get("roles", {}).values()):
        cells.extend(entry.get("models", {}).values())
    return cells


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _matrix_header(path: Path) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return tuple(_split_row(next(line for line in lines if line.startswith("|"))))


def _matrix_rows(path: Path) -> list[dict]:
    """Hàng của bảng đầu tiên trong file ma trận, mỗi hàng là dict theo tên cột."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("|"))
    header = _split_row(lines[start])
    rows: list[dict] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(dict(zip(header, _split_row(line))))
    return rows


def test_example_declares_schema_3():
    data = _load()
    assert data["schema"] == 3
    assert data["tier_scale"] == 2
    assert list(data["tiers"]) == ["1", "2", "3", "4", "5"]


def test_effort_values_reject_bool():
    bad = {"tiers": {"1": {"effort": True}}, "roles": {"qa": {"effort": {"claude": False, "codex": 2}}}}
    values = _effort_values(bad)
    assert values == [True, False, 2]
    assert [_effort_ok(x) for x in values] == [False, False, True]
    assert not all(_effort_ok(x) for x in values)


def test_example_models_are_placeholders():
    data = _load()
    assert all(v == "<model-id>" for v in _model_cells(data))


def test_example_effort_levels_in_1_to_5():
    data = _load()
    assert all(_effort_ok(x) for x in _effort_values(data))
    assert all(set(data["effort_scale"][h]) == {"1", "2", "3", "4", "5"} for h in HARNESSES)


def test_example_effort_scale_fallback():
    data = _load()
    assert data["fallback"] == {"antigravity": "clamp_to_max"}
    assert data["effort_scale"]["antigravity"]["4"] is None


def test_example_roles_are_known_role_keys():
    data = _load()
    assert data["roles"], "roles rỗng"
    assert set(data["roles"]) <= check.EXECUTORS | check.VERIFIERS


def test_example_role_tiers_match_cards():
    data = _load()
    assert all(int(v["tier"]) == _card_tier(k) for k, v in data["roles"].items())


def test_role_matrix_example_shape():
    assert _matrix_header(MATRIX) == MATRIX_COLUMNS
    rows = _matrix_rows(MATRIX)
    roles = check.EXECUTORS | check.VERIFIERS | check.ADVISORS
    assert len(rows) == len(roles) * 3
    pairs = {(r["Vai"], r["Vendor"]) for r in rows}
    assert len(pairs) == len(rows)
    assert pairs == {(ROLE_NAMES[r], h) for r in roles for h in HARNESSES}
    assert all(r["Model"] == "`<model-id>`" for r in rows)


def test_new_role_cards_are_tier_4():
    assert _card_tier("gate-delegate") == 4
    assert _card_tier("advisor") == 4


def test_role_matrix_example_tiers_match_cards():
    names = {v: k for k, v in ROLE_NAMES.items()}
    assert all(int(r["Tier"]) == _card_tier(names[r["Vai"]]) for r in _matrix_rows(MATRIX))


# Effort gốc theo vai (RF2 vòng 1): QA giữ effort của bảng cũ bằng ghi đè `roles.qa`; ô tier 2 = 3 là sàn của Implementer.
EXPECTED_EFFORT = {
    "analyst": (3, 3, 3), "architect": (3, 3, 3), "implementer": (3, 3, 3), "qa": (2, 2, 1), "researcher": (2, 2, 2),
    "business-reviewer": (3, 3, 3), "tech-reviewer": (3, 3, 3), "gate-delegate": (3, 3, 3), "advisor": (3, 3, 3),
}


def _resolved_effort(data: dict, role: str, harness: str) -> int:
    """Effort phân giải của một vai ở một harness: ghi đè `roles.<vai>` thắng ô của tier."""
    cell = data.get("roles", {}).get(role, {}).get("effort")
    if cell is None:
        tier = _card_tier(role)
        cell = data["tiers"][str(tier)]["effort"]
    return cell[harness] if isinstance(cell, dict) else cell


def test_example_resolved_effort_per_role():
    data = _load()
    for role, expected in EXPECTED_EFFORT.items():
        assert tuple(_resolved_effort(data, role, h) for h in HARNESSES) == expected, role


def test_role_matrix_example_effort_matches_table():
    data = _load()
    names = {v: k for k, v in ROLE_NAMES.items()}
    native = data["effort_scale"]
    for row in _matrix_rows(MATRIX):
        role, harness = names[row["Vai"]], row["Vendor"]
        value = _resolved_effort(data, role, harness)
        assert int(row["Effort"]) == value, (role, harness)
        assert row["Effort native"] == f"`{native[harness][str(value)]}`", (role, harness)
