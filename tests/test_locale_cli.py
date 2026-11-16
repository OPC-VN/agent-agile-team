"""SPR-33 TK2: locale resolution (_labels.resolve_locale), scripts/locale_cli.py, and the `locale` config key.

Covers FR4 (five-layer precedence, old record = vi, non-interactive, ask once, set twice) and FR6 (`locale` in
.agile.json is absent by default and validated). Tests never touch the real state directory: every CLI run gets
AGENT_AGILE_STATE_DIR pointing at a tmp path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from conftest import REPO, SCRIPTS, run_script

import _common as c
import _labels as lb


def _cli_mod():
    import importlib

    return importlib.import_module("locale_cli")


@pytest.fixture
def env(tmp_path):
    state = tmp_path / "state"
    e = {"AGENT_AGILE_STATE_DIR": str(state)}
    for name in ("CI", "AGENT_AGILE_NONINTERACTIVE"):
        e[name] = ""  # run_script merges onto os.environ; an empty value counts as not set
    return e, state


def cli(env, *args, cwd=None):
    e, _ = env
    r = run_script("locale_cli.py", *args, env=e, cwd=cwd)
    return r


def status_json(env, *args, cwd=None):
    r = cli(env, "status", "--json", *args, cwd=cwd)
    assert r.returncode == 0, r.stderr + r.stdout
    return json.loads(r.stdout)


def make_repo(tmp_path, cfg=None):
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".agile.json").write_text(json.dumps(cfg if cfg is not None else {"schema": 1}), encoding="utf-8")
    return root


# --- resolve_locale: five layers ------------------------------------------------------------------------------


def test_resolve_default_is_vi():
    r = lb.resolve_locale()
    assert (r.locale, r.source, r.ignored) == ("vi", "default", [])


def test_old_record_without_declaration_is_vi():
    r = lb.resolve_locale(explicit=None, sprint=None, repo=None, user=None)
    assert r.locale == "vi" and r.source == "default"


LAYERS = ("explicit", "sprint", "repo", "user")


@pytest.mark.parametrize("top", range(4))
def test_precedence_each_layer_overrides_all_lower_ones(top):
    # Layer `top` says en; every lower layer says vi: en wins. Layers above `top` are absent.
    kwargs = {name: ("en" if i == top else "vi") for i, name in enumerate(LAYERS) if i >= top}
    r = lb.resolve_locale(**kwargs)
    assert (r.locale, r.source) == ("en", LAYERS[top])


@pytest.mark.parametrize("top", range(4))
def test_precedence_vi_over_lower_en(top):
    kwargs = {name: ("vi" if i == top else "en") for i, name in enumerate(LAYERS) if i >= top}
    r = lb.resolve_locale(**kwargs)
    assert (r.locale, r.source) == ("vi", LAYERS[top])


def test_invalid_lower_layer_is_ignored_with_reason():
    r = lb.resolve_locale(sprint="fr", repo="en")
    assert r.locale == "en" and r.source == "repo"
    assert len(r.ignored) == 1 and r.ignored[0][0] == "sprint" and r.ignored[0][1] == "fr" and r.ignored[0][2]


@pytest.mark.parametrize("bad", ["../x", "en/../vi", "", 5, ["en"], "EN", {"en": 1}])
def test_invalid_lower_layers_never_crash(bad):
    for layer in ("sprint", "repo", "user"):
        r = lb.resolve_locale(**{layer: bad})
        assert r.locale == "vi" and r.source == "default"
        assert [i[0] for i in r.ignored] == [layer]


def test_invalid_explicit_is_an_error():
    with pytest.raises(lb.LabelError):
        lb.resolve_locale(explicit="fr")
    with pytest.raises(lb.LabelError):
        lb.resolve_locale(explicit="../x")


def test_frozen_sprint_locale_beats_repo_and_user():
    r = lb.resolve_locale(sprint="vi", repo="en", user="en")
    assert (r.locale, r.source) == ("vi", "sprint")


# --- CLI: status / set ----------------------------------------------------------------------------------------


def test_status_fresh_machine_asks(env, tmp_path):
    root = make_repo(tmp_path)
    s = status_json(env, "--root", str(root))
    assert s["locale"] == "vi" and s["source"] == "default"
    assert s["ask_needed"] is True and s["interactive"] is True and s["locale_asked"] is False


def test_status_non_interactive_flag_does_not_ask_and_writes_nothing(env, tmp_path):
    root = make_repo(tmp_path)
    s = status_json(env, "--root", str(root), "--non-interactive")
    assert s["ask_needed"] is False and s["locale"] == "vi" and s["interactive"] is False
    assert not env[1].exists()


@pytest.mark.parametrize("var", ["CI", "AGENT_AGILE_NONINTERACTIVE"])
def test_status_non_interactive_env_does_not_ask(env, tmp_path, var):
    e, state = env
    e = dict(e)
    e[var] = "1"
    root = make_repo(tmp_path)
    s = status_json((e, state), "--root", str(root))
    assert s["ask_needed"] is False and s["interactive"] is False
    assert not state.exists()


def test_status_repo_locale_means_no_ask(env, tmp_path):
    root = make_repo(tmp_path, {"schema": 1, "locale": "en"})
    s = status_json(env, "--root", str(root))
    assert (s["locale"], s["source"], s["ask_needed"]) == ("en", "repo", False)


def test_ask_once_flow(env, tmp_path):
    root = make_repo(tmp_path)
    assert status_json(env, "--root", str(root))["ask_needed"] is True
    r = cli(env, "set", "--scope", "user", "--locale", "vi", "--root", str(root))  # "no answer" path writes vi
    assert r.returncode == 0, r.stderr
    s = status_json(env, "--root", str(root))
    assert s["ask_needed"] is False and s["locale_asked"] is True and s["locale"] == "vi"
    data = json.loads((env[1] / "user-config.json").read_text(encoding="utf-8"))
    assert data == {"locale": "vi", "locale_asked": True}


def test_set_twice_keeps_semantics(env, tmp_path):
    root = make_repo(tmp_path)
    cli(env, "set", "--scope", "user", "--locale", "en", "--root", str(root))
    cli(env, "set", "--scope", "user", "--locale", "en", "--root", str(root))
    data = json.loads((env[1] / "user-config.json").read_text(encoding="utf-8"))
    assert data == {"locale": "en", "locale_asked": True}
    s = status_json(env, "--root", str(root))
    assert (s["locale"], s["source"], s["ask_needed"]) == ("en", "user", False)
    cli(env, "set", "--scope", "user", "--locale", "vi", "--root", str(root))
    assert json.loads((env[1] / "user-config.json").read_text(encoding="utf-8")) == {"locale": "vi", "locale_asked": True}


def test_corrupt_user_config_resolves_vi_and_reports(env, tmp_path):
    root = make_repo(tmp_path)
    state = env[1]
    state.mkdir()
    (state / "user-config.json").write_bytes(b"{not json")
    s = status_json(env, "--root", str(root))
    assert s["locale"] == "vi" and s["problems"] and "user-config.json" in s["problems"][0]
    r = cli(env, "status", "--root", str(root))
    assert r.returncode == 0 and "user-config.json" in (r.stdout + r.stderr)


def test_user_config_top_level_not_object_reports(env, tmp_path):
    root = make_repo(tmp_path)
    env[1].mkdir()
    (env[1] / "user-config.json").write_text("[1]", encoding="utf-8")
    s = status_json(env, "--root", str(root))
    assert s["locale"] == "vi" and s["problems"]


def test_invalid_user_locale_value_ignored_with_reason(env, tmp_path):
    root = make_repo(tmp_path)
    env[1].mkdir()
    (env[1] / "user-config.json").write_text(json.dumps({"locale": "fr", "locale_asked": True}), encoding="utf-8")
    s = status_json(env, "--root", str(root))
    assert s["locale"] == "vi" and s["ignored"] and s["ignored"][0]["layer"] == "user"


def test_explicit_locale_flag_wins_and_invalid_is_exit_2(env, tmp_path):
    root = make_repo(tmp_path, {"schema": 1, "locale": "vi"})
    assert status_json(env, "--root", str(root), "--locale", "en")["source"] == "explicit"
    r = cli(env, "status", "--root", str(root), "--locale", "fr")
    assert r.returncode == 2


def test_sprint_frontmatter_layer_via_cli(env, tmp_path):
    root = make_repo(tmp_path, {"schema": 1, "locale": "vi"})
    doc = root / "SPRINT.md"
    doc.write_text("---\nid: SPR-01\nlocale: en\n---\n\n# x\n", encoding="utf-8")
    s = status_json(env, "--root", str(root), "--sprint-file", str(doc))
    assert (s["locale"], s["source"]) == ("en", "sprint")
    old = root / "OLD.md"
    old.write_text("---\nid: SPR-00\n---\n\n# x\n", encoding="utf-8")
    s2 = status_json(env, "--root", str(root), "--sprint-file", str(old))
    assert (s2["locale"], s2["source"]) == ("vi", "repo")


@pytest.mark.parametrize("bad", ["../x", "en/../vi", "fr", "EN", "", "e", "en\\vi", "/etc"])
def test_set_rejects_path_like_and_unknown(env, tmp_path, bad):
    root = make_repo(tmp_path)
    for scope in ("user", "repo"):
        r = cli(env, "set", "--scope", scope, "--locale", bad, "--root", str(root))
        assert r.returncode == 2, (scope, bad, r.stdout, r.stderr)
    assert not env[1].exists()
    assert json.loads((root / ".agile.json").read_text(encoding="utf-8")) == {"schema": 1}


def test_set_repo_outside_repo_rejected(env, tmp_path):
    lone = tmp_path / "lone"
    lone.mkdir()
    r = cli(env, "set", "--scope", "repo", "--locale", "en", "--root", str(lone))
    assert r.returncode == 2 and ".agile.json" in (r.stdout + r.stderr)
    assert not (lone / ".agile.json").exists()


def test_set_repo_preserves_other_keys_and_leaves_no_temp(env, tmp_path):
    cfg = {"schema": 1, "visibility": "public", "paths": {"requests": "a/R.md"}, "x-extra": [1, {"k": "đ"}]}
    root = make_repo(tmp_path, cfg)
    r = cli(env, "set", "--scope", "repo", "--locale", "en", "--root", str(root))
    assert r.returncode == 0, r.stderr
    data = json.loads((root / ".agile.json").read_text(encoding="utf-8"))
    assert data == {**cfg, "locale": "en"}
    assert [p.name for p in root.iterdir()] == [".agile.json"]
    assert not (root / ".agile.json").read_bytes().startswith(b"\xef\xbb\xbf")
    assert not env[1].exists()  # repo scope does not touch the user state


def test_set_repo_corrupt_config_refused(env, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".agile.json").write_bytes(b"{oops")
    r = cli(env, "set", "--scope", "repo", "--locale", "en", "--root", str(root))
    assert r.returncode == 2
    assert (root / ".agile.json").read_bytes() == b"{oops"


def test_state_path_comes_from_agile_state(env, tmp_path, monkeypatch):
    import agile_state

    mod = _cli_mod()
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(tmp_path / "elsewhere"))
    assert mod.user_config_path() == agile_state.state_dir() / "user-config.json"
    assert mod.user_config_path().parent == tmp_path / "elsewhere"
    src = (SCRIPTS / "locale_cli.py").read_text(encoding="utf-8")
    assert "LOCALAPPDATA" not in src and "XDG_STATE_HOME" not in src  # the platform logic is not copied


# --- atomic write ---------------------------------------------------------------------------------------------


def test_atomic_write_leaves_no_temp_and_keeps_original_on_failure(tmp_path, monkeypatch):
    mod = _cli_mod()
    target = tmp_path / "d" / "f.json"
    mod.write_atomic(target, '{"a": 1}\n')
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n'
    assert [p.name for p in target.parent.iterdir()] == ["f.json"]

    def boom(src, dst):
        raise OSError("disk says no")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        mod.write_atomic(target, '{"a": 2}\n')
    monkeypatch.undo()
    assert target.read_text(encoding="utf-8") == '{"a": 1}\n'
    assert [p.name for p in target.parent.iterdir()] == ["f.json"]


def test_cli_write_failure_is_exit_1(env, tmp_path, monkeypatch, capsys):
    mod = _cli_mod()
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(tmp_path / "st"))

    def boom(src, dst):
        raise OSError("disk says no")

    monkeypatch.setattr(os, "replace", boom)
    rc = mod.main(["set", "--scope", "user", "--locale", "en"])
    monkeypatch.undo()
    assert rc == 1
    assert not list((tmp_path / "st").glob("*.tmp"))


# --- FR6: `locale` in .agile.json -----------------------------------------------------------------------------


def test_default_config_has_no_locale_key_and_template_matches():
    assert "locale" not in c.DEFAULT_CONFIG
    assert "locale" not in json.loads((REPO / "templates" / "project" / "agile.json").read_text(encoding="utf-8"))
    assert c.config_problems(c.merge_config({})) == []


def test_config_without_locale_stays_byte_identical_through_init(tmp_path):
    raw = (REPO / "templates" / "project" / "agile.json").read_bytes()
    (tmp_path / ".agile.json").write_bytes(raw)
    cfg = c.load_config(tmp_path)
    assert "locale" not in cfg
    assert (tmp_path / ".agile.json").read_bytes() == raw
    r = run_script("init.py", str(tmp_path), "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / ".agile.json").read_bytes() == raw


@pytest.mark.parametrize("good", ["vi", "en"])
def test_config_problems_accepts_shipped_locale(good):
    assert c.config_problems(c.merge_config({"locale": good})) == []


@pytest.mark.parametrize("bad", ["fr", "../x", "", "EN", 5, None, ["en"]])
def test_config_problems_rejects_other_locale(bad):
    problems = c.config_problems(c.merge_config({"locale": bad}))
    assert len(problems) == 1 and problems[0].startswith("locale")


# --- review round 1 (RF1 and notes a-d) ------------------------------------------------------------------------


@pytest.mark.parametrize("how", ["flag", "CI", "AGENT_AGILE_NONINTERACTIVE"])
def test_headless_set_user_writes_nothing_and_ask_stays_needed(env, tmp_path, how):
    e, state = env
    e = dict(e)
    args = ["set", "--scope", "user", "--locale", "vi", "--json"]
    if how == "flag":
        args.append("--non-interactive")
    else:
        e[how] = "1"
    root = make_repo(tmp_path)
    r = cli((e, state), *args, "--root", str(root))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["written"] is False and out["reason"]
    assert not state.exists()
    # a later human session is still asked
    assert status_json(env, "--root", str(root))["ask_needed"] is True


def test_interactive_set_reports_written_true(env, tmp_path):
    root = make_repo(tmp_path)
    r = cli(env, "set", "--scope", "user", "--locale", "en", "--json", "--root", str(root))
    assert json.loads(r.stdout)["written"] is True


def test_headless_set_repo_still_writes(env, tmp_path):
    root = make_repo(tmp_path)
    r = cli(env, "set", "--scope", "repo", "--locale", "en", "--non-interactive", "--root", str(root))
    assert r.returncode == 0
    assert json.loads((root / ".agile.json").read_text(encoding="utf-8"))["locale"] == "en"


def test_relative_state_dir_problem_is_reported(tmp_path, monkeypatch):
    import argparse
    import agile_state

    mod = _cli_mod()
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", "relative/dir")
    monkeypatch.setattr(agile_state, "platform_state_dir", lambda *a, **k: tmp_path / "plat")
    root = make_repo(tmp_path)
    ns = argparse.Namespace(root=str(root), locale=None, sprint_file=None)
    info = mod.gather(ns, True)
    assert any("AGENT_AGILE_STATE_DIR" in p for p in info["problems"])


def test_locale_null_is_invalid_in_repo_and_user_like_config_problems(env, tmp_path):
    assert c.config_problems(c.merge_config({"locale": None}))  # config_problems rejects null
    root = make_repo(tmp_path, {"schema": 1, "locale": None})
    s = status_json(env, "--root", str(root))
    assert s["locale"] == "vi" and s["source"] == "default"
    assert [i["layer"] for i in s["ignored"]] == ["repo"]
    assert s["ask_needed"] is True
    env[1].mkdir()
    (env[1] / "user-config.json").write_text(json.dumps({"locale": None}), encoding="utf-8")
    assert [i["layer"] for i in status_json(env, "--root", str(root))["ignored"]] == ["repo", "user"]


def test_unclosed_front_matter_does_not_read_body_locale(env, tmp_path):
    root = make_repo(tmp_path)
    doc = root / "S.md"
    doc.write_text("---\nid: SPR-9\n\n# Title\nlocale: en\nmore text\n", encoding="utf-8")
    s = status_json(env, "--root", str(root), "--sprint-file", str(doc))
    assert (s["locale"], s["source"]) == ("vi", "default")
    closed = root / "T.md"
    closed.write_text("---\nid: SPR-9\n---\n\nlocale: en\n", encoding="utf-8")
    assert status_json(env, "--root", str(root), "--sprint-file", str(closed))["source"] == "default"
