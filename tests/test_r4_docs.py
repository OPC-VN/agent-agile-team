"""SPR-32 TK6i: chữ trong tài liệu khớp rào sau vòng review R4 (số dòng/byte của AGENTS.md trong CHANGELOG, lớp chặn nhầm của ký tự đại diện sau `cd`,
tồn dư chấp nhận, tác dụng phụ của lối dự phòng `always`). Chạy: python -m pytest -q tests/test_r4_docs.py"""

from __future__ import annotations

import re

from conftest import REPO


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


def test_changelog_agents_md_size_matches_the_file():
    changelog = read("CHANGELOG.md")
    releases = re.split(r"(?m)^## ", changelog)
    latest = releases[1]
    historical = next((section for section in releases[1:] if section.startswith("0.12.0 ")), "")
    assert "`AGENTS.md` rút gọn (97 → 89 dòng, 10238 → 8805 byte)" in historical
    match = re.search(r"\*\*Số đo:\*\* `AGENTS\.md` (\d+) dòng, \d+ → (\d+) byte", latest)
    assert match, "CHANGELOG thiếu dòng số đo AGENTS.md trong mục phát hành mới nhất"
    raw = (REPO / "AGENTS.md").read_bytes()
    lines = raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)
    # CRLF trong bản chép làm việc dài hơn bản trong git: đếm byte trên nội dung đã đổi về LF
    assert (int(match.group(1)), int(match.group(2))) == (lines, len(raw.replace(b"\r\n", b"\n")))


def test_changelog_warns_that_cd_to_home_and_post_cd_globs_are_refused_while_agile_is_on():
    text = read("CHANGELOG.md")
    assert "`cd ~`" in text and "thư mục nhà" in text and "sau một `cd` trong cùng lệnh" in text and "git -C" in text


def test_law_documents_the_post_cd_glob_false_positive_class_and_the_workaround():
    law = read("method/agile.md")
    for needle in ("chặn nhầm đã biết sau một `cd` trong cùng lệnh", "git restore --staged", "tar -czf ../out.tgz *", "prettier --write", "`cd ~`", "`cd $HOME`",
                   "chạy `cd` thành một lệnh riêng", "`git -C`"):
        assert needle in law, needle


def test_law_lists_the_accepted_residuals_of_r4_with_the_exact_example_commands():
    law = read("method/agile.md")
    for needle in ("[Environment]::CurrentDirectory", "SetCurrentDirectory", "start /d", "Start-Process cmd -WorkingDirectory", "pwsh -WorkingDirectory",
                   "mklink /J", "New-Item -ItemType Junction", "ln -s", "subst X:"):
        assert needle in law, needle


def test_law_describes_the_per_command_claude_rule_and_the_encoded_command_decode():
    law = read("method/agile.md")
    assert "câu lệnh có token chương trình `claude`" in law and "xét từng câu lệnh" in law and "hosts/claude" in law  # TK6k: chữ của luật viết lại
    assert "-EncodedCommand" in law and "UTF-16LE" in law and "agile_st*.py" in law
    assert "claude -p `/agile`" not in law and "trong văn bản lệnh bị chặn (phiên con" not in law


def test_fallback_always_side_effect_for_claude_sessions_is_stated():
    """FR3.1/SC9: always bật agile nhưng không tự bật rào secure."""
    law = read("method/agile.md")
    assert "cùng repo thấy agile BẬT" in law
    assert "nhưng secure không tự bật" in law
    assert "cùng repo cũng thấy rào BẬT" not in law
