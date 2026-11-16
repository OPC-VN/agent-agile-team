"""SPR-32 TK6e: sửa vòng review R2 của rào agile (agile_guard.py): chặn đường thư mục trạng thái nằm trong mã (RF1), ký tự đại diện ở phần thư mục (RF2),
hạn nội bộ và hiệu năng lệnh dài (RF3), bớt chặn nhầm khi chỉ nhắc tên script hay biến (S1, S2). Chạy: python -m pytest -q tests/test_agile_guard_r2.py"""

from __future__ import annotations

import io
import json
import os
import time

import pytest

import agile_guard
from test_agile_guard import (BS, SID, TAMPER_REASON, assert_allowed, assert_tamper_blocked, claude, expand, good_marker, make_repo, run, state_dir,
                              write_switch)

pytestmark = pytest.mark.usefixtures("agile_state_dir")


def on_repo(tmp_path):
    return make_repo(tmp_path, marker=good_marker())


# --- S1: `agile_state.py`/`agile_hook.py` chỉ là "chạy" khi đứng đầu câu lệnh hay ngay sau trình thông dịch Python ---------------------------

@pytest.mark.parametrize("cmd", [
    "git add scripts/agile_hook.py", "cp scripts/agile_hook.py /tmp/x.py", "ruff check scripts/agile_hook.py", "git checkout -- scripts/agile_hook.py",
    "git checkout main -- scripts/agile_hook.py", "git add scripts/agile_state.py off", "mv scripts/agile_hook.py scripts/agile_hook_old.py",
    "diff scripts/agile_hook.py scripts/agile_state.py", "ruff check scripts/agile_state.py stop",
])
def test_s1_mentioning_the_script_is_not_running_it(tmp_path, cmd):
    assert_allowed(on_repo(tmp_path), cmd)


@pytest.mark.parametrize("cmd", [
    "python scripts/agile_hook.py", "python3 -u scripts/agile_state.py off", "py -3 scripts/agile_state.py stop", "py -3 -X utf8 scripts/agile_state.py on",
    "./scripts/agile_state.py off", "scripts/agile_hook.py", "python -m agile_state off", "python -B -m agile_state always",
    "timeout 5 python scripts/agile_hook.py", "FOO=1 python scripts/agile_state.py manual", "uv run scripts/agile_state.py off",
    "poetry run python scripts/agile_state.py off", "cd x && python C:" + BS + "p" + BS + "agile_hook.py", "echo {} | python scripts/agile_hook.py",
    "bash -c 'python scripts/agile_state.py off'", "python scripts/agile_state.py status; python scripts/agile_state.py off",
])
def test_s1_running_the_script_is_still_blocked(tmp_path, cmd):
    assert_tamper_blocked(on_repo(tmp_path), cmd)


# --- S2: đặt/export biến đổi hướng trạng thái xét theo từng câu lệnh, bỏ câu chỉ-đọc -----------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "grep -r CLAUDE_PROJECT_DIR= .", "git log --grep 'AGENT_AGILE_STATE_DIR=x'", "rg 'AGENT_AGILE_STATE_DIR=' .", "cat notes.md | grep CLAUDE_PROJECT_DIR=",
    "git grep AGENT_AGILE_STATE_DIR= -- docs", "echo AGENT_AGILE_STATE_DIR=x is documented",
])
def test_s2_read_only_mentions_of_the_variable_are_allowed(tmp_path, cmd):
    assert_allowed(on_repo(tmp_path), cmd)


@pytest.mark.parametrize("cmd", [
    "grep foo x; export CLAUDE_PROJECT_DIR=/x", "grep x y && AGENT_AGILE_STATE_DIR=. python z.py", "echo 'export AGENT_AGILE_STATE_DIR=x' >> ~/.bashrc",
    "find . -exec env AGENT_AGILE_STATE_DIR=x ls {} +", "cat a | AGENT_AGILE_STATE_DIR=. python -", "git log --grep x | env CLAUDE_PROJECT_DIR=/q cat",
    "python - <<EOF\nimport os\nos.environ['AGENT_AGILE_STATE_DIR'] = 'x'\nEOF",
])
def test_s2_setting_the_variable_is_still_blocked(tmp_path, cmd):
    assert_tamper_blocked(on_repo(tmp_path), cmd)


# --- RF1: đường thư mục trạng thái nằm trong mã (chưa tách token) ----------------------------------------------------------------------------

RF1_BLOCKED = [
    "python -c \"import os;os.remove(r'{S}/{F}')\"",
    "python - <<'EOF'\nimport os\nos.remove('{S}/{F}')\nEOF",
    "python <<EOF\nimport shutil\nshutil.rmtree('{S}')\nEOF",
    "python3 -c \"import shutil; shutil.rmtree(r'{S}')\"",
    "powershell -Command \"[System.IO.File]::Delete('{S}/{F}')\"",
    "pwsh -c \"[IO.File]::WriteAllText('{S}/{F}','x')\"",
    "powershell -c \"(Get-Item {S}/{F}).Delete()\"",
    "node -e \"require('fs').unlinkSync('{S}/{F}')\"",
    "perl -e 'unlink \"{S}/{F}\"'",
    "python -c \"import os;os.remove(r'{SB}" + BS + "{F}')\"",
    "python -c \"import os;os.remove('{SB2}" + BS + BS + "{F}')\"",
    "awk 'BEGIN{system(\"rm {S}/{F}\")}'",
    "x=$(rm {S}/{F})",
    "python -c \"import os\"; python -c \"os.remove('{S}/{F}')\"",
]


def rf1(cmd):
    state = str(state_dir())
    return expand(cmd).replace("{SB2}", state.replace("\\", "\\\\")).replace("{SB}", state)


@pytest.mark.parametrize("cmd", RF1_BLOCKED)
def test_rf1_literal_state_path_inside_code_is_blocked(tmp_path, cmd):
    rc, _, err = run("claude", claude(rf1(cmd), on_repo(tmp_path)))
    assert rc == 2 and TAMPER_REASON in err, (cmd, rc, err)


@pytest.mark.parametrize("cmd", [
    "cat {S}/{F}", "ls {S}", "ls -la {S}/{F}", "grep -r always {S}", "head -n 3 {S}/{F}", "Get-Content {S}/{F}", "Get-ChildItem {S}", "cp {S}/{F} out.json",
    "echo {S}", "cat {S}/{F} | wc -l", "cat {S}/{F} > out.txt", "git status", "python scripts/agile_state.py status",
])
def test_rf1_bare_reads_of_the_state_directory_stay_allowed(tmp_path, cmd):
    assert_allowed(on_repo(tmp_path), expand(cmd))


def test_rf1_write_tool_paths_with_wildcards_blocked(tmp_path):
    repo = on_repo(tmp_path)
    parent = str(state_dir().parent).replace("\\", "/")
    pattern = parent + "/" + state_dir().name[:-2] + "??/session-t1.json"
    rc, _, err = run("claude", {"tool_name": "Write", "tool_input": {"file_path": pattern, "content": "{}"}, "cwd": str(repo)})
    assert rc == 2 and TAMPER_REASON in err


# --- RF2: ký tự đại diện ở phần thư mục -------------------------------------------------------------------------------------------------------

def wild(cmd):
    """`{P}` = thư mục cha của thư mục trạng thái, `{N}` = tên thư mục trạng thái bỏ hai ký tự cuối, `{N2}` = như `{N}` nhưng `?` thay hai ký tự."""
    parent = str(state_dir().parent).replace("\\", "/")
    name = state_dir().name
    return expand(cmd).replace("{P}", parent).replace("{PB}", parent.replace("/", BS)).replace("{N}", name[:-2]).replace("{Q}", name[:-3] + "?" + name[-2:])


@pytest.mark.parametrize("cmd", [
    "rm {P}/{N}*/{F}", "rm {P}/{Q}/{F}", "rm {P}/{N}??/session-*.json", "rm {P}/[a-z]*/{F}", "Remove-Item \"{PB}" + BS + "{N}*" + BS + "*.json\"",
    "Get-ChildItem {PB}" + BS + "{N}* | Remove-Item", "ls {P}/{N}* | xargs rm", "Remove-Item -Path {P}/{N}?? -Recurse", "mv {P}/{N}*/{F} /tmp/x",
    "rm -f {P}/*/{F}",
])
def test_rf2_wildcard_in_directory_part_blocked(tmp_path, cmd):
    rc, _, err = run("claude", claude(wild(cmd), on_repo(tmp_path)))
    assert rc == 2 and TAMPER_REASON in err, (cmd, rc, err)


@pytest.mark.parametrize("cmd", [
    "cat {P}/{N}*/{F}", "ls {P}/{N}*", "rm {P}/zzzz*/{F}", "rm {P}/no?such/x.json", "Get-ChildItem {PB}" + BS + "{N}*", "ls {P}/{N}* | wc -l", "rm out/*.json",
])
def test_rf2_reads_and_unrelated_wildcards_allowed(tmp_path, cmd):
    assert_allowed(on_repo(tmp_path), wild(cmd))


# --- RF3: hiệu năng với lệnh dài, hạn nội bộ --------------------------------------------------------------------------------------------------

def test_rf3_import_state_pattern_is_linear_on_long_whitespace():
    for text in ('python -c "import' + " " * 60000, "import" + " " * 60000 + "x", "from" + " " * 60000):
        begin = time.perf_counter()
        agile_guard.IMPORT_STATE.search(text)
        assert time.perf_counter() - begin < 1.0, text[:12]


def test_rf3_long_command_is_analysed_in_bounded_time(tmp_path):
    repo = on_repo(tmp_path)
    for cmd in ("echo " + "ab " * 14000, "echo a; " * 5000, 'python -c "import' + " " * 40000):
        begin = time.perf_counter()
        rc, _, err = run("claude", claude(cmd, repo))
        took = time.perf_counter() - begin
        assert took < 4.0, (cmd[:20], took)
        assert rc == 0, (cmd[:20], err)


def test_rf3_deadline_blocks_when_exceeded(tmp_path, monkeypatch):
    repo = on_repo(tmp_path)
    monkeypatch.setattr(agile_guard, "deadline_seconds", lambda env: 0.0)  # TK6h RF5: `AGILE_GUARD_DEADLINE_S=0` nay về mặc định; hạn 0 chỉ đặt được ở đây
    rc, _, err = run("claude", claude("echo hi; echo there", repo))
    assert rc == 2 and "guard deadline: command too long to check" in err, (rc, err)
    rc, out, _ = run("antigravity", claude("echo hi; echo there", repo))
    assert rc == 0 and json.loads(out)["decision"] == "deny" and "guard deadline" in json.loads(out)["reason"]


def test_rf3_deadline_does_not_touch_a_dormant_guard_or_a_fast_command(tmp_path, monkeypatch):
    real_deadline = agile_guard.deadline_seconds
    monkeypatch.setattr(agile_guard, "deadline_seconds", lambda env: 0.0)  # TK6h RF5: `AGILE_GUARD_DEADLINE_S=0` nay về mặc định; hạn 0 chỉ đặt được ở đây
    off = make_repo(tmp_path)  # agile TẮT: thoát trước khi phân tích, không cần hạn
    assert_allowed(off, "echo hi; echo there")
    monkeypatch.setattr(agile_guard, "deadline_seconds", real_deadline)
    assert_allowed(on_repo(tmp_path / "second"), "echo hi; echo there")


def test_rf3_deadline_default_stays_below_the_hook_timeout():
    config = json.loads((agile_guard_root() / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    timeouts = {hook["timeout"] for entry in config["hooks"]["PreToolUse"] for hook in entry["hooks"]}
    assert agile_guard.DEADLINE_SECONDS < min(timeouts)


def agile_guard_root():
    from conftest import REPO
    return REPO
