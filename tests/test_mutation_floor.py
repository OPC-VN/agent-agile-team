"""Test đột biến của rào (SPR-16 FR3): gỡ rào bằng tám cách trên **bản sao** trong thư mục tạm, bộ test ghim phải đỏ
đúng test được chỉ định; bản sao chưa đột biến phải xanh; đột biến nào sống thì suite này đỏ và nêu mã đột biến.

File này thuộc sàn cứng (`FLOOR_FILES`). Một cơ chế chỉ được gọi là "rào máy" khi đột biến tương ứng ở đây đã đỏ (FR3.3).
Không chạm cây làm việc: mỗi đột biến sửa bản sao, chạy pytest trong tiến trình con ở thư mục bản sao.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pytest

REPO = Path(__file__).resolve().parent.parent
PINNED_SUITES = ("tests/test_fence_wiring.py", "tests/test_floor_check.py",
                 "tests/test_agile_guard.py", "tests/test_agile_guard_undo.py", "tests/test_check.py",
                 "tests/test_agile_guard_secure.py")
KEYWORDS = "fence or floor or marker or agile or delegation or push"
IGNORE = shutil.ignore_patterns(".git", ".tmp", ".claude", "__pycache__", ".pytest_cache", "*.pyc", ".env", ".env.*")
WIRING = "tests/test_fence_wiring.py"
UNDO = "tests/test_agile_guard_undo.py"
GUARDT = "tests/test_agile_guard.py"


@dataclass
class Mutation:
    apply: Callable[[Path], None]
    must_fail: str  # id (hoặc tiền tố id) của test ghim phải ở trạng thái FAILED
    suites: Optional[tuple] = None  # file test mutant chạy; None = bộ ghim đầy đủ (chỉ các file đang tồn tại)
    needs: Optional[str] = None  # file phải tồn tại ở bản gốc, không thì đột biến skip có lý do


def edit(root: Path, rel: str, old: str, new: str, count: int = 1) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, f"đột biến không áp được: không thấy {old!r} trong {rel}"
    path.write_bytes(text.replace(old, new, count).encode("utf-8"))


CALL_LINE = "problem = rules.agile_problem(block)"


def line_indent(root: Path, rel: str, needle: str) -> str:
    for line in (root / rel).read_text(encoding="utf-8").split("\n"):
        if needle in line:
            return line[:len(line) - len(line.lstrip())]
    raise AssertionError(f"không thấy {needle!r} trong {rel}")


def drop_call(root: Path) -> None:
    edit(root, "scripts/check.py", CALL_LINE, "problem = None")


def drop_result(root: Path) -> None:
    edit(root, "scripts/check.py", CALL_LINE, "rules.agile_problem(block)")


def early_return(root: Path) -> None:
    indent = line_indent(root, "scripts/check.py", CALL_LINE)
    edit(root, "scripts/check.py", indent + CALL_LINE, f"{indent}return\n{indent}{CALL_LINE}")


def shadow_def(root: Path) -> None:
    path = root / "scripts" / "_agile_rules.py"
    path.write_bytes((path.read_text(encoding="utf-8") + "\n\ndef agile_problem(block):\n    return None\n").encode("utf-8"))


def move_marker(root: Path) -> None:
    path = root / "method" / "process.md"
    lines = path.read_text(encoding="utf-8").split("\n")
    end = next(i for i, line in enumerate(lines) if line.strip() == "<!-- san-cung:end -->")
    lines[end], lines[end + 1] = lines[end + 1], lines[end]
    path.write_bytes("\n".join(lines).encode("utf-8"))


def remove_fence_file(root: Path) -> None:
    (root / "scripts" / "agile_guard.py").unlink()


def guard_imports_check(root: Path) -> None:
    edit(root, "scripts/agile_guard.py", "from _agile_rules import AGILE_EXCLUSIONS",
         "from check import AGILE_EXCLUSIONS")


def drop_always_blocked(root: Path) -> None:
    """Bỏ `irreversible_delete` khỏi tập bảy mục luôn chặn: guard không còn chặn xoá khi file dấu hợp lệ (thay đột biến cũ trỏ danh sách 13 mục, nay chỉ dùng khi file dấu hỏng)."""
    edit(root, "scripts/_agile_rules.py", '"network_fetch", "rules_unlisted", "irreversible_delete", "secret"', '"network_fetch", "rules_unlisted", "secret"')


GUARD = "scripts/agile_guard.py"


def stash_all_open(root: Path) -> None:
    """SPR-32 B4: bỏ luật chặn `git stash -a|-u` (luật khôi phục ở B3, trước đó chỉ có test, chưa có đột biến)."""
    edit(root, GUARD, 'if "--all" in rest or "--include-untracked" in rest or any(_cluster(a, "au") for a in rest):', "if False:")


def clean_force_open(root: Path) -> None:
    """SPR-32 B4: bỏ luật chặn `git clean -f` / `-fx` (khôi phục ở B3)."""
    edit(root, GUARD, 'return "irreversible_delete" if forced and not dry_run else None', "return None")


def state_switch_script_open(root: Path) -> None:
    """SPR-32 B3: bỏ luật chặn `agile_state.py on|off|stop|always|manual` (thay đột biến `stash-all-open` của bảo vệ file dấu đã gỡ)."""
    edit(root, GUARD, 'if kind and (kind == "hook" or any(a.lower() in SWITCH_COMMANDS for a in tokens[position + 1:])):', "if False:")


def state_path_open(root: Path) -> None:
    """SPR-32 B3: đường vào thư mục trạng thái không còn được nhận ra (thay `clean-x-open`)."""
    edit(root, GUARD, "    return any(_under(c, d) or (ancestor and c != os.path.dirname(c) and _under(d, c)) for c in candidates for d in ctx.state_dirs)",
         "    return False")


def state_problem_open(root: Path) -> None:
    """SPR-32 B3: trạng thái hỏng không còn giữ rào bật (thay `ignore-check-inverted`): đóng-khi-lỗi (SC4.3) bị gỡ."""
    edit(root, GUARD, 'if any(s["state_problem"] or s["guard_must_stay_active"] for s in states):', "if False:")


def env_redirect_open(root: Path) -> None:
    """SPR-32 B3: bỏ luật chặn đặt/export `AGENT_AGILE_STATE_DIR`/`CLAUDE_PROJECT_DIR` (R1b-M1b)."""
    edit(root, GUARD, "return any(ENV_REDIRECT.search(segment) and not _env_read_only(segment) for segment in RAW_SEPARATORS.split(text))", "return False")


def secure_on_ignored(root: Path) -> None:
    edit(root, GUARD, 'if any(s["secure_on"] for s in states) and not any(s["state_problem"] for s in states):', "if False:")


def flag_includes_agile(root: Path) -> None:
    edit(root, "scripts/agile_state.py", '"guard_must_stay_active": bool(secure_on or problems),', '"guard_must_stay_active": bool(effective or problems),')


def stop_keeps_secure(root: Path) -> None:
    edit(root, "scripts/agile_state.py", 'changes = dict(meta, agile=False, mode="auto", secure=False)', 'changes = dict(meta, agile=False, mode="auto")')


def hook_ignores_secure_off(root: Path) -> None:
    edit(root, "scripts/agile_hook.py", "    if key not in ARG_TO_COMMAND:\n        return None\n", "    if key not in ARG_TO_COMMAND or key in ('secure off', 'secure stop'):\n        return None\n")


def hook_stop_refused(root: Path) -> None:
    """SPR-32 TK6e S6: hook từ chối (thoát 2) lệnh `/agile stop`; lối dừng duy nhất của người dùng không được bị chặn."""
    edit(root, "scripts/agile_hook.py", "        out = run(payload)\n",
         "        out = run(payload)\n        if str(payload.get('command_args')).strip().lower() == 'stop':\n            return 2\n")


def hook_stop_ignored(root: Path) -> None:
    """SPR-32 TK6e S6: `/agile stop` thành lệnh không làm gì (trạng thái không đổi)."""
    edit(root, "scripts/agile_hook.py", "    if key not in ARG_TO_COMMAND:\n        return None\n",
         "    if key not in ARG_TO_COMMAND or key == 'stop':\n        return None\n")


def raw_state_scan_open(root: Path) -> None:
    """SPR-32 TK6e RF1: bỏ luật tìm đường thư mục trạng thái trong văn bản lệnh (mã `python -c`, heredoc, PowerShell .NET)."""
    edit(root, GUARD, "if _raw_tamper(text) or _raw_state_tamper(text, context):", "if _raw_tamper(text):")


def glob_state_open(root: Path) -> None:
    """SPR-32 TK6e RF2: ký tự đại diện ở phần thư mục không còn khớp thư mục trạng thái."""
    edit(root, GUARD, "        if any(_glob_covers(probe, d, ancestor) for d in ctx.state_dirs):", "        if False:")


def deadline_ignored(root: Path) -> None:
    """SPR-32 TK6e RF3: hạn nội bộ không bao giờ quá hạn (lệnh dài chạy quá hạn hook thì không còn rào)."""
    edit(root, GUARD, "if _deadline is not None and time.monotonic() >= _deadline:", "if False:")


def git_dir_delete_open(root: Path) -> None:
    edit(root, GUARD, "if any(_is_git_path(t) for t in targets + [v for _, v in _ps_split(tokens).other]):", "if False:")


def tmp_move_ignored(root: Path) -> None:
    edit(root, GUARD, "        ctx.tmp_moved = True", "        pass")


def pipeline_delete_open(root: Path) -> None:
    edit(root, GUARD, 'item = "irreversible_delete"  # `Get-ChildItem', 'item = None  # `Get-ChildItem')


def reflog_expire_open(root: Path) -> None:
    edit(root, GUARD, 'return "irreversible_delete" if rest[:1] in (["expire"], ["delete"]) else None', "return None")


def push_force_open(root: Path) -> None:
    edit(root, GUARD, 'or a.startswith("--force") or _cluster(a, "fd")', 'or _cluster(a, "fd")')


def branch_big_d_open(root: Path) -> None:
    edit(root, GUARD, 'any(_cluster(a, "D") for a in rest) or (deleting and forced)', "(deleting and forced)")


def session_cap_formula_off(root: Path) -> None:
    edit(root, "scripts/check.py", "cap > formula and not", "cap > 10 ** 9 and not")


def colon_dest_open(root: Path) -> None:
    edit(root, GUARD, 'bucket = parts.dst if canon == "destination" else parts.new', 'bucket = parts.other if canon == "destination" else parts.new')


def named_param_colon_open(root: Path) -> None:
    edit(root, GUARD, 'found = None if token.startswith("--") else _COLON_FLAG.fullmatch(token)', "found = None")


def rename_newname_open(root: Path) -> None:
    edit(root, GUARD, '(parts.new if parts.kind == "rename" else [])', "[]")


def gc_any_expiry_open(root: Path) -> None:
    edit(root, GUARD, 'any(re.fullmatch(r"gc\..*expire\w*", key) for key in config)', 'any(re.fullmatch(r"gc\..*expire\w*", key) and value in ("now", "all", "0") for key, value in config.items())')


def cwd_in_git_open(root: Path) -> None:
    edit(root, GUARD, "self.in_git = False if light else _is_git_path(self.cwd)", "self.in_git = False")


def cd_ancestor_open(root: Path) -> None:
    edit(root, GUARD, "ancestor = name in DELETE_COMMANDS or name in MOVE_COMMANDS or name in CD_COMMANDS", "ancestor = name in DELETE_COMMANDS or name in MOVE_COMMANDS")


def relative_reach_open(root: Path) -> None:
    edit(root, GUARD, "return not os.path.isabs(norm) and _reaches_state(norm, ctx, ancestor, unresolved)", "return False")


def substitution_scan_open(root: Path) -> None:
    edit(root, GUARD, "for inner in _substitutions(joined):", "for inner in []:")


def heredoc_pipe_interpreter_open(root: Path) -> None:
    edit(root, GUARD, "(interpreters and _pipes_into_interpreter(", "(interpreters and False and _pipes_into_interpreter(")


def claude_spawn_open(root: Path) -> None:
    edit(root, GUARD, "if _claude_agile(text):  # TK6k", "if False and _claude_agile(text):  # TK6k")


def claude_anywhere(root: Path) -> None:
    """TK6i MF1 (retargeted TK6k): luật `claude -p` lại nhận mọi đường chứa chữ `claude` làm chương trình và xét cả vế mở đầu bằng `grep`: `grep -r "/agile" hosts/claude` bị chặn nhầm."""
    edit(root, GUARD, "if not bare or not _claude_program(bare):", "if not bare or 'claude' not in bare.lower():")
    edit(root, GUARD, 'return "/" not in norm or norm.startswith(', "return True or norm.startswith(")
    edit(root, GUARD, "    return (name in READ_ONLY_COMMANDS and name not in (\"find\", \"awk\")) or name == \"git\"", "    return False")


def encoded_command_open(root: Path) -> None:
    edit(root, GUARD, "    item = _encoded_text_item(text, ctx, depth)\n", "    item = None\n")


def script_glob_open(root: Path) -> None:
    edit(root, GUARD, "    if max(len(run) for run in re.split(", "    if False and max(len(run) for run in re.split(")


def glob_tail_open(root: Path) -> None:
    """TK6k RF2: đuôi ký tự đại diện có `{ } $ ' "` hay gạch ngược lại bị coi là không thể là file trạng thái: `rm state/*.{json,bak}` sau `cd` lọt."""
    edit(root, GUARD, "    if any(ch in tail for ch in ", "    if False and any(ch in tail for ch in ")


def claude_pipe_body_open(root: Path) -> None:
    """TK6k RF1/RF2: prompt chỉ được tìm trong đối số của chính vế `claude`, không trong thân heredoc/here-string hay vế `echo`/chuỗi trần đứng trước trong ống."""
    edit(root, GUARD, "if body_prompt or carried or any(AGILE_PROMPT.search(piece) for piece in args):", "if any(AGILE_PROMPT.search(piece) for piece in args):")


def claude_spawner_open(root: Path) -> None:
    """TK6k RF1: token `claude` chỉ được nhận ở vị trí lệnh (không sau `start`, `Start-Process`, `wsl`, `ssh`, `docker`, `npm exec --`)."""
    edit(root, GUARD, "if _claude_token(token, at == 0) or (at == 0 and", "if (at == 0 and _claude_token(token, True)) or (at == 0 and")


def encoded_undecodable_open(root: Path) -> None:
    """TK6k RF1: giá trị `-EncodedCommand` không giải mã được lại cho qua (đóng khi lỗi bị bỏ)."""
    edit(root, GUARD, "        return True, UNDECODABLE", "        return False, None")


def encoded_prefix_dash_only(root: Path) -> None:
    """TK6k RF4: cờ `-EncodedCommand` chỉ nhận tiền tố `-` (không `/` hay gạch ngang dài `–`)."""
    edit(root, GUARD, r'ENCODED_FLAG = re.compile(r"[-/\u2013\u2014\u2015]{1,2}', r'ENCODED_FLAG = re.compile(r"[-]{1,2}')


def encoded_dash_bar_open(root: Path) -> None:
    """TK6l (R-final): gạch ngang U+2015 (thanh ngang) không còn là tiền tố cờ: `powershell ―enc <b64>` lọt."""
    edit(root, GUARD, r'ENCODED_FLAG = re.compile(r"[-/\u2013\u2014\u2015]{1,2}', r'ENCODED_FLAG = re.compile(r"[-/\u2013\u2014]{1,2}')


def encoded_single_string_open(root: Path) -> None:
    """TK6l (R-final): `-ArgumentList '-enc <b64>'` (MỘT chuỗi) không còn được tách ở khoảng trắng trước khi tìm cờ."""
    edit(root, GUARD, "    pieces = _flag_words(_pieces(args))\n", "    pieces = _pieces(args)\n")


def tee_object_open(root: Path) -> None:
    """TK6l (R-final): `Tee-Object` (tên đầy đủ của alias `tee`) không còn chuyển tiếp prompt trong ống: `"/agile stop" | Tee-Object x | claude -p` lọt."""
    edit(root, GUARD, 'PASSTHROUGH_COMMANDS = frozenset({"tee", "tee-object", "cat", "type"})', 'PASSTHROUGH_COMMANDS = frozenset({"tee", "cat", "type"})')


def dollar_quote_open(root: Path) -> None:
    """TK6l (R-final): nháy ANSI-C `$'/agile stop'` không còn được bỏ `$` ở bộ tách token: `claude -p $'/agile stop'` lọt."""
    edit(root, GUARD, '            if buf and buf[-1] == "$":', '            if False and buf and buf[-1] == "$":')


def script_sibling_open(root: Path) -> None:
    """TK6k RF3: tên script có ký tự đại diện không còn được khớp với tên file thật cạnh rào (`python scripts/a*_s*.py off` lọt)."""
    edit(root, GUARD, "    return _first_sibling_switch(base)", "    return None")


def read_only_writers_open(root: Path) -> None:
    edit(root, GUARD, "return not _writes_file(name, args)", "return True")


def deadline_env_trusted(root: Path) -> None:
    edit(root, GUARD, "return min(limit, DEADLINE_SECONDS) if math.isfinite(limit) and limit > 0 else DEADLINE_SECONDS", "return limit")


def gc_config_open(root: Path) -> None:
    edit(root, GUARD, 'if sub in ("gc", "prune", "reflog", "maintenance") and any(', "if False and any(")


# SPR-20 TK21: sáu đột biến tinh (hợp đồng đích, nhánh được bảo vệ, alias, nhánh đẩy) nhắm mô-đun rào git thường trực và suite của nó;
# hai file đó đã gỡ nên sáu đột biến bỏ theo, còn tám đột biến của dòng nối/vùng sàn/danh sách mục. Đây là gỡ cơ chế, không phải sửa test cho qua kiểm.
MUTATIONS = {
    "drop-call": Mutation(drop_call, f"{WIRING}::test_check_calls_rules_validator", (WIRING,)),
    "drop-result": Mutation(drop_result, f"{WIRING}::test_check_uses_validator_result", (WIRING,)),
    "early-return": Mutation(early_return, f"{WIRING}::test_validator_call_reachable", (WIRING,)),
    "shadow-def": Mutation(shadow_def, f"{WIRING}::test_no_shadowed_definitions", (WIRING,)),
    "move-marker": Mutation(move_marker, f"{WIRING}::test_floor_zone_hashes", (WIRING,)),
    "remove-fence-file": Mutation(remove_fence_file, f"{WIRING}::test_fence_files_exist", (WIRING,)),
    "guard-imports-check": Mutation(guard_imports_check, f"{WIRING}::test_guard_does_not_import_check", (WIRING,)),
    "drop-always-blocked": Mutation(drop_always_blocked, f"{WIRING}::test_fence_wiring_pins_7_plus_6", (WIRING,)),
    # SPR-20 TK27b: mười đột biến phủ rào mới của guard và trần phiên (mỗi cái trúng đúng một test ghim; hằng chết `drop-exclusion` cũ được thay bằng `drop-always-blocked`).
    "state-switch-script-open": Mutation(state_switch_script_open, f"{GUARDT}::test_switching_agile_state_script_blocked", (GUARDT,)),
    "state-path-open": Mutation(state_path_open, f"{GUARDT}::test_guard_state_protection_resolves_from_command_dir_and_other_trees_allowed", (GUARDT,)),
    "state-problem-open": Mutation(state_problem_open, f"{GUARDT}::test_corrupt_state_fails_guarded", (GUARDT,)),
    "env-redirect-open": Mutation(env_redirect_open, f"{GUARDT}::test_redirecting_state_by_environment_blocked", (GUARDT,)),
    # SPR-37: secure kích hoạt rào độc lập với agile và có lối tắt riêng.
    "secure-on-ignored": Mutation(secure_on_ignored, "tests/test_agile_guard_secure.py::test_secure_on_agile_off_is_healthy_seven_items", ("tests/test_agile_guard_secure.py",)),
    "flag-includes-agile": Mutation(flag_includes_agile, "tests/test_agile_guard_secure.py::test_sc1_activation_dormant", ("tests/test_agile_guard_secure.py",)),
    "stop-keeps-secure": Mutation(stop_keeps_secure, "tests/test_agile_state.py::test_secure_stop_and_last_command", ("tests/test_agile_state.py",)),
    "hook-ignores-secure-off": Mutation(hook_ignores_secure_off, "tests/test_agile_hook.py::test_secure_hook_off", ("tests/test_agile_hook.py",)),
    # SPR-32 TK6e: lối dừng của hook và ba rào của vòng R2 (đường trạng thái trong mã, ký tự đại diện, hạn nội bộ).
    "hook-stop-refused": Mutation(hook_stop_refused, "tests/test_agile_hook.py::test_stop_never_refused_even_when_off_or_corrupt", ("tests/test_agile_hook.py",)),
    "hook-stop-ignored": Mutation(hook_stop_ignored, "tests/test_agile_hook.py::test_stop_never_refused_even_when_off_or_corrupt", ("tests/test_agile_hook.py",)),
    "raw-state-scan-open": Mutation(raw_state_scan_open, "tests/test_agile_guard_r2.py::test_rf1_literal_state_path_inside_code_is_blocked", ("tests/test_agile_guard_r2.py",)),
    "glob-state-open": Mutation(glob_state_open, "tests/test_agile_guard_r2.py::test_rf2_wildcard_in_directory_part_blocked", ("tests/test_agile_guard_r2.py",)),
    "deadline-ignored": Mutation(deadline_ignored, "tests/test_agile_guard_r2.py::test_rf3_deadline_blocks_when_exceeded", ("tests/test_agile_guard_r2.py",)),
    "git-dir-delete-open": Mutation(git_dir_delete_open, f"{UNDO}::test_guard_delete_inside_git_always_blocked", (UNDO,)),
    "tmp-move-ignored": Mutation(tmp_move_ignored, f"{UNDO}::test_guard_move_into_tmp_then_delete_blocked", (UNDO,)),
    "pipeline-delete-open": Mutation(pipeline_delete_open, f"{UNDO}::test_guard_other_recursive_delete_forms_blocked", (UNDO,)),
    "reflog-expire-open": Mutation(reflog_expire_open, f"{UNDO}::test_guard_undo_breaking_git_commands_blocked", (UNDO,)),
    "push-force-open": Mutation(push_force_open, f"{UNDO}::test_guard_undo_breaking_git_commands_blocked", (UNDO,)),
    "branch-big-d-open": Mutation(branch_big_d_open, f"{UNDO}::test_guard_undo_breaking_git_commands_blocked", (UNDO,)),
    # SPR-20 TK27d: ba đột biến phủ dạng dính `-Destination:x`, thư mục làm việc trong `.git`, `git -c gc.*=now`.
    "colon-dest-open": Mutation(colon_dest_open, f"{UNDO}::test_guard_colon_attached_powershell_flags_blocked", (UNDO,)),
    # TK27e: ba đột biến phủ bộ phân tích tham số chung (dạng dính `-Tên:giá-trị`, tên mới là `.git`) và hạn hết hạn bất kỳ của `gc`.
    "named-param-colon-open": Mutation(named_param_colon_open, f"{UNDO}::test_guard_ps_parameter_forms_git_blocked", (UNDO,)),
    "rename-newname-open": Mutation(rename_newname_open, f"{UNDO}::test_guard_ps_parameter_forms_git_blocked", (UNDO,)),
    "gc-any-expiry-open": Mutation(gc_any_expiry_open, f"{UNDO}::test_guard_git_config_zero_expiry_blocked", (UNDO,)),
    "cwd-in-git-open": Mutation(cwd_in_git_open, f"{UNDO}::test_guard_delete_or_move_with_cwd_inside_git_blocked", (UNDO,)),
    "gc-config-open": Mutation(gc_config_open, f"{UNDO}::test_guard_git_config_zero_expiry_blocked", (UNDO,)),
    "stash-all-open": Mutation(stash_all_open, "tests/test_agile_guard.py::test_guard_stash_all_and_clean_x_still_blocked", ("tests/test_agile_guard.py",)),
    "clean-force-open": Mutation(clean_force_open, f"{UNDO}::test_guard_stash_clean_blocked_in_both_ignore_states", (UNDO,)),
    "session-cap-formula-off": Mutation(session_cap_formula_off, "tests/test_check.py::test_delegation_session_cap_must_not_exceed_the_formula", ("tests/test_check.py",)),
    # SPR-32 TK6h: bảy đột biến phủ các rào của vòng R3 (cd lên tổ tiên, đường tương đối sau cd, thay thế lệnh, heredoc vào trình thông dịch, `claude -p`, lệnh chỉ-đọc mà ghi, hạn nội bộ).
    "cd-ancestor-open": Mutation(cd_ancestor_open, "tests/test_agile_guard_r3.py::test_rf1_cd_to_the_state_directory_or_an_ancestor_is_blocked", ("tests/test_agile_guard_r3.py",)),
    "relative-reach-open": Mutation(relative_reach_open, "tests/test_agile_guard_r3.py::test_rf1_relative_arguments_after_a_cd_that_could_reach_the_state_directory_are_blocked", ("tests/test_agile_guard_r3.py",)),
    "substitution-scan-open": Mutation(substitution_scan_open, "tests/test_agile_guard_r3.py::test_rf3_state_path_inside_a_substitution_or_a_heredoc_for_an_interpreter_is_blocked", ("tests/test_agile_guard_r3.py",)),
    "heredoc-pipe-interpreter-open": Mutation(heredoc_pipe_interpreter_open, "tests/test_agile_guard_r3.py::test_rf3_state_path_inside_a_substitution_or_a_heredoc_for_an_interpreter_is_blocked", ("tests/test_agile_guard_r3.py",)),
    "claude-spawn-open": Mutation(claude_spawn_open, "tests/test_agile_guard_r3.py::test_rf4_spawning_claude_with_an_agile_command_is_blocked", ("tests/test_agile_guard_r3.py",)),
    "claude-anywhere": Mutation(claude_anywhere, "tests/test_agile_guard_r5.py::test_r5_claude_mentions_and_other_prompts_stay_allowed", ("tests/test_agile_guard_r5.py",)),
    "encoded-command-open": Mutation(encoded_command_open, "tests/test_agile_guard_r4.py::test_rf2_encoded_command_is_decoded_and_analysed", ("tests/test_agile_guard_r4.py",)),
    "script-glob-open": Mutation(script_glob_open, "tests/test_agile_guard_r4.py::test_rf3_script_names_with_wildcards_that_match_the_switch_scripts_are_blocked", ("tests/test_agile_guard_r4.py",)),
    # SPR-32 TK6k: sáu đột biến phủ các rào sửa ở vòng R5 (đuôi ký tự đại diện, prompt qua ống/thân heredoc, `claude` sau `start`/`ssh`, `-EncodedCommand` đóng khi lỗi và tiền tố, tên script theo tên file thật).
    "glob-tail-open": Mutation(glob_tail_open, "tests/test_agile_guard_r5.py::test_r5_glob_tails_that_may_name_a_state_file_after_a_cd_are_blocked", ("tests/test_agile_guard_r5.py",)),
    "claude-pipe-body-open": Mutation(claude_pipe_body_open, "tests/test_agile_guard_r5.py::test_r5_prompt_through_a_pipe_or_a_body_is_blocked", ("tests/test_agile_guard_r5.py",)),
    "claude-spawner-open": Mutation(claude_spawner_open, "tests/test_agile_guard_r5.py::test_r5_claude_spawn_forms_with_an_agile_prompt_are_blocked", ("tests/test_agile_guard_r5.py",)),
    "encoded-undecodable-open": Mutation(encoded_undecodable_open, "tests/test_agile_guard_r5.py::test_r5_encoded_command_value_that_cannot_be_decoded_is_blocked_with_a_clear_reason", ("tests/test_agile_guard_r5.py",)),
    "encoded-prefix-dash-only": Mutation(encoded_prefix_dash_only, "tests/test_agile_guard_r5.py::test_r5_encoded_command_variants_that_powershell_accepts_are_decoded_and_blocked", ("tests/test_agile_guard_r5.py",)),
    "encoded-dash-bar-open": Mutation(encoded_dash_bar_open, "tests/test_agile_guard_rfinal.py::test_rfinal_every_dash_that_powershell_accepts_as_a_prefix_is_decoded_and_blocked", ("tests/test_agile_guard_rfinal.py",)),
    "encoded-single-string-open": Mutation(encoded_single_string_open, "tests/test_agile_guard_rfinal.py::test_rfinal_a_single_string_argument_list_is_split_before_the_flag_is_looked_for", ("tests/test_agile_guard_rfinal.py",)),
    "tee-object-open": Mutation(tee_object_open, "tests/test_agile_guard_rfinal.py::test_rfinal_tee_object_passes_the_prompt_on_like_tee", ("tests/test_agile_guard_rfinal.py",)),
    "dollar-quote-open": Mutation(dollar_quote_open, "tests/test_agile_guard_rfinal.py::test_rfinal_bash_dollar_quotes_in_front_of_the_prompt_are_unwrapped", ("tests/test_agile_guard_rfinal.py",)),
    "script-sibling-open": Mutation(script_sibling_open, "tests/test_agile_guard_r5.py::test_r5_script_name_globs_that_expand_to_a_switch_script_are_blocked", ("tests/test_agile_guard_r5.py",)),
    "read-only-writers-open": Mutation(read_only_writers_open, "tests/test_agile_guard_r3.py::test_rf2_read_only_names_that_write_into_the_state_directory_are_blocked", ("tests/test_agile_guard_r3.py",)),
    "deadline-env-trusted": Mutation(deadline_env_trusted, "tests/test_agile_guard_r3.py::test_rf5_invalid_deadline_env_falls_back_to_the_default", ("tests/test_agile_guard_r3.py",)),
}


def run_pinned_detail(copy_root: Path, suites=None) -> tuple:
    """(id FAILED, id ERROR) khi chạy các file test ghim đang tồn tại trong `copy_root`. Lỗi import/collection là ERROR,
    không bao giờ tính là đã giết đột biến."""
    files = [s for s in (suites or PINNED_SUITES) if (copy_root / s).is_file()]
    assert files, "không có file test ghim nào trong bản sao"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    done = subprocess.run([sys.executable, "-X", "utf8", "-m", "pytest", *files, "-k", KEYWORDS, "-q", "-rfE", "--tb=no",
                           "-p", "no:cacheprovider"], cwd=copy_root, capture_output=True, text=True, encoding="utf-8", env=env)
    failed, errors = [], []
    for line in done.stdout.splitlines():
        match = re.match(r"^(FAILED|ERROR) (.+?)(?: - .*)?$", line)
        if match:
            (failed if match.group(1) == "FAILED" else errors).append(match.group(2))
    return failed, errors


def run_pinned(copy_root: Path, suites=None) -> list:
    """Danh sách id test ở trạng thái FAILED (lỗi nạp/collection được báo riêng ở `run_pinned_detail`)."""
    return run_pinned_detail(copy_root, suites)[0]


def killed(mutation: Mutation, failed: list) -> bool:
    return any(item == mutation.must_fail or item.startswith(mutation.must_fail + "[") for item in failed)


def require_killed(slug: str, mutation: Mutation, failed: list, errors: list) -> None:
    if not killed(mutation, failed):
        raise AssertionError(f"đột biến sống: {slug} — {mutation.must_fail} không FAILED "
                             f"(FAILED: {failed[:6]}; ERROR: {errors[:6]})")


@pytest.fixture(scope="module")
def pristine(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("pristine") / "repo"
    shutil.copytree(REPO, root, ignore=IGNORE, symlinks=True)
    return root


def fresh_copy(pristine: Path, tmp_path: Path) -> Path:
    root = tmp_path / "mutant"
    shutil.copytree(pristine, root)
    return root


def test_pristine_copy_is_green(pristine):
    failed, errors = run_pinned_detail(pristine)
    assert failed == [] and errors == [], f"bản sao chưa đột biến phải xanh: FAILED {failed[:6]} ERROR {errors[:6]}"


@pytest.mark.parametrize("slug", sorted(MUTATIONS))
def test_mutant_is_killed(slug, pristine, tmp_path):
    mutation = MUTATIONS[slug]
    if mutation.needs and not (REPO / mutation.needs).is_file():
        pytest.skip(f"{mutation.needs} không tồn tại")
    root = fresh_copy(pristine, tmp_path)
    mutation.apply(root)
    failed, errors = run_pinned_detail(root, mutation.suites)
    require_killed(slug, mutation, failed, errors)


def test_surviving_mutant_fails_suite(pristine, tmp_path):
    """FR3.2: vô hiệu đúng một detector (thân test ghim thành `pass`) rồi áp đột biến tương ứng → suite nhận ra đột biến
    sống và nêu slug. Chứng minh cơ chế chứ không chứng minh đột biến khác."""
    root = fresh_copy(pristine, tmp_path)
    edit(root, WIRING, "def test_check_calls_rules_validator():\n    delegation_call()\n",
         "def test_check_calls_rules_validator():\n    pass\n")
    mutation = MUTATIONS["drop-call"]
    mutation.apply(root)
    failed, errors = run_pinned_detail(root, mutation.suites)
    assert not killed(mutation, failed), "detector đã vô hiệu mà vẫn thấy FAILED: cơ chế thử không đáng tin"
    with pytest.raises(AssertionError, match="đột biến sống: drop-call"):
        require_killed("drop-call", mutation, failed, errors)


def test_load_error_is_not_a_kill(pristine, tmp_path):
    """Lỗi nạp/collection không được tính là giết: phá cú pháp file test mục tiêu thì kết quả là ERROR, không FAILED đúng test."""
    root = fresh_copy(pristine, tmp_path)
    edit(root, WIRING, '"""Test ghim dòng nối', "def broken(:\n\"\"\"Test ghim dòng nối")
    mutation = MUTATIONS["drop-call"]
    mutation.apply(root)
    failed, errors = run_pinned_detail(root, mutation.suites)
    assert not killed(mutation, failed) and errors, (failed, errors)
    with pytest.raises(AssertionError, match="đột biến sống"):
        require_killed("drop-call", mutation, failed, errors)


def test_pinned_suites_complete():
    missing = [s for s in PINNED_SUITES if not (REPO / s).is_file()]
    assert not missing, f"bộ ghim thiếu suite: {missing}"
