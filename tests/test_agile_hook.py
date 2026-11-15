"""`agile_hook.py`: SessionStart context and UserPromptExpansion switch (SPR-32 TK3; SC1.1, SC1.2, SC1.4-1.6, SC1.8)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS
import agile_state as st

HOOK = SCRIPTS / "agile_hook.py"
REAL_DIR = st.platform_state_dir()
CMD = "agent-agile-team:agile"


def snapshot(path: Path):
    return sorted((p.name, p.stat().st_mtime_ns) for p in path.iterdir()) if path.exists() else None


@pytest.fixture(autouse=True)
def state(tmp_path):
    before = snapshot(REAL_DIR)
    yield tmp_path / "state-dir"
    assert snapshot(REAL_DIR) == before  # SC4.4


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    return root


def fire(payload, state, args=("--format", "claude"), raw=None):
    env = dict(os.environ, AGENT_AGILE_STATE_DIR=str(state), PYTHONIOENCODING="utf-8")
    data = raw if raw is not None else json.dumps(payload).encode("utf-8")
    return subprocess.run([sys.executable, str(HOOK), *args], input=data, capture_output=True, env=env, timeout=60)


def start(repo, sid="s1", source="startup"):
    return {"hook_event_name": "SessionStart", "session_id": sid, "cwd": str(repo), "source": source,
            "transcript_path": "/t.jsonl"}


def expansion(repo, args, sid="s1", name=CMD, event="UserPromptExpansion"):
    return {"hook_event_name": event, "session_id": sid, "cwd": str(repo), "command_name": name, "command_args": args,
            "command_source": "plugin", "prompt_id": "pid-9", "transcript_path": "/t.jsonl"}


def context(proc):
    out = json.loads(proc.stdout.decode("utf-8"))
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    return out["hookSpecificOutput"]["additionalContext"]


def load(repo, sid="s1", state=None):
    return st.load_state(repo, sid, state)


# --- SessionStart -------------------------------------------------------------------------------------------


def test_session_start_off_carries_session_id(repo, state):  # SC1.1
    p = fire(start(repo, "abc-123"), state)
    assert p.returncode == 0 and p.stderr == b""
    text = context(p)
    assert text.startswith("agile: OFF") and "session_id=abc-123" in text and "open sprint: none" in text
    assert (state / "session-abc-123.json").exists()
    assert load(repo, "abc-123", state)["effective_on"] is False  # SessionStart never switches ON


def test_session_start_records_last_hook(repo, state):
    fire(start(repo), state)
    assert json.loads((state / "session-s1.json").read_text(encoding="utf-8"))["last_hook"]


def test_session_start_reports_on_always_and_sprint(repo, state):  # SC1.6
    (repo / ".agile.json").write_text(json.dumps({"schema": 1}), encoding="utf-8")
    folder = repo / "docs" / "plans" / "2026-01-01-demo"
    folder.mkdir(parents=True)
    (folder / "PROGRESS.md").write_bytes(b"---\nid: SPR-04-progress\ndoc: progress\ntitle: Demo\nsprint: SPR-04\nstatus: in_progress\n---\n")
    fire(expansion(repo, "always"), state)
    text = context(fire(start(repo, "s2", "resume"), state))
    assert text.startswith("agile: ON") and "always yes" in text and "SPR-04 [in_progress] Demo" in text
    assert "source hook" in text and "non-hook" not in text


def test_session_start_resume_without_state_says_off(repo, state):
    text = context(fire(start(repo, "gone", "resume"), state))
    assert text.startswith("agile: OFF") and "after resume" in text


def test_session_start_resume_keeps_on_for_same_session(repo, state):
    fire(expansion(repo, ""), state)
    text = context(fire(start(repo, "s1", "resume"), state))
    assert text.startswith("agile: ON") and "after resume" not in text


def test_clear_gives_new_session_off(repo, state):
    fire(expansion(repo, ""), state)
    assert context(fire(start(repo, "s-new", "clear"), state)).startswith("agile: OFF")


def test_session_start_notices_legacy_marker_and_non_hook(repo, state):
    marker = repo / ".tmp" / "autopilot.json"
    marker.parent.mkdir()
    marker.write_text("{}", encoding="utf-8")
    st.apply_command("on", repo, "s1", directory=state)  # source script
    text = context(fire(start(repo), state))
    assert "autopilot.json" in text and "non-hook ON" in text and marker.exists()


def test_session_start_runs_stale_cleanup(repo, state):
    st.apply_command("on", repo, "ancient", directory=state)
    st.apply_command("always", repo, "x", directory=state)
    old = (state / "session-ancient.json")
    ts = old.stat().st_mtime - 20 * 86400
    os.utime(old, (ts, ts))
    fire(start(repo), state)
    assert not old.exists() and list(state.glob("repo-*.json"))


def test_session_start_corrupt_state_reports_problem(repo, state):
    st.apply_command("on", repo, "s1", directory=state)
    (state / "session-s1.json").write_text("{", encoding="utf-8")
    p = fire(start(repo), state)
    assert p.returncode == 0
    text = context(p)
    assert text.startswith("agile: OFF") and "state problem" in text and "guard stays active" in text


# --- UserPromptExpansion ------------------------------------------------------------------------------------


def test_empty_args_turn_on_with_hook_source(repo, state):  # SC1.2
    p = fire(expansion(repo, ""), state)
    assert p.returncode == 0 and p.stdout == b""
    s = load(repo, state=state)
    assert s["session_agile"] and s["mode"] == "auto" and s["source"] == "hook" and s["non_hook_on"] is False
    assert s["prompt_id"] == "pid-9" and s["transcript_path"] == "/t.jsonl"


def test_missing_args_key_counts_as_empty(repo, state):
    payload = expansion(repo, "")
    del payload["command_args"]
    fire(payload, state)
    assert load(repo, state=state)["session_agile"]


def test_always_manual_stop(repo, state):  # SC1.4, SC1.5, SC2.1
    fire(expansion(repo, "always"), state)
    assert load(repo, "other", state)["effective_on"] is True
    fire(expansion(repo, "manual"), state)
    s = load(repo, state=state)
    assert s["mode"] == "manual" and s["session_agile"]
    fire(expansion(repo, "stop"), state)
    s = load(repo, state=state)
    assert not s["effective_on"] and not s["always"] and s["mode"] == "auto"
    assert not load(repo, "other", state)["effective_on"]


def test_args_are_case_and_space_tolerant(repo, state):
    fire(expansion(repo, "  Always "), state)
    assert load(repo, state=state)["always"]
    fire(expansion(repo, " STOP"), state)
    assert not load(repo, state=state)["effective_on"]


def test_stop_never_refused_even_when_off_or_corrupt(repo, state):
    assert fire(expansion(repo, "stop"), state).returncode == 0
    fire(expansion(repo, ""), state)
    (state / "session-s1.json").write_text("{", encoding="utf-8")
    assert fire(expansion(repo, "stop"), state).returncode == 0
    assert load(repo, state=state)["state_problem"] is None


@pytest.mark.parametrize("args", ["status", "frobnicate", "always now", "on", "--clear", "stop; rm", "alwaysx", "a" * 5000])
def test_unknown_or_readonly_args_change_nothing(repo, state, args):
    p = fire(expansion(repo, args), state)
    assert p.returncode == 0 and p.stdout == b""
    assert not state.exists() or not list(state.iterdir())


def test_non_string_args_change_nothing(repo, state):
    for bad in (5, ["always"], {"a": 1}, True):
        assert fire(expansion(repo, bad), state).returncode == 0
    assert not state.exists() or not list(state.iterdir())


@pytest.mark.parametrize("name", ["agent-agile-team:agile-goal", "agile", "agent-agile-team:agile ", "Agent-Agile-Team:agile",
                                  "agent-agile-team:agile-secure", "", None, "other:agile"])
def test_only_exact_command_name_counts(repo, state, name):  # SC1.8
    p = fire(expansion(repo, "always", name=name), state)
    assert p.returncode == 0 and p.stdout == b""
    assert not state.exists() or not list(state.iterdir())


def test_requires_expansion_event_name(repo, state):
    for event in ("UserPromptSubmit", "PreToolUse", "SubagentStart", "", None, "userpromptexpansion"):
        assert fire(expansion(repo, "always", event=event), state).returncode == 0
    assert not state.exists() or not list(state.iterdir())


def test_missing_session_id_changes_nothing(repo, state):
    payload = expansion(repo, "always")
    del payload["session_id"]
    assert fire(payload, state).returncode == 0
    assert not state.exists() or not list(state.iterdir())


def test_traversal_session_id_stays_inside_state_dir(tmp_path, repo, state):
    fire(expansion(repo, "", sid="../../../escape"), state)
    names = [p.name for p in state.iterdir()]
    assert len(names) == 1 and names[0].startswith("session-x-")
    assert not list(tmp_path.glob("*escape*"))


# --- robustness ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("raw", [b"", b"not json", b"[1]", b"null", b"\xff\xfe\x00", b"{" * 100, b'"s"'])
def test_malformed_payload_exit_0_no_stdout(state, raw):
    p = fire(None, state, raw=raw)
    assert p.returncode == 0 and p.stdout == b""
    assert not state.exists() or not list(state.iterdir())


@pytest.mark.parametrize("event", ["PreToolUse", "Stop", "SubagentStart", "UserPromptSubmit", None, 7])
def test_other_events_no_change(repo, state, event):
    p = fire({"hook_event_name": event, "session_id": "s1", "cwd": str(repo)}, state)
    assert p.returncode == 0 and p.stdout == b""
    assert not state.exists() or not list(state.iterdir())


def test_odd_field_types_never_raise(state):
    payload = {"hook_event_name": "SessionStart", "session_id": 5, "cwd": ["x"], "source": {"a": 1}}
    p = fire(payload, state)
    assert p.returncode == 0
    assert context(p).startswith("agile: OFF") and "session_id=unknown" in context(p)


def test_internal_error_exits_0_silently(repo, state, monkeypatch):
    env = dict(os.environ, AGENT_AGILE_STATE_DIR=str(state / "file-not-dir"))
    (state).mkdir(parents=True)
    (state / "file-not-dir").write_text("x", encoding="utf-8")
    p = subprocess.run([sys.executable, str(HOOK), "--format", "claude"], input=json.dumps(expansion(repo, "")).encode(),
                       capture_output=True, env=env, timeout=60)
    assert p.returncode == 0 and p.stdout == b""
    assert len(p.stderr.decode().splitlines()) <= 1


def test_unknown_format_or_no_args_still_exit_0(repo, state):
    assert fire(start(repo), state, args=()).returncode == 0
    assert fire(start(repo), state, args=("--format", "weird", "--bogus")).returncode == 0
