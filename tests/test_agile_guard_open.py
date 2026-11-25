"""SPR-20 TK22 (nay SPR-32 B3): `agile_guard.py` với MỘT chế độ agile: công tắc BẬT chặn bảy mục luôn-chặn; khoá `mode`/`exclusions` kiểu cũ trong
file trạng thái bị bỏ qua; trạng thái hỏng chặn cả 13 mục. Kích hoạt đọc từ trạng thái agile (`agile_state`), không còn file dấu `.tmp/autopilot.json`.

Phần kiểm lệnh git (đẩy, tag, gộp, rào git thường trực, `_keep_ask`) đã gỡ ở SPR-20 TK21; phần hai chế độ gỡ ở TK22.
"""

from __future__ import annotations

import pytest

import _agile_rules as rules
import agile_guard
import agile_state as st
from test_agile_guard import ALL, SID, assert_blocked, assert_tamper_blocked, claude, good_marker, make_repo, run, write_switch

ALWAYS = set(rules.OPEN_ALWAYS_BLOCKED)

pytestmark = pytest.mark.usefixtures("agile_state_dir")


def payload_for(repo):
    return claude("ls", repo)


def write_repo_state(repo, **extra):
    data = {"schema": 1, "always": True, "always_source": "hook"}
    data.update(extra)
    st.write_json_atomic(st.repo_file(repo), data)


def test_agile_on_active_set_is_the_seven_always_blocked_items(tmp_path):
    repo = make_repo(tmp_path, marker=good_marker())
    active, broken, dirs = agile_guard.activation(payload_for(repo))
    assert not broken and active == ALWAYS and len(active) == 7 and dirs


@pytest.mark.parametrize("legacy", [
    {"mode": "open"}, {"mode": "secure"}, {"mode": "wide"}, {"exclusions": ["tag", "publish"]}, {"exclusions": "all"},
    {"exclusions": []}, {"mode": "open", "exclusions": ["not_an_item"]},
], ids=["mode-open", "mode-secure", "mode-unknown", "extra-items", "bad-shape", "empty", "open-unknown-item"])
def test_legacy_mode_and_exclusions_keys_are_ignored(tmp_path, legacy):
    repo = make_repo(tmp_path)
    write_repo_state(repo, **legacy)
    write_switch(repo, {})
    active, broken, _dirs = agile_guard.activation(payload_for(repo))
    assert not broken and active == ALWAYS


def test_state_without_extra_keys_is_valid(tmp_path):
    repo = make_repo(tmp_path)
    write_repo_state(repo)
    write_switch(repo, {})
    active, broken, _dirs = agile_guard.activation(payload_for(repo))
    assert not broken and active == ALWAYS


def test_agile_on_keeps_blocking_recursive_delete(tmp_path):
    assert_blocked(make_repo(tmp_path, branch="release", marker=good_marker()), "rm -rf build", "irreversible_delete")


def test_state_dir_is_the_protected_target(tmp_path):
    """Thay cho `test_marker_is_still_protected_file`: thứ được bảo vệ nay là thư mục trạng thái agile (SC7.2)."""
    repo = make_repo(tmp_path, branch="release", marker=good_marker())
    assert_tamper_blocked(repo, "rm {S}/{F}")
    rc, _, err = run("claude", claude("rm .tmp/autopilot.json", repo))
    assert rc == 0 and "file dấu cũ" not in err  # file dấu cũ không có mặt và không còn được bảo vệ


@pytest.mark.parametrize("text", ["{not json", "[]", '"x"'], ids=["not-json", "list", "string"])
def test_corrupt_state_blocks_thirteen(tmp_path, text):
    repo = make_repo(tmp_path, marker=text)
    active, broken, _dirs = agile_guard.activation(payload_for(repo))
    assert broken and set(active) == set(ALL)


def test_session_on_is_enough_without_repo_always(tmp_path):
    repo = make_repo(tmp_path)
    write_switch(repo, good_marker(), session_id=SID)
    active, broken, _dirs = agile_guard.activation(dict(payload_for(repo), session_id=SID))
    assert not broken and active == ALWAYS
    assert agile_guard.activation(claude("ls", repo, session_id=None)) is None  # không có session_id: không phải phiên này


def test_repo_always_without_secure_is_dormant(tmp_path):
    repo = make_repo(tmp_path)
    write_repo_state(repo)
    assert agile_guard.activation(payload_for(repo)) is None
