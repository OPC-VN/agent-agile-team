"""SPR-33 TK1: label tables (labels/vi.json, labels/en.json) and the scripts/_labels.py loader.

Covers FR1 (parity, collisions), FR2 (loader, matchers, validation) and the shared translate()/scan() walker
(GC1 anchored English matching, GC3 template coverage, GC8 one production translate function).
The module is imported lazily through _mod() so that, before it exists, every test fails on its own.
"""

from __future__ import annotations

import builtins
import importlib
import json
import re
from pathlib import Path

import pytest

from conftest import REPO

LABELS = REPO / "labels"
TEMPLATES = REPO / "templates"
GROUPS = {"heading", "column", "field", "level", "quote", "phrase", "status"}
WALK_GROUPS = {"heading", "column", "field"}
LEGACY_WORD = "auto" + "pilot"  # built in two parts so the legacy-word scan (test_legacy_allowlist) does not count this file


def _mod():
    return importlib.import_module("_labels")


def _raw(locale):
    return json.loads((LABELS / f"{locale}.json").read_text(encoding="utf-8"))


def _fold(text):
    return " ".join(text.split()).casefold()


def _all_labels():
    """(key, locale, label) for every label of every shipped locale."""
    m = _mod()
    out = []
    for locale in m.shipped():
        for key, labs in m.load(locale).items():
            for lab in labs:
                out.append((key, locale, lab))
    return out


# --- FR1: tables ---------------------------------------------------------------------------------------


def test_shipped_locales():
    assert set(_mod().shipped()) == {"vi", "en"}
    assert _mod().DEFAULT_LOCALE == "vi"


def test_key_sets_identical_and_non_empty():
    m = _mod()
    vi, en = m.load("vi"), m.load("en")
    assert set(vi) == set(en), sorted(set(vi) ^ set(en))
    assert len(vi) >= 150
    for table in (vi, en):
        for key, labs in table.items():
            assert key.split(".", 1)[0] in GROUPS, key
            assert labs and all(isinstance(x, str) and x.strip() for x in labs), key


def test_alternates_are_aligned_between_locales():
    m = _mod()
    vi, en = m.load("vi"), m.load("en")
    bad = [k for k in vi if len(vi[k]) != len(en[k])]
    assert bad == []


# Labels shared by two keys of DIFFERENT domains (labels vs words) on purpose; pinned so a new one cannot slip in.
CROSS_DOMAIN_SHARED = {"đề xuất": {"column.proposal", "status.proposed"}}


def _domain(key):
    return "label" if key.split(".", 1)[0] in WALK_GROUPS else "word"


def test_no_two_keys_of_one_domain_share_a_label():
    """FR1: inside a locale and across locales, per domain (labels: heading/column/field; words: the rest)."""
    seen = {}
    for key, locale, lab in _all_labels():
        f = _fold(lab).rstrip(":")
        assert seen.setdefault((_domain(key), f), key) == key, f"{lab!r} ({locale}) maps to {seen[(_domain(key), f)]} and {key}"


def test_cross_domain_shared_labels_are_exactly_the_pinned_ones():
    owners = {}
    for key, _locale, lab in _all_labels():
        owners.setdefault(_fold(lab).rstrip(":"), set()).add(key)
    shared = {f: ks for f, ks in owners.items() if len(ks) > 1}
    assert shared == CROSS_DOMAIN_SHARED
    m = _mod()
    assert m.key_of("Đề xuất") is None  # ambiguous without a domain
    assert m.key_of("Đề xuất", groups=m.LABEL_GROUPS) == "column.proposal"
    assert m.key_of("đề xuất", groups=m.WORD_GROUPS) == "status.proposed"
    assert m.domain_of("column.proposal") == m.LABEL_GROUPS and m.domain_of("status.proposed") == m.WORD_GROUPS


def test_every_vi_label_resolves_to_its_key():
    m = _mod()
    for key, labs in m.load("vi").items():
        for lab in labs:
            assert m.key_of(lab, groups=m.domain_of(key)) == key, (key, lab)
            assert m.exact(lab, key), (key, lab)


def test_every_en_label_resolves_anchored_to_its_key():
    m = _mod()
    for key, labs in m.load("en").items():
        for lab in labs:
            assert m.key_of(lab, groups=m.domain_of(key)) == key, (key, lab)
            assert m.exact(lab, key), (key, lab)
            # numbering, case and a trailing colon do not matter; a longer text never matches
            assert m.exact(f"2.1 {lab.rstrip(':').upper()}:", key), (key, lab)
            assert m.key_of(f"before {lab}") is None, (key, lab)
            assert m.key_of(f"{lab} after") is None, (key, lab)


def test_substring_collision_across_all_labels():
    """GC1: a label that is a substring of another label of a different key must never win by substring
    in a non-Vietnamese locale; Vietnamese keeps today's substring semantics (contains)."""
    m = _mod()
    labels = _all_labels()
    for key_b, locale_b, lab_b in labels:
        if locale_b == "vi":
            continue
        assert m.key_of(lab_b, groups=m.domain_of(key_b)) == key_b, lab_b
        for key_a in {k for k, _, _ in labels if k != key_b}:
            assert not m.contains(lab_b, key_a), f"{lab_b!r} ({key_b}) matched as {key_a}"
            assert not m.startswith(lab_b, key_a), f"{lab_b!r} ({key_b}) startswith-matched as {key_a}"


def test_anchored_english_examples():
    m = _mod()
    assert m.exact("Blocker", "level.blocker") and m.exact("Must fix", "level.must_fix")
    assert not m.exact("Blockers", "level.blocker") and not m.exact("Block", "level.blocker")
    assert not m.contains("Block", "level.blocker") and not m.contains("Blockers", "level.blocker")
    assert m.contains("Note", "level.note") and not m.contains("Notes", "level.note")
    assert not m.contains("Footnote", "level.note") and not m.contains("Remote", "level.note")
    assert m.startswith("Note: x", "level.note") and not m.startswith("Notes: x", "level.note")
    assert not m.startswith("Notebook", "level.note")
    assert m.exact("Blockers", "heading.blockers") and m.exact("Vướng mắc", "heading.blockers")
    assert m.contains("2. Reviewer findings", "heading.reviewer_findings")
    assert not m.contains("Reviewer findings (round 1)", "heading.reviewer_findings")  # anchored: whole heading only
    assert not m.contains("Review focus", "field.review")  # vi label "Review" must not hijack an English heading


def test_vietnamese_keeps_substring_semantics():
    m = _mod()
    assert m.contains("Phát hiện của reviewer (vòng 1)", "heading.reviewer_findings")
    assert m.contains("Chặn tuyệt đối", "level.blocker")
    assert m.contains("Số lượt Đức phải trả lời: 3", "field.ask_count")
    assert m.startswith("Phương án chọn: DN1 (a)", "field.delegation_chosen")
    assert m.startswith("Phương án chọn: DN1 (a)", "field.delegation_chosen", tail=":")
    assert not m.startswith("Phương án chọn DN1", "field.delegation_chosen", tail=":")
    assert m.startswith("duyệt thay: chọn a", "quote.delegated")
    assert m.startswith("delegated approval: pick a", "quote.delegated")
    assert not m.startswith("delegated approvals: pick a", "quote.delegated")


def test_note_and_blocker_keys_exist_in_both_locales():
    """GC2 at table level: the keys exist and carry the English words; handling of the old scale (Note as an
    old-scale word) is check.py work (TK3) and is not decided here."""
    m = _mod()
    assert m.alternates("level.note", "en") == ("Note",) and m.alternates("level.note", "vi") == ("Ghi chú",)
    assert m.label("level.blocker", "en") == "Blocker" and m.label("level.must_fix", "en") == "Must fix"
    assert m.label("level.should_fix", "en") == "Should fix"
    assert [m.label(k, "vi") for k in ("level.blocker", "level.must_fix", "level.should_fix")] == ["Chặn", "Phải sửa", "Nên sửa"]


def test_label_json_files_are_clean():
    for locale in ("vi", "en"):
        data = (LABELS / f"{locale}.json").read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), "BOM"
        text = data.decode("utf-8")
        assert LEGACY_WORD not in text.lower()
        assert "\r" not in text


# --- FR2: loader, validation ---------------------------------------------------------------------------


def test_invalid_locales_are_rejected():
    m = _mod()
    for bad in ("../x", "..", "", "EN", "xx", "vi/", "vi\\..\\en", None, 5, ["vi"], "vi.json", "vi\x00"):
        assert m.valid_locale(bad) is False, bad
        with pytest.raises(m.LabelError):
            m.require_locale(bad)
        with pytest.raises(m.LabelError):
            m.load(bad)
        with pytest.raises(m.LabelError):
            m.label("heading.context", bad)
        with pytest.raises(m.LabelError):
            m.translate("# x\n", bad)
    assert m.require_locale("vi") == "vi" and m.valid_locale("en") is True
    assert issubclass(m.LabelError, ValueError)


def test_unknown_key_raises_label_error():
    m = _mod()
    with pytest.raises(m.LabelError):
        m.label("heading.no_such_key", "vi")
    with pytest.raises(m.LabelError):
        m.alternates("nope", "en")
    assert m.exact("anything", "heading.no_such_key") is False


def test_labels_of_and_alternates():
    m = _mod()
    got = m.labels_of("heading.gate_2")
    assert got == {"en": ("Gate 2", "Gate 2 — acceptance"), "vi": ("Cổng 2", "Cổng 2 — nghiệm thu")}
    assert m.label("heading.gate_2", "en") == "Gate 2"
    assert m.alternates("column.level", "en")[:2] == ("Level", "Severity")


def test_load_errors_with_a_custom_directory(tmp_path):
    m = _mod()
    d = tmp_path / "labels"
    d.mkdir()
    (d / "vi.json").write_text('{"heading.a": "A", "heading.b": ["B", "B2"]}', encoding="utf-8")
    assert m.load("vi", labels_dir=d) == {"heading.a": ("A",), "heading.b": ("B", "B2")}
    assert m.shipped(labels_dir=d) == ("vi",)
    assert m.valid_locale("en", labels_dir=d) is False
    cases = {
        "en": "{not json",
        "fr": "[]",
        "de": '{"heading.a": ""}',
        "it": '{"heading.a": 5}',
        "es": '{"heading.a": []}',
        "pt": '{"heading.a": ["x", ""]}',
        "nl": '{"": "x"}',
    }
    for locale, body in cases.items():
        (d / f"{locale}.json").write_text(body, encoding="utf-8")
        with pytest.raises(m.LabelError):
            m.load(locale, labels_dir=d)
    (d / "sv.json").write_bytes(b"\xef\xbb\xbf" + b'{"heading.a": "A"}')
    with pytest.raises(m.LabelError):
        m.load("sv", labels_dir=d)
    (d / "BAD.json").write_text("{}", encoding="utf-8")
    assert "BAD" not in m.shipped(labels_dir=d)
    with pytest.raises(m.LabelError):
        m.load("ro", labels_dir=d)  # no such file


def test_import_reads_nothing(monkeypatch):
    m = _mod()

    def boom(*a, **k):
        raise AssertionError("module import touched the file system")

    monkeypatch.setattr(builtins, "open", boom)
    monkeypatch.setattr(Path, "read_text", boom)
    monkeypatch.setattr(Path, "read_bytes", boom)
    monkeypatch.setattr(Path, "iterdir", boom)
    monkeypatch.setattr(Path, "glob", boom)
    importlib.reload(m)
    monkeypatch.undo()
    importlib.reload(m)
    assert m.load("vi")  # still works afterwards


def test_regex_alternation_is_escaped():
    m = _mod()
    specials = 0
    for key, _locale, lab in _all_labels():
        pat = m.alternation(key)
        assert re.fullmatch(pat, lab, re.IGNORECASE), (key, lab)
        assert re.compile(pat)
        specials += bool(re.search(r"[()/&?.+*\[\]|·→]", lab))
    assert specials >= 10  # the tables really do contain regex metacharacters
    assert re.fullmatch(m.alternation("heading.review_retro"), "Review & Retro")
    assert not re.search(m.alternation("heading.context_risk_appetite"), "Rủi ro cần chú ý và khẩu vị  mức tự trị")
    assert m.alternation("heading.no_such_key") == ""
    assert m.alternation("heading.goal", locales=("en",)) == "Goal"


# --- translate / scan ----------------------------------------------------------------------------------


def test_translate_basic_headings_fields_and_headers():
    m = _mod()
    src = (
        "## 3. Yêu cầu chức năng\n"
        "### 1.1 Ràng buộc và lưu ý do người giao\n"
        "- **Mục tiêu sprint:** giữ nguyên chữ này\n"
        "> **Kết luận:** <!-- MỘT câu -->\n"
        "| Mã | Câu chuyện | Ưu tiên |\n"
        "|---|---|---|\n"
        "| US1 | Mục tiêu | Rủi ro |\n"
    )
    out = _mod().translate(src, "en")
    assert out == (
        "## 3. Functional requirements\n"
        "### 1.1 Constraints and notes from the requester\n"
        "- **Sprint goal:** giữ nguyên chữ này\n"
        "> **Conclusion:** <!-- MỘT câu -->\n"
        "| Code | Story | Priority |\n"
        "|---|---|---|\n"
        "| US1 | Mục tiêu | Rủi ro |\n"
    )
    assert m.translate(out, "vi") == src
    assert m.translate(src, "vi") == src and m.translate(out, "en") == out  # idempotent in its own locale


def test_translate_h1_title_and_lowercase_first():
    m = _mod()
    src = "# Tên mục tiêu sprint — Kế hoạch (PLAN)\n# Sổ tập trung — tên dự án\n# Order desk — Báo cáo (REPORT)\n## Cổng 2 — nghiệm thu\n"
    out = m.translate(src, "en")
    assert out == ("# Sprint goal name — Plan (PLAN)\n# Central ledger — project name\n"
                   "# Order desk — Report (REPORT)\n## Gate 2 — acceptance\n")
    assert m.translate(out, "vi") == src  # lowercase-first header keeps its case: byte-identical round trip


def test_translate_skips_frontmatter_fences_comments_and_data_rows():
    m = _mod()
    src = (
        "---\n"
        "title: Mục tiêu\n"
        "## Mục tiêu\n"
        "---\n"
        "## Mục tiêu\n"
        "```\n"
        "## Mục tiêu\n"
        "| Mã | Rủi ro |\n"
        "|---|---|\n"
        "```\n"
        "~~~text\n"
        "- **Vai:** x\n"
        "~~~\n"
        "<!-- ## Mục tiêu\n"
        "     - **Vai:** x\n"
        "     | Mã | Rủi ro |\n"
        "-->\n"
        "<!-- one line comment: ## Rủi ro --> ## Rủi ro\n"
        "| Rủi ro | Mức |\n"
        "|---|---|\n"
        "| Mục tiêu | Mã |\n"
        "| Vai | Rủi ro |\n"
        "\n"
        "| Mã | Rủi ro |\n"
        "no separator below so this table is not a header table\n"
        "- **Vai:** Implementer\n"
    )
    out = m.translate(src, "en")
    lines_in, lines_out = src.split("\n"), out.split("\n")
    changed = [i for i, (a, b) in enumerate(zip(lines_in, lines_out)) if a != b]
    assert len(lines_in) == len(lines_out)
    assert [lines_in[i] for i in changed] == [
        "## Mục tiêu",
        "| Rủi ro | Mức |",
        "- **Vai:** Implementer",
    ]
    assert out.split("\n")[4] == "## Goal"
    assert "<!-- one line comment: ## Rủi ro --> ## Rủi ro" in out  # text after a comment is not a heading start
    assert "| Risks | Level |" in out
    assert "| Mục tiêu | Mã |" in out and "| Vai | Rủi ro |" in out  # data rows untouched
    assert "- **Role:** Implementer" in out
    assert m.translate(out, "vi") == src


def test_translate_does_not_touch_level_phrase_or_status_words():
    m = _mod()
    src = "## Ghi chú\n| Mức | Ghi chú |\n|---|---|\n- **Chặn:** x\n"
    out = m.translate(src, "en")
    assert out == "## Ghi chú\n| Level | Ghi chú |\n|---|---|\n- **Chặn:** x\n"


def test_translate_keeps_line_endings_and_unmatched_text():
    m = _mod()
    src = "## 1. Bối cảnh\r\ntext Mục tiêu\r\n## Không có nhãn này\r\n"
    out = m.translate(src, "en")
    assert out == "## 1. Context\r\ntext Mục tiêu\r\n## Không có nhãn này\r\n"
    assert m.translate("", "en") == "" and m.translate("no newline at end", "en") == "no newline at end"
    assert m.translate("## Bối cảnh", "en") == "## Context"


def test_translate_target_must_be_valid():
    with pytest.raises(_mod().LabelError):
        _mod().translate("## x\n", "../en")


def test_scan_reports_spans():
    m = _mod()
    text = "## 2. Mục tiêu\n| Mã | Zzz |\n|---|---|\n- **Vai:** x\n"
    spans = m.scan(text)
    assert [(s.kind, s.line, s.text, s.key) for s in spans] == [
        ("heading", 0, "Mục tiêu", "heading.goal"),
        ("header", 1, "Mã", "column.code"),
        ("field", 3, "Vai", "field.role"),
    ]
    line = text.split("\n")[0]
    assert line[spans[0].start:spans[0].end] == "Mục tiêu"
    assert spans[0].entries == (("vi", 0),)
    everything = m.scan(text, all_spans=True)
    assert [s.text for s in everything if s.key is None] == ["Zzz"]


def test_locales_in_detects_mixed_documents():
    m = _mod()
    assert m.locales_in("## Mục tiêu\n| Mã | Rủi ro |\n|---|---|\n") == ("vi",)
    assert m.locales_in("## Goal\n| Code | Risks |\n|---|---|\n") == ("en",)
    assert m.locales_in("## Goal\n| Mã | Rủi ro |\n|---|---|\n") == ("en", "vi")
    assert m.locales_in("## SPEC\n| Sprint | Link |\n|---|---|\n") == ()  # labels shared by both locales say nothing
    assert m.locales_in("plain text\n") == ()


def _template_files():
    return sorted(p for p in TEMPLATES.rglob("*") if p.is_file() and p.suffix in {".md", ".json"})


def test_translate_round_trip_is_byte_identical_on_every_template():
    m = _mod()
    files = _template_files()
    assert len(files) >= 15
    for path in files:
        raw = path.read_bytes().decode("utf-8")
        en = m.translate(raw, "en")
        assert m.translate(en, "vi") == raw, path.relative_to(REPO).as_posix()
        assert m.translate(raw, "vi") == raw, path.relative_to(REPO).as_posix()


# Template headings and header cells that no table covers on purpose: example content, README prose headings, repo skeleton.
ALLOWED_UNMATCHED = {
    "TK1 — Hàm tra cứu đơn (→ FR1.1, FR1.2)",
    "TK2 — Màn hình tra cứu (→ FR1.1, SC1)",
    "FR1 — Tra đơn theo mã (→ US1)",
    "FR1 — Tra đơn theo mã (từ SPR-01)",
}


def test_every_machine_read_template_heading_and_header_is_in_the_tables():
    """GC3: the tables cover every heading and table header of the sprint and registry templates, not only those
    check.py matches. Contract and skeleton docs (README files, repo-skeleton) are prose and are excluded."""
    m = _mod()
    missing = []
    for path in _template_files():
        rel = path.relative_to(TEMPLATES).as_posix()
        if path.suffix != ".md" or rel.startswith("repo-skeleton/") or rel == "README.md":
            continue
        for span in m.scan(path.read_bytes().decode("utf-8"), all_spans=True):
            if span.key is None and span.kind in {"heading", "header"} and span.text not in ALLOWED_UNMATCHED:
                missing.append((rel, span.line + 1, span.kind, span.text))
    assert missing == []


def test_en_render_of_sprint_templates_has_no_vietnamese_machine_labels():
    m = _mod()
    for path in sorted((TEMPLATES / "sprint").glob("*.md")) + sorted((TEMPLATES / "registry").glob("*.md")):
        en = m.translate(path.read_bytes().decode("utf-8"), "en")
        assert "vi" not in m.locales_in(en), path.name


# --- review round 1 (RF1, RF2, RF5) --------------------------------------------------------------------


def test_ascii_vietnamese_labels_do_not_match_english_substrings():
    """RF1: vi labels that are ASCII-only or equal to the English label (PR, Review, PLAN, ...) match anchored."""
    m = _mod()
    assert not m.contains("Approved", "field.pr")
    assert not m.contains("Preview", "field.review")
    assert not m.contains("Plan review notes", "heading.part_plan")
    assert not m.contains("Link checker", "column.link") and not m.contains("Sprinting", "column.sprint")
    assert not m.startswith("Preview: x", "field.review") and not m.startswith("PRD: x", "field.pr")
    assert m.contains("2. PLAN", "heading.part_plan") and m.contains("Timeline", "heading.timeline")
    assert m.contains("Review", "field.review") and m.startswith("Review: ok", "field.review")
    assert m.contains("Số lượt Đức phải trả lời: 3", "field.ask_count")  # accented Vietnamese keeps substring


def test_author_heading_is_a_label():
    m = _mod()
    assert m.exact("Tác giả", "heading.author") and m.exact("Author", "heading.author")
    assert m.translate("## Tác giả\n", "en") == "## Author\n" and m.translate("## Author\n", "vi") == "## Tác giả\n"


def test_documented_limits_of_translate():
    m = _mod()
    assert m.translate("## 3.Rủi ro\n", "en") == "## 3.Rủi ro\n"  # no space after the number: not a label
    assert m.translate("## RỦI RO\n", "en") == "## Risks\n"
    assert m.translate("## Risks\n", "vi") == "## Rủi ro\n"  # the round trip is byte-identical only for template casing


# --- RF2: pin the labels to the real constants of check.py and index.py ----------------------------------


def _check():
    return importlib.import_module("check")


def _index():
    return importlib.import_module("index")


def test_check_constants_resolve_to_their_keys():
    m, c = _mod(), _check()
    pins = [
        (c.DELEGATION_RECORD, "heading.delegation_record"),
        (c.DELEGATION_LABELS[0], "field.delegation_chosen"),
        (c.DELEGATION_LABELS[1], "field.delegation_rejected"),
        (c.DELEGATION_LABELS[2], "field.delegation_cost_if_wrong"),
        (c.FLOOR_TABLE_HEADING, "heading.floor_files"),
        (c.DELEGATION_QUOTE, "quote.delegated"),
        (c.PLAIN_SUMMARY_HEADING, "heading.plain_summary"),
        (c.PLAN_GOAL_LABELS[0], "field.plan_goal"),
        (c.PLAN_GOAL_LABELS[1], "field.plan_desired_result"),
        (c.PLAN_GOAL_LABELS[2], "field.plan_risk_watch"),
        (c.INPUT_FIELD, "field.input"),
        (c.OUTPUT_FIELD, "field.output"),
        (c.PARALLEL_MARK, "phrase.parallel_with"),
        (c.SELF_CHECK, "phrase.self_check"),
        (c.SPRINT_TINY_HEADINGS[0], "heading.tiny_plan"),
        (c.SPRINT_TINY_HEADINGS[1], "heading.result"),
        (c.CHAN, "level.blocker"),
        (c.PHAI, "level.must_fix"),
        (c.NEN, "level.should_fix"),
        (c.GHI, "level.note"),
        (c.BULLETIN_HEADINGS[0], "heading.bulletin"),
        # literals inside check.py code (facts-1 section 1a), pinned by hand
        ("ước lượng", "heading.estimate"),
        ("nhật ký quyết định", "heading.decision_log"),
        ("nâng trần", "phrase.raise_cap"),
        ("trần phiên", "field.session_cap"),
        ("ai ký", "column.signed_by"),
        ("bằng chứng", "column.evidence"),
        ("lệnh hoàn tác", "column.rollback_command"),
        ("mã", "column.code"),
        ("người quyết", "column.owner"),
        ("Truy vết", "heading.traceability"),
        ("đã gộp", "phrase.merged"),
        ("nhánh chính", "phrase.main_branch"),
        ("bỏ", "phrase.dropped"),
    ]
    for text, key in pins:
        assert m.exact(text, key), (text, key)
        assert m.key_of(text, groups=m.domain_of(key)) == key, (text, key)
    assert {_fold(x) for x in m.alternates("column.level", "vi")} == c.SEVERITY_HEADERS_VI


def test_required_headings_resolve_to_their_keys():
    m, c = _mod(), _check()
    expected = {
        "spec": ["context", "user_stories", "functional_requirements", "success_criteria", "out_of_scope", "clarification_questions"],
        "plan": ["goal", "architecture", "common_constraints", "review_focus", "tasks", "risks", "human_decisions", "estimate"],
        "progress": ["status_table", "log", "blockers", "current_review_round"],
        "report": ["plain_summary", "verification_results", "reviewer_findings", "remaining_risks", "usage_changes_rollback",
                   "lessons", "leftovers", "review_retro", "gate_2"],
        "sprint": ["part_spec", "part_plan", "part_progress", "part_report"],
        "feature": ["current_behaviour", "criteria_in_force", "known_limits", "related_decisions", "sprint_history"],
        "requests": ["open", "timeline"],
        "sprints": ["open", "timeline"],
        "specs": ["open", "catalog"],
    }
    assert set(expected) == set(c.REQUIRED_HEADINGS)
    for doc, keys in expected.items():
        assert len(keys) == len(c.REQUIRED_HEADINGS[doc]), doc
        for phrase, name in zip(c.REQUIRED_HEADINGS[doc], keys):
            assert m.exact(phrase, f"heading.{name}"), (doc, phrase, name)


def test_index_constants_resolve_to_their_keys():
    m, i = _mod(), _index()
    # TK5: index.py holds label keys, not Vietnamese words; these are the words it printed at db1f34a, pinned byte for byte.
    sprint_words = {"drafting": "đang viết SPEC/PLAN", "awaiting_gate_1": "chờ Cổng 1", "in_progress": "đang làm",
                    "verifying": "đang kiểm định", "blocked": "vướng", "awaiting_gate_2": "chờ Cổng 2"}
    assert set(i.SPRINT_LABEL) == set(sprint_words)
    for state, key in i.SPRINT_LABEL.items():
        assert key == f"status.{state}" and m.label(key, "vi") == sprint_words[state], state
    assert {s: m.label(k, "vi") for s, k in i.FEATURE_LABEL.items()} == {"proposed": "đề xuất", "in_progress": "đang làm"}
    assert {m.label(k, "vi") for k in i.OPEN_REQUEST} == {"mới", "đang làm"}
    for name, sentence in {"requests": "Không có yêu cầu nào đang mở.", "specs": "Không có tính năng nào đang mở.",
                           "sprints": "Không có sprint nào đang mở."}.items():
        assert i.empty_block(name, "vi") == [sentence], name
    for text, key in [("Trạng thái", "column.status"), ("Mã", "column.code"), ("Tính năng", "column.feature"),
                      ("Mở", "column.opened"), ("Mục tiêu", "heading.goal"), ("Spec sống", "column.living_spec"),
                      ("Ngày", "column.date"), ("Tóm tắt", "column.summary"), ("Vòng", "column.round"), ("Thư mục", "column.folder")]:
        assert m.exact(text, key), (text, key)
