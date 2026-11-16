"""Hand-written English golden fixtures (SPR-33 TK6, GC8).

tests/fixtures/en/ holds sprint documents written by a person in natural English, not produced by _labels.translate:
a complete four-file sprint (valid/), a combined tiny sprint (tiny/) and broken.json (negatives with the exact rule keys).
They are checked on their own, and then compared with the translate twin of the Vietnamese originals, so the shared
production function cannot drift away from what a human would write.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import _labels as lab
import check
from conftest import FIXTURES, write_lf
from test_check import VALID as VI_VALID, two_part_sprint
from test_locale_parity import declare, shape

EN = FIXTURES / "en"
CASES = json.loads((EN / "broken.json").read_text(encoding="utf-8"))["cases"]
NEGATIVES = [c for c in CASES if c["rules"]]
SPRINT_FILES = ["SPEC.md", "PLAN.md", "PROGRESS.md", "REPORT.md"]


@pytest.fixture(autouse=True)
def _no_real_tiers(monkeypatch):
    monkeypatch.delenv("AGENT_AGILE_TIERS", raising=False)


def test_golden_sprint_is_complete_clean_and_declares_en():
    assert sorted(p.name for p in (EN / "valid").iterdir()) == sorted(SPRINT_FILES)
    for name in SPRINT_FILES + ["../tiny/SPRINT.md"]:
        head = (EN / "valid" / name).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        assert "\nlocale: en" in head, name
    for root in ("valid", "tiny"):
        report = check.check_paths([EN / root])
        assert [f.render() for f in report.findings] == []
        assert report.exit_code == 0


def test_golden_files_carry_no_vietnamese_text():
    """Natural English throughout: no Vietnamese letters outside the broken.json case that needs one on purpose."""
    vietnamese = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
    for path in sorted(EN.rglob("*.md")):
        text = path.read_text(encoding="utf-8").lower()
        assert not (vietnamese & set(text)), path.name


def build(tmp_path: Path, case: dict) -> Path:
    root = tmp_path / "sprint"
    shutil.copytree(EN / case["root"], root)
    target = root / case["file"]
    text = target.read_bytes().decode("utf-8")
    for old, new in case["replaces"]:
        assert old in text, f"{case['name']}: replacement source not found in {case['file']}"
        text = text.replace(old, new, 1)
    write_lf(target, text)
    return root


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_hand_written_case_gives_exactly_its_rule_keys(tmp_path, case):
    report = check.check_paths([build(tmp_path, case)])
    assert sorted(f.rule for f in report.findings) == sorted(case["rules"]), [f.render() for f in report.findings]
    assert report.exit_code == case["exit"]


def test_negatives_cover_the_required_topics_and_are_counted():
    rules = {r for c in NEGATIVES for r in c["rules"]}
    assert len(NEGATIVES) >= 6 and len(CASES) == len(json.loads((EN / "broken.json").read_text(encoding="utf-8"))["cases"])
    assert {"heading-missing", "old-scale-label", "conclusion-missing", "plan-goal-block", "locale-label-mixed"} <= rules
    names = {c["name"] for c in CASES}
    assert {"note-uppercase-without-locale", "note-uppercase-under-locale-en"} <= names  # GC2 both directions
    print(f"golden en: 2 clean roots (5 files), {len(NEGATIVES)} negative cases, {len(CASES) - len(NEGATIVES)} clean variant(s)")


def label_skeleton(text: str) -> list:
    """(kind, key, text) of every label span, minus table headers that reuse a heading key (en.json decision: the column
    "Rủi ro" is heading.risks, so translate writes the plural "Risks"; a person writes the singular "Risk", which no table
    names). Those headers are not machine-read; every other span must agree."""
    return [(s.kind, s.key, s.text) for s in lab.scan(text) if not (s.kind == "header" and s.key.startswith("heading."))]


@pytest.mark.parametrize("name", SPRINT_FILES)
def test_translate_twin_uses_the_same_labels_a_human_wrote(name):
    """Heading, table-header and field labels of the hand-written file equal those translate gives the Vietnamese original."""
    twin = declare((VI_VALID / name).read_bytes().decode("utf-8"), "en")
    human = (EN / "valid" / name).read_bytes().decode("utf-8")
    assert label_skeleton(human) == label_skeleton(twin)
    assert human.split("\n---\n", 1)[0].count("locale: en") == twin.split("\n---\n", 1)[0].count("locale: en") == 1


def test_translate_twin_of_the_tiny_sprint_uses_the_same_labels_a_human_wrote():
    twin = declare(two_part_sprint(), "en")
    human = (EN / "tiny" / "SPRINT.md").read_bytes().decode("utf-8")
    assert label_skeleton(human) == label_skeleton(twin)


def test_hand_written_set_and_translate_twin_agree_on_findings(tmp_path):
    twin = tmp_path / "twin"
    shutil.copytree(VI_VALID, twin)
    for path in sorted(twin.glob("*.md")):
        write_lf(path, declare(path.read_bytes().decode("utf-8"), "en"))
    human = check.check_paths([EN / "valid"])
    generated = check.check_paths([twin])
    assert shape(human) == shape(generated) == shape(check.check_paths([VI_VALID]))
    assert human.exit_code == generated.exit_code == 0
