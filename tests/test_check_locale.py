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
PENDING: set = set()

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


# --- batch b: severity keyed internally, old scale, decision log ---------------------------------------------

from test_check import (DECISION_LOG_HEAD, DECISION_LOG_OK, SPRINT_LOG_OK, _new_delegated_plan,  # noqa: E402
                        _new_delegated_report, _new_two_gate_sprint, _rewrite, _rule_hits)


@pytest.fixture(autouse=True)
def _no_real_tiers(monkeypatch):
    monkeypatch.delenv("AGENT_AGILE_TIERS", raising=False)


def test_level_key_resolves_labels_of_every_locale():
    pairs = [("Chặn", "level.blocker"), ("Phải sửa", "level.must_fix"), ("Nên sửa", "level.should_fix"), ("Ghi chú", "level.note"),
             ("Blocker", "level.blocker"), ("Must fix", "level.must_fix"), ("Should fix", "level.should_fix"), ("Note", "level.note")]
    for text, key in pairs:
        assert check.level_key(text) == key, text
    assert check.level_key("Block") is None and check.level_key("Blocking") is None and check.level_key("") is None


def test_blocking_keys_are_the_two_blocking_levels():
    assert check.BLOCKING_KEYS == {"level.blocker", "level.must_fix"}
    assert check.BLOCKING == {"Chặn", "Phải sửa"}  # display form kept for existing callers


@pytest.mark.parametrize("level,code", [("Blocker", 1), ("Must fix", 1), ("Chặn", 1), ("Phải sửa", 1),
                                        ("Should fix", 0), ("Note", 0), ("Nên sửa", 0), ("Ghi chú", 0)])
def test_exit_code_works_on_severity_keys(monkeypatch, level, code):
    monkeypatch.setitem(check.RULES, "heading-missing", (level, "x"))
    finding = check.Finding(Path("PLAN.md"), 1, "heading-missing", "m")
    assert finding.level == level and finding.level_key == check.level_key(level)
    assert check.Report(findings=[finding]).exit_code == code


def _en_progress_with_table(tmp_path: Path, cell: str, locale_line):
    root = make_sprint(tmp_path)
    to_en(root)
    path = root / "PROGRESS.md"
    text = path.read_text(encoding="utf-8").rstrip("\n") + f"\n\n| Finding | Severity |\n|---|---|\n| x | {cell} |\n"
    if locale_line:
        assert "\n---\n" in text
        text = text.replace("\n---\n", f"\n{locale_line}\n---\n", 1)
    write_lf(path, text)
    return root


def _old_scale_hits(root: Path) -> list:
    return [f for f in check.check_paths([root]).findings if f.rule == "old-scale-label"]


@pytest.mark.parametrize("cell", ["NOTE", "Note"])
def test_note_is_a_level_only_when_the_document_declares_en(tmp_path, cell):
    """GC2: `NOTE` in a severity cell is the old scale unless the document's own frontmatter says `locale: en`."""
    assert _old_scale_hits(_en_progress_with_table(tmp_path / "a", cell, "locale: en")) == []
    declared_vi = _old_scale_hits(_en_progress_with_table(tmp_path / "b", cell, "locale: vi"))
    undeclared = _old_scale_hits(_en_progress_with_table(tmp_path / "c", cell, None))
    assert bool(declared_vi) is bool(undeclared) is (cell == "NOTE")  # `Note` was never flagged; `NOTE` stays flagged


def test_blocker_is_a_level_and_block_is_still_the_old_scale(tmp_path):
    for tag, locale_line in (("en", "locale: en"), ("none", None)):
        assert _old_scale_hits(_en_progress_with_table(tmp_path / f"b{tag}", "Blocker", locale_line)) == []
        assert len(_old_scale_hits(_en_progress_with_table(tmp_path / f"k{tag}", "Block", locale_line))) == 1
    for word in ("Must fix", "Should fix"):
        assert _old_scale_hits(_en_progress_with_table(tmp_path / word.replace(" ", ""), word, "locale: en")) == []


def test_old_scale_words_stay_flagged_in_english_documents(tmp_path):
    for word in ("critical", "High", "WARN"):
        assert len(_old_scale_hits(_en_progress_with_table(tmp_path / word, word, "locale: en"))) == 1, word


def test_english_severity_column_headers_are_recognised(tmp_path):
    for header in ("Severity", "Level", "Severity level"):
        root = make_sprint(tmp_path / header.replace(" ", ""))
        to_en(root)
        path = root / "PROGRESS.md"
        write_lf(path, path.read_text(encoding="utf-8").rstrip("\n") + f"\n\n| Finding | {header} |\n|---|---|\n| x | critical |\n")
        assert len(_old_scale_hits(root)) == 1, header


def _decision_report(tmp_path: Path, log, english: bool) -> Path:
    root = make_sprint(tmp_path)
    _new_delegated_report(root, log=log)
    if english:
        to_en(root)
    return root


@pytest.mark.parametrize("english", [False, True], ids=["vi", "en"])
def test_decision_log_complete_and_missing(tmp_path, english):
    ok = _decision_report(tmp_path / "ok", DECISION_LOG_OK, english)
    assert _rule_hits(ok, "decision-log-missing") == []
    missing = _decision_report(tmp_path / "no", None, english)
    assert len(_rule_hits(missing, "decision-log-missing")) == 1


@pytest.mark.parametrize("row", [
    "| Không có quyết định nào ngoài hai cổng. | — | — | — |\n",
    "| Đạt Cổng 2 | agent-d · gate-delegate · T1 | evidence/gate-2-verdict.md | git revert abc1234 |\n",
    "| Đạt Cổng 2 | agent-d · gate-delegate · T1 · Fable 5.2 | — | git revert abc1234 |\n",
    "| Đạt Cổng 2 | agent-d · gate-delegate · T1 · Fable 5.2 | evidence/gate-2-verdict.md |  |\n",
], ids=["placeholder", "no-model", "no-evidence", "no-undo"])
def test_decision_log_row_twins(tmp_path, row):
    for english in (False, True):
        root = _decision_report(tmp_path / str(english), DECISION_LOG_HEAD + row, english)
        assert len(_rule_hits(root, "decision-log-missing")) == 1, english


def test_en_decision_log_table_is_translated_and_read(tmp_path):
    root = _decision_report(tmp_path, DECISION_LOG_OK, True)
    text = (root / "REPORT.md").read_text(encoding="utf-8")
    assert "## Decision log" in text and "| Decision | Signed by | Evidence | Rollback command |" in text
    assert _rule_hits(root, "decision-log-missing") == []


@pytest.mark.parametrize("english", [False, True], ids=["vi", "en"])
def test_sprint_file_decision_log_bullet_form(tmp_path, english):
    (tmp_path / "ok").mkdir()
    (tmp_path / "bare").mkdir()
    ok = _new_two_gate_sprint(tmp_path / "ok", log=SPRINT_LOG_OK)
    bare = _new_two_gate_sprint(tmp_path / "bare", log="\n- **Nhật ký quyết định:** Không có quyết định nào ngoài hai cổng.\n")
    if english:
        to_en(ok)
        to_en(bare)
        assert "- **Decision log:**" in (ok / "SPRINT.md").read_text(encoding="utf-8")
    assert _rule_hits(ok, "decision-log-missing") == []
    assert len(_rule_hits(bare, "decision-log-missing")) == 1


def test_delegated_quote_prefix_in_english(tmp_path):
    """The quote prefix is a label: `delegated approval:` is read like `duyệt thay:`."""
    root = make_sprint(tmp_path)
    _rewrite(root / "PLAN.md", 'gate_1_quote: "duyệt"\n', 'gate_1_quote: "delegated approval: pick option a"\n')
    hits = _rule_hits(root, "gate-delegation-invalid")
    assert len(hits) == 1 and "gate_1_quote bắt đầu" in hits[0].message  # human mode with a delegated quote
    root2 = make_sprint(tmp_path / "ok")
    _new_delegated_plan(root2)
    _rewrite(root2 / "PLAN.md", "duyệt thay: chọn phương án a", "delegated approval: pick option a")
    to_en(root2)
    hits2 = [f for f in check.check_paths([root2]).findings if f.rule in ("gate-delegation-invalid", "gate-signer-independence")]
    assert not any("phải bắt đầu" in f.message for f in hits2), [f.render() for f in hits2]


# --- batch c: tiny sprint, conclusion, cap, ledger, phrase regexes (facts 1a) ---------------------------------

from test_check import (_add_fr2, _set_report, ledger_project, ledger_rules, put, two_part_sprint)  # noqa: E402
from test_check_stops import ASK_LINE, BULLETIN, _report  # noqa: E402

EN_BULLETIN = """
## Agile bulletin

- Gate 1 · Pass · Gate Delegate agent-g · `evidence/gate-1-verdict.md`
- **Number of turns the human had to answer:** 1 (Gate 1)
- **Pushed / PR:** not pushed.
- **Merge commit:** {merged}
"""


def test_en_tiny_two_part_sprint_and_conclusion(tmp_path):
    (tmp_path / "en").mkdir()
    text = lab.translate(two_part_sprint(), "en")
    assert "## 1. Work plan" in text and "## 2. Result" in text and "> **Conclusion:**" in text
    put(tmp_path / "en", "SPRINT.md", text)
    assert [f.render() for f in check.check_paths([tmp_path / "en"]).findings] == []
    broken = text.replace("## 2. Result", "## 2. Outcome")
    put(tmp_path / "en", "SPRINT.md", broken)
    assert "heading-missing" in {f.rule for f in check.check_paths([tmp_path / "en"]).findings}


def test_en_conclusion_block_is_required(tmp_path):
    root = make_sprint(tmp_path)
    to_en(root)
    path = root / "SPEC.md"
    text = path.read_text(encoding="utf-8")
    assert "> **Conclusion:**" in text and "conclusion-missing" not in {f.rule for f in check.check_paths([root]).findings}
    write_lf(path, text.replace("> **Conclusion:**", "> **Verdict:**", 1))
    assert "conclusion-missing" in {f.rule for f in check.check_paths([root]).findings}


def test_en_ask_count_line(tmp_path):
    ok = _report(tmp_path / "ok", created="2026-11-13", bulletin=EN_BULLETIN.format(merged="none."))
    to_en(ok)
    assert _rule_hits(ok, "report-missing-ask-count") == []
    no_number = _report(tmp_path / "nn", created="2026-11-13", bulletin="\n- Number of turns the human had to answer: <fill in>\n")
    to_en(no_number)
    assert len(_rule_hits(no_number, "report-missing-ask-count")) == 1
    missing = _report(tmp_path / "no", created="2026-11-13")
    to_en(missing)
    assert len(_rule_hits(missing, "report-missing-ask-count")) == 1


@pytest.mark.parametrize("merged,flagged", [
    ("merged the sprint branch into `main` (abc1234).", True),
    ("`3f2a9c1d` into main", True),
    ("merged into the main branch", True),
    ("not merged into main; waiting for a human.", False),
    ("unmerged, waiting for a human on main.", False),
    ("nothing merged yet.", False),
    ("none.", False),
], ids=["sentence", "sha-line", "main-branch", "not-merged", "unmerged", "no-main", "none"])
def test_en_conditional_pass_merged_main(tmp_path, merged, flagged):
    if merged.startswith("`3f"):
        bulletin = EN_BULLETIN.format(merged=merged)
    else:
        bulletin = EN_BULLETIN.format(merged="none.") + f"\n- Result: {merged}\n"
    root = _report(tmp_path, created="2026-11-13", bulletin=bulletin, conditional=True)
    to_en(root)
    assert bool(_rule_hits(root, "conditional-pass-merged-main")) is flagged


def test_merged_main_in_a_mixed_bulletin_and_legacy_heading(tmp_path):
    """Accept-any-locale: a Vietnamese merged line under an English bulletin heading, and the legacy bulletin heading."""
    root = _report(tmp_path / "a", created="2026-11-13", conditional=True,
                   bulletin=EN_BULLETIN.format(merged="none.") + "\n- đã gộp nhánh vào `main`.\n")
    assert len(_rule_hits(root, "conditional-pass-merged-main")) == 1
    legacy = _report(tmp_path / "b", created="2026-11-13", conditional=True,
                     bulletin=BULLETIN.format(ask=ASK_LINE, merged="đã gộp nhánh vào `main`."))
    to_en(legacy)
    assert len(_rule_hits(legacy, "conditional-pass-merged-main")) == 1


def _cap_plan(tmp_path: Path, cap: int, *, english: bool, size: str = "small") -> Path:
    root = make_sprint(tmp_path)
    _new_delegated_plan(root, cap=cap)
    _rewrite(root / "PLAN.md", "size: medium", f"size: {size}")
    if english:
        _rewrite(root / "PLAN.md", "Trần phiên: ", "Session cap: ")
        to_en(root)
    return root


@pytest.mark.parametrize("english", [False, True], ids=["vi", "en"])
def test_session_cap_line_and_over_note(tmp_path, english):
    ok = _cap_plan(tmp_path / "ok", 8, english=english)
    assert _rule_hits(ok, "session-cap-missing") == [] and _rule_hits(ok, "session-cap-over") == []
    over = _cap_plan(tmp_path / "over", 20, english=english)
    hits = _rule_hits(over, "session-cap-over")
    assert len(hits) == 1 and hits[0].level == "Ghi chú" and _rule_hits(over, "session-cap-missing") == []
    assert check.check_paths([over]).exit_code == 0
    gone = _cap_plan(tmp_path / "gone", 8, english=english)
    text = (gone / "PLAN.md").read_text(encoding="utf-8")
    write_lf(gone / "PLAN.md", re.sub(r"^(?:Trần phiên|Session cap): .*\n\n", "", text, count=1, flags=re.M))
    assert len(_rule_hits(gone, "session-cap-missing")) == 1


def test_en_raise_cap_line_silences_the_over_note(tmp_path):
    root = _cap_plan(tmp_path, 20, english=True)
    assert len(_rule_hits(root, "session-cap-over")) == 1
    log = ("\n## Decision log\n\n| Decision | Signed by | Evidence | Rollback command |\n|---|---|---|---|\n"
           "| Raise cap 8 → 20 | agent-d · gate-delegate · T1 · Fable 5.2 | evidence/gate-1-verdict.md | restore Session cap |\n")
    write_lf(root / "PLAN.md", (root / "PLAN.md").read_text(encoding="utf-8") + log)
    assert _rule_hits(root, "session-cap-over") == []
    other = _cap_plan(tmp_path / "o", 20, english=True)
    write_lf(other / "PLAN.md", (other / "PLAN.md").read_text(encoding="utf-8") + log.replace("Raise cap", "Increase of the ceiling"))
    assert len(_rule_hits(other, "session-cap-over")) == 1  # anchored: a different phrase does not silence it


def test_en_estimate_heading_bounds_the_cap_line(tmp_path):
    """The cap line counts only inside the Estimate section of a PLAN (an English heading is read like `Ước lượng`)."""
    root = _cap_plan(tmp_path, 8, english=True)
    text = (root / "PLAN.md").read_text(encoding="utf-8")
    write_lf(root / "PLAN.md", text.replace("## Estimate", "## Estimate (extra)", 1))
    assert len(_rule_hits(root, "session-cap-missing")) == 1


def test_en_self_check_phrase_allows_conditional_pass_only(tmp_path):
    root = make_sprint(tmp_path)
    _set_report(root, "qa: [T3, agent-f]", "qa: [T3, agent-e]")
    _set_report(root, "| 4 passed |", "| 4 passed; self-checked, not independent |")
    to_en(root)
    assert "qa-not-independent" in rules_of(check.check_paths([root]))  # verdict still pass
    _set_report(root, "verdict: pass", "verdict: conditional_pass")
    assert "qa-not-independent" not in rules_of(check.check_paths([root]))
    plain = make_sprint(tmp_path / "p")
    _set_report(plain, "qa: [T3, agent-f]", "qa: [T3, agent-e]")
    to_en(plain)
    assert "qa-not-independent" in rules_of(check.check_paths([plain]))


def test_en_dropped_and_not_applicable_waive_a_requirement(tmp_path):
    root = make_sprint(tmp_path)
    _add_fr2(root, "### FR2 — Lọc theo ngày (→ US1) — dropped")
    to_en(root)
    assert "report-fr-without-vr" not in rules_of(check.check_paths([root]))
    for tail in ("- dropped", "(dropped)", "— not dropped yet"):
        other = make_sprint(tmp_path / tail.replace(" ", "_").replace("(", "").replace(")", "").replace("—", "x"))
        _add_fr2(other, f"### FR2 — Lọc theo ngày (→ US1) {tail}")
        to_en(other)
        assert ("report-fr-without-vr" in rules_of(check.check_paths([other]))) is (tail == "— not dropped yet"), tail


def test_en_ledger_table_is_read(tmp_path):
    root, env = ledger_project(tmp_path)
    report = check.check_paths([root], env=env)
    assert [f.render() for f in report.findings] == []
    store = tmp_path / "store" / "order-desk.md"
    text = store.read_text(encoding="utf-8")
    assert "| Sprint |" in text  # the header word is the same in both locales
    write_lf(store, text.replace("| Sprint |", "| Sprinte |", 1))
    assert "ledger-unreadable" in ledger_rules(check.check_paths([root], env=env))


def test_phrase_regexes_are_anchored_in_english():
    assert check.MERGED_MAIN.search("merged into main") and not check.MERGED_MAIN.search("unmerged into main")
    assert not check.MERGED_MAIN.search("not merged into main") and check.MERGED_MAIN.search("đã gộp vào main")
    assert check.ASK_COUNT_LINE.search("Number of turns the human had to answer: 2")
    assert not check.ASK_COUNT_LINE.search("Number of turns the human had to answer: none")
    assert check.DROPPED.search("— dropped") and not check.DROPPED.search("— dropped yet") and check.DROPPED.search("(bỏ)")
    assert check.CONCLUSION.match("> **Conclusion:** ok") and not check.CONCLUSION.match("> **Conclusions:** ok")
