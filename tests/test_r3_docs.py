"""SPR-32 TK6h: chữ trong tài liệu khớp thực tế sau vòng review R3 (số hook, dòng trạng thái vắng mặt, host Codex/Antigravity, câu hứa sai của README Claude,
số lượt thử của skill agile). Chạy: python -m pytest -q tests/test_r3_docs.py"""

from __future__ import annotations

import json

from conftest import REPO


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def test_hooks_json_has_four_command_entries_and_the_docs_say_four():
    config = json.loads(read("hooks/hooks.json"))
    entries = [hook for group in config["hooks"].values() for entry in group for hook in entry["hooks"] if hook.get("type") == "command"]
    assert len(entries) == 4
    law = read("method/agile.md")
    assert "Năm hook" not in law and "cả năm hook" not in law and "Bốn hook" in law and "cả bốn hook" in law
    assert "năm hook (thêm" not in read("CHANGELOG.md")


def test_agents_md_says_a_missing_state_line_means_agile_is_inactive():
    line = read("AGENTS.md").split("\n")[7].lower()
    assert "agile: on|off" in line and "không có dòng" in line and "hook không chạy" in line and "model không được tự bật" in line


def test_claude_readme_does_not_claim_the_model_cannot_turn_agile_on():
    text = read("hosts/claude/README.md")
    assert "Model không tự bật được" not in text
    assert "non-hook ON" in text and "tự khai" in text


def test_codex_and_antigravity_regression_is_stated_in_law_hosts_and_changelog():
    for rel in ("method/agile.md", "hosts/codex/README.md", "hosts/antigravity/README.md", "CHANGELOG.md"):
        text = read(rel)
        assert "không bật được bằng lệnh chat" in text and "agile_state.py always --project" in text, rel
    assert "chỉ được bảo đảm như chỉ dẫn của skill" not in read("method/agile.md")
    assert "Hồi quy ở Codex và Antigravity" in read("CHANGELOG.md")


def test_law_lists_the_child_session_residual_and_the_resume_hypothesis():
    law = read("method/agile.md")
    assert "Phiên con có `session_id` riêng" in law and "claude --resume <id>" in law and "Giả thuyết, Chưa chạy" in law


def test_agile_skill_run_counts_are_consistent_in_the_docs():
    for rel in ("skills/README.md", "docs/OVERVIEW.md"):
        text = read(rel)
        assert "0/4 kịch bản" not in text and "chưa chạy (0/4" not in text, rel
        assert "39 trong 39 skill có tệp thử đã chạy" in text and "9/10 lượt GREEN" in text, rel
    assert "runs sonnet, grader opus" in read("skills/agile/tests/pressure.md")
