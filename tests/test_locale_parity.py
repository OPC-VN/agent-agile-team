"""SC-A of SPR-33: check.py gives the same answers in every shipped locale (TK6).

Every valid fixture and every negative case that tests/test_check.py exercises is run twice per locale: the Vietnamese
original, and a twin made by the one production function _labels.translate (GC8) plus the `locale: <loc>` front matter
line that `init --locale <loc>` writes (init.add_locale, the same function). A third shipped locale joins automatically
(shipped_locales). Valid units must give the same findings in every locale (rule key, severity, count); negative units
must raise the rule keys of the original. The data is read from the fixture folders and broken.json, never copied.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

import _labels as lab
import check
import init
from conftest import FIXTURES, REPO, SAMPLES, write_lf
from test_check import CASES, apply_case, make_sprint

SOURCE = lab.DEFAULT_LOCALE
LOCALES = lab.shipped()
OTHER = [loc for loc in LOCALES if loc != SOURCE]
SPRINT_NAMES = {"SPEC.md", "PLAN.md", "PROGRESS.md", "REPORT.md", "SPRINT.md"}
HAND_WRITTEN = "en"  # tests/fixtures/en holds hand-written golden files (test_golden_en.py), not translate twins


def valid_roots() -> list:
    """Every folder of fixtures, templates and samples that holds sprint documents; derived from the disk."""
    found = set()
    for base in (FIXTURES, REPO / "templates", SAMPLES):
        for path in base.rglob("*.md"):
            if path.name in SPRINT_NAMES and not (base == FIXTURES and path.relative_to(base).parts[0] == HAND_WRITTEN):
                found.add(path.parent)
    return sorted(found)


VALID = valid_roots()
NEGATIVE = list(CASES)  # every case of broken.json; the three locale rules live in test_check_locale_rules.py, not there


def label_of(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def declare(text: str, locale: str) -> str:
    """The twin of one document: labels translated, and the same locale line init writes into sprint documents."""
    out = lab.translate(text, locale)
    if out.startswith("---\n") and "\ndoc:" in out.split("\n---\n", 1)[0]:
        out = init.add_locale(out, locale)
    return out


def twin_tree(root: Path, locale: str) -> None:
    for path in sorted(root.rglob("*.md")):
        write_lf(path, declare(path.read_bytes().decode("utf-8"), locale))


def shape(report) -> Counter:
    return Counter((f.rule, f.level) for f in report.findings)


def copy_tree(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"))
    return dst


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("AGENT_AGILE_TIERS", raising=False)


def test_the_shipped_locales_include_source_and_en():
    assert SOURCE in LOCALES and "en" in LOCALES and OTHER


@pytest.mark.parametrize("locale", OTHER)
@pytest.mark.parametrize("root", VALID, ids=[label_of(r) for r in VALID])
def test_valid_unit_has_the_same_findings_in_every_locale(tmp_path, root, locale):
    original = check.check_paths([copy_tree(root, tmp_path / "vi")])
    twin_root = copy_tree(root, tmp_path / locale)
    twin_tree(twin_root, locale)
    twin = check.check_paths([twin_root])
    assert shape(twin) == shape(original), [f.render() for f in twin.findings]
    assert twin.exit_code == original.exit_code


def run_negative(tmp_path: Path, case: dict, locale: str):
    root = make_sprint(tmp_path)
    apply_case(root, case)
    store = tmp_path / "store"
    if "ledger" in case or "env" in case:
        folder = root / "docs" / "plans" / "2026-02-01-export-orders"
        folder.mkdir(parents=True)
        for item in [p for p in root.iterdir() if p.name not in (".agile.json", "docs")]:
            shutil.move(str(item), str(folder / item.name))
    if "ledger" in case:
        store.mkdir(parents=True, exist_ok=True)
        write_lf(store / "order-desk.md", case["ledger"])
    if locale != SOURCE:
        twin_tree(root, locale)
    env = {k: v.replace("{store}", store.as_posix()) for k, v in case.get("env", {}).items()}
    return check.check_paths([root], env=env)


@pytest.mark.parametrize("locale", OTHER)
@pytest.mark.parametrize("case", NEGATIVE, ids=[c.get("name", c["rule"]) for c in NEGATIVE])
def test_negative_case_raises_the_same_rule_keys_in_every_locale(tmp_path, case, locale):
    original = run_negative(tmp_path / "vi", case, SOURCE)
    twin = run_negative(tmp_path / locale, case, locale)
    assert case["rule"] in {f.rule for f in twin.findings}, [f.render() for f in twin.findings]
    assert sorted(f.rule for f in twin.findings) == sorted(f.rule for f in original.findings)
    assert twin.exit_code == original.exit_code == case["exit"]


def test_unit_counts_are_derived_from_the_disk_and_recorded(record_property):
    on_disk = len(json.loads((FIXTURES / "broken.json").read_text(encoding="utf-8"))["cases"])
    assert len(NEGATIVE) == on_disk
    assert {p.name for p in VALID} >= {"valid", "product-codes"}
    units = (len(VALID) + len(NEGATIVE)) * len(OTHER)
    record_property("parity_units", units)
    record_property("valid_roots", len(VALID))
    record_property("negative_cases", len(NEGATIVE))
    record_property("locales_compared", ",".join(OTHER))
    print(f"locale parity: {len(VALID)} valid roots + {len(NEGATIVE)} negative cases x {len(OTHER)} twin locale(s) = {units} units")
    assert units > 0
