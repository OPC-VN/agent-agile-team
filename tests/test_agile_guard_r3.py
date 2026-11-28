"""SPR-32 TK6h: sửa vòng review R3 của rào agile (agile_guard.py): đổi thư mục lên thư mục trạng thái hay tổ tiên của nó rồi dùng đường tương đối (RF1),
lệnh "chỉ-đọc" mà ghi được (RF2), `$(...)`/dấu huyền/thân heredoc đưa vào trình thông dịch (RF3), phiên con `claude -p` (RF4), hạn nội bộ nan/inf (RF5),
và chữ "năm hook" sai (hooks.json có bốn mục). Chạy: python -m pytest -q tests/test_agile_guard_r3.py

Cách dựng: thư mục trạng thái dạng thật `<nhà>/.claude/plugins/data/agent-agile-team/state` (tên cuối đúng `state`, như bản cài thật), repo ở cây khác
(`<tmp>/work/repo`) để `cd ..` từ repo KHÔNG đi lên tổ tiên của thư mục trạng thái."""

from __future__ import annotations

import json
import os

import pytest

import agile_guard
from test_agile_guard import BS, TAMPER_REASON, assert_allowed, claude, good_marker, make_repo, run

pytestmark = pytest.mark.usefixtures("agile_state_dir")
FILE = "session-t1.json"
# Ghép chuỗi để file test không chứa nguyên văn đường thư mục giả (quy ước như test_communication_rules.py); giá trị lúc chạy không đổi.
_H = "ho" + "me"


@pytest.fixture
def layout(tmp_path, monkeypatch):
    state = tmp_path / "home" / ".claude" / "plugins" / "data" / "agent-agile-team" / "state"
    state.mkdir(parents=True)
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(state))
    repo = make_repo(tmp_path / "work", marker=good_marker())
    return repo, state


def fmt(cmd, repo, state):
    slash = lambda path: str(path).replace("\\", "/")  # noqa: E731
    parent = state.parent
    return (cmd.replace("{REL}", slash(os.path.relpath(parent, repo))).replace("{PB}", str(parent).replace("/", BS))
            .replace("{S}", slash(state)).replace("{P}", slash(parent)).replace("{G}", slash(parent.parent)).replace("{F}", FILE))


def blocked(layout, cmd):
    repo, state = layout
    text = fmt(cmd, repo, state)
    rc, _, err = run("claude", claude(text, repo))
    assert rc == 2 and TAMPER_REASON in err, (text, rc, err)


def allowed(layout, cmd):
    repo, state = layout
    assert_allowed(repo, fmt(cmd, repo, state))


# --- RF1: cd tới thư mục trạng thái hay tổ tiên rồi đường tương đối --------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "cd {P}; rm state/*", "cd {P} && rm state/sess*", "cd {P}; mv state x", "pushd {P}; rm state/*", "Set-Location {PB}; Remove-Item state" + BS + "*.json",
    "cd {P}; sed -i s/true/false/ state/*.json", "cd {S}", "cd {S}/..", "cd {G}", "sl {P}", "push-location {PB}", "chdir {P}", "cd '{P}'", "cd \"{PB}\"",
    "git status && cd {P} && ls", "(cd {P}; ls)", "bash -c 'cd {P}; ls'", "cd {REL}; ls", "Set-Location -Path {PB}", "Set-Location -LiteralPath:{PB}",
    "env -C {P} rm state/*", "env -C{P} ls", "env --chdir={P} ls", "sudo -D {P} ls", "pushd {S}", "cd {G}/..",
])
def test_rf1_cd_to_the_state_directory_or_an_ancestor_is_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "cd $UNSET_DIR; rm state/*", "cd /unrelated; rm state/sess*", "cd $UNSET_DIR && mv state x", "cd /unrelated; Remove-Item state" + BS + "*.json",
    "cd /unrelated; sed -i s/true/false/ state/*.json", "cd $UNSET_DIR; mv * /tmp/x", "cd $UNSET_DIR; rm */*.json", "cd $UNSET_DIR; rm st*/*.json",
    "cd /unrelated; rm -f agent-agile-team/state/x", "cd /unrelated; mv data/agent-agile-team old", "cd /unrelated; rm $UNSET_X/state/y", "cd /unrelated; rm state",
])
def test_rf1_relative_arguments_after_a_cd_that_could_reach_the_state_directory_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "cd /unrelated-dir && ls", "cd .. && ls", "cd src; rm build.log", "cd docs && rm old.md", "cd sub && git add .",
    "cd sub && git commit -m state", "cd tests; cat state/x", "cd tests; ls state", "cd /unrelated; rm -f out/*.json", "cd /unrelated; mv a.txt b.txt",
    "cd /unrelated; cp state/x out.json", "cd sub && sed -i s/a/b/ main.py", "cd /unrelated; rm *.log", "cd /unrelated; mv *.md docs/", "pushd sub", "popd",
    "env -C sub ls", "cd . && ls", "cd src && git checkout -b feature", "git -C src status",
])
def test_rf1_legit_cd_and_commands_stay_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF2: lệnh trong danh sách chỉ-đọc mà ghi được -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "sort -o {S}/{F} x.txt", "sort --output={S}/{F} x.txt", "sort -ro {S}/{F} x.txt", "uniq a.txt {S}/{F}", "xxd -r a.hex {S}/{F}", "find . -fprint {S}/{F}",
    "find . -fls {S}/{F}", "find . -fprintf {S}/{F} x", "git diff --output={S}/{F}", "git log --output={S}/{F}", "git show --output={S}/{F} HEAD",
    "tee {S}/{F}", "echo x | tee -a {S}/{F}", "dd if=a of={S}/{F}", "cp a.txt {S}/{F}", "mv a.txt {S}/{F}", "ln -sf a.txt {S}/{F}",
    "sed -i s/a/b/ {S}/{F}", "awk -i inplace '{print}' {S}/{F}", "awk '{print > \"{S}/{F}\"}' a.txt",
    "sort -o {REL}/state/{F} x.txt", "uniq a.txt {REL}/state/{F}", "awk -i inplace 1 {REL}/state/{F}",
])
def test_rf2_read_only_names_that_write_into_the_state_directory_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "sort a.txt", "sort -o out.txt a.txt", "sort -r a.txt | uniq -c", "uniq a.txt", "uniq -c a.txt", "xxd a.bin", "xxd -r a.hex out.bin", "find . -name x", "find . -fprint out.txt",
    "git diff", "git log --oneline", "git diff --output=out.patch", "git show HEAD", "awk '{print $1}' a.txt", "cat {S}/{F} | sort | uniq -c", "sort {S}/{F}", "uniq {S}/{F}",
    "xxd {S}/{F}", "find {S} -name x", "git diff --stat", "cp {S}/{F} out.json", "head -n 3 {S}/{F} | tee out.txt",
])
def test_rf2_the_same_commands_without_a_state_target_are_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF3: thay thế lệnh, dấu huyền, thân heredoc đưa vào trình thông dịch -------------------------------------------------------------------

PYWRITE = "python -c \"open(r'{S}/{F}','w')\""


@pytest.mark.parametrize("cmd", [
    "echo $(" + PYWRITE + ")", "printf %s \"$(" + PYWRITE + ")\"", "echo `" + PYWRITE + "`", "printf '%s' \"`" + PYWRITE + "`\"", "echo $(echo $(" + PYWRITE + "))",
    "echo $(" + PYWRITE.replace("'w'", "'w'; x=1") + ")", "test -n \"$(" + PYWRITE + ")\"", "diff <(" + PYWRITE + ") a.txt", "cat <(" + PYWRITE + ")",
    "cat <<EOF | python\nopen(r'{S}/{F}','w')\nEOF", "cat <<'EOF' | python3 -\nopen(r'{S}/{F}','w')\nEOF", "cat <<EOF | node\nrequire('fs').unlinkSync('{S}/{F}')\nEOF",
    "cat <<EOF | tee x | python\nopen(r'{S}/{F}','w')\nEOF", "cat <<EOF | sudo python\nopen(r'{S}/{F}','w')\nEOF", "echo $(rm {S}/{F})",
])
def test_rf3_state_path_inside_a_substitution_or_a_heredoc_for_an_interpreter_is_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "echo $(cat {S}/{F})", "echo $(date)", "echo `date`", "printf %s \"$(ls {S})\"", "diff <(cat {S}/{F}) a.txt", "cat <<EOF | wc -l\n{S}/{F}\nEOF",
    "cat <<EOF | python\nprint(1)\nEOF", "cat <<EOF | tee out.txt\n{S}/{F}\nEOF", "echo $(git rev-parse HEAD)", "cat {S}/{F} | wc -l",
])
def test_rf3_substitutions_and_heredocs_without_a_state_write_are_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF4: phiên con có session_id riêng (`claude -p`, `--resume`) với lệnh agile -----------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "claude -p \"/agent-agile-team:agile stop\"", "claude --resume abc123 -p \"/agent-agile-team:agile stop\"", "claude -p '/agile stop' --resume abc123",
    "echo \"/agent-agile-team:agile stop\" | claude -p", "claude --continue -p \"/agile off\"", "claude --print \"/agent-agile-team:agile always\"",
    "claude.cmd -p \"/agile stop\"", "bash -c 'claude -p \"/agile stop\"'", "FOO=1 claude -p /agile", "timeout 60 claude -p \"/agent-agile-team:agile\"",
])
def test_rf4_spawning_claude_with_an_agile_command_is_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "claude -p \"summarize the sprint report\"", "claude --version", "claude -p \"explain agile methods\"", "git commit -m \"docs: agile stop wording\"",
    "claude --resume abc123", "echo \"/agile stop\" > notes.txt", "grep -r '/agile' docs", f"ls /{_H}/agile",
])
def test_rf4_other_claude_calls_and_mentions_stay_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF5: AGILE_GUARD_DEADLINE_S không hợp lệ phải về mặc định 6 s -----------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["nan", "NaN", "inf", "-inf", "Infinity", "0", "-1", "-0.5", "abc", "", " ", "1e999", "1,5"])
def test_rf5_invalid_deadline_env_falls_back_to_the_default(value):
    assert agile_guard.deadline_seconds({agile_guard.DEADLINE_ENV: value}) == agile_guard.DEADLINE_SECONDS


@pytest.mark.parametrize("value, expected", [("0.5", 0.5), ("3", 3.0), ("1e-9", 1e-9)])
def test_rf5_valid_deadline_env_may_only_shorten_the_limit(value, expected):
    assert agile_guard.deadline_seconds({agile_guard.DEADLINE_ENV: value}) == expected


@pytest.mark.parametrize("value", ["7", "60", "1e6"])
def test_rf5_deadline_env_cannot_extend_beyond_the_default(value):
    assert agile_guard.deadline_seconds({agile_guard.DEADLINE_ENV: value}) == agile_guard.DEADLINE_SECONDS


def test_rf5_missing_env_gives_the_default():
    assert agile_guard.deadline_seconds({}) == agile_guard.DEADLINE_SECONDS
