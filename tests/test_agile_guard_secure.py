"""Session-scoped secure guard behavior (SPR-37)."""
import pytest
import agile_guard
import agile_state as st
import _agile_rules as rules
from test_agile_guard import SID, TAMPER_REASON, claude, make_repo, run

pytestmark = pytest.mark.usefixtures("agile_state_dir")


def session(agile=True, secure=False):
    st.write_json_atomic(st.session_file(SID), {"schema": 1, "session_id": SID,
                         "agile": agile, "secure": secure, "mode": "auto", "source": "hook"})


def test_secure_on_agile_off_is_healthy_seven_items(tmp_path):
    repo = make_repo(tmp_path)
    session(agile=False, secure=True)
    active, broken, _ = agile_guard.activation(claude("ls", repo, session_id=SID))
    assert run("claude", claude("ls", repo, session_id=SID)) == (0, "", "")
    assert active == set(rules.OPEN_ALWAYS_BLOCKED) and len(active) == 7
    assert broken is False
    rc, _, err = run("claude", claude("rm -rf x", repo, session_id=SID))
    assert rc == 2 and "tr\u1ea1ng th\u00e1i h\u1ecfng" not in err


@pytest.mark.parametrize("cmd", ["rm -rf build", "Remove-Item -Recurse x", "git push --force", "python scripts/agile_state.py manual"])
def test_sc1_agile_only_dormant(tmp_path, cmd):
    repo = make_repo(tmp_path)
    session()
    payload = claude(cmd, repo, session_id=SID)
    assert run("claude", payload) == (0, "", "")


def test_sc1_activation_dormant(tmp_path):
    repo = make_repo(tmp_path)
    session()
    assert agile_guard.activation(claude("ls", repo, session_id=SID)) is None


def test_sc1_write_state_and_malformed_payload_allowed(tmp_path):
    repo = make_repo(tmp_path)
    session()
    payload = {"session_id": SID, "cwd": str(repo), "tool_name": "Write", "tool_input": {"file_path": str(st.session_file(SID)), "content": "x"}}
    assert run("claude", payload) == (0, "", "")
    assert run("claude", '{"session_id": "t1", "tool_name": ') == (0, "", "")


@pytest.mark.parametrize("agile", [True, False])
def test_fr23_secure_on_blocks(tmp_path, agile):
    repo = make_repo(tmp_path)
    session(agile=agile, secure=True)
    assert run("claude", claude("rm -rf x", repo, session_id=SID))[0] == 2


def test_fr24_broken_state_blocks_thirteen(tmp_path):
    repo = make_repo(tmp_path)
    st.session_file(SID).write_text("{broken", encoding="utf-8")
    active, broken, _ = agile_guard.activation(claude("rm -rf x", repo, session_id=SID))
    assert broken and set(active) == set(rules.AGILE_EXCLUSIONS) and len(active) == 13
    rc, _, err = run("claude", claude("rm -rf x", repo, session_id=SID))
    assert rc == 2 and "tr\u1ea1ng th\u00e1i h\u1ecfng" in err and "c\u1ea7n ng\u01b0\u1eddi d\u00f9ng n\u00f3i trong chat \u2014 l\u1ec7nh kh\u00f4ng ch\u1ea1y" in err


def test_fr24_broken_state_explains_recovery(tmp_path):
    repo = make_repo(tmp_path)
    st.session_file(SID).write_text("{broken", encoding="utf-8")
    rc, _, err = run("claude", claude("rm -rf x", repo, session_id=SID))
    assert rc == 2
    assert "cần người dùng nói trong chat — lệnh không chạy" in err
    assert "người dùng gõ /agent-agile-team:agile stop" in err


def test_fr24_healthy_secure_has_no_recovery_guidance(tmp_path):
    repo = make_repo(tmp_path)
    session(secure=True)
    rc, _, err = run("claude", claude("rm -rf x", repo, session_id=SID))
    assert rc == 2
    assert "trạng thái hỏng" not in err
    assert "/agent-agile-team:agile stop" not in err
    assert "cần người dùng nói trong chat — lệnh không chạy" in err


def test_fr25_subagent_without_session_sleeps(tmp_path):
    repo = make_repo(tmp_path)
    payload = dict(claude("rm -rf x", repo, session_id=SID), agent_id="child")
    assert agile_guard.activation(payload) is None
    assert run("claude", payload) == (0, "", "")


def test_fr26_subagent_shares_secure_session(tmp_path):
    repo = make_repo(tmp_path)
    session(secure=True)
    payload = dict(claude("rm -rf x", repo, session_id=SID), agent_id="child")
    assert run("claude", payload)[0] == 2


def test_fr31_repo_always_does_not_enable_secure(tmp_path):
    repo = make_repo(tmp_path, repo_always=True, marker={})
    assert agile_guard.activation(claude("rm -rf x", repo, session_id=SID)) is None


@pytest.mark.parametrize("cmd", ["git push origin +x:ma\\\nin", "git push origin :ma\\\nin", "git branch -D ma\\\nin"])
def test_spr29_rf1_line_continuations(tmp_path, cmd):
    repo = make_repo(tmp_path)
    session(secure=True)
    assert run("claude", claude(cmd, repo, session_id=SID))[0] == 2


@pytest.mark.parametrize("cmd", ["git branch -D x *>/dev/null", "git push origin --delete x *>/dev/null", "git push origin --delete x *>>/dev/null", "git push origin --delete x *>NUL", "git push -f origin x:x *>/dev/null"])
def test_spr29_rf2_redirect_with_main_file(tmp_path, cmd):
    repo = make_repo(tmp_path)
    (repo / "main").write_text("", encoding="utf-8")
    session(secure=True)
    assert run("claude", claude(cmd, repo, session_id=SID))[0] == 2


@pytest.mark.parametrize("cmd", ["python scripts/agile_state.py stop", "python scripts/agile_state.py on", "python scripts/agile_state.py secure_off", 'claude -p "/agile secure off"'])
def test_sc7_secure_cannot_disable_itself(tmp_path, cmd):
    repo = make_repo(tmp_path)
    session(secure=True)
    rc, _, err = run("claude", claude(cmd, repo, session_id=SID))
    assert rc == 2 and TAMPER_REASON in err
    assert "ho\u1eb7c ng\u01b0\u1eddi d\u00f9ng g\u00f5 /agent-agile-team:agile secure off" in err


def test_fr24_corrupt_repo_with_agile_on_secure_off(tmp_path):
    repo = make_repo(tmp_path)
    session()
    st.repo_file(repo).write_text("{broken", encoding="utf-8")
    active, broken, _ = agile_guard.activation(claude("ls", repo, session_id=SID))
    assert broken and set(active) == set(rules.AGILE_EXCLUSIONS) and len(active) == 13


def test_secure_session_with_second_repo_broken_blocks_thirteen(tmp_path):
    a = make_repo(tmp_path / "a")
    b = make_repo(tmp_path / "b")
    session(secure=True)
    payload = claude("ls", a, session_id=SID)
    st.repo_file(b).write_text("{broken", encoding="utf-8")
    active, broken, _ = agile_guard.activation(payload, projects=(a, b))
    assert active == set(rules.AGILE_EXCLUSIONS) and len(active) == 13
    assert broken is True


def test_secure_session_with_second_repo_healthy_blocks_seven(tmp_path):
    a = make_repo(tmp_path / "a")
    b = make_repo(tmp_path / "b")
    session(secure=True)
    payload = claude("ls", a, session_id=SID)
    active, broken, _ = agile_guard.activation(payload, projects=(a, b))
    assert active == set(rules.OPEN_ALWAYS_BLOCKED) and len(active) == 7
    assert broken is False
