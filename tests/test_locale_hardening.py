"""SPR-33 TK5 review fixes: linear label scanning, bounded repo-config edits, capped messages, exclusive temp files."""

import json
import os
import re
import time
import uuid
from pathlib import Path

import pytest

import _common as c
import _labels as lab
import index
import init
import locale_cli
from conftest import run_script

BIG = 100_000  # a 100 KB line; the quadratic patterns needed 15 s at 50 KB
BUDGET = 1.0


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


# --- RF1 (security): no quadratic regex on long lines ----------------------------------------------------------------


LONG_LINES = {
    "heading, spaces inside": "# a" + " " * BIG + "b",
    "heading, spaces after": "## label" + " " * BIG,
    "separator, spaces": "| a |\n" + " " * BIG + "---|" + " " * BIG + "x",
    "separator, dashes": "| a |\n|" + "---|" * (BIG // 4) + " x",
    "bold, never closed": "**" + "a" * BIG,
    "code spans": "`" * BIG,
    "table row": "| " + "a | " * (BIG // 4),
}


@pytest.mark.parametrize("name", sorted(LONG_LINES))
def test_scan_and_translate_are_linear_on_long_lines(name):
    line = LONG_LINES[name]
    _, elapsed = timed(lambda: (lab.scan(line + "\n"), lab.translate(line + "\n", "en"), lab.locales_in(line + "\n")))
    assert elapsed < BUDGET, (name, elapsed)


def test_registry_locale_is_linear(tmp_path):
    text = "## a" + " " * BIG + "b\n| x |\n" + " " * BIG + "---|" + " " * BIG + "y\n"
    _, elapsed = timed(lambda: index.registry_locale(text))
    assert elapsed < BUDGET


def test_front_matter_locale_read_is_linear(tmp_path):
    doc = tmp_path / "SPEC.md"
    doc.write_bytes(("---\nlocale: a" + " " * BIG + "b\ntitle: x\n---\n").encode("utf-8"))
    _, elapsed = timed(lambda: locale_cli.read_sprint_locale(doc))
    assert elapsed < BUDGET
    folder = tmp_path / "sprint"
    folder.mkdir()
    (folder / "SPEC.md").write_bytes(doc.read_bytes())
    _, elapsed = timed(lambda: init.check_existing_locale([folder], "vi"))
    assert elapsed < BUDGET


# The old patterns are the oracle: the linear replacements must classify every short sample the same way.
OLD_HEADING = re.compile(r"^(#{1,6})([ \t]+)(\S.*?)[ \t]*$")
OLD_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
OLD_FRONT = re.compile(r"^locale[ \t]*:[ \t]*(.*?)[ \t]*$")
SAMPLES = ["", " ", "|", "||", "---", "|---|", "| --- | :---: | ---: |", "--- |", "|---", "|--|", "---|---", " | --- ", "|:---:|", "| - |",
           "|---||---|", "---:", ":---", "::---", "|  ---  |  ---", "a---", "|---|x", "\t|---|\t", "# a", "#  a  ", "#a", "# ", "#",
           "####### a", "# a b  ", "## 1.2 Title \t", "#\ta", "#  x", "locale: en", "locale:en", "locale : en  ", "locale:", "locale: 'en' ",
           "locale: a  b", "localex: en", " locale: en", "locale:\ten\t"]


@pytest.mark.parametrize("sample", SAMPLES)
def test_linear_replacements_agree_with_the_old_patterns(sample):
    assert bool(lab._is_separator(sample)) == bool(OLD_SEPARATOR.match(sample)), sample
    old = OLD_HEADING.match(sample)
    new = lab._match_heading(sample)
    assert (old is None) == (new is None), sample
    if old:
        assert old.groups() == new.groups() and old.span(3) == new.span(3), sample
    old = OLD_FRONT.match(sample)
    new = locale_cli._front_locale(sample)
    assert (old.group(1) if old else None) == new, sample


# --- RF2 (security): `set --scope repo` stays inside the repository --------------------------------------------------


@pytest.fixture
def state_env(tmp_path):
    return {"AGENT_AGILE_STATE_DIR": str(tmp_path / "state"), "CI": "", "AGENT_AGILE_NONINTERACTIVE": ""}


def set_repo(state_env, root, *extra):
    return run_script("locale_cli.py", "set", "--scope", "repo", "--locale", "en", "--root", str(root), *extra, env=state_env)


def cfg(path: Path, data=None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".agile.json").write_text(json.dumps(data or {"schema": 1}), encoding="utf-8")


def test_set_repo_edits_the_config_of_the_enclosing_repo(state_env, tmp_path):
    repo = tmp_path / "repo"
    cfg(repo)
    (repo / ".git").mkdir()
    sub = repo / "pkg" / "deep"
    sub.mkdir(parents=True)
    r = set_repo(state_env, sub)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((repo / ".agile.json").read_text(encoding="utf-8"))["locale"] == "en"


def test_set_repo_never_crosses_the_repository_root(state_env, tmp_path):
    outer = tmp_path / "outer"
    cfg(outer, {"schema": 1, "keep": "me"})
    inner = outer / "inner"
    (inner / ".git").mkdir(parents=True)
    before = (outer / ".agile.json").read_bytes()
    r = set_repo(state_env, inner)
    assert r.returncode == 2 and ".agile.json" in r.stdout + r.stderr and ".git" in r.stdout + r.stderr
    assert (outer / ".agile.json").read_bytes() == before


def test_set_repo_without_any_git_folder_only_edits_the_root_itself(tmp_path, monkeypatch):
    parent = tmp_path / "home"
    cfg(parent)
    child = parent / "child"
    child.mkdir()
    before = (parent / ".agile.json").read_bytes()
    # a folder above the temp directory may itself be a repository (a home under git): only the tmp tree counts here
    monkeypatch.setattr(locale_cli, "_is_repo_root", lambda folder: False)
    assert locale_cli.find_repo_config_bounded(child) is None
    assert locale_cli.find_repo_config_bounded(parent) == (parent / ".agile.json").resolve()
    assert (parent / ".agile.json").read_bytes() == before


def test_set_repo_monorepo_config_between_root_and_git_folder_is_found(state_env, tmp_path):
    mono = tmp_path / "mono"
    (mono / ".git").mkdir(parents=True)
    cfg(mono / "apps" / "one")
    deep = mono / "apps" / "one" / "src"
    deep.mkdir()
    assert set_repo(state_env, deep).returncode == 0
    assert json.loads((mono / "apps" / "one" / ".agile.json").read_text(encoding="utf-8"))["locale"] == "en"


def test_find_repo_config_status_walk_is_unchanged(tmp_path):
    cfg(tmp_path / "up")
    (tmp_path / "up" / "down").mkdir()
    assert locale_cli.find_repo_config(tmp_path / "up" / "down") == (tmp_path / "up" / ".agile.json").resolve()


# --- RF3 (security): bad locale values are capped in messages ---------------------------------------------------------


def test_config_problem_caps_a_huge_locale_value():
    problems = c.config_problems(c.merge_config({"locale": "x" * 1_000_000}))
    assert problems and all(len(p) < 400 for p in problems if "locale" in p)
    assert not any("x" * 100 in p for p in problems)


def test_config_problem_short_value_message_is_unchanged():
    [problem] = [p for p in c.config_problems(c.merge_config({"locale": "xx"})) if p.startswith("locale")]
    assert problem == "locale: 'xx' phải là một trong " + ", ".join(lab.shipped())


def test_check_locale_invalid_message_caps_a_huge_value(tmp_path):
    import check

    doc = tmp_path / "SPEC.md"
    doc.write_text("---\nid: SPR-01-spec\ndoc: spec\nlocale: " + "y" * 1_000_000 + "\n---\n\n# T\n", encoding="utf-8")
    report = check.check_paths([doc])
    found = [f for f in report.findings if f.rule == "locale-invalid"]
    assert found and all(len(f.message) < 400 for f in found)


# --- RF4 (security): exclusive temp file ------------------------------------------------------------------------------


def test_atomic_write_opens_its_temp_file_exclusively(tmp_path, monkeypatch):
    seen = []
    real_open = os.open

    def spy(path, flags, mode=0o777, **kw):
        seen.append((Path(path).name, flags, mode))
        return real_open(path, flags, mode, **kw)

    monkeypatch.setattr(os, "open", spy)
    locale_cli.write_atomic(tmp_path / "f.json", "{}\n")
    [(name, flags, mode)] = [s for s in seen if s[0].endswith(".tmp")]
    assert flags & os.O_EXCL and flags & os.O_CREAT and mode == 0o600


def test_atomic_write_refuses_an_existing_temp_name_and_leaves_it_alone(tmp_path, monkeypatch):
    class Fixed:
        hex = "deadbeefcafe"

    monkeypatch.setattr(uuid, "uuid4", lambda: Fixed())
    target = tmp_path / "f.json"
    target.write_text("old", encoding="utf-8")
    squatter = tmp_path / f".f.json.{os.getpid()}.deadbeef.tmp"
    squatter.write_text("not ours", encoding="utf-8")
    with pytest.raises(FileExistsError):
        locale_cli.write_atomic(target, "new")
    assert squatter.read_text(encoding="utf-8") == "not ours"
    assert target.read_text(encoding="utf-8") == "old"


def test_atomic_write_of_a_repo_config_keeps_its_mode_bits(tmp_path):
    target = tmp_path / ".agile.json"
    target.write_text("{}", encoding="utf-8")
    os.chmod(target, 0o644)
    locale_cli.write_atomic(target, "{}\n", mode=0o644)
    if os.name == "posix":
        assert (target.stat().st_mode & 0o777) == 0o644


def test_user_locale_value_is_public_and_init_uses_it(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(tmp_path / "st"))
    assert locale_cli.user_locale_value() is None
    (tmp_path / "st").mkdir()
    (tmp_path / "st" / "user-config.json").write_text('{"locale": "en"}', encoding="utf-8")
    assert locale_cli.user_locale_value() == "en" and init.user_locale() == "en"
    assert "_layer_value" not in Path(init.__file__).read_text(encoding="utf-8")
