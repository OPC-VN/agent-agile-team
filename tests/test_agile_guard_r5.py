"""SPR-32 TK6k: sửa vòng review R5 của rào agile (agile_guard.py). Hai Phải sửa là hồi quy so với 7e9d35c:
(1) luật `claude -p … /agile` từng câu (TK6i) bỏ lọt các dạng mà luật chữ thô cũ chặn: `Start-Process claude -ArgumentList '-p','/agile stop'`, `start "" claude`,
`wsl|ssh|docker … claude`, prompt trong heredoc/here-string/ống (`cat <<EOF | claude -p`, `'/agile stop' | claude -p`, `echo … | tee x | claude -p`), `sh -c 'echo /agile stop | claude -p'`,
`pwsh -c "claude -p `"/agile stop`""`, `alias`/`iex`/`Start-Job`/`Invoke-Command`, `npm exec … -- @anthropic-ai/claude-code`, `claude -pc`; luật nay xét CÂU LỆNH: token chương trình
`claude` đứng riêng + cờ phiên + prompt bắt đầu bằng `/agile` trong chính câu đó (kể cả thân heredoc và vế đứng trước trong ống);
(2) đuôi ký tự đại diện sau `cd` (`rm state/*.{json,bak}`, `*.js{on}`, `*.$EXT`, `*.$'json'`): đuôi có `{ } $ ' " \\` có thể là `.json`.
Cộng `-EncodedCommand`: tiền tố `-`/`/`/`–`, base64 lỏng như PowerShell (khoảng trắng, xuống dòng, thiếu `=`, byte lẻ, ký tự thế), qua `Start-Process … -ArgumentList`, không giải mã được thì CHẶN;
và tên script có ký tự đại diện khớp tên file thật cạnh rào (`python scripts/a*_s*.py off`).
Chạy: python -m pytest -q tests/test_agile_guard_r5.py"""

from __future__ import annotations

import pytest

from test_agile_guard import BS, claude, run
from test_agile_guard_r4 import FILE, allowed, b64, blocked, encode_markers, fmt, layout  # noqa: F401  (layout: fixture)

pytestmark = pytest.mark.usefixtures("agile_state_dir")


# --- RF1 (security) / RF2 (Opus): `claude` với prompt `/agile` — các dạng đã chặn ở 7e9d35c và bị bỏ lọt ở TK6i ----------------------------------

@pytest.mark.parametrize("cmd", [
    "Start-Process claude -ArgumentList '-p','/agile stop'", "saps claude -ArgumentList '-p','/agile stop'", "Start-Process -FilePath claude -ArgumentList '-p','/agile stop'",
    "Start-Job {claude -p \"/agile stop\"}", "Invoke-Command -ScriptBlock {claude -p \"/agile stop\"}", "& (Get-Command claude) -p \"/agile stop\"",
    "start /min claude -p \"/agile stop\"", "start /b claude -p \"/agile stop\"", "start \"\" claude -p \"/agile stop\"", "start \"\" claude -p \"/agent-agile-team:agile stop\"",
    "cmd /c start /b claude -p \"/agile stop\"", "wsl claude -p \"/agile stop\"", "ssh host claude -p \"/agile stop\"", "ssh host \"claude -p '/agile stop'\"",
    "docker exec c claude -p \"/agile stop\"", "pwsh -c \"claude -p `\"/agile stop`\"\"", "pwsh -c \"claude -p \\\"/agile stop\\\"\"", "alias c=claude; c -p \"/agile stop\"",
    "iex \"claude -p `\"/agile stop`\"\"", "npm exec --yes --prefix /tmp/x --cache /tmp/c -- @anthropic-ai/claude-code -p \"/agile stop\"",
    "claude -pc \"/agile stop\"", "claude -cp \"/agile stop\"", "env X=1 claude -p '/agile stop'", "echo $(claude -p \"/agile stop\")",
    "Start-Process claude -ArgumentList '-p /agile stop'", "Start-Process claude -ArgumentList \"--print\",\"/agent-agile-team:agile always\"",
    "set-alias c claude; c --resume s1 \"/agile off\"", "x=claude; $x -p \"/agile stop\"",
])
def test_r5_claude_spawn_forms_with_an_agile_prompt_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "claude -p @'\n/agile stop\n'@", "claude -p <<'X'\n/agile stop\nX", "cat <<EOF | claude -p\n/agile stop\nEOF", "cat <<EOF | claude -p\n/agent-agile-team:agile stop\nEOF",
    "'/agile stop' | claude -p", "\"/agile stop\" | claude -p", "echo \"/agile stop\" | tee x.txt | claude -p", "sh -c 'echo /agile stop | claude -p'",
    "echo '/agile stop' | xargs claude -p", "printf '/agile stop' | tee a | tee b | claude --print", "echo \"/agile stop\" 2>&1 | claude -p",
    "cat <<-EOF | claude -p\n\t/agile stop\n\tEOF", "claude -p <<< \"/agile stop\"", "bash -c 'cat <<EOF | claude -p\n/agile stop\nEOF'",
])
def test_r5_prompt_through_a_pipe_or_a_body_is_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "grep -r \"/agile\" hosts/claude", "git log -p --grep=\"/agile\" -- hosts/claude", "grep -rn \"/agile\" skills | grep -c claude", "grep -r \"/agile\" . | claude -p \"summarize\"",
    "claude -p \"explain how /agile works\"", "git commit -m \"claude -p /agile\"", "echo \"claude -p /agile\"", "echo \"use claude -p then /agile\"", "grep -rn \"claude -p /agile\" docs/",
    "claude --version", "claude --resume abc123", "claude -p \"summarize the sprint report\"", "echo \"/agile stop\" > notes.txt", "cd hosts/claude && grep -r /agile .",
    "cat hosts/claude/README.md | grep -c /agile", "rg -n \"/agile\" hosts/claude -p", "grep -r \"/agile\" claude", "git log --oneline -p -- claude", "start \"\" notepad notes.txt",
    "Start-Process notepad -ArgumentList 'a.txt'", "npm install -g @anthropic-ai/claude-code", "npx @anthropic-ai/claude-code -p \"summarize the diff\"", "cp -r hosts/claude /agile/dest",
    "echo hi | claude -p \"fix the build\"", "cat prompt.txt | claude -p \"summarize\"", "echo \"/agile stop\"; claude -p \"summarize\"", "echo \"/agile stop\"\nclaude -p \"summarize\"",
    "Start-Process claude -ArgumentList '-p','summarize the diff'", "ssh host \"claude -p 'summarize'\"", "alias c=claude; c -p \"summarize\"",
    "echo '/agile' && claude -p \"fix it\"", "grep -n claude -r \"/agile\" docs", "git log claude -p --grep=\"/agile\"", "python tools/x.py hosts/claude -p \"/agile\"",
])
def test_r5_claude_mentions_and_other_prompts_stay_allowed(layout, cmd):
    allowed(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "python -c \"import subprocess; subprocess.run(['claude','-p','/agile stop'])\"", "claude -p < prompt.txt", "cat prompt.txt | claude -p", "$n='cla'+'ude'; & $n -p \"/agile stop\"",
    "claude -p \"$(cat prompt.txt)\"", "P=/agile; claude -p \"$P stop\"",
])
def test_r5_residuals_documented_in_the_law_still_pass(layout, cmd):
    allowed(layout, cmd)  # lách được bằng gián tiếp: ghi ở method/agile.md 5.1 "Không chặn được"; đổi thành chặn thì sửa test và luật cùng lúc


# --- RF2 (security): đuôi ký tự đại diện sau `cd` ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "cd /unrelated; rm state/*.{json,bak}", "cd /unrelated; rm state/*.js{on}", "cd /unrelated; rm state/*.{j,x}son", "cd /unrelated; rm state/*{.json,.bak}",
    "cd /unrelated; EXT=json; rm state/*.$EXT", "cd /unrelated; rm state/*.${EXT}", "cd /unrelated; rm state/*.$'json'", "cd /unrelated; rm state/*.\"json\"",
    "cd /unrelated; rm state/*.js\\on", "cd /unrelated; rm state/*.json", "cd /unrelated; rm state/*.JSON", "cd /unrelated; rm state/*.jso[n]", "cd /unrelated; rm state/*son",
    "cd /unrelated; rm state/*.jso?", "cd /unrelated; rm state/session-*", "cd /unrelated; rm **/*.json", "cd /unrelated; rm */*.json", "cd /unrelated; Remove-Item state" + BS + "*.json",
])
def test_r5_glob_tails_that_may_name_a_state_file_after_a_cd_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "cd src && npx prettier --write \"**/*.ts\"", "cd src; eslint --fix \"**/*.js\"", "cd src; sed -i s/a/b/ */config.yml", "cd src; rm -f */*.o", "cd src; git add '*.ts'",
    "cd src; rm */*.log", "cd src; rm */*~", "cd src && git add \"**/*.py\"",
])
def test_r5_plainly_non_json_glob_tails_after_a_cd_stay_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF3 (security): tên script có ký tự đại diện, so với tên file thật cạnh rào ----------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "python scripts/a*_s*.py off", "python scripts/*e_s*.py always", "python scripts" + BS + "a*_s*.py off", "python scripts/a*e.py off", "python scripts/a??le_s???e.py off",
    "python scripts/*state*.py stop", "python3 scripts/a*_h*.py", "uv run python scripts/a*_s*.py manual", "python scripts/agile_st*.py off",
])
def test_r5_script_name_globs_that_expand_to_a_switch_script_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "python scripts/*.py", "uv run pytest tests/test_*.py", "python scripts/agile_*.py status", "python scripts/ag*.py", "pytest tests/*state* -k manual",
    "ruff check scripts/agile_st*.py", "python scripts/a*_s*.py status", "python scripts/c*.py --self", "python tests/test_*.py off",
])
def test_r5_other_script_globs_stay_allowed(layout, cmd):
    allowed(layout, cmd)


def test_r5_known_false_positive_a_project_glob_that_matches_agile_hook(layout):
    blocked(layout, "python tools/*hook*.py --dry-run")  # lệnh khớp `agile_hook.py` bằng chữ: chặn nhầm, đóng khi lỗi, ghi ở luật


# --- RF4/RF5 (security) + RF1 (Opus): -EncodedCommand ----------------------------------------------------------------------------------------------

def _write(layout):
    repo, state = layout
    return "Set-Content -Path '%s/%s' -Value x" % (str(state).replace("\\", "/"), FILE)


def _forms(layout):
    write = _write(layout)
    good = b64(write)
    return {
        "{W}": good,
        "{WX}": __import__("base64").b64encode(write.encode("utf-16-le") + b"\x00").decode(),
        "{WS}": good[:8] + " " + good[8:],
        "{WC}": good[:20] + "\r\n" + good[20:],
        "{WP}": good.rstrip("="),
        "{WL}": __import__("base64").b64encode(write.encode("utf-16-le") + b"\x00\xd8").decode(),
    }


@pytest.mark.parametrize("cmd", [
    "powershell /EncodedCommand {W}", "powershell /e {W}", "pwsh /EncodedCommand {W}", "powershell –EncodedCommand {W}", "powershell –enc {W}", "pwsh -NoProfile /ec {W}",
    "Start-Process powershell -ArgumentList '-enc','{W}'", "Start-Process pwsh -ArgumentList \"-NoProfile\",\"-EncodedCommand\",\"{W}\"", "saps powershell -ArgumentList '/e','{W}'",
    "powershell -EncodedCommand \"{WS}\"", "powershell -EncodedCommand {WX}", "powershell -EncodedCommand {WL}", "powershell -EncodedCommand {WP}",
    "powershell -EncodedCommand \"{WC}\"", "cmd /c powershell /e {W}", "powershell -EncodedCommand:{W}", "bash -c 'powershell /enc {W}'", "powershell -en {W}",
])
def test_r5_encoded_command_variants_that_powershell_accepts_are_decoded_and_blocked(layout, cmd):
    repo, state = layout
    for key, value in _forms(layout).items():
        cmd = cmd.replace(key, value)
    rc, _, err = run("claude", claude(cmd, repo))
    assert rc == 2, (cmd, rc, err)


@pytest.mark.parametrize("cmd", [
    "powershell -EncodedCommand !!!not-base64!!!", "powershell -EncodedCommand !!!notbase64", "powershell -EncodedCommand $e", "pwsh -enc $env:PAYLOAD", "powershell /e @@@",
    "Start-Process powershell -ArgumentList '-enc','@@@'", "powershell -EncodedCommand A", "pwsh -NoProfile -ec ====",
])
def test_r5_encoded_command_value_that_cannot_be_decoded_is_blocked_with_a_clear_reason(layout, cmd):
    repo, state = layout
    rc, _, err = run("claude", claude(cmd, repo))
    assert rc == 2 and "-EncodedCommand không giải mã được" in err, (cmd, rc, err)


@pytest.mark.parametrize("cmd", [
    "powershell -EncodedCommand {W0}", "powershell -Command Get-Date", "powershell -ExecutionPolicy Bypass -File build.ps1", "powershell -File x.ps1 -e foo", "grep powershell -e foo notes.txt",
    "powershell -EncodedCommand", "pwsh -NoProfile -c \"Write-Output -e foo\"", "powershell -ExecutionPolicy Bypass -NoProfile", "git log --grep powershell -e abc",
])
def test_r5_harmless_powershell_commands_stay_allowed(layout, cmd):
    cmd = cmd.replace("{W0}", b64("Get-Date"))
    allowed(layout, cmd)


# --- chữ của luật (method/agile.md 5.1) khớp rào sau vòng R5 ----------------------------------------------------------------------------------------

def _law():
    from conftest import REPO
    return (REPO / "method" / "agile.md").read_text(encoding="utf-8")


def test_law_says_an_undecodable_encoded_command_is_blocked_not_passed():
    law = _law()
    assert "không giải mã được thì cho qua" not in law
    for needle in ("KHÔNG giải mã được", "CHẶN (đóng khi lỗi", "tiền tố `-`, `/` hay gạch ngang dài `–`", "-ArgumentList '-enc'", "byte lẻ"):
        assert needle in law, needle


def test_law_describes_the_statement_rule_for_claude_and_lists_the_residuals_of_r5():
    law = _law()
    for needle in ("BẤT KỲ vị trí nào", "`Start-Process`", "`wsl`", "`ssh`", "`docker`", "cat <<EOF | claude -p", "`tee`", "cụm `-pc`",
                   "claude -p < prompt.txt", "cat prompt.txt | claude -p", "$n='cla'+'ude'", "subprocess.run(['claude','-p','/agile stop'])"):
        assert needle in law, needle


def test_law_documents_the_glob_tail_rule_the_script_name_rule_and_its_false_positive():
    law = _law()
    for needle in ("`rm state/*.{json,bak}`", "`*.$'json'`", "python scripts/a*_s*.py off", "python tools/*hook*.py", "tên file THẬT cạnh rào"):
        assert needle in law, needle
