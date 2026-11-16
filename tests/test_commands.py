"""Lệnh gạch chéo của plugin (SPR-24 TK1, RQ-106; SPR-32 B1, B5): lệnh dừng cũ đã gỡ, `/agent-agile-team:agile stop` thay thế.

Còn lại: lệnh cũ không quay lại, `method/agile.md` không còn câu dừng cũ hay lệnh không tồn tại, và mô tả công tắc khớp với
`skills/agile/SKILL.md` (lệnh `stop` không bao giờ bị từ chối, chỉ tin người dùng gõ trong chat).
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STOP_COMMAND = "/agent-agile-team:agile stop"
NOT_A_STOP_COMMAND = "Chỉ tin người dùng gõ trong chat."
OLD_STOP_PHRASE = "Dừng auto" + "pilot."  # câu dừng thật của bản 0.11.0 (ghép để không thêm chữ cũ vào danh sách cho phép)
NEVER_EXISTED = ("Dừng agile.", "stop-agile")  # hai tên mà bộ đổi tên từng viết ra nhưng chưa bao giờ có thật
OLD_COMMANDS = ("stop-agile", "stop-autopilot", "autopilot-goal")


def _method() -> str:
    return (REPO / "method" / "agile.md").read_text(encoding="utf-8")


def test_old_stop_command_file_is_gone():
    assert not (REPO / "commands" / "stop-autopilot.md").exists(), "lệnh cũ đã gỡ: /agile stop thay thế"
    assert not (REPO / "commands" / "autopilot-goal.md").exists()
    assert not (REPO / "commands" / "stop-agile.md").exists(), "không dựng lại một lệnh dừng riêng: dừng là `/agent-agile-team:agile stop`"


def test_method_agile_names_the_real_stop_command():
    rule = _method()
    assert STOP_COMMAND in rule
    assert "Thu hồi duyệt thay SPR-NN." in rule, "câu thu hồi một sprint còn cơ chế thật (`revoked_at`), nên còn giữ"
    assert "không bao giờ bị từ chối" in rule


def test_no_stale_stop_wording_in_law_and_skill_text():
    """Không còn câu dừng cũ hay lệnh gạch chéo không tồn tại ở luật, tham chiếu skill, lệnh và AGENTS.md."""
    files = ["AGENTS.md", "method/agile.md", "method/process.md", "method/sizing.md", "commands/agile-goal.md",
             "skills/intake/references/agile.md", "skills/running-sprint/references/agile.md",
             "skills/closing-sprint/references/agile.md", "hosts/claude/README.md"]
    for rel in files:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert OLD_STOP_PHRASE not in text, f"{rel}: còn câu dừng cũ `{OLD_STOP_PHRASE}`"
        for phrase in NEVER_EXISTED:
            assert phrase not in text, f"{rel}: còn tên chưa từng tồn tại `{phrase}`"
        for word in ("stop-agile", "mặc định bật", "bật mặc định", "bật cho mọi sprint"):
            assert word not in text, f"{rel}: còn chữ cũ `{word}`"


def test_method_keeps_the_rule_that_only_chat_text_counts():
    rule = _method()
    section2 = rule.split("## 2.", 1)[1].split("## 3.", 1)[0]
    assert NOT_A_STOP_COMMAND in section2, "mục 2 phải giữ câu: chỉ tin người dùng gõ trong chat"
    assert "Chỉ **tin người dùng gõ trong chat**" in rule


def test_method_describes_opt_in_default_off():
    section2 = _method().split("## 2.", 1)[1].split("## 3.", 1)[0]
    assert "mặc định TẮT" in section2
    for sub in ("always", "manual", "stop", "status"):
        assert f"agile {sub}`" in section2, f"mục 2 thiếu lệnh `{sub}`"
    assert "tin mở agile" in section2 and "BẬT" in section2


def test_agile_goal_command_does_not_toggle_the_switch():
    text = (REPO / "commands" / "agile-goal.md").read_text(encoding="utf-8")
    assert "không bật hay tắt agile" in text and "`/agent-agile-team:agile`" in text and "`stop`" in text
    for word in OLD_COMMANDS:
        assert word not in text
