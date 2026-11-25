"""Test cho scripts/agile_guard.py — rào máy agile (hook PreToolUse). Chạy: python -m pytest -q tests/test_agile_guard.py"""

from __future__ import annotations

import io
import shutil
import json
import os
import subprocess
import sys

import pytest

import _agile_rules
import _agile_rules as rules
import agile_guard
import agile_state as st
from pathlib import Path

from conftest import REPO, SCRIPTS

pytestmark = pytest.mark.usefixtures("agile_state_dir")

ALL = list(_agile_rules.AGILE_EXCLUSIONS)
WITHOUT_BRANCH = [e for e in ALL if e != "branch_merge_local"]
SID = "t1"  # session_id dùng trong test: file phiên `session-t1.json`


def write_repo_always(repo, spec, session_id=None):
    """Bật công tắc agile cho `repo` trong thư mục trạng thái tạm (SPR-32 B3: thay file dấu `.tmp/autopilot.json`).
    `spec` là dict → agile BẬT ở mức repo (`always`, cùng phạm vi repo như file dấu cũ) hay, có `session_id`, ở mức phiên; là chuỗi → ghi nguyên văn
    làm file trạng thái hỏng. Đường file lấy từ `agile_state` (khoá repo từ `repo`)."""
    import agile_state as st
    if session_id is not None:
        path = st.session_file(session_id)
        data = {"schema": 1, "session_id": st.sanitize_session_id(session_id), "agile": True, "mode": "auto", "source": "hook"}
    else:
        path = st.repo_file(repo)
        data = {"schema": 1, "always": True, "always_source": "hook"}
    if isinstance(spec, str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(spec, encoding="utf-8")
    else:
        st.write_json_atomic(path, data)
    return path


def write_switch(repo, spec, session_id=SID):
    return write_secure_session(repo, spec, session_id)


def write_secure_session(repo, spec, session_id=SID):
    if isinstance(spec, str) or session_id is None:
        return write_repo_always(repo, spec, session_id)
    path = st.session_file(session_id)
    data = {"schema": 1, "session_id": st.sanitize_session_id(session_id), "agile": True,
            "secure": True, "mode": "auto", "source": "hook"}
    st.write_json_atomic(path, data)
    return path


def make_repo(tmp_path, branch="main", marker=None, worktree=False, repo_always=False):
    """Dựng repo giả: `.git/HEAD` ở nhánh `branch`; `marker` (tên cũ, giữ để khỏi đổi mọi chỗ gọi) là dict (agile BẬT ở mức repo), chuỗi (trạng
    thái hỏng, ghi nguyên văn) hay None (agile TẮT)."""
    repo = tmp_path / "repo"
    git = repo / ".git"
    git.mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/{}\n".format(branch), encoding="utf-8")
    (repo / ".tmp").mkdir()
    if marker is not None:
        (write_repo_always if repo_always else write_switch)(repo, marker)
    return repo


def good_marker(exclusions=None):
    return {"level": "gate_1_2", "scope": ["gate_1", "gate_2"], "expires": "sprint_end",
            "exclusions": ALL if exclusions is None else exclusions, "grant_at": "2026-11-20 09:00 +07", "sprints": ["SPR-20"]}


def link_dir(target, link):
    """Symlink thư mục; Windows không đặc quyền thì dùng junction (`mklink /J`). Không được thì bỏ qua test."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        import subprocess
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        if done.returncode == 0:
            return
    pytest.skip("không tạo được liên kết thư mục trên máy này")


def claude_without_session(cmd, cwd, tool="Bash"):
    return {"tool_name": tool, "tool_input": {"command": cmd}, "cwd": str(cwd)}


def claude(cmd, cwd, tool="Bash", session_id=SID):
    payload = claude_without_session(cmd, cwd, tool)
    if session_id is not None:
        payload["session_id"] = session_id
    return payload


def run(fmt, payload, *extra):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    out, err = io.StringIO(), io.StringIO()
    rc = agile_guard.main(["--format", fmt, *extra], stdin=io.StringIO(raw), stdout=out, stderr=err)
    return rc, out.getvalue(), err.getvalue()


TAMPER_REASON = "công tắc agile là rào — chỉ người dùng gõ /agile stop mới tắt được"
BS = chr(92)  # dấu gạch ngược trong lệnh Windows/PowerShell


def state_dir():
    return Path(os.environ["AGENT_AGILE_STATE_DIR"])


def expand(cmd):
    """`{S}` = thư mục trạng thái tạm (dấu `/`), `{F}` = tên file phiên `session-t1.json`."""
    return cmd.replace("{S}", str(state_dir()).replace("\\", "/")).replace("{F}", "session-t1.json")


def assert_tamper_blocked(repo, cmd):
    rc, _, err = run("claude", claude(expand(cmd), repo))
    assert rc == 2 and TAMPER_REASON in err, (cmd, rc, err)


def assert_blocked(repo, cmd, item):
    rc, _, err = run("claude", claude(cmd, repo))
    assert rc == 2, (cmd, err)
    assert "'{}'".format(item) in err and "cần người dùng nói trong chat — lệnh không chạy" in err


def assert_allowed(repo, cmd):
    rc, out, err = run("claude", claude(cmd, repo))
    assert (rc, out, err) == (0, "", ""), (cmd, rc, err)


# --- đối chiếu hằng với check.py -------------------------------------------------------------------------------

PINNED_EXCLUSIONS = {"push", "tag", "version", "main_merge", "publish", "license", "irreversible_delete", "rules_unlisted",
                     "user_soul", "secret", "auth", "network_fetch", "branch_merge_local"}


def test_guard_uses_rules_exclusions():
    assert agile_guard.known_exclusions() == _agile_rules.AGILE_EXCLUSIONS


def test_guard_exclusions_pinned_to_thirteen():
    """Bớt một mục ở `_agile_rules.AGILE_EXCLUSIONS` sẽ tắt chặn im lặng: ghim danh sách viết tay để test đỏ."""
    assert len(PINNED_EXCLUSIONS) == 13
    assert set(agile_guard.known_exclusions()) == PINNED_EXCLUSIONS
    assert set(_agile_rules.AGILE_EXCLUSIONS) == PINNED_EXCLUSIONS and len(_agile_rules.AGILE_EXCLUSIONS) == 13


# --- các test PLAN -----------------------------------------------------------------------------------------------

def test_guard_no_marker_allows(tmp_path):
    repo = make_repo(tmp_path)
    assert_allowed(repo, "git push origin main")
    assert_allowed(repo, "rm -rf build")


@pytest.mark.parametrize("cmd", [
    "rm -rf build", "rm -fr build", "rm -Rf build", "rm -r -f build", "rm --recursive build", "rm -r build",
    "rm -rfv build", "rm -fR build", "rm -r",  # không đích: vẫn chặn
    "git worktree remove -f ../w", "git worktree remove --force ../w",
    "Remove-Item -Recurse -Force build", "Remove-Item build -Recurse", "remove-item -recurse build", "ri -r build",
    "rmdir /s /q build", "rd /S build", "rm -Recurse build", "del /s build",
])
def test_guard_blocks_rm_rf(tmp_path, cmd):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, cmd, "irreversible_delete")


def test_guard_safe_deletes_allowed(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    for cmd in ("rm file.txt", "rm -f file.txt", "git branch -d merged", "git clean -n", "git reset --soft HEAD~1",
                "git worktree remove ../w", "Remove-Item file.txt -Force", "rmdir empty", "git status", "git log --oneline",
                "git commit -m 'fix git push docs'", "echo git push", "ls -la"):
        assert_allowed(repo, cmd)


def test_guard_blocks_compound_command(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, "git add -A && git commit -m x && rm -rf x", "irreversible_delete")
    assert_blocked(repo, "ls; rm -rf x", "irreversible_delete")
    assert_blocked(repo, "git log | cat\nrm -rf x", "irreversible_delete")
    assert_blocked(repo, "false || rm -rf x", "irreversible_delete")
    assert_blocked(repo, "(rm -rf x)", "irreversible_delete")
    assert_blocked(repo, "echo $(rm -rf x)", "irreversible_delete")
    assert_blocked(repo, "sleep 1 & rm -rf x", "irreversible_delete")
    assert_blocked(repo, "sudo rm -rf x", "irreversible_delete")
    assert_blocked(repo, "bash -c 'git add . && rm -rf x'", "irreversible_delete")
    assert_blocked(repo, 'pwsh -NoProfile -Command "rm -rf x"', "irreversible_delete")
    assert_blocked(repo, "cmd /c rm -rf x", "irreversible_delete")
    # chặn nhầm có chủ ý (mục 5.1): tách thô không hiểu dấu nháy
    assert_blocked(repo, 'git commit -m "a && rm -rf x"', "irreversible_delete")


def test_guard_exclusions_missing_required_filled_in(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker(["version"]))  # thiếu push, tag, ...
    assert_blocked(repo, "rm -rf x", "irreversible_delete")
    assert_blocked(repo, "rm -rf x", "irreversible_delete")
    # mục lạ bị bỏ qua, không làm hỏng
    odd = make_repo(tmp_path / "o", branch="spr-12", marker=good_marker(WITHOUT_BRANCH + ["bogus", 3]))
    assert_blocked(odd, "rm -rf x", "irreversible_delete")
    assert_allowed(odd, "git merge x")


@pytest.mark.parametrize("text", ["{not json", "", "[]", "null", '"x"', "\xef\xbf\xbd"])
def test_guard_bad_marker_fails_closed(tmp_path, text):
    repo = make_repo(tmp_path, branch="spr-12", marker=text)
    rc, _, err = run("claude", claude("rm -rf x", repo))
    assert rc == 2 and "trạng thái hỏng" in err and "'irreversible_delete'" in err
    assert_allowed(repo, "ls")  # lệnh không khớp mẫu vẫn qua


def test_guard_bad_marker_binary_bytes(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    import agile_state as st
    st.repo_file(repo).write_bytes(b"\xff\xfe\x00bad")
    rc, _, err = run("claude", claude("rm -rf x", repo))
    assert rc == 2 and "trạng thái hỏng" in err


def test_guard_codex_and_antigravity_event_shapes(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    # Codex: tool shell, command dạng chuỗi hoặc danh sách ["bash","-lc","<script>"], cwd ở payload hoặc workdir
    for tool in ("shell", "Bash", "exec_command"):
        rc, out, err = run("codex", {"tool_name": tool, "tool_input": {"command": "rm -rf x"}, "cwd": str(repo), "session_id": SID})
        assert rc == 2 and out == "" and "'irreversible_delete'" in err
    rc, _, err = run("codex", {"tool_name": "shell", "tool_input": {"command": ["bash", "-lc", "git add . && rm -rf x"], "workdir": str(repo)}, "session_id": SID})
    assert rc == 2 and "'irreversible_delete'" in err
    rc, _, err = run("codex", {"tool_name": "shell", "tool_input": {"command": ["rm", "-rf", "x"]}, "cwd": str(repo), "session_id": SID})
    assert rc == 2 and "'irreversible_delete'" in err
    rc, _, err = run("codex", {"tool_name": "shell", "tool_input": {"cmd": "rm -rf x"}, "cwd": str(repo), "session_id": SID})
    assert rc == 2
    assert run("codex", {"tool_name": "shell", "tool_input": {"command": ["ls"]}, "cwd": str(repo), "session_id": SID}) == (0, "", "")
    # Codex apply_patch có khoá command nhưng là patch, không phải shell
    patch = "*** Begin Patch\n*** Update File: a.md\n+rm -rf x\n*** End Patch"
    assert run("codex", {"tool_name": "apply_patch", "tool_input": {"command": patch}, "cwd": str(repo), "session_id": SID}) == (0, "", "")
    # Antigravity: toolCall.args.CommandLine, in JSON quyết định chặn ở stdout, thoát 0; cho qua in {}
    payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf x", "Cwd": str(repo)}}, "stepIdx": 1, "session_id": SID}
    rc, out, err = run("antigravity", payload)
    assert rc == 0 and err == ""
    decision = json.loads(out)
    assert decision["decision"] == "deny" and "'irreversible_delete'" in decision["reason"]
    ok = {"toolCall": {"name": "run_command", "args": {"CommandLine": "ls", "Cwd": str(repo)}}, "stepIdx": 1, "session_id": SID}
    assert run("antigravity", ok) == (0, "{}\n", "")
    write = {"toolCall": {"name": "write_to_file", "args": {"TargetFile": str(repo / "a.md")}}}
    assert run("antigravity", write) == (0, "{}\n", "")
    # PowerShell của Claude trên Windows
    rc, _, err = run("claude", claude("rm -rf x", repo, tool="PowerShell"))
    assert rc == 2
    # công cụ không phải shell: cho qua dù chứa chữ rm -rf x
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": "x", "content": "rm -rf x", "command": "rm -rf x"}, "cwd": str(repo), "session_id": SID}) == (0, "", "")
    assert run("claude", {"tool_name": "mcp__x__y", "tool_input": {"command": "rm -rf x"}, "cwd": str(repo), "session_id": SID}) == (0, "", "")
    # không có tên công cụ nhưng có lệnh: coi là shell (đóng)
    assert run("claude", {"tool_input": {"command": "rm -rf x"}, "cwd": str(repo), "session_id": SID})[0] == 2
    # shell mà không có lệnh
    assert run("claude", {"tool_name": "Bash", "tool_input": {}, "cwd": str(repo), "session_id": SID}) == (0, "", "")


# --- tìm file dấu và nhánh ----------------------------------------------------------------------------------------

def test_guard_finds_marker_walking_up(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)
    assert_blocked(sub, "rm -rf x", "irreversible_delete")


def test_guard_stops_at_first_git(tmp_path):
    outer = make_repo(tmp_path, branch="spr-12", marker="{broken", repo_always=True)
    inner = outer / "vendor"
    (inner / ".git").mkdir(parents=True)  # repo lồng: file dấu ở ngoài không áp
    assert_allowed(inner, "rm -rf x")


def test_guard_no_cwd_uses_process_cwd(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, branch="spr-12", marker="{broken", repo_always=True)
    monkeypatch.chdir(repo)
    rc, _, err = run("claude", {"tool_name": "Bash", "tool_input": {"command": "rm -rf x"}})
    assert rc == 2 and "'irreversible_delete'" in err
    monkeypatch.chdir(tmp_path)
    assert run("claude", {"tool_name": "Bash", "tool_input": {"command": "rm -rf x"}}) == (0, "", "")


def test_guard_state_without_git_repo(tmp_path):
    (tmp_path / "plain" / ".tmp").mkdir(parents=True)
    write_switch(tmp_path / "plain", good_marker(WITHOUT_BRANCH))  # không có .git: khoá repo theo đường thư mục
    assert_blocked(tmp_path / "plain", "rm -rf x", "irreversible_delete")
    assert_blocked(tmp_path / "plain", "rm -rf .tmp/x", "irreversible_delete")  # không có gốc repo: không có ngoại lệ .tmp


# --- ngoại lệ dọn .tmp/ (N1) --------------------------------------------------------------------------------------

def test_guard_tmp_cleanup_exception(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    (repo / ".tmp" / "scratch").mkdir()
    for cmd in ("rm -rf .tmp/scratch", "rm -fr .tmp/scratch", "rm -r -f .tmp/scratch", "rm --recursive .tmp/scratch",
                "rm -rf ./.tmp/scratch", "rm -rf .tmp/scratch/", "rm -rf .tmp\\scratch", "Remove-Item -Recurse -Force .tmp\\scratch",
                "rm -rf .tmp/a .tmp/b", "rm -rf '.tmp/with space'", "rm -rf .tmp/out*", "rm -rf .tmp/scratch/*", "rm -rf .tmp/ab[c]",
                "rm -rf " + str(repo / ".tmp" / "scratch"), "rmdir /s /q .tmp\\scratch"):
        assert_allowed(repo, cmd)


@pytest.mark.parametrize("cmd", [
    "rm -rf .tmp", "rm -rf .tmp/", "rm -rf .tmp/.", "rm -rf .tmp/../src", "rm -rf .tmp/x/../../src", "rm -rf .tmp/scratch ..", "rm -rf .tmp/scratch build",
    "rm -rf src/.tmp/x", "rm -rf /tmp/x", "rm -rf .tmp/$X", "rm -rf .tmp/x,../y", "rm -rf ~/.tmp/x", "rm -rf .tmp/{a,b}",
    "rm -rf .tmp/*/x/../..", "rm -rf .tm*/x", "cd src && rm -rf .tmp/scratch",
    "rm -rf .tmpx/a", "rm -rf", "Remove-Item -Recurse .tmp",
])
def test_guard_tmp_exception_not_applied(tmp_path, cmd):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    (repo / "src").mkdir()
    assert_blocked(repo, cmd, "irreversible_delete")


def test_guard_tmp_glob_and_old_marker_name_now_plain_files(tmp_path):
    """SPR-32 B3 (đổi quyết định CÓ CHỦ Ý): `.tmp/autopilot.json` không còn là file dấu được bảo vệ, chỉ là một file dưới `.tmp/`; `.tmp/*` và
    `.tmp/a*` không còn mở ra file dấu nên qua như mọi glob nằm trong `.tmp/`."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    (repo / ".tmp" / "autopilot.json").write_text("{}", encoding="utf-8")
    for cmd in ("rm -rf .tmp/autopilot.json", "rm -rf .tmp/AUTOPILOT.JSON", "rm -rf .tmp/*", "rm -rf .tmp/a*"):
        rc, _, err = run("claude", claude(cmd, repo))
        assert rc == 0 and "file dấu cũ" in err and "không còn tác dụng" in err, (cmd, rc, err)  # một dòng nhắc, không chặn


def test_guard_tmp_exception_from_subdir_uses_repo_root(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    sub = repo / "src"
    sub.mkdir()
    # từ thư mục con, `.tmp/x` là .tmp của thư mục con, không phải của gốc repo → chặn; đường tuyệt đối vào .tmp gốc → qua
    assert_blocked(sub, "rm -rf .tmp/x", "irreversible_delete")
    assert_blocked(sub, "rm -rf ../.tmp/x", "irreversible_delete")  # có ".."
    assert_allowed(sub, "rm -rf " + str(repo / ".tmp" / "x"))


def test_guard_tmp_exception_symlink_escapes(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    outside = tmp_path / "outside"
    outside.mkdir()
    link_dir(outside, repo / ".tmp" / "link")
    assert_blocked(repo, "rm -rf .tmp/link", "irreversible_delete")
    assert_blocked(repo, "rm -rf .tmp/link/inside", "irreversible_delete")
    assert_allowed(repo, "rm -rf .tmp/real")  # tên thường không tồn tại: vẫn nằm trong .tmp


def test_guard_tmp_dir_itself_a_link(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=None)
    outside = tmp_path / "outside"
    outside.mkdir()
    write_switch(repo, good_marker())
    (repo / ".tmp").rmdir()
    link_dir(outside, repo / ".tmp")
    assert_blocked(repo, "rm -rf .tmp/x", "irreversible_delete")  # .tmp là link ra ngoài: không có ngoại lệ


def test_guard_tmp_symlink_alias_resolved(tmp_path):
    """Liên kết trong `.tmp/` trỏ ra ngoài `.tmp/` thì chặn; trỏ tới file trong `.tmp/` thì qua (không còn file dấu để bảo vệ)."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    inside, outside_file = repo / ".tmp" / "real.txt", tmp_path / "elsewhere.txt"
    inside.write_text("x", encoding="utf-8")
    outside_file.write_text("x", encoding="utf-8")
    try:
        os.symlink(inside, repo / ".tmp" / "alias_in")
        os.symlink(outside_file, repo / ".tmp" / "alias_out")
    except (OSError, NotImplementedError):
        pytest.skip("không tạo được symlink trên máy này")
    assert_blocked(repo, "rm -rf .tmp/alias_out", "irreversible_delete")
    assert_allowed(repo, "rm -rf .tmp/alias_in")


# --- lỗi đầu vào ------------------------------------------------------------------------------------------------

def test_guard_bad_stdin_with_agile_off_passes_and_with_agile_on_blocks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run("claude", "{broken") == (0, "", "")
    assert run("antigravity", "[]") == (0, "{}\n", "")
    repo = make_repo(tmp_path / "r", branch="spr-12", marker=good_marker())
    monkeypatch.chdir(repo)
    rc, _, err = run("claude", '{"session_id": "t1", "tool_name": ')
    assert rc == 2 and "agile" in err
    rc, out, _ = run("antigravity", '{"session_id": "t1", "toolCall": ')
    assert rc == 0 and json.loads(out)["decision"] == "deny"


def test_guard_unexpected_exception_closed_when_agile_on(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    monkeypatch.chdir(repo)  # ngoại lệ lạ → xác định trạng thái từ thư mục của tiến trình hook
    monkeypatch.setattr(agile_guard, "_analyze", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    rc, _, err = run("claude", claude("git status", repo))
    assert rc == 2 and "RuntimeError" in err
    monkeypatch.setenv("AGILE_GUARD_DEBUG", "1")
    rc, _, err = run("claude", claude("git status", repo))
    assert rc == 2 and "Traceback" in err
    # agile TẮT: lỗi lạ không chặn việc của người dùng
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)
    assert run("claude", claude("git status", plain, session_id=None))[0] == 0


def _nest(cmd, layers):
    for _ in range(layers):
        cmd = 'bash -c "{}"'.format(cmd.replace('"', "'"))
    return cmd


def test_guard_deep_command_nesting_fails_closed(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    rc, _, err = run("claude", claude(_nest("rm -rf x", 3), repo))  # trong giới hạn: mở hết lớp, thấy push
    assert rc == 2 and "'irreversible_delete'" in err
    rc, _, err = run("claude", claude(_nest("rm -rf x", 4), repo))  # quá giới hạn: không phân tích được → chặn
    assert rc == 2 and "lồng" in err and "hook gặp lỗi" not in err
    rc, _, err = run("claude", claude(_nest("ls", 6), repo))
    assert rc == 2 and "lồng" in err
    plain = tmp_path / "plain"
    plain.mkdir()
    assert run("claude", claude(_nest("rm -rf x", 6), plain, session_id=None)) == (0, "", "")  # không có file dấu → qua


def test_guard_cli_subprocess(tmp_path):
    import subprocess
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    payload = json.dumps(claude("rm -rf x", repo))
    proc = subprocess.run([sys.executable, str(SCRIPTS / "agile_guard.py"), "--format", "claude"], input=payload,
                          capture_output=True, text=True, encoding="utf-8", cwd=str(repo))
    assert proc.returncode == 2 and "'irreversible_delete'" in proc.stderr and proc.stdout == ""
    ok = subprocess.run([sys.executable, str(SCRIPTS / "agile_guard.py"), "--format", "antigravity"], input="{broken",
                        capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path))
    assert ok.returncode == 0 and ok.stdout.strip() == "{}"


# ===================== vòng sửa 1 (S-RF1…S-RF9, T-RF1…T-RF4) =====================

def codex(cmd, cwd=None, workdir=None, session_id=SID):
    payload = {"tool_name": "shell", "tool_input": {"command": cmd}}
    if session_id is not None:
        payload["session_id"] = session_id
    if cwd is not None:
        payload["cwd"] = str(cwd)
    if workdir is not None:
        payload["tool_input"]["workdir"] = str(workdir)
    return payload


def fwd(path):
    return str(path).replace("\\", "/")


def test_guard_workdir_beats_session_cwd(tmp_path):
    """S-RF1 / T-RF3: thư mục của lệnh (workdir) quyết định, không phải cwd của phiên."""
    repo = make_repo(tmp_path / "a", branch="spr-12", marker=good_marker())
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    rc, _, err = run("codex", codex(["bash", "-lc", "rm -rf x"], cwd=elsewhere, workdir=repo))
    assert rc == 2 and "'irreversible_delete'" in err
    # cwd phiên trong repo có file dấu, workdir nơi không có: file dấu của phiên vẫn áp (thấy ở đâu cũng bật)
    rc, _, err = run("codex", codex(["bash", "-lc", "rm -rf x"], cwd=repo, workdir=elsewhere))
    assert rc == 2
    # workdir tương đối ghép với cwd phiên; Antigravity: Cwd trong args thắng cwd phiên
    (repo / "sub").mkdir()
    rc, _, err = run("codex", {"tool_name": "shell", "cwd": str(repo), "tool_input": {"command": "rm -rf x", "workdir": "sub"}, "session_id": SID})
    assert rc == 2
    ag = {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf x", "Cwd": str(repo)}}, "cwd": str(elsewhere), "session_id": SID}
    assert json.loads(run("antigravity", ag)[1])["decision"] == "deny"


def test_guard_error_after_event_dir_probes_event_dir(tmp_path, monkeypatch):
    """T-RF1 / S-RF4: lỗi sau khi có sự kiện → trạng thái xác định từ chính sự kiện (cwd của nó), không phải thư mục tiến trình."""
    claude = claude_without_session  # repo-scoped legacy case
    repo = make_repo(tmp_path / "r", branch="spr-12", marker="{broken", repo_always=True)
    away = tmp_path / "away"
    away.mkdir()
    monkeypatch.chdir(away)
    monkeypatch.setattr(agile_guard, "_analyze", lambda *a, **k: (_ for _ in ()).throw(ImportError("check không nhập được")))
    rc, _, err = run("claude", claude("git status", repo))
    assert rc == 2 and "ImportError" in err
    rc, out, _ = run("antigravity", {"toolCall": {"name": "run_command", "args": {"CommandLine": "git status", "Cwd": str(repo)}}})
    assert rc == 0 and json.loads(out)["decision"] == "deny"
    assert run("claude", claude("git status", away)) == (0, "", "")  # thư mục sự kiện agile TẮT: lỗi không chặn
    monkeypatch.setattr(agile_guard, "_analyze", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))  # (không `undo`: sẽ gỡ cả biến thư mục trạng thái)
    rc, _, err = run("claude", claude("git status", repo))
    assert rc == 2 and "RuntimeError" in err


@pytest.mark.parametrize("cmd", [
    "timeout 60 rm -rf x", "timeout -s KILL 30 rm -rf x", "timeout --signal=KILL 5 rm -rf x", "timeout -k 5 60 rm -rf x",
    "env -i rm -rf x", "env -u HOME rm -rf x", "env FOO=bar BAZ=1 rm -rf x", "env -i FOO=1 rm -rf x", "env -S 'rm -rf x'",
    "sudo -u deploy rm -rf x", "sudo -E rm -rf x", "sudo -u x -g y rm -rf x", "sudo --user=x rm -rf x",
    "nice -n 10 rm -rf x", "nice -10 rm -rf x", "command -p rm -rf x", "nohup rm -rf x", "time rm -rf x", "time -p rm -rf x",
    "ls | xargs -0 rm -rf x", "xargs -n 1 -I {} rm -rf x", "echo x | xargs -r rm -rf x",
    "stdbuf -oL rm -rf x", "exec rm -rf x", "/usr/bin/env rm -rf x", "sudo env FOO=1 timeout 5 rm -rf x",
])
def test_guard_prefix_wrappers_with_their_arguments(tmp_path, cmd):
    """S-RF2 / T-RF6: tiền tố kèm cờ và đối số vẫn lộ lệnh thật."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, cmd, "irreversible_delete")


def test_guard_prefix_wrappers_other_items(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, "timeout 60 rm -rf build", "irreversible_delete")
    assert_blocked(repo, "ls | xargs -0 rm -rf", "irreversible_delete")
    assert_allowed(repo, "timeout 60 ls")
    assert_allowed(repo, "env -i FOO=1 ls")
    assert_allowed(repo, "sudo -u x ls")


def test_guard_more_patterns(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, "find . -name '*.o' -delete", "irreversible_delete")
    assert_blocked(repo, "find build -exec rm -rf {} +", "irreversible_delete")
    assert_blocked(repo, "find build -type d -execdir rm -r {} +", "irreversible_delete")
    assert_allowed(repo, "find . -name '*.py'")
    assert_allowed(repo, "find . -name x -exec grep foo {} +")


@pytest.mark.skipif(os.name != "nt", reason="tên file không phân biệt hoa thường chỉ trên Windows")
def test_guard_state_path_case_insensitive_on_windows(tmp_path):
    """S-RF7 (đổi đích sang thư mục trạng thái): đường so không phân biệt hoa thường nơi hệ file như vậy."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_tamper_blocked(repo, "rm {S}/SESSION-T1.JSON")
    assert_tamper_blocked(repo, "rm {S}/Sess*")


def test_guard_tmp_glob_expands_and_checks_each_match(tmp_path):
    """S-RF3 / T-RF7: đích glob mở rộng theo thư mục lệnh; mỗi mục khớp phải nằm thật trong .tmp/."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / ".tmp" / "keep1").mkdir()
    (repo / ".tmp" / "keep2").mkdir()
    assert_allowed(repo, "rm -rf .tmp/keep*")
    assert_allowed(repo, "rm -rf .tmp/nomatch*")  # không khớp gì: không xoá gì
    link_dir(outside, repo / ".tmp" / "lnk")
    assert_blocked(repo, "rm -rf .tmp/ln*", "irreversible_delete")
    assert_blocked(repo, "rm -rf .tmp/l*", "irreversible_delete")
    assert_blocked(repo, "rm -rf .tmp/ln*/", "irreversible_delete")
    assert_blocked(repo, "rm -rf .tmp/lnk/", "irreversible_delete")
    assert_blocked(repo, "Remove-Item -Recurse -Force .tmp\\ln*", "irreversible_delete")
    assert_blocked(repo, "rm -rf .tmp/[kl]*", "irreversible_delete")  # khớp keep* lẫn lnk
    assert_allowed(repo, "rm -rf .tmp/keep[12]")


def test_guard_tmp_glob_unreadable_parent_blocks(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    real = os.listdir

    def failing(path="."):
        if str(path).endswith(".tmp"):
            raise OSError("denied")
        return real(path)

    monkeypatch.setattr(os, "listdir", failing)
    assert_blocked(repo, "rm -rf .tmp/keep*", "irreversible_delete")


# ===================== vòng sửa 2 (S-N-RF1, S-N-RF2, T-N-RF1, S-RF6 phần còn) =====================



# ===================== vòng sửa 3: mọi thao tác đổi thư mục trước merge/pull (không -C) = main =====================



# ===================== TK8 vòng 1: bảo vệ file dấu, công cụ ghi file, cụm cờ, nối dòng, eval/ống, -C, launcher, hooks.json =====================

@pytest.mark.parametrize("cmd", [
    "rm {S}/{F}", "rm -f {S}/{F}", "rm -f {S}/*", "rm {S}/sess*", "rm {S}/SESSION-T1.JSON",
    "rm -f {S}/./{F}", "rm -f {S}\\{F}", "mv {S}/{F} .tmp/x", "mv x {S}/{F}",
    "mv {S} x", "cp x {S}/{F}", "cp /dev/null {S}/{F}", "Remove-Item {S}\\{F}",
    "Remove-Item {S}/*", "Move-Item {S}/{F} x", "Rename-Item {S}/{F} y", "Set-Content {S}/{F} '{}'",
    "Out-File -FilePath {S}/{F}", "echo '{}' > {S}/{F}", "echo x >> {S}/{F}",
    "echo x >{S}/{F}", "echo x 2>{S}/{F}", "> {S}/{F}", ": > {S}/{F}",
    "echo x | tee {S}/{F}", "truncate -s 0 {S}/{F}", "sed -i s/a/b/ {S}/{F}",
    "sed -i.bak s/a/b/ {S}/{F}", "python -c pass {S}/{F}", "git rm {S}/{F}", "git checkout -- {S}",
    "unlink {S}/{F}", "cd {S} && rm {F}", "cd {S}; rm *", "Set-Location {S}; Remove-Item {F}",
])
def test_guard_state_dir_is_protected_from_shell_writes(tmp_path, cmd):
    """RF2 (TK8 tr-a) / RF3 (tr-b), đích đổi từ file dấu sang thư mục trạng thái agile (SC7.2): không xoá, đổi tên, ghi đè bằng lệnh shell không chỉ-đọc."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_tamper_blocked(repo, cmd)


def test_guard_state_protection_read_only_and_other_files_allowed(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    (repo / ".tmp" / "autopilot.json").write_text("{}", encoding="utf-8")  # file dấu cũ: chỉ là file thường, rào không còn bảo vệ
    for cmd in ("cat {S}/{F}", "type {S}" + chr(92) + "{F}", "Get-Content {S}/{F}", "ls {S}", "ls {S}/*",
                "ls -la {S}/{F}", "test -f {S}/{F}", "[ -f {S}/{F} ]", "grep always {S}/{F}",
                "git status .tmp", "git diff .tmp/autopilot.json", "sed -n 1p {S}/{F}", "head -n 1 {S}/{F}",
                "echo hi", "rm -f .tmp/other.txt", "rm .tmp/scratch.txt", "cp a b", "mv a b", "echo x > .tmp/out.txt", "echo x > out.txt",
                "echo x > src/autopilot.json.bak", "python -c pass .tmp/notes.json", "rm .tmp/autopilot.json", "echo x > .tmp/autopilot.json"):
        rc, out, err = run("claude", claude(expand(cmd), repo))
        assert rc == 0 and out == "" and (err == "" or "file dấu cũ" in err), (cmd, rc, err)


def test_guard_state_protection_resolves_from_command_dir_and_other_trees_allowed(tmp_path):
    repo = make_repo(tmp_path / "a", branch="spr-12", marker=good_marker())
    (repo / "src").mkdir()
    rel = fwd(os.path.relpath(state_dir() / "session-t1.json", repo / "src"))
    assert_tamper_blocked(repo / "src", "rm -f " + rel)  # tương đối + `..` từ thư mục lệnh
    assert_tamper_blocked(repo / "src", "rm -f {S}/{F}")
    assert_tamper_blocked(repo / "src", "rm -f {S}/../" + state_dir().name + "/{F}")  # `..` vòng lại
    assert_allowed(repo / "src", "rm -f .tmp/autopilot.json")  # `.tmp` của thư mục con: file thường
    other = tmp_path / "wt"
    (other / ".tmp").mkdir(parents=True)
    assert_allowed(repo, "echo '{}' > " + fwd(other / ".tmp" / "autopilot.json"))
    assert_allowed(repo, "cp x " + fwd(other / ".tmp" / "autopilot.json"))


def test_guard_state_protection_symlink_and_junction_alias(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    try:
        os.symlink(state_dir() / "session-t1.json", repo / ".tmp" / "alias")
    except (OSError, NotImplementedError):
        pass
    else:
        assert_tamper_blocked(repo, "rm .tmp/alias")
    link_dir(state_dir(), repo / "statelink")  # symlink hay junction; không có thì bỏ qua
    assert_tamper_blocked(repo, "rm statelink/{F}")
    assert_tamper_blocked(repo, "echo x > statelink/session-new.json")
    assert_tamper_blocked(repo, "rm -rf statelink")


@pytest.mark.parametrize("payload_of", ["claude_write", "claude_edit", "claude_multiedit", "claude_notebook", "codex_patch",
                                        "codex_patch_move", "antigravity_write", "antigravity_replace", "antigravity_multi"])
def test_guard_state_dir_blocks_write_tools(tmp_path, payload_of):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    target = str(state_dir() / "session-t1.json")
    rel = os.path.relpath(target, repo)
    payloads = {
        "claude_write": ("claude", {"tool_name": "Write", "tool_input": {"file_path": target, "content": "{}"}, "cwd": str(repo)}),
        "claude_edit": ("claude", {"tool_name": "Edit", "tool_input": {"file_path": rel, "old_string": "a", "new_string": "b"},
                                   "cwd": str(repo)}),
        "claude_multiedit": ("claude", {"tool_name": "MultiEdit", "tool_input": {"file_path": target, "edits": []}, "cwd": str(repo)}),
        "claude_notebook": ("claude", {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": target}, "cwd": str(repo)}),
        "codex_patch": ("codex", {"tool_name": "apply_patch", "cwd": str(repo),
                                  "tool_input": {"command": "*** Begin Patch\n*** Update File: " + target + "\n@@\n-a\n+b\n*** End Patch"}}),
        "codex_patch_move": ("codex", {"tool_name": "apply_patch", "cwd": str(repo),
                                       "tool_input": {"command": "*** Begin Patch\n*** Update File: x.md\n*** Move to: " + target + "\n*** End Patch"}}),
        "antigravity_write": ("antigravity", {"toolCall": {"name": "write_to_file", "args": {"TargetFile": target}}, "cwd": str(repo)}),
        "antigravity_replace": ("antigravity", {"toolCall": {"name": "replace_file_content", "args": {"TargetFile": target}}, "cwd": str(repo)}),
        "antigravity_multi": ("antigravity", {"toolCall": {"name": "multi_replace_file_content", "args": {"TargetFile": target, "Cwd": str(repo)}}}),
    }
    fmt, payload = payloads[payload_of]
    payload = dict(payload, session_id=SID)
    rc, out, err = run(fmt, payload)
    if fmt == "antigravity":
        decision = json.loads(out)
        assert rc == 0 and decision["decision"] == "deny" and TAMPER_REASON in decision["reason"]
    else:
        assert rc == 2 and TAMPER_REASON in err


def test_guard_write_tools_other_files_and_other_trees_allowed(tmp_path):
    repo = make_repo(tmp_path / "a", branch="spr-12", marker=good_marker())
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(repo / "src.md")}, "cwd": str(repo)}) == (0, "", "")
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(repo / ".tmp" / "notes.md")}, "cwd": str(repo)}) == (0, "", "")
    other = make_repo(tmp_path / "b", branch="spr-12")  # không file dấu: intake ghi file dấu lần đầu phải qua
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(other / ".tmp" / "autopilot.json")}, "cwd": str(other)}) == (0, "", "")
    # worktree khác (không phải file dấu đang bật): điều phối chép file dấu bằng công cụ ghi được qua
    wt = tmp_path / "wt"
    (wt / ".tmp").mkdir(parents=True)
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(wt / ".tmp" / "autopilot.json")}, "cwd": str(repo)}) == (0, "", "")


@pytest.mark.parametrize("cmd", ["sudo -Hu deploy rm -rf x", "sudo -Eu root rm -rf x", "env -iu HOME rm -rf x", "xargs -tI {} rm -rf x",
                                 "sudo -EHu x -g y rm -rf x", "env -iC /opt/x rm -rf x"])
# `-C` chỉ cần MỘT giá trị thư mục; `/tmp` từng dùng ở đây bao thư mục trạng thái của test trên Linux (tmp_path nằm trong /tmp) nên luật công tắc bắn
# trước luật xoá không đảo ngược. `/opt/x` không bao thư mục trạng thái trên nền nào: vẫn thử đúng cụm cờ ngắn kết thúc bằng cờ có giá trị.
def test_guard_short_flag_clusters_ending_in_value_flag(tmp_path, cmd):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, cmd, "irreversible_delete")
    assert_allowed(repo, cmd.replace("rm -rf x", "ls"))


def test_guard_line_continuation_joined(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, "rm \\\n-rf x", "irreversible_delete")
    assert_blocked(repo, "rm \\\r\n  -rf x", "irreversible_delete")
    assert_blocked(repo, "rm `\n-rf x", "irreversible_delete")
    assert_blocked(repo, "rm -rf \\\n x", "irreversible_delete")
    assert_allowed(repo, "ls \\\n-l")
    assert_blocked(repo, "ls\nrm -rf x", "irreversible_delete")


@pytest.mark.parametrize("cmd,item", [
    ('eval "rm -rf x"', "irreversible_delete"), ("eval rm -rf x", "irreversible_delete"), ("eval 'git add . && rm -rf x'", "irreversible_delete"), ("eval rm -rf build", "irreversible_delete"),
    ('iex "rm -rf x"', "irreversible_delete"), ("Invoke-Expression 'rm -rf x'", "irreversible_delete"),
    ("echo rm -rf x | bash", "irreversible_delete"), ('echo "rm -rf x" | sh', "irreversible_delete"), ("printf 'rm -rf x' | pwsh", "irreversible_delete"),
    ("echo rm -rf x | sudo bash", "irreversible_delete"), ("echo rm -rf x | bash -s", "irreversible_delete"), ("echo rm -rf x | iex", "irreversible_delete"),
    ('bash <<< "rm -rf x"', "irreversible_delete"), ("echo rm -rf build | bash", "irreversible_delete"),
])
def test_guard_eval_and_pipe_into_shell(tmp_path, cmd, item):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    rc, _, err = run("claude", claude(cmd, repo))
    assert rc == 2, (cmd, err)
    assert "'{}'".format(item) in err


def test_guard_eval_and_pipe_benign_allowed(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    for cmd in ("eval echo hi", "eval $(ssh-agent)", "echo hi | bash", "cat script.sh | bash", "curl -s x | sh", "echo git status | bash",
                "ls | grep git", "echo $X | bash", "bash -s < script.sh"):
        assert_allowed(repo, cmd)
    # lồng quá sâu qua eval: chặn
    deep = "eval \"eval 'eval \\\"eval git push\\\"'\""
    rc, _, _ = run("claude", claude(deep, repo))
    assert rc == 2


def test_guard_git_c_from_outside_repo_with_session_on(tmp_path):
    """Công tắc theo PHIÊN: agile BẬT thì rào bật dù lệnh chạy từ thư mục nào (thay cho việc dò file dấu của repo `-C`)."""
    repo = make_repo(tmp_path / "r", branch="spr-12")
    write_switch(repo, good_marker(), session_id=SID)
    outside = tmp_path / "outside"
    outside.mkdir()
    rel = fwd(os.path.relpath(repo, outside))
    for cmd in ("git -C {r} worktree remove --force x", "git -C {rel} worktree remove --force x", "cd {rel} && rm -rf x",
                "bash -c 'git -C {rel} worktree remove --force x'", "git -c a=b -C {rel} worktree remove --force x", "Set-Location {rel}; rm -rf x",
                "git -C {o} worktree remove --force x"):
        rc, _, err = run("claude", dict(claude(cmd.format(r=fwd(repo), rel=rel, o=fwd(outside)), outside), session_id=SID))
        assert rc == 2, (cmd, err)
    ok = dict(claude("git -C {} status".format(rel), outside), session_id=SID)
    assert run("claude", ok) == (0, "", "")
    off = claude_without_session("git -C {} worktree remove --force x".format(fwd(outside)), outside)  # cùng lệnh, không có session_id: phiên khác, agile TẮT
    assert run("claude", off) == (0, "", "")


# --- launcher ---

SH = shutil.which("sh")
LAUNCHER = Path(os.environ.get("AGILE_LAUNCHER_PATH", str(SCRIPTS / "agile-hook.sh")))


def run_launcher(cwd, payload, path_dirs, extra_env=None):
    env = {"PATH": os.pathsep.join(str(d) for d in path_dirs), "CLAUDE_PROJECT_DIR": fwd(cwd), "PYTHONIOENCODING": "utf-8",
           "AGENT_AGILE_STATE_DIR": os.environ["AGENT_AGILE_STATE_DIR"]}
    for key in ("SystemRoot", "SYSTEMROOT", "TEMP", "TMP", "HOME"):
        if key in os.environ:
            env[key] = os.environ[key]
    env.update(extra_env or {})
    import subprocess
    return subprocess.run([SH, fwd(LAUNCHER), "--format", "claude"], input=json.dumps(payload), capture_output=True, text=True,
                          encoding="utf-8", cwd=str(cwd), env=env)


@pytest.fixture
def bare_sh_ok(tmp_path):
    if SH is None:
        pytest.skip("không có `sh` trên máy này")
    empty = tmp_path / "emptybin"
    empty.mkdir()
    probe = run_launcher(tmp_path, {}, [empty])
    if probe.returncode != 0:
        pytest.skip("sh không chạy được với PATH rỗng trên máy này: " + probe.stderr[:80])
    return empty


WARNING = "KHÔNG hoạt động lần này"


def test_launcher_without_python_warns_and_exits_zero(tmp_path, bare_sh_ok):
    """SPR-32 B3: không có Python dùng được thì launcher KHÔNG tự phán đoán công tắc: cảnh báo rõ ở stderr, thoát 0 (giới hạn đã ghi)."""
    repo = make_repo(tmp_path / "r", branch="spr-12", marker=good_marker())
    sub = repo / "src"
    sub.mkdir()
    for cwd in (repo, sub):
        done = run_launcher(cwd, claude("git push", cwd), [bare_sh_ok])
        assert done.returncode == 0 and WARNING in done.stderr and "không chạy được Python" in done.stderr, done.stderr
    plain = make_repo(tmp_path / "p", branch="spr-12")
    done = run_launcher(plain, claude("git push", plain), [bare_sh_ok])
    assert done.returncode == 0 and WARNING in done.stderr  # cảnh báo như nhau, bật hay tắt: không giả vờ kiểm


def test_launcher_with_python_delegates_to_guard(tmp_path, bare_sh_ok):
    repo = make_repo(tmp_path / "r", branch="spr-12", marker=good_marker())
    path = [bare_sh_ok, Path(sys.executable).parent]
    blocked_run = run_launcher(repo, claude("rm -rf x", repo), path)
    if "không chạy được Python" in blocked_run.stderr:
        pytest.skip("launcher không thấy Python dùng được trong PATH thử")
    assert blocked_run.returncode == 2 and "'irreversible_delete'" in blocked_run.stderr
    assert run_launcher(repo, claude("ls", repo), path).returncode == 0
    plain = make_repo(tmp_path / "p", branch="spr-12")
    assert run_launcher(plain, claude("rm -rf x", plain, session_id=None), path).returncode == 0  # agile TẮT: guard ngủ


def test_launcher_is_posix_sh_text():
    text = LAUNCHER.read_bytes().decode("utf-8")
    assert text.startswith("#!/bin/sh\n") and "\r" not in text
    assert "python3" in text and "py -3" in text and "exit " in text and WARNING in text
    assert "has_marker" not in text and "autopilot" not in text.lower() and "--clear" not in text  # không còn dò file dấu hay lối --clear


# --- hooks/hooks.json ---

def test_hooks_json_registers_guard():
    """Hook sống máy-rộng: đổi lệnh hay matcher ở `hooks/hooks.json` thì cập nhật test này cùng commit. SPR-32 B6: ba sự kiện, dạng `command` + `args`
    (không `sh`), đúng dạng đã đo ở TK1; launcher `agile-hook.sh` còn trong repo nhưng không được gọi."""
    config = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert set(config["hooks"]) == {"SessionStart", "UserPromptExpansion", "PreToolUse"}
    hook_script = ["${CLAUDE_PLUGIN_ROOT}/scripts/agile_hook.py", "--format", "claude"]
    guard_script = ["${CLAUDE_PLUGIN_ROOT}/scripts/agile_guard.py", "--format", "claude"]
    for event in ("SessionStart", "UserPromptExpansion"):
        assert config["hooks"][event] == [{"hooks": [{"type": "command", "command": "python", "args": hook_script, "timeout": 10}]}], event
    entries = config["hooks"]["PreToolUse"]
    assert [e["matcher"] for e in entries] == ["Bash|PowerShell", "Write|Edit|MultiEdit|NotebookEdit", "Agent|Task"]  # RQ-435 L2a: tier_hook added, guard blocks unchanged
    assert entries[2]["hooks"] == [{"type": "command", "command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/tier_hook.py"], "timeout": 10}]
    for entry in entries[:2]:
        assert entry["hooks"] == [{"type": "command", "command": "python", "args": guard_script, "timeout": 10}]
        assert "onFailure" not in entry["hooks"][0]  # SPR-32 TK6e M3: đo 2026-11-16, thiếu `python` + `onFailure: block` chặn MỌI Bash/PowerShell của người chưa bật agile; để hook lỗi mở
    text = (REPO / "hooks" / "hooks.json").read_text(encoding="utf-8")
    assert "sh " not in text and "agile-hook.sh" not in text and "python3" not in text
    for name in ("agile-hook.sh", "agile_guard.py", "agile_hook.py"):
        assert (REPO / "scripts" / name).is_file(), name


# ===================== lối dừng cũ `--clear` đã bỏ (SPR-32 B3) =====================

def test_clear_flag_is_gone_and_format_is_required(tmp_path):
    """Lối dừng cũ `--clear <thư mục>` (xoá file dấu) không còn: argparse từ chối; `--format` bắt buộc. Lối dừng thật là `/agile stop` do người gõ."""
    import subprocess
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    done = subprocess.run([sys.executable, str(SCRIPTS / "agile_guard.py"), "--clear", str(repo)], capture_output=True, text=True,
                          encoding="utf-8", cwd=str(tmp_path), input="")
    assert done.returncode == 2 and "--format" in done.stderr
    assert not hasattr(agile_guard, "clear_marker") and not hasattr(agile_guard, "_is_clear_command")
    missing = subprocess.run([sys.executable, str(SCRIPTS / "agile_guard.py")], capture_output=True, text=True, encoding="utf-8",
                             cwd=str(tmp_path), input="{}")
    assert missing.returncode == 2 and "--format" in missing.stderr


def test_old_clear_command_text_is_just_a_command_now(tmp_path):
    """Lệnh cũ `python agile_guard.py --clear <dir>` không còn được cho qua đặc biệt: không đụng thư mục trạng thái thì chỉ là lệnh thường."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_allowed(repo, "python {} --clear {}".format(fwd(SCRIPTS / "agile_guard.py"), fwd(repo)))
    assert_tamper_blocked(repo, "python {} --clear {{S}}".format(fwd(SCRIPTS / "agile_guard.py")))  # nhưng vẫn bị chặn nếu nhắm thư mục trạng thái


def test_legacy_marker_only_prints_one_notice_and_never_blocks(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12")  # agile TẮT
    (repo / ".tmp" / "autopilot.json").write_text("{}", encoding="utf-8")
    rc, out, err = run("claude", claude("rm -rf x", repo))
    assert rc == 0 and out == "" and err.count("file dấu cũ") == 1 and err.count("\n") == 1
    rc, out, err = run("antigravity", {"toolCall": {"name": "run_command", "args": {"CommandLine": "ls", "Cwd": str(repo)}}})
    assert rc == 0 and out == "{}\n" and err.count("file dấu cũ") == 1  # antigravity: stdout vẫn chỉ `{}`, nhắc ở stderr
    (repo / ".tmp" / "autopilot.json").write_bytes(b"\xff\xfe not json")  # nội dung không bao giờ được đọc
    assert run("claude", claude("ls", repo))[0] == 0
    write_switch(repo, good_marker())  # agile BẬT: lệnh bị chặn là do trạng thái, và file dấu cũ không đổi gì
    rc, _, err = run("claude", claude("rm -rf x", repo))
    assert rc == 2 and "file dấu cũ" not in err


# ===================== TK8 vòng sửa 2: launcher dự phòng, find, đường tuyệt đối từ ngoài, cp nguồn, heredoc, stash =====================

@pytest.fixture
def outside(tmp_path):
    folder = tmp_path / "outside"
    folder.mkdir()
    return folder


def stage_launcher(folder, guard_text=None):
    """Chép launcher đang thử vào `folder` (như thư mục scripts của plugin), kèm guard giả nếu có; trả đường launcher đã chép."""
    folder.mkdir(parents=True, exist_ok=True)
    staged = folder / "agile-hook.sh"
    staged.write_bytes(LAUNCHER.read_bytes())
    if guard_text is not None:
        (folder / "agile_guard.py").write_text(guard_text, encoding="utf-8")
    return staged


def run_staged(staged, cwd, payload, path_dirs, stdin_text=None):
    import subprocess
    env = {"PATH": os.pathsep.join(str(d) for d in path_dirs), "CLAUDE_PROJECT_DIR": fwd(cwd),
           "AGENT_AGILE_STATE_DIR": os.environ["AGENT_AGILE_STATE_DIR"]}
    for key in ("SystemRoot", "SYSTEMROOT", "TEMP", "TMP", "HOME"):
        if key in os.environ:
            env[key] = os.environ[key]
    data = stdin_text if stdin_text is not None else json.dumps(payload)
    return subprocess.run([SH, fwd(staged), "--format", "claude"], input=data, capture_output=True, text=True, encoding="utf-8", cwd=str(cwd), env=env)


def test_launcher_guard_missing_warns_and_exits_zero(tmp_path, bare_sh_ok):
    staged = stage_launcher(tmp_path / "scripts_no_guard")  # không có agile_guard.py cạnh launcher
    plain = make_repo(tmp_path / "p", branch="spr-12")
    marked = make_repo(tmp_path / "m", branch="spr-12", marker=good_marker())
    path = [bare_sh_ok, Path(sys.executable).parent]
    for repo in (plain, marked):
        done = run_staged(staged, repo, claude("git push", repo), path)
        assert done.returncode == 0 and WARNING in done.stderr


def test_launcher_guard_broken_warns_and_exits_zero(tmp_path, bare_sh_ok):
    plain = make_repo(tmp_path / "p", branch="spr-12")
    marked = make_repo(tmp_path / "m", branch="spr-12", marker=good_marker())
    path = [bare_sh_ok, Path(sys.executable).parent]
    if run_launcher(plain, claude("git status", plain), path).returncode != 0:
        pytest.skip("launcher không thấy Python dùng được trong PATH thử")
    for index, text in enumerate(("def (:\n", "raise RuntimeError('boom')\n", "import no_such_module_xyz\n")):
        staged = stage_launcher(tmp_path / "scripts_bad_{}".format(index), text)
        for repo in (plain, marked):
            done = run_staged(staged, repo, claude("git push", repo), path)
            assert done.returncode == 0 and "guard lỗi" in done.stderr and WARNING in done.stderr, text


def test_launcher_passes_guard_exit_codes_and_stdout(tmp_path, bare_sh_ok):
    repo = make_repo(tmp_path / "r", branch="spr-12", marker=good_marker())
    path = [bare_sh_ok, Path(sys.executable).parent]
    code_of = "import sys\nprint('seen', sys.stdin.read().strip())\nsys.exit({})\n"
    staged = stage_launcher(tmp_path / "scripts_fake", code_of.format(0))
    done = run_staged(staged, repo, None, path, stdin_text="EVENT")
    if "seen" not in done.stdout:
        pytest.skip("launcher không thấy Python dùng được trong PATH thử")
    assert done.returncode == 0 and "seen EVENT" in done.stdout  # sự kiện đi nguyên vẹn tới guard
    (tmp_path / "scripts_fake" / "agile_guard.py").write_text(code_of.format(2), encoding="utf-8")
    two = run_staged(staged, repo, None, path, stdin_text="E")
    assert two.returncode == 2 and "guard lỗi" not in two.stderr  # mã 2 của guard trả nguyên, không thay bằng cảnh báo dự phòng


def test_launcher_has_no_guard_path_override(tmp_path, bare_sh_ok):
    """RF18: biến môi trường không đổi được guard mà launcher chạy."""
    assert "AGILE_GUARD_PATH" not in LAUNCHER.read_text(encoding="utf-8")
    plain = make_repo(tmp_path / "p", branch="spr-12")
    marked = make_repo(tmp_path / "m", branch="spr-12", marker=good_marker())
    path = [bare_sh_ok, Path(sys.executable).parent]
    evil = tmp_path / "evil.py"
    evil.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    done = run_launcher(marked, claude("rm -rf x", marked), path, {"AGILE_GUARD_PATH": fwd(evil)})
    if "không chạy được Python" in done.stderr:
        pytest.skip("launcher không thấy Python dùng được trong PATH thử")
    assert done.returncode == 2 and "'irreversible_delete'" in done.stderr  # guard thật vẫn chạy, giả không thay được
    assert run_launcher(plain, claude("ls", plain), path, {"AGILE_GUARD_PATH": fwd(evil)}).returncode == 0


@pytest.mark.parametrize("cmd,item", [
    ("find {S} -type f -exec rm {} +", "tamper"), ("find {S} -exec rm {} " + BS + ";", "tamper"), ("find {S}/.. -exec rm {} +", "tamper"),
    ("find {S} -execdir mv {} /tmp +", "tamper"), ("find {S} -name '*.json' -exec sed -i s/a/b/ {} +", "tamper"),
    ("find {S} -name '*.json' -delete", "irreversible_delete"),
])
def test_guard_find_exec_over_state_dir(tmp_path, cmd, item):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    rc, _, err = run("claude", claude(expand(cmd), repo))
    assert rc == 2, (cmd, err)
    assert (TAMPER_REASON if item == "tamper" else "'irreversible_delete'") in err


def test_guard_find_exec_elsewhere_or_read_only_allowed(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    (repo / "build").mkdir()
    # TK27b A1(iii): `find … -exec rm` chỉ qua khi điểm bắt đầu nằm trong `.tmp/` (trước đây `find build -exec rm {} +` qua)
    for cmd in ("find .tmp/x -exec rm {} +", "find . -name '*.py'", "find .tmp -exec grep level {} +", "find . -exec cat {} +",
                "find .tmp -name x -print", "find build -type f -exec ls {} +", "find {S} -exec grep always {} +", "find {S} -name x -print"):
        assert_allowed(repo, expand(cmd))
    assert_blocked(repo, "find build -exec rm {} +", "irreversible_delete")


def test_guard_absolute_paths_from_outside_the_tree(tmp_path, outside):
    """RF12: sự kiện có cwd ngoài cây repo; agile BẬT theo PHIÊN thì rào bật ở mọi thư mục; đường tuyệt đối/tương đối vào thư mục trạng thái vẫn được bảo vệ."""
    repo = make_repo(tmp_path / "r", branch="spr-12")
    write_switch(repo, good_marker(), session_id=SID)
    r, rel = fwd(repo), fwd(os.path.relpath(repo, outside))
    srel = fwd(os.path.relpath(state_dir(), outside))

    def from_outside(cmd):
        return run("claude", dict(claude(cmd, outside), session_id=SID))

    for cmd in ("rm {S}/{F}", "rm -f {S}/*", "rm -f " + srel + "/{F}", "rm -f '{S}/SESSION-T1.JSON'", "mv {S}/{F} {r}/x", "mv {S} {r}/old",
                "mv " + srel + " x", "Remove-Item {S}\\{F}", "echo x > {S}/{F}", "cp x {S}/{F}", "find {S} -exec rm {{}} +",
                "bash -c 'rm {S}/{F}'"):
        rc, _, err = from_outside(expand(cmd.replace("{r}", r)))
        assert rc == 2 and TAMPER_REASON in err, (cmd, err)
    for cmd in ("rm -rf {r}", "rm -rf {rel}", "rm -rf {r}/build", "rm -rf {r}/.tmp"):
        rc, _, err = from_outside(cmd.format(r=r, rel=rel))
        assert rc == 2 and "irreversible_delete" in err, (cmd, err)
    # chỉ-đọc và cây khác (không phải thư mục trạng thái) không bị chặn bởi rào chống phá
    for cmd in ("cat {S}/{F}", "ls {S}", "rm -f {o}/x.txt"):
        rc, out, err = from_outside(expand(cmd.replace("{o}", fwd(outside))))
        assert (rc, out, err) == (0, "", ""), (cmd, err)
    # dọn thư mục tạm bên trong .tmp của repo bằng đường tuyệt đối từ ngoài: cho qua (như trước); ghi file thường cũng qua
    (repo / ".tmp" / "scratch").mkdir()
    assert from_outside("rm -rf {r}/.tmp/scratch".format(r=r)) == (0, "", "")  # đường tuyệt đối vào `.tmp/` của cây khác: qua như trước
    assert from_outside("echo x > {r}/.tmp/notes.txt".format(r=r)) == (0, "", "")


def test_guard_write_tool_absolute_path_from_outside(tmp_path, outside):
    repo = make_repo(tmp_path / "r", branch="spr-12")
    write_switch(repo, good_marker(), session_id=SID)
    target = state_dir() / "session-t1.json"
    for path in (str(target), fwd(os.path.relpath(target, outside))):
        rc, _, err = run("claude", {"tool_name": "Write", "tool_input": {"file_path": path, "content": "{}"}, "cwd": str(outside), "session_id": SID})
        assert rc == 2 and TAMPER_REASON in err, path
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(repo / "a.md")}, "cwd": str(outside), "session_id": SID}) == (0, "", "")
    fresh = tmp_path / "fresh"
    (fresh / ".tmp").mkdir(parents=True)
    assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(fresh / ".tmp" / "autopilot.json")}, "cwd": str(outside),
                          "session_id": SID}) == (0, "", "")  # file tên cũ ở cây khác: chỉ là file thường


def test_guard_cp_state_as_source_only(tmp_path):
    """N2 (TK8 re-review B), đích đổi sang thư mục trạng thái: chép TỪ trạng thái (nguồn) qua; đích trong thư mục trạng thái hay mv: chặn."""
    repo = make_repo(tmp_path / "r", branch="spr-12", marker=good_marker())
    wt = tmp_path / "wt"
    (wt / ".tmp").mkdir(parents=True)
    w = fwd(wt)
    for cmd in ("cp {S}/{F} {w}/.tmp/x.json", "cp {S}/{F} {w}/.tmp/", "cp -f {S}/{F} {w}/.tmp/x.json",
                "Copy-Item {S}/{F} {w}/.tmp/x.json", "Copy-Item -Path {S}/{F} -Destination {w}/.tmp/x.json",
                "cp -t {w}/.tmp {S}/{F}"):
        assert_allowed(repo, expand(cmd.replace("{w}", w)))
    for cmd in ("cp {w}/.tmp/x.json {S}/{F}", "cp x {S}/{F}", "cp {S}/{F} {S}/{F}", "cp -t {S} x", "Copy-Item x -Destination {S}/{F}",
                "Copy-Item x {S}" + BS + "{F}", "mv {S}/{F} {w}/.tmp/x.json", "Move-Item {S}/{F} {w}", "cp {S}/{F} x > {S}/{F}"):
        assert_tamper_blocked(repo, cmd.replace("{w}", w))


@pytest.mark.parametrize("cmd", [
    "python - <<EOF\nrm -rf x\nEOF", "python - <<'EOF'\nrm -rf build\nrm -rf x\nEOF", "node - <<-EOF\n\trm -rf x\n\tEOF",
    "cat > notes.txt <<EOF\nrm -rf x\nEOF", "python3 - <<\"PY\"\nsubprocess.run(['git','push'])\nrm -rf x\nPY",
    "python - <<EOF\nrm -rf x\nEOF\ngit status", "cat <<EOF\nrm -rf x\nEOF", "tee out.txt <<EOF\nrm -rf x\nEOF",
])
def test_guard_heredoc_body_for_non_shell_is_data(tmp_path, cmd):
    """N3: thân heredoc cho python/node/cat… là dữ liệu, không bị coi là lệnh."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_allowed(repo, cmd)


@pytest.mark.parametrize("cmd,item", [
    ("bash <<EOF\nrm -rf x\nEOF", "irreversible_delete"), ("sh <<'EOF'\nrm -rf build\nEOF", "irreversible_delete"), ("bash -s <<-EOF\n\trm -rf x\n\tEOF", "irreversible_delete"),
    ("pwsh <<EOF\nrm -rf x\nEOF", "irreversible_delete"), ("cat <<EOF | bash\nrm -rf x\nEOF", "irreversible_delete"), ("python - <<EOF\nx\nEOF\nrm -rf x", "irreversible_delete"),
    ("cat > f <<EOF\nx\nEOF\nrm -rf x", "irreversible_delete"), ("eval <<EOF\nrm -rf x\nEOF", "irreversible_delete"),
    ("python - <<EOF\nx\nEOF\ncat <<EOF2 > {S}/{F}\ny\nEOF2", "tamper"),
])
def test_guard_heredoc_body_for_shell_still_analyzed(tmp_path, cmd, item):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    rc, _, err = run("claude", claude(expand(cmd), repo))
    assert rc == 2, (cmd, err)
    assert (TAMPER_REASON if item == "tamper" else "'{}'".format(item)) in err


@pytest.mark.parametrize("cmd", ["git stash -a", "git stash --all", "git stash push -a", "git stash push --all -m x", "git stash -ua", "git stash -au",
                                 "git stash push -ua", "git -C . stash -a",
                                 "git clean -fdx", "git clean -xdf", "git clean -fX", "git clean -f -x", "git clean --force -x", "git clean -f -X",
                                 "git clean -x --force", "git clean -fdX", "git -C . clean -fdx"])
def test_guard_stash_all_and_clean_x_still_blocked(tmp_path, cmd):
    """SPR-32 B3: các lệnh này phá dữ liệu chưa theo dõi/ignore tự thân (luật chữ cấm `stash` trần, `clean -fd[x]` khi chưa sao lưu): giữ chặn vô điều kiện, không phụ thuộc file dấu."""

    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, cmd, "irreversible_delete")


def test_guard_stash_and_clean_plain_allowed(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    # TK27b A3: `stash -u` và `clean -f[d]` chỉ còn qua khi file dấu bị gitignore (repo thật) — các ca đó ở tests/test_agile_guard_undo.py
    for cmd in ("git stash", "git stash list", "git stash pop", "git stash push -m x", "git stash show -p",
                "git clean -n", "git clean -nx", "git clean -x"):
        assert_allowed(repo, cmd)


def test_guard_old_python_guard_falls_back(tmp_path, monkeypatch):
    """Python < 3.9: không phân tích, chỉ xác định công tắc agile từ thư mục tiến trình (hàm lưới cuối)."""
    repo = make_repo(tmp_path / "r", branch="spr-12", marker="{broken", repo_always=True)
    plain = tmp_path / "p"
    plain.mkdir()
    import contextlib
    monkeypatch.chdir(repo)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        assert agile_guard._last_resort(["--format", "claude"]) == 2
    monkeypatch.chdir(plain)
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        assert agile_guard._last_resort(["--format", "claude"]) == 0
        assert agile_guard._last_resort(["--format=antigravity"]) == 0


# ===================== TK8 vòng sửa 3: heredoc theo nháy, file dấu lồng trong .tmp =====================

@pytest.mark.parametrize("cmd", [
    "echo 'a <<END'\nrm -rf x",
    'git commit -m "x <<EOF"\nrm -rf x origin HEAD',
    "echo \"y <<'EOF'\"\nrm -rf x",
    "echo hi # <<EOF\nrm -rf x",
    "echo a <<<'x <<EOF'\nrm -rf x",
    "cat <<EOF\nrm -rf x",  # không có dòng kết thúc: giữ thân để phân tích
    "python - <<EOF\nprint(1)\nrm -rf x\nEOFX",  # nhãn kết thúc phải khớp đúng
    "python - <<EOF\nprint(1)\n EOF\nrm -rf x",  # thụt lề không phải dòng kết thúc của <<
    "echo 'multi\nline <<EOF'\nrm -rf x\nEOF",
])
def test_guard_heredoc_only_outside_quotes_and_comments(tmp_path, cmd):
    """RF16: `<<` trong nháy hay comment, hoặc heredoc không có dòng kết thúc, không được che lệnh thật."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    assert_blocked(repo, cmd, "irreversible_delete")


def test_guard_real_heredoc_still_data(tmp_path):
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    for cmd in ("python - <<EOF\nrm -rf x\nEOF", "python - <<'EOF'\nrm -rf x\nEOF", "node - <<-EOF\n\trm -rf x\n\tEOF",
                "cat > f <<EOF\nrm -rf x\nEOF", "python - <<EOF\nx = '<<'\nrm -rf x\nEOF\ngit status"):
        assert_allowed(repo, cmd)


def test_guard_tmp_cleanup_allowed_even_when_target_holds_legacy_marker_files(tmp_path):
    """RF15/RF17/G3 (đổi quyết định CÓ CHỦ Ý, B3): không còn khái niệm file dấu lồng: dọn thư mục trong `.tmp/` có chứa `.tmp/autopilot.json` lồng bên
    trong qua như mọi thư mục dưới `.tmp/` (không còn `--clear` từng thư mục)."""
    repo = make_repo(tmp_path, branch="spr-12", marker=good_marker())
    nested = repo / ".tmp" / "livetest"
    (nested / ".tmp").mkdir(parents=True)
    (nested / ".tmp" / "AutoPilot.JSON").write_text("{}", encoding="utf-8")
    deep = repo / ".tmp" / "wrap" / "a" / "b" / "c"
    (deep / ".tmp").mkdir(parents=True)
    (deep / ".tmp" / "autopilot.json").write_text("{}", encoding="utf-8")
    for cmd in ("rm -rf .tmp/livetest", "rm -rf .tmp/wrap", "Remove-Item -Recurse -Force .tmp" + BS + "livetest", "rm -rf .tmp/live*", "rm -rf .tmp/wrap/a"):
        assert_allowed(repo, cmd)
    assert_blocked(repo, "rm -rf .tmp/../src", "irreversible_delete")  # ngoại lệ vẫn không vượt ra ngoài `.tmp/`

# ===================== SPR-32 B3: kích hoạt theo trạng thái agile (SC1.7, SC4.3, R0-M11) và chống phá công tắc (SC7.2, R0-M6, R1b-M1b) =====================
# Mọi test dùng thư mục trạng thái tạm (`agile_state_dir`), không bao giờ thư mục trạng thái thật của máy. Luật chống phá là so khớp chuỗi/đường:
# test ghi các dạng bị chặn VÀ các dạng được phép; dạng gián tiếp (ghép tên từ mảnh, viết script rồi chạy sau) KHÔNG bị chặn và không có test nói ngược.

ALWAYS = set(rules.OPEN_ALWAYS_BLOCKED)


def session_payload(cmd, cwd, **extra):
    return dict(claude(cmd, cwd), session_id=SID, **extra)


def blocked_delete(payload):
    rc, _, err = run("claude", payload)
    return rc == 2 and "'irreversible_delete'" in err, err


# --- kích hoạt ------------------------------------------------------------------------------------------------------

def test_agile_off_and_healthy_state_means_dormant_for_every_format(tmp_path):
    repo = make_repo(tmp_path)
    assert run("claude", session_payload("rm -rf x", repo)) == (0, "", "")
    assert run("codex", {"tool_name": "shell", "tool_input": {"command": "rm -rf x"}, "cwd": str(repo), "session_id": SID}) == (0, "", "")
    ag = {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf x", "Cwd": str(repo)}}, "session_id": SID}
    assert run("antigravity", ag) == (0, "{}\n", "")
    # kể cả lệnh đổi công tắc: agile TẮT thì rào ngủ hẳn (không có gì để bảo vệ)
    assert run("claude", session_payload("python scripts/agile_state.py on --session x", repo)) == (0, "", "")


def test_session_switch_activates_only_that_session(tmp_path):
    claude = claude_without_session  # ca này kiểm tra cả payload không có session_id
    repo = make_repo(tmp_path)
    write_secure_session(repo, good_marker(), session_id=SID)
    assert blocked_delete(session_payload("rm -rf x", repo))[0]
    other = dict(claude("rm -rf x", repo), session_id="another-session")
    assert run("claude", other) == (0, "", "")
    assert run("claude", claude("rm -rf x", repo)) == (0, "", "")  # không có session_id
    for fmt, payload in (("codex", {"tool_name": "shell", "tool_input": {"command": "rm -rf x"}, "cwd": str(repo), "session_id": SID}),
                         ("antigravity", {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf x", "Cwd": str(repo)}}, "session_id": SID})):
        rc, out, err = run(fmt, payload)
        assert (rc == 2 and "'irreversible_delete'" in err) or (fmt == "antigravity" and json.loads(out)["decision"] == "deny"), fmt


def test_repo_always_activates_every_session_of_that_repo_only(tmp_path):
    """SPR-37 FR3.1: always chỉ bật agile, không tự bật rào."""
    repo = make_repo(tmp_path / "a")
    write_repo_always(repo, good_marker())
    assert st.load_state(repo, SID)["effective_on"]
    assert run("claude", claude("rm -rf x", repo)) == (0, "", "")


def test_project_dir_env_decides_the_repo_key(tmp_path, monkeypatch):
    """SPR-37 FR3.1: khoá repo theo môi trường, rào theo secure của phiên."""
    repo = make_repo(tmp_path / "r")
    write_repo_always(repo, good_marker())
    sub = repo / "sub"
    (sub / ".git").mkdir(parents=True)
    assert not st.load_state(sub, SID)["effective_on"]
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    assert st.load_state(sub, SID)["effective_on"]
    assert run("claude", claude("rm -rf x", sub)) == (0, "", "")
    write_secure_session(repo, {})
    assert blocked_delete(claude("rm -rf x", sub))[0]


def test_subagent_without_session_file_is_guarded_not_dormant(tmp_path):
    """SPR-37 CQ4 = C: tác tử con thiếu file phiên thì rào ngủ khi trạng thái lành."""
    repo = make_repo(tmp_path)
    sub = dict(claude_without_session("rm -rf x", repo), session_id="no-such-session", agent_id="child")
    assert agile_guard.activation(sub) is None
    assert run("claude", sub) == (0, "", "")
    sub.pop("session_id")
    assert run("claude", sub) == (0, "", "")


def test_subagent_with_matching_session_file_follows_the_switch(tmp_path):
    repo = make_repo(tmp_path)
    write_secure_session(repo, good_marker(), session_id=SID)
    assert blocked_delete(session_payload("rm -rf x", repo, agent_id="a1", agent_type="general-purpose"))[0]  # cùng session_id (TK1b)
    st.apply_command("secure_off", repo, SID, source="hook")  # phiên đã TẮT tường minh: có file phiên khớp → tác tử con cũng ngủ
    assert run("claude", session_payload("rm -rf x", repo, agent_id="a1")) == (0, "", "")


@pytest.mark.parametrize("which", ["session", "repo"])
@pytest.mark.parametrize("text", ["{not json", "[]", "", "\xef\xbf\xbd"])
def test_corrupt_state_fails_guarded(tmp_path, which, text):
    """SC4.3: trạng thái hỏng → công tắc TẮT nhưng rào vẫn bật, chặn cả 13 mục."""
    repo = make_repo(tmp_path)
    write_repo_always(repo, text, session_id=SID if which == "session" else None)
    rc, _, err = run("claude", session_payload("rm -rf x", repo))
    assert rc == 2 and "trạng thái hỏng" in err and "'irreversible_delete'" in err
    active, broken, _ = agile_guard.activation(session_payload("ls", repo))
    assert broken and set(active) == set(ALL)
    assert run("claude", session_payload("ls", repo)) == (0, "", "")  # lệnh không khớp mẫu vẫn qua


def test_state_dir_that_is_a_file_or_relative_override_fails_guarded(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(blocker))
    ok, err = blocked_delete(session_payload("rm -rf x", repo))
    assert ok and "trạng thái hỏng" in err
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", "relative/dir")  # đường tương đối bị lớp trạng thái bỏ qua và báo hỏng
    ok, err = blocked_delete(session_payload("rm -rf x", repo))
    assert ok and "trạng thái hỏng" in err


def test_unimportable_state_layer_fails_guarded(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)

    def boom():
        raise ImportError("không nhập được agile_state")

    monkeypatch.setattr(agile_guard, "_state_module", boom)
    ok, err = blocked_delete(session_payload("rm -rf x", repo))
    assert ok and "trạng thái hỏng" in err
    active, broken, dirs = agile_guard.activation(session_payload("ls", repo))
    assert broken and set(active) == set(ALL) and dirs == ()


def test_state_layer_exception_fails_guarded(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    monkeypatch.setattr(st, "load_state", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    ok, err = blocked_delete(session_payload("rm -rf x", repo))
    assert ok and "trạng thái hỏng" in err


def test_unreadable_home_does_not_break_the_guard(tmp_path, monkeypatch):
    """`platform_state_dir()` không xác định được (không có thư mục home) chỉ làm mất một ứng viên đường, không làm rào hỏng."""
    repo = make_repo(tmp_path)
    write_switch(repo, good_marker())
    monkeypatch.setattr(st, "platform_state_dir", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no home")))
    active, broken, dirs = agile_guard.activation(claude("ls", repo))
    assert not broken and active == ALWAYS and dirs


def test_broken_stdin_still_finds_the_session(tmp_path, monkeypatch):
    """JSON hỏng nhưng còn đọc được `session_id` bằng biểu thức chính quy → vẫn xác định được công tắc (không đoán theo thư mục tiến trình)."""
    repo = make_repo(tmp_path)
    write_switch(repo, good_marker(), session_id=SID)
    monkeypatch.chdir(repo)
    rc, _, err = run("claude", '{"session_id": "%s", "tool_name": "Bash", "tool_input": {' % SID)  # cụt giữa chừng
    assert rc == 2 and "hook gặp lỗi" in err
    assert run("claude", '{"session_id": "other", "tool_name": ') == (0, "", "")


def test_guard_cli_subprocess_uses_state_and_never_reads_the_legacy_marker(tmp_path):
    repo = make_repo(tmp_path)
    (repo / ".tmp" / "autopilot.json").write_text("{}", encoding="utf-8")  # file dấu cũ: không có tác dụng
    write_switch(repo, good_marker(), session_id=SID)
    env = dict(os.environ)
    argv = [sys.executable, str(SCRIPTS / "agile_guard.py"), "--format", "claude"]
    on = subprocess.run(argv, input=json.dumps(session_payload("rm -rf x", repo)), capture_output=True, text=True, encoding="utf-8", cwd=str(repo), env=env)
    assert on.returncode == 2 and "'irreversible_delete'" in on.stderr and on.stdout == ""
    off = subprocess.run(argv, input=json.dumps(dict(claude("rm -rf x", repo), session_id="not-on")), capture_output=True, text=True, encoding="utf-8",
                         cwd=str(repo), env=env)
    assert off.returncode == 0 and off.stdout == "" and "file dấu cũ" in off.stderr and off.stderr.count("\n") == 1


# --- chống phá công tắc: dạng bị chặn --------------------------------------------------------------------------------

STATE_ENV_FORMS = ["rm $T_STATE/{F}", "rm ${T_STATE}/{F}", "Remove-Item $env:T_STATE\\{F}", "del %T_STATE%\\{F}", "echo x > $T_STATE/{F}",
                   "echo x > $env:T_STATE\\session-new.json", "cd $T_STATE", "mv $T_STATE/{F} x"]


@pytest.mark.parametrize("cmd", STATE_ENV_FORMS)
def test_state_dir_by_environment_variable_forms_blocked(tmp_path, monkeypatch, cmd):
    monkeypatch.setenv("T_STATE", str(state_dir()))
    assert_tamper_blocked(make_repo(tmp_path, marker=good_marker()), cmd)


@pytest.mark.parametrize("cmd", ["rm $UNKNOWN_DIR/session-a.json", "rm -f $X/repo-0123.json", "Remove-Item $env:NOPE\\session-b.json",
                                 "echo x > %NOPE%\\repo-1.json", "cd $NOWHERE && rm session-c.json", "cd src && rm repo-1.json"])
def test_unresolvable_path_with_state_file_name_blocked(tmp_path, cmd):
    """Biến không biết giá trị hay đã đổi thư mục (đường tương đối không giải được): so theo tên file trạng thái, đóng an toàn."""
    assert_tamper_blocked(make_repo(tmp_path, marker=good_marker()), cmd)


def test_platform_default_state_dir_is_protected_even_with_an_override(tmp_path):
    repo = make_repo(tmp_path, marker=good_marker())
    default = fwd(st.platform_state_dir())
    for cmd in ("rm {d}/session-a.json", "echo x > {d}/repo-9.json", "mv {d} {d}-old", "rm -rf {d}/..", "Set-Content {d}/{F} x"):
        rc, _, err = run("claude", claude(cmd.format(d=default, F="session-t1.json"), repo))
        assert rc == 2, (cmd, err)
    for cmd in ("rm -rf ~/.local/state/agent-agile-team/x", "rm $HOME/.local/state/agent-agile-team/session-1.json",
                "rm %LOCALAPPDATA%" + BS + "agent-agile-team" + BS + "state" + BS + "session-1.json",
                "Remove-Item $env:LOCALAPPDATA" + BS + "agent-agile-team" + BS + "state" + BS + "repo-1.json"):
        assert_tamper_blocked(repo, cmd)


@pytest.mark.parametrize("cmd", [
    "python scripts/agile_state.py off", "python scripts/agile_state.py on --session x", "python scripts/agile_state.py stop",
    "python scripts/agile_state.py always", "python scripts/agile_state.py manual --session x", "python scripts/agile_state.py --json off",
    "python3 -X utf8 scripts/agile_state.py stop --project .", "py -3 scripts/agile_state.py OFF", "python -m agile_state stop",
    "python -m scripts.agile_state off", "./scripts/agile_state.py off", "python C:/x/plugin/scripts/agile_state.py stop",
    "python scripts" + BS + "agile_state.py stop", "bash -c 'python scripts/agile_state.py stop'", "sh -c \"python scripts/agile_state.py off\"",
    "pwsh -Command \"python scripts/agile_state.py stop\"", "cmd /c python scripts\\agile_state.py stop", "timeout 5 python scripts/agile_state.py off",
    "env FOO=1 python scripts/agile_state.py off", "xargs python scripts/agile_state.py stop", "true && python scripts/agile_state.py stop",
    "echo ok; python scripts/agile_state.py stop",
])
def test_switching_agile_state_script_blocked(tmp_path, cmd):
    assert_tamper_blocked(make_repo(tmp_path, marker=good_marker()), cmd)


@pytest.mark.parametrize("cmd", [
    "python scripts/agile_hook.py", "python3 scripts/agile_hook.py < payload.json", "echo '{}' | python scripts/agile_hook.py",
    "cat p.json | python -I scripts/agile_hook.py", "python -X utf8 C:/x/scripts/agile_hook.py", "./scripts/agile_hook.py",
    "python scripts/agile_hook.py <<EOF\n{}\nEOF", "python -m agile_hook", "bash -c 'echo {} | python scripts/agile_hook.py'",
])
def test_running_the_hook_script_blocked(tmp_path, cmd):
    assert_tamper_blocked(make_repo(tmp_path, marker=good_marker()), cmd)


@pytest.mark.parametrize("cmd", [
    "python -c \"import agile_state; agile_state.apply_command('off', '.', 'x')\"", "python -c 'import agile_hook'",
    "python -c \"from agile_state import apply_command\"", "python -c \"__import__('agile_state')\"",
    "python3 -c \"import importlib; importlib.import_module('agile_hook')\"", "python - <<EOF\nimport agile_state\nEOF",
    "python - <<'EOF'\nfrom agile_hook import run\nEOF", "cat > t.py <<EOF\nimport agile_state\nEOF", "pwsh -c \"python -c 'import agile_state'\"",
    "python -c \"import os, agile_state\"", "python -c \"import importlib.util as u; u.spec_from_file_location('m', 'scripts/agile_state.py')\"",
])
def test_importing_the_state_modules_blocked(tmp_path, cmd):
    assert_tamper_blocked(make_repo(tmp_path, marker=good_marker()), cmd)


@pytest.mark.parametrize("cmd", [
    "AGENT_AGILE_STATE_DIR=/tmp/x python scripts/agile_state.py status", "export AGENT_AGILE_STATE_DIR=/tmp/x", "export AGENT_AGILE_STATE_DIR",
    "$env:AGENT_AGILE_STATE_DIR = 'C:\\x'", "set AGENT_AGILE_STATE_DIR=C:\\x", "setx AGENT_AGILE_STATE_DIR C:\\x",
    "[Environment]::SetEnvironmentVariable('AGENT_AGILE_STATE_DIR','C:\\x','User')", "env AGENT_AGILE_STATE_DIR=/tmp/x claude", "unset AGENT_AGILE_STATE_DIR",
    "export CLAUDE_PROJECT_DIR=/tmp/other", "CLAUDE_PROJECT_DIR=/tmp/other python scripts/agile_state.py status", "$env:CLAUDE_PROJECT_DIR='D:\\o'",
    "env -u CLAUDE_PROJECT_DIR ls", "env --unset=AGENT_AGILE_STATE_DIR ls", "python -c \"import os; os.environ['AGENT_AGILE_STATE_DIR']='x'\"",
    "Set-Item Env:AGENT_AGILE_STATE_DIR C:\\x", "bash -c 'export CLAUDE_PROJECT_DIR=/x; ls'", "FOO=1 AGENT_AGILE_STATE_DIR=. true",
])
def test_redirecting_state_by_environment_blocked(tmp_path, cmd):
    assert_tamper_blocked(make_repo(tmp_path, marker=good_marker()), cmd)


def test_tamper_rules_apply_to_subagents_and_other_formats(tmp_path):
    repo = make_repo(tmp_path)
    payloads = [
        ("claude", dict(claude("python scripts/agile_state.py off", repo, session_id=None), agent_id="a9")),
        ("antigravity", {"toolCall": {"name": "run_command", "args": {"CommandLine": "python scripts/agile_state.py stop", "Cwd": str(repo)}}, "agent_id": "a9"}),
        ("codex", {"tool_name": "shell", "tool_input": {"command": ["bash", "-lc", "python scripts/agile_state.py off"]}, "cwd": str(repo), "agent_id": "a9"}),
    ]
    for fmt, payload in payloads:
        rc, out, err = run(fmt, payload)
        assert (rc, out, err) == ((0, "{}\n", "") if fmt == "antigravity" else (0, "", ""))
    write_secure_session(repo, {})
    for fmt, payload in payloads:
        payload["session_id"] = SID
        rc, out, err = run(fmt, payload)
        if fmt == "antigravity":
            assert rc == 0 and json.loads(out)["decision"] == "deny" and TAMPER_REASON in json.loads(out)["reason"]
        else:
            assert rc == 2 and TAMPER_REASON in err



# --- chống phá công tắc: dạng được phép ------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "python scripts/agile_state.py status", "python scripts/agile_state.py status --json --session x", "python scripts/agile_state.py get",
    "python scripts/agile_state.py get --json --project .", "python3 -X utf8 scripts/agile_state.py status", "python -m agile_state status",
    "cat scripts/agile_hook.py", "grep -n apply_command scripts/agile_state.py", "grep 'import agile_state' tests/test_agile_state.py",
    "rg \"import agile_hook\" scripts", "head -n 5 scripts/agile_state.py", "sed -n 1,5p scripts/agile_hook.py", "type scripts" + BS + "agile_state.py",
    "git diff scripts/agile_state.py", "git log -- scripts/agile_hook.py", "git add tests/test_agile_state.py tests/test_agile_hook.py",
    "python -m pytest tests/test_agile_state.py -q", "pytest tests/test_agile_hook.py", "python scripts/check.py --self", "python -c \"import json; print(1)\"",
    "echo $AGENT_AGILE_STATE_DIR", "printenv CLAUDE_PROJECT_DIR", "echo \"$CLAUDE_PROJECT_DIR/x\"", "echo $env:AGENT_AGILE_STATE_DIR",
    "ls {S}", "ls -la {S}/{F}", "cat {S}/{F}", "Get-Content {S}/{F}", "Get-ChildItem {S}", "grep always {S}/{F}", "cp {S}/{F} out.json",
    "ls scripts", "echo agile_state is a module", "python - <<EOF\nimport json\nEOF", "echo on", "python scripts/other.py off",
])
def test_readonly_and_unrelated_forms_allowed(tmp_path, cmd):
    repo = make_repo(tmp_path, marker=good_marker())
    rc, out, err = run("claude", claude(expand(cmd), repo))
    assert (rc, out, err) == (0, "", ""), (cmd, err)


def test_write_tool_blocked_only_for_state_paths(tmp_path):
    repo = make_repo(tmp_path, marker=good_marker())
    state = state_dir()
    for path in (state / "session-t1.json", state / "repo-whatever.json", state / "new-file.txt", state):
        rc, _, err = run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "{}"}, "cwd": str(repo), "session_id": SID})
        assert rc == 2 and TAMPER_REASON in err, path
    link_dir(state, repo / "alias")
    rc, _, err = run("claude", {"tool_name": "Edit", "tool_input": {"file_path": "alias/session-t1.json", "old_string": "a", "new_string": "b"},
                                "cwd": str(repo), "session_id": SID})
    assert rc == 2 and TAMPER_REASON in err  # liên kết/junction giải về thư mục trạng thái
    for path in (repo / "scripts" / "agile_state.py", repo / "tests" / "test_agile_state.py", repo / "session-notes.json", tmp_path / "state-copy" / "x.json"):
        assert run("claude", {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "import agile_state"}, "cwd": str(repo), "session_id": SID}) == (0, "", "")


def test_hook_state_write_path_is_not_a_tool_call(tmp_path):
    """Đường được phép tắt: hook `UserPromptExpansion` do người gõ `/agile stop` ghi trạng thái trong tiến trình hook, không qua công cụ nên rào
    không can thiệp; sau đó rào ngủ."""
    repo = make_repo(tmp_path)
    write_switch(repo, good_marker(), session_id=SID)
    assert blocked_delete(session_payload("rm -rf x", repo))[0]
    import agile_hook
    out = agile_hook.run({"hook_event_name": "UserPromptExpansion", "command_name": "agent-agile-team:agile", "command_args": "stop",
                          "session_id": SID, "cwd": str(repo), "prompt_id": "p1"})
    assert out is None
    assert run("claude", session_payload("rm -rf x", repo)) == (0, "", "")
