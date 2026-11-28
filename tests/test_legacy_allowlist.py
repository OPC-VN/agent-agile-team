"""SPR-32 TK6 B5 (SC6.1, R0-M4): chữ cũ (autopilot, không phân biệt hoa thường) chỉ được nằm trong danh sách cho phép.

Mỗi mục có đường (glob), lý do và số lần xuất hiện tối đa, nên danh sách không phình âm thầm: thêm một lần xuất hiện mới
ở file đã cho phép cũng đỏ khi vượt trần. Đọc văn bản, không nhập module nào của repo.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NEEDLE = "autopilot"
# `.venv`, `venv`: môi trường ảo của máy người chạy, thư viện bên thứ ba (vd pygments) không thuộc repo và có thể chứa chữ này.
# `.worktrees`: worktree git của nhánh khác (thư mục bị ignore), bản sao của chính repo, không phải nội dung nhánh đang kiểm.
SKIP_DIRS = {".git", ".tmp", ".claude", ".worktrees", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".sh", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".mdx", ".html", "",
                 ".ps1", ".js", ".cmd", ".bat", ".mjs", ".ts"}  # TK6e S7: thêm các đuôi script, không để chữ cũ lọt qua file không quét

# (glob theo đường tương đối kiểu POSIX, số lần xuất hiện tối đa, lý do). Muốn thêm mục: nêu lý do ở thông điệp commit.
ALLOWLIST: tuple[tuple[str, int, str], ...] = (
    ("CHANGELOG.md", 61, "lịch sử phát hành: bản ghi cũ không sửa; mục BREAKING của SPR-32 nêu tên cũ"),
    ("docs/architecture/adr/0001-*", 9, "ADR 0001 là bản ghi lịch sử, không sửa"),
    ("scripts/_agile_rules.py", 3, "legacy: tiền tố lời cấp cũ `bật autopilot` mà hồ sơ cũ còn mang (SC6.1, SC10.3)"),
    ("scripts/check.py", 3, "legacy: tên mục cũ `Bản tin autopilot` của hồ sơ cũ (SC6.1, SC10.3)"),
    ("scripts/agile_guard.py", 3, "dòng nhắc file dấu cũ `.tmp/autopilot.json` (rào không đọc nó) và docstring giải thích"),
    ("scripts/agile_state.py", 1, "báo `legacy_markers`: file dấu cũ còn nằm trong dự án (RK11)"),
    ("scripts/README.md", 2, "mô tả hành vi: rào không đọc file dấu cũ; luật `gate-delegation-invalid` nhắc lời cấp cũ"),
    ("method/agile.md", 3, "legacy: câu cấp cũ `Bật autopilot …` và file dấu cũ bị bỏ qua kèm một dòng nhắc (mục 2, 4, 5.2)"),
    ("hosts/claude/README.md", 1, "ghi rõ file dấu cũ không còn"),
    ("templates/README.md", 2, "legacy: tiền tố lời cấp cũ và tên mục cũ của REPORT mà `check` còn đọc"),
    ("templates/sprint/REPORT.md", 1, "legacy: chú thích tên mục cũ `Bản tin autopilot` mà `check` còn đọc"),
    ("skills/*/tests/pressure.md", 165, "lịch sử các lần chạy thử áp lực (hàng cũ không sửa); TK10 owns"),
    ("skills/*/tests/scenarios.txt", 4, "TK6c: phần CHẤM của ca ON và ca đã loại nêu `.tmp/autopilot.json` như thứ KHÔNG được làm"),
    ("tests/fixtures/broken.json", 1, "legacy: ca thử tên mục cũ `Bản tin autopilot`"),
    ("tests/test_check.py", 25, "legacy: chuỗi lời cấp cũ làm dữ liệu thử cho tiền tố cũ"),
    ("tests/test_agile_modes.py", 4, "legacy: chuỗi lời cấp cũ làm dữ liệu thử cho tiền tố cũ"),
    ("tests/test_check_stops.py", 6, "legacy: tên mục cũ `Bản tin autopilot` làm dữ liệu thử (hồ sơ cũ còn đọc được)"),
    ("tests/test_agile_guard.py", 23, "legacy: thử rằng file dấu cũ bị bỏ qua và chỉ in một dòng nhắc"),
    ("tests/test_agile_guard_open.py", 2, "legacy: thử rằng file dấu cũ không còn kích hoạt rào"),
    ("tests/test_agile_hook.py", 2, "legacy: thử `status` báo file dấu cũ"),
    ("tests/test_agile_state.py", 2, "legacy: thử `legacy_markers`"),
    ("tests/test_agile_goal_command.py", 1, "danh sách từ cấm trong lệnh: `autopilot.json` không được in"),
    ("tests/test_commands.py", 4, "tên file của lệnh đã gỡ, thử rằng nó không quay lại"),
    ("tests/test_legacy_allowlist.py", 12, "chính file này mang chữ cần tìm"),
)


def _rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _walk():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield Path(root) / name


def _hits() -> dict[str, int]:
    found: dict[str, int] = {}
    for path in _walk():
        rel = _rel(path)
        if NEEDLE in rel.lower():
            found[rel] = found.get(rel, 0) + 1  # tên file hay thư mục mang chữ cũ cũng tính một lần
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        count = text.lower().count(NEEDLE)
        if count:
            found[rel] = found.get(rel, 0) + count
    return found


def _allowed(rel: str) -> tuple[str, int, str] | None:
    for entry in ALLOWLIST:
        if fnmatch.fnmatchcase(rel, entry[0]):
            return entry
    return None


def test_legacy_word_only_in_allowlist():
    stray, over = [], []
    budget: dict[str, int] = {}
    for rel, count in sorted(_hits().items()):
        entry = _allowed(rel)
        if entry is None:
            stray.append(f"{rel} ({count})")
        else:
            budget[entry[0]] = budget.get(entry[0], 0) + count
    for pattern, used in budget.items():
        limit = next(e[1] for e in ALLOWLIST if e[0] == pattern)
        if used > limit:
            over.append(f"{pattern}: {used} > {limit}")
    assert not stray, "legacy-allowlist: chữ cũ ngoài danh sách cho phép: " + "; ".join(stray)
    assert not over, "legacy-allowlist: vượt trần số lần xuất hiện: " + "; ".join(over)


def test_allowlist_entries_have_reasons_and_are_not_stale():
    for pattern, limit, reason in ALLOWLIST:
        assert reason.strip() and limit >= 0, f"mục {pattern} thiếu lý do"
    assert len({e[0] for e in ALLOWLIST}) == len(ALLOWLIST), "mục trùng đường"
    live = _hits()
    for pattern, limit, _ in ALLOWLIST:
        if limit == 0:
            continue
        used = sum(c for rel, c in live.items() if fnmatch.fnmatchcase(rel, pattern))
        assert used >= 1, f"mục {pattern} không còn khớp chữ nào: bỏ khỏi danh sách"


def test_allowlist_is_tight():
    """Trần không được rộng hơn số thật quá một khoảng nhỏ: tránh để chỗ trống cho chữ cũ lẻn vào."""
    live = _hits()
    for pattern, limit, _ in ALLOWLIST:
        if limit == 0:
            continue
        used = sum(c for rel, c in live.items() if fnmatch.fnmatchcase(rel, pattern))
        assert limit - used <= 2, f"{pattern}: trần {limit}, thật {used}: hạ trần xuống sát"
