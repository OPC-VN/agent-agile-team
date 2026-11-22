"""tier_hook.py (RQ-435 L2a): PreToolUse `Agent|Task` forces the Claude subagent model by role; receipts; hooks.json wiring."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import FIXTURES, REPO
import agile_state as st
import tier_hook as th
from test_tier_resolve import make_snapshot

GOLD = FIXTURES / "tier-golden"
DEFAULTS = REPO / "tiers" / "tiers.defaults.json"
CATALOG = REPO / "tiers" / "role-catalog.json"
SID = "sess-1"

pytestmark = pytest.mark.usefixtures("agile_state_dir")


@pytest.fixture(autouse=True)
def _warn_dir(tmp_path_factory, monkeypatch):
    """The once-per-session receipt warning leaves a marker file; keep it in a temp folder per test."""
    monkeypatch.setenv("AGENT_AGILE_TIER_WARN_DIR", str(tmp_path_factory.mktemp("warned")))


def make_repo(tmp_path, on=True, git=False, ignore_tmp=True):
    """git=True makes a real repository (the `.tmp` fallback of the receipt asks git check-ignore)."""
    repo = tmp_path / "repo"
    if git:
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        if ignore_tmp:
            (repo / ".gitignore").write_text(".tmp/\n", encoding="utf-8")
    else:
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    if on:
        st.write_json_atomic(st.repo_file(repo), {"schema": 1, "always": True, "always_source": "hook"})
    return repo


def payload(repo, subagent="python-reviewer", tool="Agent", **extra):
    tool_input = {"description": "review it", "prompt": "do the thing", "subagent_type": subagent, "model": "haiku", "run_in_background": False}
    tool_input.update(extra)
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": str(repo), "session_id": SID}


def standalone_env(table=DEFAULTS, catalog=CATALOG, **more):
    return {"AGENT_AGILE_TIERS": str(table), "AGENT_AGILE_ROLE_CATALOG": str(catalog), **more}


def out_of(result):
    return result["output"]["hookSpecificOutput"]


def test_on_and_ok_returns_updated_input_with_every_old_key_plus_model(tmp_path):
    repo = make_repo(tmp_path)
    p = payload(repo, "python-reviewer")
    res = th.decide(p, standalone_env())
    hso = out_of(res)
    assert hso["hookEventName"] == "PreToolUse" and hso["permissionDecision"] == "allow"
    new = hso["updatedInput"]
    assert new["model"] == "opus"  # python-reviewer inherits tech-reviewer: tier 3 -> claude-opus-5-5 -> opus
    assert {k: v for k, v in new.items() if k != "model"} == {k: v for k, v in p["tool_input"].items() if k != "model"}
    assert set(p["tool_input"]) <= set(new)  # negative: nothing dropped
    assert p["tool_input"]["model"] == "haiku"  # the input event itself is not mutated


@pytest.mark.parametrize("tool", ["Agent", "Task"])
def test_both_tool_names_and_plugin_prefix(tmp_path, tool):
    repo = make_repo(tmp_path)
    res = th.decide(payload(repo, "agent-agile-team:build-fixer", tool=tool), standalone_env())
    assert out_of(res)["updatedInput"]["model"] == "sonnet"  # build-fixer inherits implementer: tier 2


def test_agile_off_sleeps_without_output_or_receipt(tmp_path, capsys):
    repo = make_repo(tmp_path, on=False)
    assert th.decide(payload(repo), standalone_env()) is None
    stdout = io.StringIO()
    assert th.main(io.StringIO(json.dumps(payload(repo))), stdout) == 0
    assert stdout.getvalue() == "" and not (repo / ".tmp" / th.RECEIPT_NAME).exists()


def test_other_tools_are_ignored(tmp_path):
    assert th.decide(payload(make_repo(tmp_path), tool="Bash"), standalone_env()) is None


def test_agent_outside_the_catalog_passes_untouched(tmp_path):
    repo = make_repo(tmp_path)
    for other in ("agent-other-plugin:reviewer", "other:python-reviewer", "my-agent"):
        res = th.decide(payload(repo, other), standalone_env())
        assert res["output"] is None and res["receipt"]["decision"] == "pass" and res["receipt"]["role"] is None
    off = make_repo(tmp_path / "off", on=False)
    assert th.decide(payload(off, "general-purpose"), standalone_env()) is None


def test_tier_4_fable_is_mapped_and_other_unmeasured_ids_are_denied_not_guessed(tmp_path):
    repo = make_repo(tmp_path)
    res = th.decide(payload(repo, "gate-delegate"), standalone_env())  # tier 4 -> claude-fable-5-2 -> fable (measured 22/11/2026)
    assert out_of(res)["permissionDecision"] == "allow" and out_of(res)["updatedInput"]["model"] == "fable"
    old = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    old["tiers"]["4"]["models"]["claude"] = "claude-fable-5-1"
    table = tmp_path / "t.json"
    table.write_text(json.dumps(old), encoding="utf-8")
    res = th.decide(payload(repo, "gate-delegate"), standalone_env(table=table))
    hso = out_of(res)
    assert hso["permissionDecision"] == "deny" and "model_unmappable" in hso["permissionDecisionReason"]
    assert res["receipt"]["error_code"] == "model_unmappable" and res["receipt"]["decision"] == "deny"
    env = standalone_env(table=table, AGENT_AGILE_MODEL_ALIASES=json.dumps({"claude-fable-5-1": "fable"}))
    assert out_of(th.decide(payload(repo, "gate-delegate"), env))["updatedInput"]["model"] == "fable"


def test_alias_table_covers_every_claude_model_of_the_defaults():
    defaults = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    for tier in ("1", "2", "3", "4"):
        model = defaults["tiers"][tier]["models"]["claude"]
        assert model in th.BUILTIN_ALIASES, f"tier {tier}: {model} has no measured alias in tier_hook.BUILTIN_ALIASES"


def test_opcos_snapshot_ok_and_broken_snapshot_denies(tmp_path):
    repo = make_repo(tmp_path)
    snap, _ = make_snapshot(tmp_path)
    cat = GOLD / "catalog.json"
    env = {"AGENT_AGILE_TIER_SNAPSHOT": str(snap), "AGENT_AGILE_ROLE_CATALOG": str(cat),
           "AGENT_AGILE_MODEL_ALIASES": json.dumps({"fake-claude-t2": "sonnet"})}
    res = th.decide(payload(repo, "implementer"), env)
    assert out_of(res)["updatedInput"]["model"] == "sonnet"
    assert res["receipt"]["snapshot_revision"] == 1 and res["receipt"]["resolver"] == "tier_resolve.py/opcos"
    snap.write_text("{ broken", encoding="utf-8")
    bad = th.decide(payload(repo, "implementer"), env)
    assert out_of(bad)["permissionDecision"] == "deny" and "snapshot_unreadable" in out_of(bad)["permissionDecisionReason"]
    snap.unlink()
    assert "snapshot_missing" in out_of(th.decide(payload(repo, "implementer"), env))["permissionDecisionReason"]


def test_missing_table_or_catalog_denies_on_a_mandatory_turn(tmp_path):
    repo = make_repo(tmp_path)
    env = standalone_env(table=tmp_path / "none.json")
    assert "tiers_file_missing" in out_of(th.decide(payload(repo), env))["permissionDecisionReason"]
    env = standalone_env(catalog=tmp_path / "none.json")
    assert "catalog_missing" in out_of(th.decide(payload(repo, "gate-delegate"), env))["permissionDecisionReason"]


def test_catalog_unusable_denies_only_the_nine_core_roles(tmp_path):
    repo = make_repo(tmp_path)
    env = standalone_env(catalog=tmp_path / "none.json")
    for name in th.CORE_ROLES:
        assert out_of(th.decide(payload(repo, name), env))["permissionDecision"] == "deny", name
        assert out_of(th.decide(payload(repo, "agent-agile-team:" + name), env))["permissionDecision"] == "deny", name
    for other in ("python-reviewer", "other-plugin:agent"):
        res = th.decide(payload(repo, other), env)
        assert res["output"] is None and res["receipt"]["decision"] == "pass" and res["receipt"]["error_code"] == "catalog_missing"
        assert "catalog unusable" in res["warnings"][0]
    # generic type with a non-core tag: cannot be checked without the catalog, passes with a warning; with a core tag it is denied
    res = th.decide(payload(repo, "Explore", prompt="[AAT role=python-reviewer] x"), env)
    assert res["output"] is None and res["receipt"]["error_code"] == "catalog_missing" and "catalog unusable" in res["warnings"][0]
    res = th.decide(payload(repo, "general-purpose", prompt="[AAT role=qa] x"), env)
    assert out_of(res)["permissionDecision"] == "deny" and res["receipt"]["role"] == "qa" and res["receipt"]["role_source"] == "tag"
    assert out_of(th.decide(payload(repo, "general-purpose"), env))["permissionDecision"] == "deny"


def test_catalog_unusable_pass_reaches_the_user_as_a_warning(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, git=True)
    for k, v in standalone_env(catalog=tmp_path / "none.json").items():
        monkeypatch.setenv(k, v)
    out = io.StringIO()
    assert th.main(io.StringIO(json.dumps(payload(repo, "python-reviewer"))), out) == 0
    assert "catalog unusable" in json.loads(out.getvalue())["systemMessage"]


def test_other_plugin_prefix_is_outside_the_catalog(tmp_path):
    repo = make_repo(tmp_path)
    for name in ("other-plugin:code-reviewer", "other-plugin:gate-delegate"):
        res = th.decide(payload(repo, name), standalone_env())
        assert res["output"] is None and res["receipt"]["role"] is None, name
    assert th.agent_name("agent-agile-team:qa") == "qa" and th.agent_name("x:qa") == "x:qa"


def test_every_deny_names_a_way_out(tmp_path):
    repo = make_repo(tmp_path)
    table = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    table["tiers"]["3"]["models"]["claude"] = "claude-opus-9-9"
    unmappable = tmp_path / "t.json"
    unmappable.write_text(json.dumps(table), encoding="utf-8")
    cases = [
        ("python-reviewer", standalone_env(table=tmp_path / "none.json"), "RESTART"),
        ("gate-delegate", standalone_env(catalog=tmp_path / "none.json"), "role-catalog.json"),
        ("python-reviewer", {**standalone_env(), "AGENT_AGILE_TIER_SNAPSHOT": str(tmp_path / "none.json")}, "tier-snapshot.mjs snapshot"),
        ("python-reviewer", standalone_env(table=unmappable), "AGENT_AGILE_MODEL_ALIASES"),
    ]
    for name, env, needle in cases:
        reason = out_of(th.decide(payload(repo, name), env))["permissionDecisionReason"]
        assert "/agent-agile-team:agile stop" in reason and needle in reason, (needle, reason)


def test_alias_env_entries_are_validated():
    raw = {"claude-x-1-0": "fable", "bad id!": "opus", "claude-y-1-0": "gpt", "claude-z-1-0": 5}
    table, used, warnings = th.model_aliases({"AGENT_AGILE_MODEL_ALIASES": json.dumps(raw)})
    assert used == {"claude-x-1-0"} and table["claude-x-1-0"] == "fable"
    assert "claude-y-1-0" not in table and "claude-z-1-0" not in table and "bad id!" not in table
    assert len(warnings) == 3
    assert th.model_aliases({"AGENT_AGILE_MODEL_ALIASES": "[1]"})[2] and th.model_aliases({"AGENT_AGILE_MODEL_ALIASES": "{"})[2]
    assert th.model_aliases({})[2] == [] and th.model_aliases({})[0] == th.BUILTIN_ALIASES


def test_receipt_records_alias_source_and_claude_code_version(tmp_path):
    repo = make_repo(tmp_path)
    p = payload(repo, "python-reviewer")
    first = th.decide(p, standalone_env())["receipt"]
    assert first["claude_code_version"] is None and first["alias_table_source"] == "default"  # version is never guessed
    assert th.decide({**p, "claude_code_version": "2.1.310"}, standalone_env())["receipt"]["claude_code_version"] == "2.1.310"
    assert th.decide(p, standalone_env(CLAUDE_CODE_VERSION="2.1.311"))["receipt"]["claude_code_version"] == "2.1.311"
    assert th.decide(p, standalone_env(CLAUDE_CODE_VERSION="not a version"))["receipt"]["claude_code_version"] is None
    env = standalone_env(AGENT_AGILE_MODEL_ALIASES=json.dumps({"claude-opus-5-5": "opus"}))
    assert th.decide(p, env)["receipt"]["alias_table_source"] == "env"


def test_unreadable_agile_state_passes_with_a_warning(tmp_path, agile_state_dir):
    repo = make_repo(tmp_path)
    st.repo_file(repo).write_text("{ not json", encoding="utf-8")
    res = th.decide(payload(repo), standalone_env())
    assert res["mandatory"] is False and "systemMessage" in res["output"] and "hookSpecificOutput" not in res["output"]


def run_main(p, env_patch, monkeypatch):
    for k, v in env_patch.items():
        monkeypatch.setenv(k, v)
    stdout = io.StringIO()
    assert th.main(io.StringIO(json.dumps(p)), stdout) == 0
    return stdout.getvalue()


def test_receipt_is_written_honestly_in_the_fallback_folder(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, git=True)
    text = run_main(payload(repo, "python-reviewer", model="haiku"), standalone_env(), monkeypatch)
    assert json.loads(text)["hookSpecificOutput"]["updatedInput"]["model"] == "opus"
    lines = (repo / ".tmp" / th.RECEIPT_NAME).read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    assert len(lines) == 1
    assert rec["schema"] == 1 and rec["role"] == "python-reviewer" and rec["tier"] == 3 and rec["requested_model"] == "haiku"
    assert rec["actual_model"] is None and rec["model_identity_status"] == "unverified" and rec["enforcement"] == "hook"
    assert rec["decision"] == "allow" and rec["session_id"] == SID and rec["error_code"] is None
    assert "do the thing" not in lines[0] and "prompt" not in rec  # no prompt text in the receipt
    run_main(payload(repo, "general-purpose"), standalone_env(), monkeypatch)
    assert len((repo / ".tmp" / th.RECEIPT_NAME).read_text(encoding="utf-8").splitlines()) == 2


def test_receipt_goes_to_the_open_sprint_folder(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    (repo / ".agile.json").write_text('{"schema": 1}', encoding="utf-8")
    folder = repo / "docs" / "plans" / "2026-11-22-demo"
    folder.mkdir(parents=True)
    (folder / "PROGRESS.md").write_text("---\nsprint: SPR-07\nstatus: in_progress\ntitle: demo\n---\n", encoding="utf-8")
    run_main(payload(repo, "python-reviewer"), standalone_env(), monkeypatch)
    rec = json.loads((folder / th.RECEIPT_NAME).read_text(encoding="utf-8").splitlines()[0])
    assert rec["sprint"] == "SPR-07" and not (repo / ".tmp" / th.RECEIPT_NAME).exists()


def test_fallback_is_not_written_when_tmp_is_not_git_ignored(tmp_path, monkeypatch):
    cases = (("no ignore rule", make_repo(tmp_path / "a", git=True, ignore_tmp=False)), ("not a repository", make_repo(tmp_path / "b")))
    for i, (case, repo) in enumerate(cases):
        out = json.loads(run_main({**payload(repo, "python-reviewer"), "session_id": f"s-{i}"}, standalone_env(), monkeypatch))
        assert out["hookSpecificOutput"]["permissionDecision"] == "allow", case  # the turn is not broken
        assert "receipt not written" in out["systemMessage"] and not (repo / ".tmp" / th.RECEIPT_NAME).exists(), case


def test_receipt_write_failure_does_not_break_the_turn(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, git=True)
    (repo / ".tmp").write_text("a file where the folder should be", encoding="utf-8")  # mkdir fails
    text = run_main(payload(repo, "python-reviewer"), standalone_env(), monkeypatch)
    out = json.loads(text)
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow" and "receipt not written" in out["systemMessage"]


def test_garbage_input_never_breaks_a_turn():
    for raw in ("", "not json", "[]", "null"):
        stdout = io.StringIO()
        assert th.main(io.StringIO(raw), stdout) == 0 and stdout.getvalue() == ""


def test_hooks_json_keeps_the_old_blocks_and_adds_the_tier_hook():
    config = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert set(config["hooks"]) == {"SessionStart", "UserPromptExpansion", "PreToolUse"}
    entries = config["hooks"]["PreToolUse"]
    assert [e["matcher"] for e in entries] == ["Bash|PowerShell", "Write|Edit|MultiEdit|NotebookEdit", "Agent|Task"]
    for e in entries[:2]:
        assert e["hooks"][0]["args"][0].endswith("scripts/agile_guard.py")
    new = entries[2]["hooks"]
    assert new == [{"type": "command", "command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/tier_hook.py"], "timeout": 10}]
    assert (REPO / "scripts" / "tier_hook.py").is_file()


def test_tiers_file_missing_hint_depends_on_which_variables_are_set(tmp_path):
    repo = make_repo(tmp_path)
    wrong = out_of(th.decide(payload(repo), standalone_env(table=tmp_path / "none.json")))["permissionDecisionReason"]
    assert "AGENT_AGILE_TIERS" in wrong and "RESTART" in wrong and "tier_setup.py" not in wrong
    assert "system/workshop/records/agent-agile-team/tiers.json" in wrong
    both_unset = {"LOCALAPPDATA": str(tmp_path / "empty"), "AGENT_AGILE_ROLE_CATALOG": str(CATALOG)}
    fresh = out_of(th.decide(payload(repo), both_unset))["permissionDecisionReason"]
    assert "tiers_file_missing" in fresh and "tier_setup.py" in fresh and "RESTART" not in fresh
    snap = {**both_unset, "AGENT_AGILE_TIER_SNAPSHOT": str(tmp_path / "x.json")}
    assert "tier_setup.py" not in out_of(th.decide(payload(repo), snap))["permissionDecisionReason"]
    assert "tier_setup.py" not in th.exit_hint("tiers_file_missing", {"AGENT_AGILE_TIER_SNAPSHOT": "x"})


def test_hardcoded_core_roles_match_the_real_catalog_and_the_catalog_test():
    from test_role_catalog import CATALOG as REAL, CORE as CATALOG_TEST_CORE
    non_inheriting = {name for name, r in REAL["roles"].items() if "inherits" not in r}
    assert set(th.CORE_ROLES) == non_inheriting == set(CATALOG_TEST_CORE)


def test_receipt_warning_is_once_per_session_and_never_for_pass(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, git=True, ignore_tmp=False)  # every write is refused: .tmp not ignored
    first = json.loads(run_main(payload(repo, "python-reviewer"), standalone_env(), monkeypatch))
    second = json.loads(run_main(payload(repo, "python-reviewer"), standalone_env(), monkeypatch))
    assert "receipt not written" in first["systemMessage"] and "systemMessage" not in second
    other = json.loads(run_main({**payload(repo, "python-reviewer"), "session_id": "another"}, standalone_env(), monkeypatch))
    assert "receipt not written" in other["systemMessage"]
    for sid in ("s-pass-1", "s-pass-2"):  # a pass (agent outside the catalog, or role=direct) never warns
        text = run_main({**payload(repo, "other-plugin:agent"), "session_id": sid}, standalone_env(), monkeypatch)
        assert text == ""



# ---- CO16: role card `[AAT role=<role>]` for generic subagent types ----
GENERIC = ("general-purpose", "claude", "Plan", "Explore", None, "")


def test_valid_tag_forces_the_model_like_the_agent_of_that_role(tmp_path):
    repo = make_repo(tmp_path)
    for generic in GENERIC:
        res = th.decide(payload(repo, generic, prompt="[AAT role=gate-delegate] decide"), standalone_env())
        hso = out_of(res)
        assert hso["permissionDecision"] == "allow" and hso["updatedInput"]["model"] == "fable", generic
        assert res["receipt"]["role"] == "gate-delegate" and res["receipt"]["role_source"] == "tag" and res["receipt"]["decision"] == "allow"
    by_agent = th.decide(payload(repo, "gate-delegate"), standalone_env())
    assert by_agent["receipt"]["role_source"] == "agent"
    by_tag = th.decide(payload(repo, "general-purpose", prompt="[AAT role=gate-delegate]"), standalone_env())
    assert out_of(by_agent)["updatedInput"]["model"] == out_of(by_tag)["updatedInput"]["model"]
    assert by_agent["receipt"]["tier"] == by_tag["receipt"]["tier"]


def test_tag_updated_input_copies_every_field_and_takes_the_first_tag(tmp_path):
    repo = make_repo(tmp_path)
    res = th.decide(payload(repo, "general-purpose", prompt="intro [AAT role=researcher] and [AAT role=qa]", isolation="worktree", name="n1"),
                    standalone_env())
    upd = out_of(res)["updatedInput"]
    assert res["receipt"]["role"] == "researcher"
    assert upd["isolation"] == "worktree" and upd["name"] == "n1" and upd["description"] == "review it" and upd["run_in_background"] is False
    assert upd["prompt"] == "intro [AAT role=researcher] and [AAT role=qa]" and upd["subagent_type"] == "general-purpose" and upd["model"] == "haiku"


def test_role_direct_passes_without_forcing_a_model(tmp_path):
    repo = make_repo(tmp_path)
    res = th.decide(payload(repo, "general-purpose", prompt="[AAT role=direct] quick fix"), standalone_env())
    assert res["output"] is None and res["receipt"]["decision"] == "pass_direct" and res["receipt"]["role_source"] == "tag"
    assert res["mandatory"] is True and res["receipt"]["role"] is None


def test_unknown_tag_is_denied_with_a_way_out(tmp_path):
    repo = make_repo(tmp_path)
    for bad in ("nonsense", "human-arbiter"):
        res = th.decide(payload(repo, "Plan", prompt=f"[AAT role={bad}] x"), standalone_env())
        hso = out_of(res)
        assert hso["permissionDecision"] == "deny" and res["receipt"]["error_code"] == "unknown_role"
        reason = hso["permissionDecisionReason"]
        assert "role=direct" in reason and "/agent-agile-team:agile stop" in reason and "researcher" in reason


def test_missing_tag_is_denied_for_every_generic_type(tmp_path):
    repo = make_repo(tmp_path)
    for generic in GENERIC:
        res = th.decide(payload(repo, generic, prompt="no tag here AAT role=qa"), standalone_env())
        hso = out_of(res)
        assert hso["permissionDecision"] == "deny" and res["receipt"]["error_code"] == "role_tag_required", generic
        reason = hso["permissionDecisionReason"]
        assert "[AAT role=<role>]" in reason and "role=direct" in reason and "/agent-agile-team:agile stop" in reason
    no_prompt = payload(repo, "general-purpose")
    del no_prompt["tool_input"]["prompt"]
    assert out_of(th.decide(no_prompt, standalone_env()))["permissionDecision"] == "deny"


def test_tag_is_ignored_for_other_agents_and_agile_off(tmp_path):
    repo = make_repo(tmp_path)
    res = th.decide(payload(repo, "other-plugin:agent", prompt="[AAT role=qa]"), standalone_env())
    assert res["output"] is None and res["receipt"]["decision"] == "pass" and res["receipt"]["role"] is None
    res = th.decide(payload(repo, "python-reviewer", prompt="[AAT role=qa]"), standalone_env())  # the agent name wins over a tag
    assert res["receipt"]["role"] == "python-reviewer" and res["receipt"]["role_source"] == "agent"
    off = make_repo(tmp_path / "off", on=False)
    assert th.decide(payload(off, "general-purpose", prompt="no tag"), standalone_env()) is None


def test_pass_direct_receipt_is_written(tmp_path):
    repo = make_repo(tmp_path, git=True)
    stdout = io.StringIO()
    assert th.main(io.StringIO(json.dumps(payload(repo, "general-purpose", prompt="[AAT role=direct]"))), stdout) == 0
    assert stdout.getvalue() == ""
    line = json.loads((repo / ".tmp" / th.RECEIPT_NAME).read_text(encoding="utf-8").splitlines()[-1])
    assert line["decision"] == "pass_direct" and line["role_source"] == "tag"
