"""`init.py --locale` (SPR-33 TK5): rendering per locale, `locale:` front matter, registry locale, refusal on an
existing sprint, path safety. The Vietnamese output without the flag stays byte-identical to db1f34a (GC3)."""

import hashlib
import json
from pathlib import Path

import pytest

import _common as c
import _labels as lab
import check
import init
import locale_cli
from conftest import FIXTURES, write_lf

DATE = "2026-03-02"
TITLE = "Order lookup"
GOLDEN = json.loads((FIXTURES / "init_vi_golden.json").read_text(encoding="utf-8"))
COMBOS = {
    "ledgers_only": [],
    "medium": ["--sprint", "order-lookup"],
    "tiny": ["--sprint", "order-lookup", "--tiny"],
    "small": ["--sprint", "order-lookup", "--size", "small"],
    "large": ["--sprint", "order-lookup", "--size", "large"],
    "high": ["--sprint", "order-lookup", "--size", "large", "--risk", "high", "--risk-tags", "auth,secret"],
    "reqfeat": ["--sprint", "order-lookup", "--request", "RQ-003", "--feature", "FS-002"],
}
SHAPES = {"tiny": ["--tiny"], "small": ["--size", "small"], "medium": [], "large": ["--size", "large"]}


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """No test reads the real user config: the state directory is an empty folder next to the project."""
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(tmp_path.parent / (tmp_path.name + "-state")))


def files_of(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def run(root: Path, *extra: str, title: str = TITLE, sprint: str = "order-lookup") -> int:
    return init.main([str(root), "--apply", "--date", DATE, "--sprint", sprint, "--title", title, *extra])


def sprint_folder(root: Path, sprint: str = "order-lookup") -> Path:
    return root / "docs" / "plans" / f"{DATE}-{sprint}"


def serious(root: Path) -> list:
    report = check.check_paths([root])
    return [f.render() for f in report.findings]


@pytest.mark.parametrize("name", sorted(COMBOS))
def test_plain_vi_run_is_byte_identical_to_db1f34a(tmp_path, name):
    """Golden của lần chạy `vi` thường. Hai mục KHÔNG còn giống db1f34a, đã ghim lại có chủ ý (SPR-35 TK2): `tiny` (file ra đổi thành `TASK.md`,
    `doc: task`, nhãn H1 mới) và `small` (một dòng comment mẫu `SPRINT.md` trỏ `TASK.md` thay `SPRINT-tiny.md`); các mục khác vẫn
    byte-identical với db1f34a."""
    root = tmp_path / "p"
    root.mkdir()
    argv = [str(root), "--apply", "--date", DATE, *COMBOS[name]]
    if COMBOS[name]:
        argv += ["--title", "Tra đơn | nhanh"]
    assert init.main(argv) == 0
    got = {rel: hashlib.sha256(data).hexdigest() for rel, data in files_of(root).items()}
    assert got == GOLDEN[name]
    assert all(b"locale" not in data for rel, data in files_of(root).items() if rel.endswith(".md"))


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_en_output_has_zero_findings(tmp_path, shape):
    assert init.main([str(tmp_path), "--apply", "--date", DATE, "--locale", "en", "--sprint", "order-lookup",
                      "--title", TITLE, *SHAPES[shape]]) == 0
    assert serious(tmp_path) == []
    docs = [p for p in sprint_folder(tmp_path).glob("*.md")]
    assert docs and all(c.parse_frontmatter(p.read_text(encoding="utf-8")).data["locale"] == "en" for p in docs)


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_title_lands_in_the_first_heading_of_every_document(tmp_path, shape):
    run(tmp_path, "--locale", "en", *SHAPES[shape], title="Order lookup")
    for path in sprint_folder(tmp_path).glob("*.md"):
        lines = path.read_text(encoding="utf-8").split(chr(10))
        first = next(line for line in lines[lines.index("---", 1):] if line.startswith("# "))
        assert first.startswith("# Order lookup — "), path.name


def test_en_high_risk_large_has_zero_findings(tmp_path):
    assert run(tmp_path, "--locale", "en", "--size", "large", "--risk", "high", "--risk-tags", "auth,secret") == 0
    assert serious(tmp_path) == []


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_en_headings_are_english_and_vietnamese_machine_labels_are_gone(tmp_path, shape):
    run(tmp_path, "--locale", "en", *SHAPES[shape])
    for path in sprint_folder(tmp_path).glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert lab.locales_in(text) == ("en",), path.name
    ledger = (tmp_path / "docs" / "plans" / "SPRINTS.md").read_text(encoding="utf-8")
    assert "## Open" in ledger.split(chr(10))  # a fresh repo records the flag in its config, so the ledgers are English too
    assert lab.locales_in(ledger) == ("en",)


def test_explicit_vi_writes_locale_vi_and_nothing_else_differs(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    run(a)
    run(b, "--locale", "vi")
    fa, fb = files_of(a), files_of(b)
    assert set(fa) == set(fb)
    for rel in fa:
        if rel.endswith(".md") and "order-lookup" in rel:
            assert fa[rel] != fb[rel]
            lines = fb[rel].decode("utf-8").split("\n")
            assert "locale: vi" in lines
            lines.remove("locale: vi")
            assert "\n".join(lines).encode("utf-8") == fa[rel], rel


def test_en_rendering_is_the_shared_translate_over_the_vietnamese_skeleton(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    run(a)
    run(b, "--locale", "en")
    for path in sprint_folder(a).glob("*.md"):
        vi = path.read_text(encoding="utf-8")
        en = (sprint_folder(b) / path.name).read_text(encoding="utf-8")
        lines = en.split("\n")
        lines.remove("locale: en")
        assert "\n".join(lines) == lab.translate(vi, "en"), path.name


def test_repo_config_locale_en_drives_sprint_and_new_ledgers(tmp_path):
    write_lf(tmp_path / ".agile.json", json.dumps({"schema": 1, "locale": "en"}))
    assert init.main([str(tmp_path), "--apply", "--date", DATE]) == 0
    for rel in ("REQUESTS.md", "SPRINTS.md"):
        text = (tmp_path / "docs" / "plans" / rel).read_text(encoding="utf-8")
        lines = text.split(chr(10))
        assert "## Open" in lines and "## Đang mở" not in lines
    assert "## Catalog" in (tmp_path / "docs" / "specs" / "SPECS.md").read_text(encoding="utf-8")
    assert run(tmp_path) == 0
    doc = (sprint_folder(tmp_path) / "PROGRESS.md").read_text(encoding="utf-8")
    assert c.parse_frontmatter(doc).data["locale"] == "en"
    assert serious(tmp_path) == []


def test_user_config_locale_applies_when_repo_declares_nothing(tmp_path, monkeypatch):
    state = tmp_path.parent / (tmp_path.name + "-state")
    state.mkdir(parents=True, exist_ok=True)
    write_lf(state / "user-config.json", json.dumps({"locale": "en"}))
    assert run(tmp_path) == 0
    doc = (sprint_folder(tmp_path) / "SPEC.md").read_text(encoding="utf-8")
    assert c.parse_frontmatter(doc).data["locale"] == "en"
    ledger = (tmp_path / "docs" / "plans" / "SPRINTS.md").read_text(encoding="utf-8").split(chr(10))
    assert "## Đang mở" in ledger  # ledgers follow the repo config only (GC9)


def test_repo_vi_beats_user_en_and_stays_byte_identical(tmp_path):
    state = tmp_path.parent / (tmp_path.name + "-state")
    state.mkdir(parents=True, exist_ok=True)
    write_lf(state / "user-config.json", json.dumps({"locale": "en"}))
    write_lf(tmp_path / ".agile.json", json.dumps({"schema": 1, "locale": "vi"}))
    assert run(tmp_path, title="Tra đơn | nhanh") == 0
    doc = (sprint_folder(tmp_path) / "PROGRESS.md").read_text(encoding="utf-8")
    assert "locale" not in doc


def test_explicit_flag_beats_repo_config(tmp_path):
    write_lf(tmp_path / ".agile.json", json.dumps({"schema": 1, "locale": "en"}))
    assert run(tmp_path, "--locale", "vi") == 0
    doc = (sprint_folder(tmp_path) / "PROGRESS.md").read_text(encoding="utf-8")
    assert c.parse_frontmatter(doc).data["locale"] == "vi" and "Tiến độ" in doc


def test_fresh_repo_with_explicit_locale_records_it_in_the_new_config(tmp_path):
    assert init.main([str(tmp_path), "--apply", "--date", DATE, "--locale", "en"]) == 0
    cfg = json.loads((tmp_path / ".agile.json").read_text(encoding="utf-8"))
    assert cfg["locale"] == "en"
    assert c.config_problems(c.merge_config(cfg)) == []
    assert "## Open" in (tmp_path / "docs" / "plans" / "REQUESTS.md").read_text(encoding="utf-8")


def test_existing_config_is_never_rewritten_for_the_flag(tmp_path):
    init.main([str(tmp_path), "--apply", "--date", DATE])
    before = (tmp_path / ".agile.json").read_bytes()
    run(tmp_path, "--locale", "en")
    assert (tmp_path / ".agile.json").read_bytes() == before


def test_ledger_row_goes_under_the_english_timeline(tmp_path):
    run(tmp_path, "--locale", "en")
    ledger = (tmp_path / "docs" / "plans" / "SPRINTS.md").read_text(encoding="utf-8")
    assert f"| SPR-01 | {DATE} |  | {TITLE} |  | [{DATE}-order-lookup]({DATE}-order-lookup/) |" in ledger
    head = ledger.index("| Code |")
    assert head < ledger.index("| SPR-01 |"), "the real row sits under the English header"


# --- GC7: an existing sprint refuses a conflicting --locale ---------------------------------------------------


def test_existing_en_sprint_refuses_vi(tmp_path, capsys):
    run(tmp_path, "--locale", "en")
    before = files_of(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "--locale", "vi") == 2
    out = capsys.readouterr().out
    assert "en" in out and "vi" in out
    assert files_of(tmp_path) == before


def test_existing_sprint_without_locale_key_is_vi_and_refuses_en(tmp_path):
    run(tmp_path)
    before = files_of(tmp_path)
    assert run(tmp_path, "--locale", "en") == 2
    assert files_of(tmp_path) == before


def test_existing_sprint_refuses_on_dry_run_too(tmp_path):
    run(tmp_path)
    assert init.main([str(tmp_path), "--date", DATE, "--sprint", "order-lookup", "--title", TITLE, "--locale", "en"]) == 2


@pytest.mark.parametrize("first,again", [(("--locale", "en"), ("--locale", "en")), ((), ("--locale", "vi")), ((), ()),
                                         (("--locale", "en"), ()), (("--locale", "vi"), ("--locale", "vi"))])
def test_existing_sprint_same_or_absent_locale_is_a_no_op(tmp_path, first, again):
    run(tmp_path, *first)
    before = files_of(tmp_path)
    assert run(tmp_path, *again) == 0
    assert files_of(tmp_path) == before


def test_existing_sprint_conflict_in_any_document_refuses(tmp_path):
    run(tmp_path, "--locale", "en")
    plan = sprint_folder(tmp_path) / "PLAN.md"
    write_lf(plan, plan.read_text(encoding="utf-8").replace("locale: en\n", "locale: vi\n", 1))
    before = files_of(tmp_path)
    assert run(tmp_path, "--locale", "en") == 2
    assert files_of(tmp_path) == before


# --- path safety --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["xx", "../x", "..\\x", "en/..", "EN", "e", "english", "en\n", ""])
def test_unknown_or_path_like_locale_is_refused_and_writes_nothing(tmp_path, bad, capsys):
    assert init.main([str(tmp_path), "--apply", "--date", DATE, "--locale", bad]) == 2
    assert "locale" in capsys.readouterr().out
    assert files_of(tmp_path) == {}
    assert run(tmp_path, "--locale", bad) == 2
    assert files_of(tmp_path) == {}


def test_help_text_is_english_and_names_the_shipped_locales(capsys):
    with pytest.raises(SystemExit):
        init.main(["--help"])
    out = capsys.readouterr().out
    assert "--locale" in out and "vi" in out and "en" in out


def test_locale_cli_helpers_are_the_state_source(tmp_path, monkeypatch):
    """init reads the user config through locale_cli, so AGENT_AGILE_STATE_DIR applies the same way."""
    assert locale_cli.user_config_path().parent == tmp_path.parent / (tmp_path.name + "-state")


# --- GC3 read as "en findings == vi findings" (DN3): a date after PLAIN_SUMMARY_EFFECTIVE makes the rule run ------------------

LATE = "2026-11-16"
FINDING_SHAPES = {**SHAPES, "large_high": ["--size", "large", "--risk", "high", "--risk-tags", "auth,secret"]}


def findings_of(root: Path) -> list:
    from collections import Counter

    report = check.check_paths([root])
    return sorted(Counter((f.rule, f.level) for f in report.findings).items())


@pytest.mark.parametrize("shape", sorted(FINDING_SHAPES))
def test_en_findings_equal_vi_findings_on_a_date_where_plain_summary_runs(tmp_path, shape):
    vi, en = tmp_path / "vi", tmp_path / "en"
    vi.mkdir(), en.mkdir()
    for root, extra in ((vi, []), (en, ["--locale", "en"])):
        assert init.main([str(root), "--apply", "--date", LATE, "--sprint", "order-lookup", "--title", TITLE,
                          *FINDING_SHAPES[shape], *extra]) == 0
    assert findings_of(en) == findings_of(vi), shape
    expected = [] if shape in ("tiny", "small") else [(("plain-summary", "Nên sửa"), 2)]  # the skeleton's empty summary section
    assert findings_of(vi) == expected
