"""check.py matches machine-read labels through _labels (SPR-33 TK3): en twins of the existing negatives, a clean en copy
of the valid fixture, anchoring (GC1), keyed severity and the Note rule (GC2), accept-any-locale (D2).

Twins are produced with _labels.translate, never copied by hand. Rule messages stay Vietnamese (output only).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import FIXTURES, write_lf
import _labels as lab
import check
from test_check import apply_case, delegate_plan, delegate_report, make_sprint, rules_of

VALID = FIXTURES / "valid"
CASES = json.loads((FIXTURES / "broken.json").read_text(encoding="utf-8"))["cases"]

# Rules whose label matching moves in a later TK3 batch; their en twins are not compared yet. Emptied at the end of batch c.
PENDING = {
    "conclusion-missing", "old-scale-label", "decision-log-missing", "session-cap-missing", "session-cap-over",
    "report-missing-ask-count", "conditional-pass-merged-main", "qa-not-independent", "report-fr-without-vr",
    "ledger-missing-row", "ledger-stale", "ledger-unreadable", "ledger-unconfigured"}

# Notes the en copy of the valid fixture may carry (GC3). Empty until TK4 adds `locale` to KNOWN_KEYS.
PERMITTED_EN_NOTES: set = set()


def to_en(root: Path) -> None:
    """Rewrite every Markdown file of a tree into English labels (shared translate helper)."""
    for path in sorted(root.rglob("*.md")):
        text = path.read_bytes().decode("utf-8")
        write_lf(path, lab.translate(text, "en"))


def run_case(tmp_path: Path, case: dict, english: bool):
    root = make_sprint(tmp_path)
    apply_case(root, case)
    if english:
        to_en(root)
    store = tmp_path / "store"
    if "ledger" in case or "env" in case:
        folder = root / "docs" / "plans" / "2026-02-01-export-orders"
        folder.mkdir(parents=True)
        for item in [p for p in root.iterdir() if p.name not in (".agile.json", "docs")]:
            shutil.move(str(item), str(folder / item.name))
    if "ledger" in case:
        store.mkdir(parents=True, exist_ok=True)
        write_lf(store / "order-desk.md", case["ledger"])
    env = {k: v.replace("{store}", store.as_posix()) for k, v in case.get("env", {}).items()}
    return check.check_paths([root], env=env)


# --- batch a: headings and bold-field labels -----------------------------------------------------------------


def test_en_copy_of_valid_fixture_is_clean(tmp_path):
    root = make_sprint(tmp_path)
    to_en(root)
    report = check.check_paths([root])
    unexpected = [f.render() for f in report.findings if f.rule not in PERMITTED_EN_NOTES | PENDING]
    assert unexpected == []
    if not PENDING:
        assert report.exit_code == 0


@pytest.mark.parametrize("case", CASES, ids=[c.get("name", c["rule"]) for c in CASES])
def test_en_twin_of_each_negative_has_the_same_rule(tmp_path, case):
    vi = run_case(tmp_path / "vi", case, english=False)
    en = run_case(tmp_path / "en", case, english=True)
    if case["rule"] in PENDING:
        pytest.skip("rule moves in a later batch")
    hits = [f for f in en.findings if f.rule == case["rule"]]
    assert hits, f"en twin lost {case['rule']}: {[f.render() for f in en.findings]}"
    assert any(Path(f.path).as_posix().endswith(case["file"]) for f in hits)
    if "line" in case:
        assert any(f.line == case["line"] for f in hits)
    if not any(f.rule in PENDING for f in en.findings):
        assert en.exit_code == vi.exit_code == case["exit"]
    assert sorted(f.rule for f in en.findings if f.rule not in PENDING) == sorted(f.rule for f in vi.findings if f.rule not in PENDING)


def test_every_required_heading_of_every_kind_matches_in_english(tmp_path):
    """Each required heading key is found in its English form: delete one heading at a time from an en copy."""
    for kind, keys in check.REQUIRED_HEADING_KEYS.items():
        assert len(keys) == len(check.REQUIRED_HEADINGS[kind]), kind
        for key, phrase in zip(keys, check.REQUIRED_HEADINGS[kind]):
            assert lab.exact(phrase, f"heading.{key}", locales=("vi",)), (kind, key, phrase)
            assert lab.label(f"heading.{key}", "en"), (kind, key)


def test_english_heading_must_match_whole_not_substring(tmp_path):
    """GC1: `Risks to track` is not the heading `Risks`; the Vietnamese substring semantics stay."""
    root = make_sprint(tmp_path / "en")
    to_en(root)
    path = root / "PLAN.md"
    text = path.read_text(encoding="utf-8")
    assert "\n## Risks\n" in text
    write_lf(path, text.replace("\n## Risks\n", "\n## Risks to track\n", 1))
    hits = [f for f in check.check_paths([root]).findings if f.rule == "heading-missing"]
    assert any("'Rủi ro'" in f.message for f in hits), [f.render() for f in hits]
    vi = make_sprint(tmp_path / "vi")
    vtext = (vi / "PLAN.md").read_text(encoding="utf-8")
    write_lf(vi / "PLAN.md", vtext.replace("\n## Rủi ro\n", "\n## Rủi ro cần theo dõi\n", 1))
    assert "heading-missing" not in rules_of(check.check_paths([vi]))  # accented Vietnamese labels keep substring matching


def test_english_ascii_heading_collisions(tmp_path):
    """The six ASCII headings keep prefix matching at a word boundary; `Planning` and `Preview` are not the part `PLAN`."""
    assert not lab.startswith("Planning notes", "heading.part_plan") and not lab.contains("Plan review notes", "heading.part_plan")
    assert lab.startswith("plan — extra", "heading.part_plan") and lab.startswith("PLAN", "heading.part_plan")
    assert not check._has_heading("planning notes", "part_plan") and check._has_heading("plan — extra", "part_plan")


def test_mixed_locale_document_matches_by_accept_any_locale(tmp_path):
    """D2: one en heading and one en bold label inside an otherwise Vietnamese PLAN change nothing."""
    root = make_sprint(tmp_path)
    path = root / "PLAN.md"
    text = path.read_text(encoding="utf-8")
    assert "\n## Mục tiêu\n" in text and "\n## Rủi ro\n" in text
    mixed = text.replace("\n## Mục tiêu\n", "\n## Goal\n", 1).replace("\n## Rủi ro\n", "\n## Risks\n", 1)
    mixed = mixed.replace("**Mục tiêu sprint:**", "**Sprint goal:**", 1)
    write_lf(path, mixed)
    assert [f.render() for f in check.check_paths([root]).findings] == []


def test_plan_goal_labels_english_and_missing_one(tmp_path):
    root = make_sprint(tmp_path)
    to_en(root)
    text = (root / "PLAN.md").read_text(encoding="utf-8")
    assert "Sprint goal:" in text
    broken = re.sub(r"^.*Sprint goal:.*\n", "", text, count=1, flags=re.M)
    write_lf(root / "PLAN.md", broken)
    hits = [f for f in check.check_paths([root]).findings if f.rule == "plan-goal-block"]
    assert hits and "'Mục tiêu sprint:'" in hits[0].message  # message stays Vietnamese
