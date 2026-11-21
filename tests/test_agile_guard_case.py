"""Rào agile so đường thư mục trạng thái KHÔNG phân biệt hoa/thường trên mọi nền (lỗi chỉ lộ trên macOS/Linux, CI đỏ từ fc55599).

Lỗi cũ: (1) `_mentions_state` hạ câu lệnh về chữ thường rồi so với thư mục trạng thái còn chữ hoa (`os.path.normcase` chỉ hạ chữ trên Windows):
trên macOS (`/Users/...`) 13 dạng xoá file trạng thái viết trong `python -c`, `node -e`, `perl`… lọt rào; (2) đuôi mẫu `*.JSON` sau `cd` bị coi là
không thể là file trạng thái (so phân biệt hoa/thường), trong khi ổ mặc định của macOS không phân biệt nên `rm state/*.JSON` xoá được `repo-x.json`.

Mô phỏng trên Windows: thay `_state_dirs` bằng bản giống hệt nhưng KHÔNG `normcase` (đúng điều `normcase` làm trên POSIX: không đổi gì), đặt thư mục
trạng thái có chữ hoa. Chạy: python -m pytest -q tests/test_agile_guard_case.py"""

from __future__ import annotations

import os

import pytest

import agile_guard
from test_agile_guard import TAMPER_REASON, claude, good_marker, make_repo, run
from test_agile_guard_r2 import RF1_BLOCKED

pytestmark = pytest.mark.usefixtures("agile_state_dir")

POSIX_DIR = "/Users/Runner/Library/AgileState"  # thư mục trạng thái kiểu macOS (ghi đè bằng AGENT_AGILE_STATE_DIR), có chữ hoa


def _posix_like_state_dirs(st: object) -> tuple[str, ...]:
    """Như `agile_guard._state_dirs` nhưng bỏ `normcase`: trên macOS/Linux `normcase` là phép đồng nhất nên đây đúng là giá trị rào thấy ở đó."""
    found: list[str] = []
    for getter in ("state_dir", "platform_state_dir", "state_dir_override"):
        try:
            path = getattr(st, getter)()
        except Exception:  # noqa: BLE001 — như bản gốc
            continue
        if path is None:
            continue
        for variant in (str(path), os.path.realpath(str(path))):
            norm = os.path.normpath(variant)
            if norm not in found:
                found.append(norm)
    return tuple(found)


@pytest.fixture
def upper_state(tmp_path, monkeypatch):
    """Thư mục trạng thái có chữ hoa và KHÔNG mang dấu `agent-agile-team/state` (để chỉ phép so đường, không phải STATE_SIGNATURE, bắt được)."""
    state = tmp_path / "Users" / "Runner" / "Library" / "AgileState"
    state.mkdir(parents=True)
    monkeypatch.setenv("AGENT_AGILE_STATE_DIR", str(state))
    monkeypatch.setattr(agile_guard, "_state_dirs", _posix_like_state_dirs)
    repo = make_repo(tmp_path / "work", marker=good_marker())
    assert any(ch.isupper() for ch in str(state))
    return repo, state


@pytest.mark.parametrize("cmd", RF1_BLOCKED)
def test_literal_state_path_with_uppercase_inside_code_is_blocked(upper_state, cmd):
    """13 dạng (cộng `x=$(rm …)`) của RF1 với thư mục trạng thái giữ chữ hoa như trên macOS: trước bản sửa lọt rào (rc 0)."""
    repo, state = upper_state
    text = cmd.replace("{SB2}", str(state).replace("\\", "\\\\")).replace("{SB}", str(state))
    text = text.replace("{S}", str(state).replace("\\", "/")).replace("{F}", "session-t1.json")
    rc, _, err = run("claude", claude(text, repo))
    assert rc == 2 and TAMPER_REASON in err, (text, rc, err)


@pytest.mark.parametrize("variant", [str.lower, str.upper, lambda s: s])
def test_mentions_state_ignores_case_on_both_sides(variant):
    """Đơn vị: câu lệnh nhắc thư mục trạng thái ở bất kỳ kiểu chữ nào đều được nhận ra, khi thư mục trạng thái giữ chữ hoa (POSIX)."""
    ctx = agile_guard.Context(set(), os.getcwd(), (POSIX_DIR,), light=True)
    assert agile_guard._mentions_state("python -c \"import os;os.remove('" + variant(POSIX_DIR) + "/repo-x.json')\"", ctx)
    assert not agile_guard._mentions_state("python -c \"import os;os.remove('/Users/Runner/Library/Other/repo-x.json')\"", ctx)


@pytest.mark.parametrize("component", ["*.JSON", "*.Json", "repo-*.JSON", "*.JSO?", "*SON"])
def test_glob_tail_in_upper_case_may_name_a_state_file(component):
    """`rm state/*.JSON` sau `cd`: đuôi `.JSON` khớp `repo-x.json` trên ổ không phân biệt hoa/thường (macOS). Trước bản sửa: False ở mọi nền."""
    assert agile_guard._could_name_state_file(component)


@pytest.mark.parametrize("component", ["*.TS", "*.Log", "CONFIG.YML"])
def test_glob_tail_that_plainly_is_not_json_stays_allowed_in_any_case(component):
    assert not agile_guard._could_name_state_file(component)


@pytest.mark.parametrize("rel", ["state/*.JSON", "STATE/*.json", "State/repo-*.JSON", "state/*"])
def test_relative_glob_after_cd_reaches_state_dir_in_any_case(rel):
    """Đơn vị `_reaches_state` (đường tương đối sau `cd`) với thư mục trạng thái kiểu POSIX: thành phần và đuôi so không phân biệt hoa/thường."""
    ctx = agile_guard.Context(set(), os.getcwd(), ("/Users/Runner/agile/State",), light=True)
    assert agile_guard._reaches_state(rel, ctx, False, False), rel


def test_negated_class_with_uppercase_still_matches():
    """Review PR #18: chỉ hạ chữ cả mẫu thì `[!A-Z]tore` thành `[!a-z]tore` và không còn khớp `store` (bản đầu của PR làm lọt dạng base chặn).
    Shell mở rộng `[!A-Z]tore` thành `store`: phải chặn."""
    linux_dir = "/home/runner/agile/store"
    assert agile_guard._glob_covers("/home/runner/agile/[!A-Z]tore/*.json", linux_dir, False)
    assert agile_guard._glob_covers("/home/runner/agile/[!A-Z]tore", linux_dir, False)
    ctx = agile_guard.Context(set(), os.getcwd(), (linux_dir,), light=True)
    assert agile_guard._reaches_state("[!A-Z]tore/*.json", ctx, False, False)
    assert agile_guard._reaches_state("[!A-Z]tore", ctx, True, False)


def test_negated_class_with_lowercase_on_an_uppercase_state_dir_is_blocked(upper_state):
    """Qua cả rào: `[!a-z]gileState` khớp `AgileState` (chữ `A` không thuộc a-z). Hạ chữ cả mẫu sẽ làm lọt."""
    repo, state = upper_state
    pattern = (str(state.parent) + "/[!a-z]gileState/*.json").replace("\\", "/")
    rc, _, err = run("claude", claude("rm -f " + pattern, repo))
    assert rc == 2 and TAMPER_REASON in err, (pattern, rc, err)


@pytest.mark.parametrize("path, directory", [
    ("/users/runner/agile/STORE/repo-x.json", "/Users/Runner/Agile/Store"),
    ("/Users/Runner/Agile/Store", "/users/runner/agile/store"),
])
def test_under_ignores_case(path, directory):
    """`_under` (đường đã giải, không ký tự đại diện): trên macOS `../agile/STORE/repo-x.json` trúng `.../Agile/Store` (có từ trước PR)."""
    assert agile_guard._under(path.replace("/", os.sep), directory.replace("/", os.sep))
    assert not agile_guard._under("/Users/Runner/Agile/Storex/repo-x.json".replace("/", os.sep), directory.replace("/", os.sep))


@pytest.mark.parametrize("cmd", ["rm ../../Users/Runner/Library/AGILESTATE/session-t1.json", "rm -rf ../../users/runner/library/agilestate",
                                 "mv ../../USERS/runner/LIBRARY/agileState/session-t1.json x.json"])
def test_relative_path_in_other_case_is_blocked(upper_state, cmd):
    """Qua cả rào, đường tương đối khác kiểu chữ tới thư mục trạng thái giữ chữ hoa (mô phỏng macOS): trước bản sửa `_under` lọt."""
    repo, _ = upper_state
    rc, _, err = run("claude", claude(cmd, repo))
    assert rc == 2 and TAMPER_REASON in err, (cmd, rc, err)


def test_glob_covers_state_dir_in_any_case():
    """Đơn vị `_glob_covers`: mẫu tuyệt đối có ký tự đại diện, khác kiểu chữ với thư mục trạng thái (POSIX không `normcase` hạ chữ)."""
    assert agile_guard._glob_covers("/USERS/runner/library/agile*", POSIX_DIR, False)
    assert agile_guard._glob_covers("/users/RUNNER/*", POSIX_DIR, True)
    assert not agile_guard._glob_covers("/users/runner/other*", POSIX_DIR, True)
