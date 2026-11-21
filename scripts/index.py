#!/usr/bin/env python3
"""Sinh lại khối "Đang mở" ở đầu ba sổ gốc (REQUESTS · SPECS · SPRINTS).

Cách chạy:
    python scripts/index.py <gốc-dự-án>            # ghi lại khối giữa hai dấu mốc khi nội dung đổi
    python scripts/index.py <gốc-dự-án> --check    # không ghi; thoát 1 nếu có sổ chưa cập nhật

Nguồn (hợp đồng `templates/README.md` mục 6):
- REQUESTS: dòng Timeline có trạng thái `mới` hoặc `đang làm`.
- SPECS: frontmatter spec sống trong `paths.feature_specs_dir` có `status` `proposed` hoặc `in_progress`.
- SPRINTS: frontmatter `PROGRESS.md` (hoặc `SPRINT.md`) của từng thư mục sprint, `status` khác `done`/`dropped`.
Sắp theo mã giảm dần (mới nhất ở trên). Cùng đầu vào cho cùng đầu ra, từng byte.

Mã thoát: 0 = xong / đã cập nhật · 1 = `--check` thấy sổ cũ · 2 = lỗi đầu vào (gồm file không phải UTF-8).

Locale (SPR-33): the tool reads the column names and the open-status words of every shipped locale (labels/*.json),
so a registry written in English is read like a Vietnamese one. The block it writes uses the locale of the registry
itself, detected from the registry's own headings, table headers and field labels (never from the config): English
column names, status words, empty sentence and notice for an English registry, the unchanged Vietnamese output for a
Vietnamese one. A registry whose labels are shared or mixed (no single owner locale) is treated as Vietnamese.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402
import _labels as lab  # noqa: E402

START = "<!-- agile:open:start -->"
END = "<!-- agile:open:end -->"
NOTICE = "<!-- Khối này do công cụ `index` ghi lại — đừng sửa tay. -->"
NOTICES = {"vi": NOTICE, "en": "<!-- This block is rewritten by the `index` tool — do not edit by hand. -->"}
# Words are label keys (labels/<locale>.json); the text comes from the registry's locale. Frontmatter value -> status key.
OPEN_REQUEST = ("status.new", "status.in_progress")
FEATURE_LABEL = {"proposed": "status.proposed", "in_progress": "status.in_progress"}
SPRINT_LABEL = {"drafting": "status.drafting", "awaiting_gate_1": "status.awaiting_gate_1", "in_progress": "status.in_progress",
                "verifying": "status.verifying", "blocked": "status.blocked", "awaiting_gate_2": "status.awaiting_gate_2"}
COLUMNS = {"requests": ("column.code", "column.date", "column.summary", "column.status", "column.sprint"),
           "specs": ("column.code", "column.feature", "column.status", "column.living_spec"),
           "sprints": ("column.code", "column.opened", "heading.goal", "column.status", "column.round", "column.folder")}


class InputError(Exception):
    pass


_EOL = re.compile(r"\r+\n|\r")


def _plain(text: str) -> str:
    """Mọi cuối dòng (LF, CRLF, CR-CR-LF) về LF, không nhân đôi dòng."""
    return _EOL.sub("\n", text)


def _read(path: Path) -> str:
    """Đọc UTF-8 để phân tích: bỏ BOM, cuối dòng về LF."""
    return _plain(Path(path).read_bytes().decode("utf-8").lstrip(chr(0xFEFF)))


def _words(key: str) -> tuple:
    """Every label of a key in every shipped locale, exactly as written (index matches cells byte for byte)."""
    return tuple(dict.fromkeys(alt for loc in lab.shipped() for alt in lab.alternates(key, loc)))


def cell(row: dict, key: str) -> str:
    """The cell of the column that carries the label key, whatever locale its header is written in ("" when absent)."""
    for header, value in row.items():
        if header in _words(key):
            return value
    return ""


def registry_locale(text: str) -> str:
    """Locale of a registry, from its own labels outside the machine-written block; no single owner locale -> vi."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == START]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        lines = lines[:starts[0]] + lines[ends[0] + 1:]
    found = lab.locales_in("\n".join(lines))
    return found[0] if len(found) == 1 else lab.DEFAULT_LOCALE


def empty_block(kind: str, locale: str) -> list:
    """The sentence a ledger shows when nothing is open (`kind` is requests, specs or sprints)."""
    return [lab.label(f"phrase.empty_{kind}", locale)]


def _header(kind: str, locale: str) -> list:
    return [lab.label(key, locale) for key in COLUMNS[kind]]


def table_under(text: str, heading_key: str) -> list[dict]:
    """Các dòng dữ liệu của bảng đầu tiên dưới tiêu đề cấp 2 mang nhãn `heading_key` (mọi locale), dạng {cột: ô}."""
    lines = c.mask_markdown(text.split("\n"))
    raw = text.split("\n")
    names = _words(heading_key)
    start = next((i for i, line in enumerate(lines) if line.startswith("## ") and any(n in line for n in names)), None)
    if start is None:
        return []
    header = None
    rows = []
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            break
        cells = c.table_cells(raw[i]) if lines[i].strip() else None
        if cells is None:
            if header is not None and rows:
                break
            continue
        if header is None:
            header = cells
        elif not c.is_separator_row(cells):
            rows.append(dict(zip(header, cells)))
    return rows


def _id_key(record: str) -> int:
    parsed = c.parse_id(record)
    return parsed[1] if parsed else -1


def _frontmatter(path: Path) -> dict:
    try:
        fm = c.parse_frontmatter(_read(path))
    except c.SubsetError as exc:
        raise InputError(f"{c.display(path)}:{exc.line}: {exc.message}") from exc
    return fm.data if fm else {}


def _table(header: list, rows: list) -> list:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows]


def _link(target: Path, ledger: Path, folder: bool = False) -> str:
    rel = Path(os.path.relpath(target.resolve(), ledger.parent.resolve())).as_posix()
    return f"[{target.name}]({rel}{'/' if folder else ''})"


def requests_block(ledger: Path) -> list:
    text = _read(ledger)
    loc = registry_locale(text)
    open_words = {w for key in OPEN_REQUEST for w in _words(key)}
    rows = [r for r in table_under(text, "heading.timeline") if cell(r, "column.status") in open_words and c.parse_id(cell(r, "column.code"))]
    rows.sort(key=lambda r: _id_key(cell(r, "column.code")), reverse=True)
    keys = COLUMNS["requests"]
    return _table(_header("requests", loc), [[cell(r, k) for k in keys] for r in rows]) if rows else empty_block("requests", loc)


def specs_block(ledger: Path, feature_dir: Path) -> list:
    text = _read(ledger)
    loc = registry_locale(text)
    names = {cell(r, "column.code"): cell(r, "column.feature") for r in table_under(text, "heading.catalog")}
    rows = []
    for path in sorted(feature_dir.glob("*.md")) if feature_dir.is_dir() else []:
        if path.resolve() == ledger.resolve():
            continue
        data = _frontmatter(path)
        if data.get("doc") != "feature" or data.get("status") not in FEATURE_LABEL:
            continue
        fid = str(data.get("id"))
        rows.append([fid, names.get(fid) or str(data.get("title", "")), lab.label(FEATURE_LABEL[data["status"]], loc), _link(path, ledger)])
    rows.sort(key=lambda r: _id_key(r[0]), reverse=True)
    return _table(_header("specs", loc), rows) if rows else empty_block("specs", loc)


def sprints_block(ledger: Path, base: Path, pattern: str) -> list:
    text = _read(ledger)
    loc = registry_locale(text)
    timeline = {cell(r, "column.code"): r for r in table_under(text, "heading.timeline")}
    rows = []
    for folder in sorted(p for p in base.glob(pattern.replace("{date}", "*").replace("{slug}", "*")) if p.is_dir()):
        state = next((folder / n for n in ("PROGRESS.md", "SPRINT.md") if (folder / n).is_file()), None)
        if state is None:
            continue
        data = _frontmatter(state)
        sid = data.get("sprint")
        if data.get("status") not in SPRINT_LABEL or not c.parse_id(sid):
            continue
        row = timeline.get(sid, {})
        rows.append([sid, cell(row, "column.opened") or str(data.get("created", "")), cell(row, "heading.goal") or str(data.get("title", "")),
                     lab.label(SPRINT_LABEL[data["status"]], loc), str(data.get("review_round", 0)), _link(folder, ledger, folder=True)])
    rows.sort(key=lambda r: _id_key(r[0]), reverse=True)
    return _table(_header("sprints", loc), rows) if rows else empty_block("sprints", loc)


def rewrite(raw: str, block: list, path: Path, locale: str = lab.DEFAULT_LOCALE) -> str:
    """Thay khối giữa hai dấu mốc trên văn bản THÔ: dòng ngoài khối giữ nguyên từng byte; dòng trong khối
    dùng đúng đuôi cuối dòng của dòng dấu mốc đầu (LF, CRLF hay CR-CR-LF)."""
    lines = raw.split("\n")  # mỗi đoạn có thể còn đuôi CR
    starts = [i for i, line in enumerate(lines) if line.strip() == START]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise InputError(f"{c.display(path)}: cần đúng một cặp dấu mốc {START} … {END}")
    marker = lines[starts[0]]
    tail = "\r" * (len(marker) - len(marker.rstrip("\r")))
    inner = [line + tail for line in [NOTICES.get(locale, NOTICE)] + block]
    return "\n".join(lines[:starts[0] + 1] + inner + lines[ends[0]:])


def build(root: Path) -> list:
    """Trả [(đường dẫn sổ, nội dung cũ, nội dung mới, kiểu file gốc)]."""
    try:
        cfg = c.load_config(root)
        problems = c.config_problems(cfg)
        if problems:
            raise c.ConfigError(f"{c.display(root / c.CONFIG_NAME)}: " + "; ".join(problems))
        paths = cfg["paths"]
        ledgers = {key: c.safe_path(root, cfg, paths[key]) for key in ("requests", "specs", "sprints")}
    except c.ConfigError as exc:
        raise InputError(str(exc)) from exc
    for key, path in ledgers.items():
        if not path.is_file():
            raise InputError(f"{c.display(path)}: không có sổ {key.upper()} (chạy init.py --apply)")
    blocks = {
        "requests": requests_block(ledgers["requests"]),
        "specs": specs_block(ledgers["specs"], c.artifact_path(root, cfg, paths["feature_specs_dir"])),
        "sprints": sprints_block(ledgers["sprints"], c.artifact_path(root, cfg, ""), paths["sprint_dir"]),
    }
    out = []
    for key, path in ledgers.items():
        old = path.read_bytes().decode("utf-8")  # thô: giữ BOM và cuối dòng
        out.append((path, old, rewrite(old, blocks[key], path, registry_locale(_plain(old).lstrip(chr(0xFEFF))))))
    return out


def main(argv=None) -> int:
    c.utf8_stdio()
    parser = argparse.ArgumentParser(prog="index.py", description="Sinh lại khối 'Đang mở' của ba sổ gốc.")
    parser.add_argument("root", help="gốc dự án (chứa .agile.json)")
    parser.add_argument("--check", action="store_true", help="không ghi; thoát 1 nếu có sổ chưa cập nhật")
    args = parser.parse_args(argv)
    try:
        results = build(Path(args.root))
    except UnicodeDecodeError as exc:
        print(f"lỗi đầu vào: có sổ hoặc spec sống không đọc được dạng UTF-8 ({exc.reason}) — lưu lại file bằng UTF-8")
        return 2
    except InputError as exc:
        print(f"lỗi đầu vào: {exc}")
        return 2
    stale = False
    for path, old, new in results:
        if _plain(old) == _plain(new):  # so nội dung, không so cuối dòng
            print(f"= không đổi {c.display(path)}")
            continue
        stale = True
        if args.check:
            print(f"! chưa cập nhật {c.display(path)}")
        else:
            path.write_bytes(new.encode("utf-8"))  # giữ BOM và cuối dòng của file gốc
            print(f"~ đã ghi {c.display(path)}")
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
