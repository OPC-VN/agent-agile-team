"""SPR-32 TK6 B5 (SC7.0, SC8.1, SC8.2): `AGENTS.md` được nạp MỌI phiên, nên khi agile TẮT nó chỉ được mang luật lõi.

Kiểm bằng đọc văn bản, không nhập module nào của repo. File này không thuộc sàn cứng; hai vùng sàn của `AGENTS.md`
được ghim băm ở `tests/test_fence_wiring.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
AGENTS = REPO / "AGENTS.md"
START = "<!-- san-cung:start -->"
END = "<!-- san-cung:end -->"
MAX_LINES = 120
MAX_BYTES = 10 * 1024


def _text() -> str:
    return AGENTS.read_text(encoding="utf-8").replace("\r\n", "\n")


def _split(text: str) -> tuple[str, list[str]]:
    """(chữ ngoài vùng sàn, danh sách chữ trong từng vùng sàn)."""
    outside, zones, current, inside = [], [], [], False
    for raw in text.split("\n"):
        line = raw.strip()
        if line == START:
            assert not inside, "vùng sàn lồng nhau"
            inside, current = True, []
        elif line == END:
            assert inside, "mốc đóng không có mốc mở"
            zones.append("\n".join(current))
            inside = False
        elif inside:
            current.append(raw)
        else:
            outside.append(raw)
    assert not inside, "mốc mở không đóng"
    return "\n".join(outside), zones


def test_sc7_0_both_floor_zones_still_present():
    text = _text()
    assert text.count(START) == 2 and text.count(END) == 2, "AGENTS.md phải giữ đúng hai cặp mốc san-cung"
    _, zones = _split(text)
    assert len(zones) == 2
    assert "dừng chỉ khi" in zones[0] and "Làm thẳng" in zones[0], "vùng sàn 1 là thủ tục dừng/cổng/làm thẳng"
    assert "Git và điều cấm" in zones[1], "vùng sàn 2 là Git và điều cấm"


def test_sc7_0_a1_stop_rules_outside_the_zones():
    outside, _ = _split(_text())
    assert re.search(r"^## .*[Dd]ừng.*$", outside, re.M), "thiếu mục luật dừng A1 ngoài vùng sàn"
    a1 = next(s for s in re.split(r"^## ", outside, flags=re.M)[1:] if s.startswith("Luật dừng"))
    lowered = a1.lower()
    for needle in ("secret", "xác thực", "user", "soul", "xoá", "git", "hỏi"):
        assert needle in lowered, f"mục luật dừng thiếu ý `{needle}`"
    assert "tắt" in lowered and "bật" in lowered, "luật dừng phải nói rõ áp cả khi agile bật lẫn tắt"


def test_pointer_to_agile_process_is_present():
    text = _text()
    assert "method/agile.md" in text, "thiếu con trỏ tới method/agile.md"
    assert "/agent-agile-team:agile" in text, "thiếu tên lệnh người dùng gõ để bật"
    outside, _ = _split(text)
    assert "người dùng gõ" in outside or "người dùng đã gõ" in outside, "con trỏ phải nói rõ chỉ khi người dùng gõ lệnh"


def test_sc8_2_budget():
    data = AGENTS.read_bytes()
    lines = len(data.decode("utf-8").splitlines())
    assert lines <= MAX_LINES, f"AGENTS.md {lines} dòng, trần {MAX_LINES}"
    assert len(data) <= MAX_BYTES, f"AGENTS.md {len(data)} byte, trần {MAX_BYTES}"


@pytest.mark.parametrize("needle", ["RQ-", "SPRINT.md", "Gate Delegate", "Cổng 1", "Cổng 2", "gate_1", "tin mở agile",
                                   "Tiếp nhận", "Thực thi", "Kiểm định"])
def test_sc8_1_no_process_procedure_outside_floor_zone_1(needle):
    """Ngoài hai vùng sàn (và mục luật dừng A1), AGENTS.md không mang thủ tục sprint/cổng."""
    outside, _ = _split(_text())
    assert needle not in outside, f"AGENTS.md ngoài vùng sàn còn thủ tục agile: `{needle}`"


def test_no_six_step_narrative_left_in_agents_md():
    assert "## Quy trình sáu bước" not in _text(), "sáu bước đã dời sang method/agile.md"
    assert "## Vai và tier" not in _text(), "chi tiết vai/tier đã dời sang method/agile.md và roles/README.md"


def test_moved_text_exists_in_method_agile():
    agile = (REPO / "method" / "agile.md").read_text(encoding="utf-8")
    assert "Sáu bước" in agile and "Vai và tier" in agile, "method/agile.md phải nhận phần đã dời khỏi AGENTS.md"
    assert "Người làm không tự chấm" in agile
