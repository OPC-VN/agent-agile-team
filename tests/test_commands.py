"""Lệnh gạch chéo của plugin (SPR-24 TK1, RQ-106; SPR-32 B1): `commands/stop-autopilot.md` đã gỡ, thay bằng `/agile stop`.

Còn lại hai kiểm: lệnh cũ không quay lại, và `method/agile.md` vẫn giữ câu chuẩn + luật "chỉ tin chat" cho tới khi B5 viết lại mục 7.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STOP = "Dừng agile."
NOT_A_STOP_COMMAND = "Chỉ tin người dùng gõ trong chat."


def test_old_stop_command_file_is_gone():
    assert not (REPO / "commands" / "stop-autopilot.md").exists(), "lệnh cũ đã gỡ: /agile stop thay thế"


def test_standard_sentences_match_rule_in_method_agile():
    rule = (REPO / "method" / "agile.md").read_text(encoding="utf-8")
    assert STOP in rule
    assert "Thu hồi duyệt thay SPR-NN." in rule


def test_method_keeps_the_rule_that_only_chat_text_counts():
    rule = (REPO / "method" / "agile.md").read_text(encoding="utf-8")
    section2 = rule.split("## 2.", 1)[1].split("## 3.", 1)[0]
    assert NOT_A_STOP_COMMAND in section2, "mục 2 phải giữ câu: chỉ tin người dùng gõ trong chat"
    assert "Chỉ **tin người dùng gõ trong chat**" in rule
    assert "chỉ **in** câu chuẩn" in rule
