"""`index.py` reads both locales and writes the block in the locale of the registry itself (SPR-33 TK5, FR5, GC9)."""

import json
import re
from pathlib import Path

import pytest

import _labels as lab
import index
import init
from conftest import run_script, write_lf

DATE = "2026-03-02"
VIETNAMESE = re.compile("[à-ỹ]")  # any accented Latin letter
PLANS = Path("docs") / "plans"


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(tmp_path.parent / (tmp_path.name + "-state")))


def project(root: Path, *extra: str) -> Path:
    assert init.main([str(root), "--apply", "--date", DATE, *extra]) == 0
    return root


def add_rows(path: Path, rows: list) -> None:
    text = path.read_text(encoding="utf-8")
    sep = text.index("\n", text.index("|---", text.index("\n## Timeline"))) + 1
    write_lf(path, text[:sep] + "".join(r + "\n" for r in rows) + text[sep:])


def block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[text.index(index.START):text.index(index.END)]


def sprint(root: Path, slug: str, *extra: str) -> None:
    assert init.main([str(root), "--apply", "--date", DATE, "--sprint", slug, "--title", "Goal " + slug, *extra]) == 0


# --- Vietnamese output stays as it was ----------------------------------------------------------------------------


VI_SPRINTS = """<!-- agile:open:start -->
<!-- Khối này do công cụ `index` ghi lại — đừng sửa tay. -->
| Mã | Mở | Mục tiêu | Trạng thái | Vòng | Thư mục |
|---|---|---|---|---|---|
| SPR-02 | 2026-03-02 | Goal beta | đang viết SPEC/PLAN | 0 | [2026-03-02-beta](2026-03-02-beta/) |
| SPR-01 | 2026-03-02 | Goal alpha | đang viết SPEC/PLAN | 0 | [2026-03-02-alpha](2026-03-02-alpha/) |
"""


def test_vietnamese_sprint_block_is_unchanged(tmp_path):
    root = project(tmp_path)
    sprint(root, "alpha")
    sprint(root, "beta")
    assert index.main([str(root)]) == 0
    assert block(root / PLANS / "SPRINTS.md").startswith(VI_SPRINTS)


def test_vietnamese_requests_and_specs_blocks_are_unchanged(tmp_path):
    root = project(tmp_path)
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-002 | 2026-03-02 | Hai | đang làm | FS-001 | SPR-01 |",
                                           "| RQ-001 | 2026-03-02 | Một | mới | FS-001 | SPR-01 |",
                                           "| RQ-003 | 2026-03-02 | Ba | xong | FS-001 | SPR-01 |"])
    spec = root / "docs" / "specs" / "orders.md"
    write_lf(spec, "---\nid: FS-001\ndoc: feature\ntitle: Orders\nstatus: proposed\n---\n\n# Orders\n")
    assert index.main([str(root)]) == 0
    assert block(root / PLANS / "REQUESTS.md") == (
        "<!-- agile:open:start -->\n" + index.NOTICE + "\n| Mã | Ngày | Tóm tắt | Trạng thái | Sprint |\n|---|---|---|---|---|\n"
        "| RQ-002 | 2026-03-02 | Hai | đang làm | SPR-01 |\n| RQ-001 | 2026-03-02 | Một | mới | SPR-01 |\n")
    assert "| FS-001 | Orders | đề xuất | [orders.md](orders.md) |" in block(root / "docs" / "specs" / "SPECS.md")


def test_empty_vietnamese_registry_keeps_its_sentences(tmp_path):
    root = project(tmp_path)
    before = (root / PLANS / "REQUESTS.md").read_bytes()
    assert index.main([str(root), "--check"]) == 0
    assert (root / PLANS / "REQUESTS.md").read_bytes() == before


# --- English registry -----------------------------------------------------------------------------------------


def en_project(root: Path) -> Path:
    return project(root, "--locale", "en")


def test_fresh_english_registry_is_current(tmp_path, capsys):
    root = en_project(tmp_path)
    capsys.readouterr()
    assert index.main([str(root), "--check"]) == 0
    assert "! " not in capsys.readouterr().out


def test_english_sprint_block_uses_english_columns_and_status_words(tmp_path):
    root = en_project(tmp_path)
    sprint(root, "alpha")
    assert index.main([str(root)]) == 0
    text = block(root / PLANS / "SPRINTS.md")
    assert "| Code | Opened | Goal | Status | Round | Folder |" in text
    assert "| SPR-01 | 2026-03-02 | Goal alpha | drafting SPEC/PLAN | 0 | [2026-03-02-alpha](2026-03-02-alpha/) |" in text
    assert index.NOTICES["en"] in text
    assert not VIETNAMESE.search(text)


def test_english_requests_block_reads_english_status_words(tmp_path):
    root = en_project(tmp_path)
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-003 | 2026-03-02 | Three | done | FS-001 | SPR-01 |",
                                           "| RQ-002 | 2026-03-02 | Two | in progress | FS-001 | SPR-01 |",
                                           "| RQ-001 | 2026-03-02 | One | new | FS-001 | SPR-01 |"])
    assert index.main([str(root)]) == 0
    text = block(root / PLANS / "REQUESTS.md")
    assert "| Code | Date | Summary | Status | Sprint |" in text
    assert text.index("| RQ-002 |") < text.index("| RQ-001 |") and "RQ-003" not in text
    assert not VIETNAMESE.search(text)


def test_english_specs_block(tmp_path):
    root = en_project(tmp_path)
    write_lf(root / "docs" / "specs" / "orders.md", "---\nid: FS-001\ndoc: feature\ntitle: Orders\nstatus: in_progress\n---\n\n# Orders\n")
    write_lf(root / "docs" / "specs" / "pay.md", "---\nid: FS-002\ndoc: feature\ntitle: Pay\nstatus: proposed\n---\n\n# Pay\n")
    assert index.main([str(root)]) == 0
    text = block(root / "docs" / "specs" / "SPECS.md")
    assert "| Code | Feature | Status | Living spec |" in text
    assert "| FS-002 | Pay | proposed | [pay.md](pay.md) |" in text and "| FS-001 | Orders | in progress | [orders.md](orders.md) |" in text
    assert not VIETNAMESE.search(text)


@pytest.mark.parametrize("status,word", [("drafting", "drafting SPEC/PLAN"), ("awaiting_gate_1", "awaiting Gate 1"),
                                         ("in_progress", "in progress"), ("verifying", "verifying"), ("blocked", "blocked"),
                                         ("awaiting_gate_2", "awaiting Gate 2")])
def test_every_sprint_status_has_an_english_word(tmp_path, status, word):
    root = en_project(tmp_path)
    sprint(root, "alpha")
    progress = root / PLANS / f"{DATE}-alpha" / "PROGRESS.md"
    write_lf(progress, progress.read_text(encoding="utf-8").replace("status: drafting", f"status: {status}", 1))
    index.main([str(root)])
    assert f"| {word} |" in block(root / PLANS / "SPRINTS.md")


def test_english_registry_empty_sentences(tmp_path):
    root = en_project(tmp_path)
    index.main([str(root)])
    assert lab.label("phrase.empty_requests", "en") in block(root / PLANS / "REQUESTS.md")
    assert "No features are open." in block(root / "docs" / "specs" / "SPECS.md")
    assert "No sprints are open." in block(root / PLANS / "SPRINTS.md")


def test_english_check_mode_exit_codes(tmp_path, capsys):
    root = en_project(tmp_path)
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-001 | 2026-03-02 | One | new | FS-001 | SPR-01 |"])
    assert index.main([str(root), "--check"]) == 1
    assert "! " in capsys.readouterr().out
    assert index.main([str(root)]) == 0
    assert index.main([str(root), "--check"]) == 0


def test_registry_locale_comes_from_the_registry_not_the_config(tmp_path):
    root = en_project(tmp_path)  # config says en ...
    cfg = json.loads((root / ".agile.json").read_text(encoding="utf-8"))
    cfg["locale"] = "vi"  # ... now the config says vi, the registries are still English
    write_lf(root / ".agile.json", json.dumps(cfg))
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-001 | 2026-03-02 | One | new | FS-001 | SPR-01 |"])
    index.main([str(root)])
    text = block(root / PLANS / "REQUESTS.md")
    assert "| Code | Date |" in text and not VIETNAMESE.search(text)


def test_vietnamese_registry_stays_vietnamese_whatever_the_config_says(tmp_path):
    root = project(tmp_path)
    cfg = json.loads((root / ".agile.json").read_text(encoding="utf-8"))
    cfg["locale"] = "en"
    write_lf(root / ".agile.json", json.dumps(cfg))
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-001 | 2026-03-02 | Một | mới | FS-001 | SPR-01 |"])
    index.main([str(root)])
    assert "| Mã | Ngày | Tóm tắt | Trạng thái | Sprint |" in block(root / PLANS / "REQUESTS.md")


def test_each_ledger_is_detected_on_its_own(tmp_path):
    root = en_project(tmp_path)
    text = (root / PLANS / "REQUESTS.md").read_text(encoding="utf-8")
    assert index.registry_locale(text) == "en"
    assert index.registry_locale(lab.translate(text, "vi")) == "vi"
    assert index.registry_locale("# Nothing machine-read here\n") == "vi"


# --- reading both locales -----------------------------------------------------------------------------------


def test_vietnamese_registry_accepts_english_open_status_words(tmp_path):
    root = project(tmp_path)
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-002 | 2026-03-02 | Two | in progress | FS-001 | SPR-01 |",
                                           "| RQ-001 | 2026-03-02 | One | new | FS-001 | SPR-01 |"])
    index.main([str(root)])
    text = block(root / PLANS / "REQUESTS.md")
    assert "| RQ-002 |" in text and "| RQ-001 |" in text and "| Mã | Ngày |" in text


def test_english_registry_accepts_vietnamese_open_status_words(tmp_path):
    root = en_project(tmp_path)
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-001 | 2026-03-02 | One | mới | FS-001 | SPR-01 |"])
    index.main([str(root)])
    assert "| RQ-001 |" in block(root / PLANS / "REQUESTS.md")


def test_english_column_names_in_a_vietnamese_registry_are_read(tmp_path):
    """A header row in English inside a registry whose headings are Vietnamese is still read by label key."""
    root = project(tmp_path)
    path = root / PLANS / "REQUESTS.md"
    text = path.read_text(encoding="utf-8").replace("| Mã | Ngày | Tóm tắt | Trạng thái | Tính năng | Sprint |",
                                                    "| Code | Date | Summary | Status | Feature | Sprint |", 1)
    write_lf(path, text)
    add_rows(path, ["| RQ-001 | 2026-03-02 | One | mới | FS-001 | SPR-01 |"])
    index.main([str(root)])
    assert "| RQ-001 |" in block(path)


def test_closed_requests_never_listed_in_either_locale(tmp_path):
    root = en_project(tmp_path)
    add_rows(root / PLANS / "REQUESTS.md", ["| RQ-002 | 2026-03-02 | Two | xong | FS-001 | SPR-01 |",
                                           "| RQ-001 | 2026-03-02 | One | dropped | FS-001 | SPR-01 |"])
    index.main([str(root)])
    assert lab.label("phrase.empty_requests", "en") in block(root / PLANS / "REQUESTS.md")


def test_script_runs_standalone_on_an_english_project(tmp_path):
    root = en_project(tmp_path)
    result = run_script("index.py", str(root), "--check")
    assert result.returncode == 0, result.stdout
