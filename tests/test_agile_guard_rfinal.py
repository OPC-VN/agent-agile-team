"""SPR-32 TK6l: sửa vòng review R-final của rào agile (agile_guard.py). Hai lỗ cùng lớp với Phải sửa R5, một lỗ nhỏ và một lỗ khác:
(1) gạch ngang U+2015 (thanh ngang) làm lọt `-EncodedCommand`: PowerShell 5.1 nhận đúng bốn dấu gạch làm tiền tố tham số (`-`, U+2013, U+2014, U+2015; đã thử:
U+2010-2012, U+2212, U+FE58, U+FE63, U+FF0D KHÔNG được nhận), nên `powershell ―enc <b64>` chạy mà rào không giải mã;
(2) `Start-Process powershell -ArgumentList '-enc <b64>'` (MỘT chuỗi, cũng `"-enc <b64>"` và `'-NoProfile -EncodedCommand <b64>'`): chỉ dạng phẩy bị chặn; luật `claude` đã tách chuỗi một khối;
(3) `"/agile stop" | Tee-Object x | claude -p`: `Tee-Object` là tên đầy đủ của alias `tee`; (4) `claude -p $'/agile stop'` (nháy ANSI-C của bash).
Chạy: python -m pytest -q tests/test_agile_guard_rfinal.py"""

from __future__ import annotations

import pytest

from test_agile_guard import claude, run
from test_agile_guard_r4 import allowed, blocked, layout  # noqa: F401  (layout: fixture)
from test_agile_guard_r5 import _forms

pytestmark = pytest.mark.usefixtures("agile_state_dir")


def _encoded_blocked(layout, cmd):
    repo, state = layout
    for key, value in _forms(layout).items():
        cmd = cmd.replace(key, value)
    rc, _, err = run("claude", claude(cmd, repo))
    assert rc == 2, (cmd, rc, err)


@pytest.mark.parametrize("cmd", [
    "powershell ―enc {W}", "pwsh ―e {W}", "powershell ―EncodedCommand {W}", "pwsh -NoProfile ―ec {W}", "powershell ――enc {W}",
    "powershell ―EncodedCommand:{W}", "Start-Process powershell -ArgumentList '―enc','{W}'", "cmd /c powershell ―e {W}",
    "powershell –enc {W}", "powershell —enc {W}",  # đối chứng: hai dấu đã chặn từ R5
])
def test_rfinal_every_dash_that_powershell_accepts_as_a_prefix_is_decoded_and_blocked(layout, cmd):
    _encoded_blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "Start-Process powershell -ArgumentList '-enc {W}'", "Start-Process powershell -ArgumentList \"-enc {W}\"",
    "Start-Process powershell -ArgumentList '-NoProfile -EncodedCommand {W}'", "Start-Process pwsh -ArgumentList '-NoProfile -ExecutionPolicy Bypass -e {W}'",
    "saps powershell -ArgumentList '/enc {W}'", "Start-Process -FilePath powershell -ArgumentList '―enc {W}'", "Start-Process powershell -ArgumentList '-enc:{W}'",
    "Start-Process powershell -ArgumentList '-enc','{W}'", "Start-Process powershell -ArgumentList '-NoProfile','-EncodedCommand','{W}'",  # đối chứng: dạng phẩy
])
def test_rfinal_a_single_string_argument_list_is_split_before_the_flag_is_looked_for(layout, cmd):
    _encoded_blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "Start-Process powershell -ArgumentList '-NoProfile -Command Get-Date'", "Start-Process powershell -ArgumentList '-File x.ps1 -e foo'",
    "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File build.ps1'", "Start-Process notepad -ArgumentList '-enc abc'",
    "Start-Process powershell -ArgumentList '-enc'", "powershell ―Command Get-Date", "powershell ―File x.ps1 ―e foo",
    "powershell ‐enc abc", "powershell −enc abc",  # U+2010 và U+2212 PowerShell không nhận làm tiền tố: không phải cờ
])
def test_rfinal_harmless_forms_with_the_same_shapes_stay_allowed(layout, cmd):
    allowed(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "\"/agile stop\" | Tee-Object x | claude -p", "\"/agile stop\" | tee-object x | claude -p", "echo \"/agile stop\" | Tee-Object -FilePath x.txt | claude -p",
    "'/agile stop' | TEE-OBJECT x | claude --print", "Write-Output '/agile stop' | Tee-Object x | Tee-Object y | claude -p",
])
def test_rfinal_tee_object_passes_the_prompt_on_like_tee(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "claude -p $'/agile stop'", "claude -p $'/agent-agile-team:agile stop'", "claude --print $'/agile off'", "claude -p $\"/agile stop\"", "claude --resume s1 $'/agile stop'",
    "echo $'/agile stop' | claude -p", "Start-Process claude -ArgumentList $'-p',$'/agile stop'",
])
def test_rfinal_bash_dollar_quotes_in_front_of_the_prompt_are_unwrapped(layout, cmd):
    blocked(layout, cmd)


@pytest.mark.parametrize("cmd", [
    "Get-Content x | Tee-Object y", "Tee-Object -FilePath log.txt -InputObject hi", "echo hi | Tee-Object x | claude -p \"summarize\"",
    "echo \"/agile stop\" | Tee-Object x", "claude -p $'summarize the diff'", "claude -p $'explain how /agile works'", "echo $'/agile stop' > notes.txt",
    "git commit -m $'docs: mention /agile stop'", "grep -rn $'/agile' docs",
])
def test_rfinal_benign_forms_next_to_the_fixed_ones_stay_allowed(layout, cmd):
    allowed(layout, cmd)
