"""SPR-32 TK6i: sửa vòng review R4 của rào agile (agile_guard.py): luật `claude -p` xét từng câu lệnh và chỉ khi câu đó CHẠY `claude` (MF1; không chặn nhầm
`grep -r "/agile" hosts/claude`, `git log --grep`, thông điệp commit), `claude-code`/`npx @anthropic-ai/claude-code` (RF4), `powershell -EncodedCommand` được giải mã
rồi xét lại (RF2), tên script có ký tự đại diện `agile_st*.py` (RF3), vùng chặn nhầm của ký tự đại diện sau `cd` thu hẹp lại (SF1) và bố cục thật (repo dưới thư mục nhà).
Chạy: python -m pytest -q tests/test_agile_guard_r4.py"""

from __future__ import annotations

import base64
import os
import re

import pytest

from test_agile_guard import BS, TAMPER_REASON, assert_allowed, claude, good_marker, make_repo, run

pytestmark = pytest.mark.usefixtures("agile_state_dir")
FILE = "session-t1.json"


@pytest.fixture
def layout(tmp_path, monkeypatch):
    """Như `test_agile_guard_r3.layout`: thư mục trạng thái `<tmp>/<thư mục nhà>/.claude/plugins/data/agent-agile-team/state`, repo ở cây khác."""
    state = tmp_path / "home" / ".claude" / "plugins" / "data" / "agent-agile-team" / "state"
    state.mkdir(parents=True)
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(state))
    repo = make_repo(tmp_path / "work", marker=good_marker())
    return repo, state


@pytest.fixture
def home_layout(tmp_path, monkeypatch):
    """Bố cục thật (SF1): nhà `<tmp>/home`, thư mục trạng thái `<nhà>/AppData/Local/agent-agile-team/state`, repo `<nhà>/proj/repo`: nhà là TỔ TIÊN của thư mục trạng thái."""
    home = tmp_path / "home"
    state = home / "AppData" / "Local" / "agent-agile-team" / "state"
    state.mkdir(parents=True)
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(state))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    repo = make_repo(home / "proj", marker=good_marker())
    return repo, state


def fmt(cmd, repo, state):
    slash = lambda path: str(path).replace("\\", "/")  # noqa: E731
    return cmd.replace("{S}", slash(state)).replace("{P}", slash(state.parent)).replace("{F}", FILE).replace("{PB}", str(state.parent).replace("/", BS))


def b64(text):
    return base64.b64encode(text.encode("utf-16-le")).decode()


def E(text):
    """Dấu hiệu `⟦…⟧`: văn bản được mã hoá base64 (UTF-16LE) SAU khi `{S}`/`{F}` đã được thay (xong từ trong ra ngoài, nên lồng được)."""
    return "⟦" + text + "⟧"


def encode_markers(text):
    pattern = re.compile("⟦([^⟦⟧]*)⟧")
    while pattern.search(text):
        text = pattern.sub(lambda m: b64(m.group(1)), text, count=1)
    return text


def blocked(layout, cmd):
    repo, state = layout
    text = encode_markers(fmt(cmd, repo, state))
    rc, _, err = run("claude", claude(text, repo))
    assert rc == 2 and TAMPER_REASON in err, (text, rc, err)


def allowed(layout, cmd):
    repo, state = layout
    assert_allowed(repo, encode_markers(fmt(cmd, repo, state)))


# --- MF1: luật `claude -p` theo từng câu lệnh, chỉ khi câu đó chạy `claude` -----------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "claude -p \"/agent-agile-team:agile stop\"", "claude --resume abc123 \"/agile stop\"", "claude --resume abc123 -p \"/agile stop\"", "claude -p '/agile stop' --resume abc123",
    "echo \"/agent-agile-team:agile stop\" | claude -p", "printf '/agile stop' | claude -p", "claude.cmd -p \"/agile stop\"", "bash -c 'claude -p \"/agile stop\"'",
    "FOO=1 claude -p /agile", "timeout 60 claude -p \"/agent-agile-team:agile\"", "echo $(claude -p \"/agile stop\")", "ls && claude -p \"/agile off\"",
    "/usr/local/bin/claude -p \"/agile stop\"", "claude --print \"/agent-agile-team:agile always\"", "claude --continue -p \"/agile off\"",
])
def test_mf1_a_segment_that_runs_claude_with_an_agile_prompt_is_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "grep -r \"/agile\" hosts/claude", "git log -p --grep=\"/agile\" -- hosts/claude", "grep -rn \"/agile\" skills | grep -c claude",
    "grep -r \"/agile\" . | claude -p \"summarize\"", "claude -p \"explain how /agile works\"", "git commit -m \"claude -p /agile\"",
    "echo \"use claude -p then /agile\"", "grep -rn \"claude -p /agile\" docs/", "git commit -m \"docs: claude -p example for /agile\"",
    "ls hosts/claude/README.md", "cat hosts/claude/README.md | grep -c /agile", "git diff -- hosts/claude", "rg -n \"/agile\" hosts/claude -p",
    "claude -p \"summarize the sprint report\"", "claude --version", "claude --resume abc123", "echo \"/agile stop\" > notes.txt", "grep -r '/agile' docs",
    "cd hosts/claude && grep -r /agile .", "sed -n 1,5p hosts/claude/README.md",
])
def test_mf1_mentions_and_path_fragments_without_a_claude_command_stay_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF4: `claude-code`, `npx @anthropic-ai/claude-code`, `node …/claude-code/cli.js` ------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "npx @anthropic-ai/claude-code -p \"/agent-agile-team:agile stop\"", "npx -y @anthropic-ai/claude-code --resume abc \"/agile off\"", "claude-code -p \"/agile stop\"",
    "node /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js -p \"/agile stop\"", "pnpm dlx @anthropic-ai/claude-code@latest -p \"/agile stop\"",
    "bunx @anthropic-ai/claude-code -p /agile", "npm exec -- claude -p \"/agile stop\"", "timeout 60 npx @anthropic-ai/claude-code -p \"/agent-agile-team:agile\"",
    "bash -c 'npx @anthropic-ai/claude-code -p \"/agile stop\"'",
])
def test_rf4_claude_code_package_forms_with_an_agile_prompt_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "npx @anthropic-ai/claude-code -p \"summarize the diff\"", "npx @anthropic-ai/claude-code --version", "npm install -g @anthropic-ai/claude-code",
    "npm view @anthropic-ai/claude-code version", "node scripts/build.js hosts/claude", "node tools/cli.js -p \"/agile\"",
])
def test_rf4_other_claude_code_commands_stay_allowed(layout, cmd):
    allowed(layout, cmd)


# --- RF2: powershell -EncodedCommand ---------------------------------------------------------------------------------------------------------------

ENC_WRITE = "Set-Content -Path '{S}/{F}' -Value x"


@pytest.mark.parametrize("cmd", [
    "powershell -EncodedCommand " + E(ENC_WRITE), "pwsh -enc " + E(ENC_WRITE), "powershell.exe -NoProfile -e " + E(ENC_WRITE),
    "pwsh -NoProfile -EncodedCommand " + E(ENC_WRITE), "cmd /c powershell -EncodedCommand " + E(ENC_WRITE), "powershell -ec " + E(ENC_WRITE),
    "powershell -EncodedCommand " + E("python -c \"open(r'{S}/{F}','w')\""), "powershell -EncodedCommand " + E("claude -p \"/agile stop\""),
    "powershell -EncodedCommand " + E("python scripts/agile_state.py off"), "powershell -enc " + E("powershell -enc " + E(ENC_WRITE)),
    "bash -c 'powershell -EncodedCommand " + E(ENC_WRITE) + "'",
])
def test_rf2_encoded_command_is_decoded_and_analysed(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "powershell -EncodedCommand " + E("Get-Date"), "pwsh -enc " + E("Write-Output hi"), "powershell -NoProfile -e " + E("Get-ChildItem ."),
    "powershell -EncodedCommand AAAA", "powershell -EncodedCommand", "pwsh -enc " + E("Get-Content notes.txt"),
    "powershell -Command Get-Date", "powershell -ExecutionPolicy Bypass -File build.ps1",
])
def test_rf2_harmless_encoded_commands_stay_allowed(layout, cmd):  # TK6k: `!!!not-base64!!!` (không giải mã được) nay bị chặn, xem test_agile_guard_r5.py
    allowed(layout, cmd)


def test_rf2_undecodable_text_with_the_state_path_in_the_raw_command_is_blocked(layout):
    blocked(layout, "powershell -EncodedCommand @@@ {S}/{F}")


def test_rf2_decoding_is_capped_in_depth(layout):
    text = ENC_WRITE
    for _ in range(6):
        text = "powershell -enc " + E(text)
    repo, state = layout
    rc, _, err = run("claude", claude(encode_markers(fmt(text, repo, state)), repo))
    assert rc == 2, err


# --- RF3: tên script có ký tự đại diện --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "python scripts/agile_st*.py off", "python scripts/agile_sta?e.py off", "python3 scripts/agile_st[a]te.py stop", "python ./agile_*.py always",
    "python scripts/agile_ho*.py", "py -3 scripts/agile_stat*.py manual", "uv run python scripts/agile_st*.py on", "python scripts/agile_state.p* off",
    "python '{S}/../../agile_st*.py' off",
])
def test_rf3_script_names_with_wildcards_that_match_the_switch_scripts_are_blocked(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "python scripts/*.py", "python scripts/check.py --self", "python scripts/agile_st*.py status", "uv run pytest tests/*.py", "python -m pytest tests/test_*.py",
    "poetry run ruff check src/*.py", "python scripts/agile_state.py status", "python scripts/test_*.py off", "python scripts/floor_ch*.py off",
])
def test_rf3_other_wildcards_and_status_stay_allowed(layout, cmd):
    allowed(layout, cmd)


# --- SF1: ký tự đại diện sau `cd`: thu hẹp (đuôi khác .json không thể là file trạng thái), phần còn lại vẫn chặn ----------------------------------

@pytest.mark.parametrize("cmd", [
    "cd src && npx prettier --write \"**/*.ts\"", "cd src; eslint --fix \"**/*.js\"", "cd src; sed -i s/a/b/ */config.yml", "cd src; rm -f */*.o", "cd src && git add \"**/*.py\"",
    "cd src; sed -i s/a/b/ */*.md", "cd src && npx prettier --write \"**/*.tsx\"", "cd src; cp -r a/*.txt b/",
])
def test_sf1_wildcards_with_a_non_json_extension_after_a_cd_are_allowed(layout, cmd):
    allowed(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "cd src; git restore --staged \"**/*\"", "cd src; tar -czf ../out.tgz *", "cd src && npx prettier --write \"**/*.json\"", "cd src; rm state/*.json",
    "cd /unrelated; rm state/sess*", "cd src; mv * ../backup/", "cd src; rm */*", "cd src; sed -i s/a/b/ */*.j*", "cd src; rm */*n", "cd src; sed -i s/a/b/ st*/session-t1.json",
])
def test_sf1_wildcards_that_could_name_a_state_file_after_a_cd_are_still_blocked(layout, cmd):
    blocked(layout, cmd)


# --- SF1: bố cục thật, repo dưới thư mục nhà (nhà là tổ tiên của thư mục trạng thái) ---------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["cd ../..", "cd ~", "cd $HOME", "cd ../../AppData/Local", "cd ../.. && ls", "cd \"$HOME\"; ls", "pushd ../..", "Set-Location ~"])
def test_sf1_cd_to_home_or_an_ancestor_is_refused_in_the_real_layout(home_layout, cmd):
    blocked(home_layout, cmd)


@pytest.mark.parametrize("cmd", [
    "cd .. && ls", "cd src; ls", "cd .. && git status", "cd ../other && rm build.log", "cd src && npx prettier --write \"**/*.ts\"", "git -C ../.. status",
    "ls ~", "ls ../..", "git -C \"$HOME\" status",
])
def test_sf1_the_workarounds_and_non_ancestor_cd_are_allowed_in_the_real_layout(home_layout, cmd):
    allowed(home_layout, cmd)


@pytest.mark.parametrize("cmd", ["cd src; rm state/*", "cd src; mv state x", "cd src; git restore --staged \"**/*\"", "cd src; tar -czf ../out.tgz *"])
def test_sf1_post_cd_relative_state_forms_are_refused_in_the_real_layout(home_layout, cmd):
    blocked(home_layout, cmd)


def test_the_real_layout_state_dir_is_under_the_home(home_layout):
    repo, state = home_layout
    assert os.path.normcase(str(state)).startswith(os.path.normcase(str(repo.parent.parent)))
