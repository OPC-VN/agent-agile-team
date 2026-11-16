"""Rào máy agile — hook PreToolUse từ chối lệnh shell thuộc danh sách loại (method/agile.md mục 5). Chỉ thư viện chuẩn.

Gọi: python agile_guard.py --format {claude,codex,antigravity}; đọc JSON sự kiện ở stdin.

KÍCH HOẠT (SPR-32 B3, thay file dấu `.tmp/autopilot.json`): rào BẬT khi (a) công tắc agile hiệu lực — `always` của repo (khoá repo suy từ
`cwd` của sự kiện / `CLAUDE_PROJECT_DIR`, đúng như `agile_state`) hoặc phiên của `session_id` trong sự kiện đang BẬT; (b) lớp trạng thái
báo `guard_must_stay_active` (trạng thái hỏng/không đọc được: đóng khi lỗi, chặn cả 13 mục); (c) sự kiện có `agent_id` (tác tử con) mà
không có file phiên nào khớp: coi là đang bảo vệ, không bao giờ ngủ; (d) không nạp được `agile_state`: đóng khi lỗi. Ngoài bốn trường hợp
đó (agile TẮT, trạng thái lành) rào thoát 0 ngay, không in. Không dùng tiến trình con (không `git`): tra trạng thái trong tiến trình.
Rào KHÔNG đọc file dấu cũ; nếu `.tmp/autopilot.json` còn đó thì chỉ in MỘT dòng nhắc ở stderr, không chặn.

Lối dừng: lối thoát cũ (`--clear` xoá file dấu) đã bỏ. Thay bằng luật chống phá công tắc dưới đây và lệnh `/agile stop` do NGƯỜI DÙNG gõ
(hook `UserPromptExpansion`, không phải tác tử, ghi trạng thái); đó là cách duy nhất được phép tắt rào.

Khi rào đang bật: lệnh shell hay công cụ ghi file bị chặn (thoát 2, cùng khuôn lý do) nếu (a) đích là thư mục trạng thái (thư mục mặc định
của nền tảng hay giá trị `AGENT_AGILE_STATE_DIR`; đường tương đối, `..`, dạng biến môi trường, qua liên kết/junction) hay file `repo-*.json`/
`session-*.json` trong đó; (b) chạy `agile_state.py` với lệnh con đổi công tắc (`on|off|stop|always|manual`; `status`/`get` vẫn qua) hay chạy
`agile_hook.py` (nhận JSON qua stdin); (c) `import agile_state`/`agile_hook` trong `python -c`/heredoc/văn bản lệnh; (d) đặt hay export
`AGENT_AGILE_STATE_DIR`/`CLAUDE_PROJECT_DIR` để đổi hướng trạng thái. Lệnh chỉ-đọc (`cat`, `ls`, `grep`…) vào thư mục trạng thái vẫn qua.
TK6h (R3): (e) `cd`/`pushd`/`Set-Location`/`env -C`/`sudo -D` tới thư mục trạng thái HAY BẤT KỲ TỔ TIÊN của nó bị chặn; sau mọi `cd` (thư mục hiện hành không còn
biết) đường tương đối bị chặn nếu có thể trỏ vào thư mục trạng thái từ một tổ tiên (`state/*`, `mv state x`, `*`); (f) lệnh trong nhóm chỉ-đọc mà ghi được (`sort -o`,
`uniq a b`, `xxd a b`, `find -fprint`, `git diff --output`, `awk -i inplace`) không còn được coi là chỉ-đọc; (g) đường trạng thái trong `$(…)`, dấu huyền, `<(…)`
và thân heredoc đưa vào trình thông dịch qua ống (`cat <<EOF | python`) bị chặn dù câu ngoài là `echo`; (h) `claude -p`/`--resume` kèm lệnh `/agile` hay
`/agent-agile-team:agile` bị chặn; `AGILE_GUARD_DEADLINE_S` chỉ rút ngắn được hạn (nan/inf/<=0/chữ về 6 s).

GIỚI HẠN ĐÃ BIẾT (nói thẳng): so khớp chuỗi LUÔN lách được bằng gián tiếp (`python -c` ghép tên lệnh/đường từ mảnh, file script viết trước
rồi chạy sau, biến chưa biết giá trị, `getattr`, `eval` dựng chuỗi). Luật này là sàn chống TAI NẠN, không phải bằng chứng an ninh; cùng tài
khoản có Bash thì ghi đè file trạng thái được. Cái bảo vệ thật là lệnh người dùng gõ + cờ `source` + soát transcript.

Rào không còn dựa vào file dấu: bật hay ngủ theo trạng thái agile (không phải theo việc có file nào hay không); xem KÍCH HOẠT. Đầu ra: claude/codex in lý do ở stderr rồi thoát 2; antigravity
in JSON `deny` ở stdout, thoát 0; cho qua: claude/codex thoát 0 không in, antigravity in `{}`.
Lý do: `agile: '<mục loại>' cần người dùng nói trong chat — lệnh không chạy`.

Mục có mẫu lệnh: chỉ `irreversible_delete` — xoá đệ quy ngoài `.tmp/`, mọi lệnh xoá có đích thuộc `.git`, `find -delete`/`-exec rm`,
`Get-ChildItem -Recurse | Remove-Item`, `[IO.Directory]::Delete(…, $true)`, `robocopy /MIR`, `busybox rm`, chuỗi `mv`/`robocopy`/`cp -r` vào `.tmp/` rồi xoá,
`git worktree remove --force` và các lệnh git phá hoàn tác (`reflog expire`, `gc --prune=now`, `update-ref -d`, `push` xoá hay ép, `branch -D`; SPR-20 TK27b).
Lệnh git khác (đẩy thường, tag, gộp, `commit`, `reset`) không bị hook chặn (TK21): luật chữ ở method/git-conventions.md. Các mục khác là rào hành vi.
Danh sách đóng 13 mục lấy từ `_agile_rules.AGILE_EXCLUSIONS` chỉ dùng khi trạng thái hỏng (chặn cả 13); trạng thái lành chặn bảy mục
`OPEN_ALWAYS_BLOCKED`. Không còn tiến trình con nào (SPR-32 B3 bỏ `git check-ignore` cùng với bảo vệ file dấu).

Không phân tích chuỗi chương trình tuỳ ý (`awk 'BEGIN{system(…)}'`, `perl -e`, `ruby -e`, `node -e`, `python -c`): giới hạn đã biết.

GIỚI HẠN ĐÃ BIẾT: mẫu là danh sách đóng, tách lệnh thô theo `&&`, `||`, `;`, `|`, `&`, xuống dòng, ngoặc và dấu huyền, không hiểu
dấu nháy (chấp nhận chặn nhầm). Chỉ mở lớp `bash -c`/`pwsh -Command`/`cmd /c` trực tiếp, tối đa MAX_UNWRAP lớp (quá thì chặn).
Đối thủ cố ý (biến môi trường, script, `python -c`, thoát ký tự `g\\it`, ghép chuỗi tên lệnh) lách được; đây là lưới
an toàn, không phải ranh giới bảo mật.

Đóng khi lỗi: rào đang bật (hay không xác định được) mà JSON hỏng hay hook gặp ngoại lệ → chặn; agile tắt và trạng thái lành thì
ngoại lệ không chặn việc của người dùng. AGILE_GUARD_DEBUG=1 in traceback ra stderr.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import re
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # `typing.TextIO` only annotates (SPR-32 B4: not imported per tool call)
    from typing import TextIO

FORMATS = ("claude", "codex", "antigravity")
LEGACY_MARKER_PARTS = (".tmp", "autopilot.json")  # chỉ để in dòng nhắc; rào không đọc nó
SHELL_TOOLS = frozenset({"bash", "powershell", "shell", "exec_command", "run_command", "local_shell", "shell_command"})
COMMAND_KEYS = ("command", "cmd", "CommandLine")  # tool_input.* (Claude, Codex) và toolCall.args.* (Antigravity)
CWD_KEYS = ("workdir", "cwd", "Cwd")
SHELL_WRAPPERS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "pwsh", "powershell", "cmd"})
WRAPPER_FLAGS = frozenset({"-c", "-lc", "-ic", "-cl", "-command", "/c", "/k"})
SEPARATORS = re.compile(r"&&|\|\||[;|&\n\r()`]")
LEAD_WORDS = frozenset({"if", "then", "else", "elif", "do", "while", "until", "{", "!"})
# Tiền tố bỏ được: tên -> (cờ nhận giá trị ở token kế, số đối số vị trí cần bỏ sau cờ)
PREFIXES = {
    "sudo": (frozenset({"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U", "-r", "-t", "--user", "--group", "--host", "--prompt",
                        "--chdir", "--role", "--type"}), 0),
    "env": (frozenset({"-u", "-C", "--unset", "--chdir"}), 0),
    "timeout": (frozenset({"-s", "-k", "--signal", "--kill-after"}), 1),
    "nice": (frozenset({"-n", "--adjustment"}), 0),
    "xargs": (frozenset({"-n", "-I", "-i", "-d", "-a", "-E", "-L", "-l", "-P", "-s", "--max-args", "--delimiter", "--arg-file",
                         "--max-procs", "--max-lines", "--max-chars", "--replace", "--eof"}), 0),
    "stdbuf": (frozenset({"-i", "-o", "-e"}), 0),
    "exec": (frozenset({"-a"}), 0),
    "command": (frozenset(), 0),
    "builtin": (frozenset(), 0),
    "nohup": (frozenset(), 0),
    "setsid": (frozenset(), 0),
    "ionice": (frozenset({"-c", "-n", "-p", "-P", "-u", "--class", "--classdata"}), 0),
    "doas": (frozenset({"-u", "-C"}), 0),
    "time": (frozenset(), 0),
}
ENV_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
GIT_DIR_VARS = frozenset({"GIT_DIR", "GIT_WORK_TREE"})
GIT_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"})
DELETE_COMMANDS = frozenset({"rm", "ri", "del", "erase", "rmdir", "rd", "remove-item"})
CD_COMMANDS = frozenset({"cd", "chdir", "pushd", "popd", "set-location", "sl", "push-location", "pop-location"})
CHDIR_OPTIONS = {"env": frozenset({"-C", "--chdir"}), "sudo": frozenset({"-D", "--chdir"})}  # dạng tách rời: giá trị ở token kế
FIND_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
FIND_WRITE = frozenset({"-fprint", "-fprint0", "-fprintf", "-fls"})  # `find` ghi kết quả ra file (TK6h RF2)
MOVE_COMMANDS = frozenset({"mv", "move", "move-item", "mi", "ren", "rename", "rename-item", "rni", "robocopy"})  # đích dưới `.tmp/` → bỏ ngoại lệ dọn tạm cho phần xoá phía sau
COPY_RECURSIVE_NAMES = frozenset({"cp", "copy-item", "cpi"})  # chỉ tính khi có cờ đệ quy
LISTING_COMMANDS = frozenset({"get-childitem", "gci", "ls", "dir"})  # `… -Recurse | Remove-Item`
SEP_KEEP = re.compile("(" + SEPARATORS.pattern + ")")  # như SEPARATORS nhưng giữ dấu ngăn để biết ống dẫn
CHAIN_BREAKS = frozenset({"&&", "||", ";", "&", chr(10), chr(13)})  # dấu ngăn cắt mạch ống dẫn
IO_DELETE = re.compile(r"\[(?:system\.)?io\.directory\]\s*::\s*delete\s*\([^)]*\$true|\.delete\s*\(\s*\$true\s*\)", re.IGNORECASE)
ROBOCOPY_FLAG = re.compile(r"/[A-Za-z]+(?::.*)?")
UNSAFE_PATH_CHARS = set(",$%`~{}()<>!^\"'\n\r;|&")
GLOB_CHARS = set("*?[")
MAX_UNWRAP = 3
DEADLINE = "deadline"  # lý do riêng: phân tích lệnh vượt hạn nội bộ (DEADLINE_SECONDS)
NESTED = "nested"  # đơn vị chặn riêng: lồng shell quá sâu, không phân tích được
TAMPER = "tamper"  # đơn vị chặn riêng: đụng tới công tắc agile (thư mục trạng thái, agile_state/agile_hook, biến đổi hướng)
SPECIAL_ITEMS = frozenset({NESTED, TAMPER})
WRITE_TOOLS = frozenset({"write", "edit", "multiedit", "notebookedit", "apply_patch", "write_to_file", "replace_file_content",
                         "multi_replace_file_content"})
PATH_KEYS = ("file_path", "path", "notebook_path", "TargetFile")
PATCH_PREFIXES = ("*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: ")
REDIRECT = re.compile(r"^(?:[0-9]*|&)>>?\|?(.*)$", re.S)
DYNAMIC_CHARS = set("$%`")
REDIRECT_INSIDE = re.compile(r">>?\|?")
LINE_CONTINUATION = re.compile(r"[\\`]\r?\n")
PIPE = re.compile(r"(?<!\|)\|(?!\|)")
EVAL_COMMANDS = frozenset({"eval", "iex", "invoke-expression"})
COPY_COMMANDS = frozenset({"cp", "copy", "copy-item", "cpi"})  # lệnh chép: đích thuộc thư mục trạng thái vẫn bị chặn; nguồn thì không (công tắc không còn là file trong dự án)
HEREDOC = re.compile(r"<<(?!<)(-?)\s*(?:'([^']+)'|\"([^\"]+)\"|\\?([A-Za-z_][\w.-]*))")
PIPE_INTO_SHELL = re.compile(r"\|\s*(?:sudo\s+)?(?:bash|sh|zsh|dash|ksh|pwsh|powershell)\b")
READ_ONLY_COMMANDS = frozenset({
    "cat", "type", "get-content", "gc", "ls", "dir", "get-childitem", "gci", "stat", "head", "tail", "less", "more", "wc", "grep", "egrep",
    "fgrep", "rg", "select-string", "sls", "file", "diff", "cmp", "sha256sum", "sha1sum", "md5sum", "get-item", "gi", "test-path", "findstr",
    "test", "[", "[[", "jq", "echo", "printf", "write-output", "write-host", "realpath", "readlink", "basename", "dirname", "cut", "sort",
    "uniq", "nl", "od", "hexdump", "xxd", "strings", "get-filehash", "find", "awk"})
READ_ONLY_GIT = frozenset({"status", "log", "diff", "show", "ls-files", "check-ignore", "blame", "ls-tree", "cat-file", "rev-parse",
                           "grep", "describe", "shortlog", "rev-list"})


PYTHON_NAME = re.compile(r"^(?:py|python[0-9.]*)$")
RUNNER_NAMES = frozenset({"uv", "uvx", "pipx", "poetry", "pdm", "hatch", "pipenv", "rye", "tox", "nox"})  # chạy Python qua công cụ môi trường: mọi token sau tên đều có thể là script
INTERPRETER_NAMES = frozenset({"node", "nodejs", "deno", "bun", "perl", "ruby", "php", "lua", "osascript", "rscript", "groovy", "tclsh"})
INTERPRETER_VALUE_FLAGS = frozenset({"-X", "-W", "--check-hash-based-pycs"})  # cờ của `python` nhận giá trị ở token kế (`-X utf8`)
DEADLINE_ENV = "AGILE_GUARD_DEADLINE_S"  # chỉ để test; mặc định DEADLINE_SECONDS
DEADLINE_SECONDS = 6.0  # dưới hạn 10 s của hooks.json (hook hết giờ KHÔNG chặn): quá hạn này thì tự chặn, không để lệnh dài chạy không rào
_deadline: float | None = None


def deadline_seconds(env: "dict[str, str] | os._Environ[str]") -> float:
    """Hạn nội bộ (giây). `AGILE_GUARD_DEADLINE_S` chỉ được RÚT NGẮN hạn: không phải số hữu hạn dương (nan, inf, <= 0, chữ, rỗng) hay lớn hơn mặc định thì
    dùng mặc định `DEADLINE_SECONDS` (TK6h RF5: `nan`/`inf` từ khối `env` của settings từng tắt hạn)."""
    try:
        limit = float(env.get(DEADLINE_ENV) or DEADLINE_SECONDS)
    except ValueError:
        return DEADLINE_SECONDS
    return min(limit, DEADLINE_SECONDS) if math.isfinite(limit) and limit > 0 else DEADLINE_SECONDS


class _Deadline(Exception):
    """Phân tích lệnh vượt hạn nội bộ (DEADLINE_SECONDS): lệnh bị chặn với lý do riêng."""


def _tick() -> None:
    if _deadline is not None and time.monotonic() >= _deadline:
        raise _Deadline()


def known_exclusions() -> tuple[str, ...]:
    """Danh sách đóng 13 mục từ `_agile_rules.AGILE_EXCLUSIONS`; nạp muộn để lệnh khi rào đang ngủ không trả phí nhập."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    from _agile_rules import AGILE_EXCLUSIONS
    return tuple(AGILE_EXCLUSIONS)


# --- gốc repo ---------------------------------------------------------------------------------------------------

def _has_git(directory: str) -> bool:
    return os.path.exists(os.path.join(directory, ".git"))


def find_repo_root(start: str) -> str | None:
    """Thư mục chứa `.git` đầu tiên khi đi lên từ `start`, hoặc None."""
    current = os.path.abspath(start)
    while True:
        if _has_git(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


# --- kích hoạt theo trạng thái agile ------------------------------------------------------------------------------

def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _state_module():
    """Nạp `agile_state` (cùng thư mục) muộn; ngoại lệ nổi lên cho người gọi (không nạp được = đóng khi lỗi)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import agile_state
    return agile_state


def _state_dirs(st: object) -> tuple[str, ...]:
    """Thư mục trạng thái đã chuẩn hoá (`normcase`): thư mục đang dùng, thư mục mặc định nền tảng, giá trị `AGENT_AGILE_STATE_DIR` (nếu hợp lệ), mỗi
    cái ở dạng chữ và dạng `realpath` (liên kết/junction)."""
    found: list[str] = []
    for getter in ("state_dir", "platform_state_dir", "state_dir_override"):
        try:
            path = getattr(st, getter)()
        except Exception:  # noqa: BLE001 — vd. không xác định được thư mục home: bỏ ứng viên đó, không coi là hỏng
            continue
        if path is None:
            continue
        for variant in (str(path), os.path.realpath(str(path))):
            norm = os.path.normcase(os.path.normpath(variant))
            if norm not in found:
                found.append(norm)
    return tuple(found)


def activation(payload: dict, projects: tuple[str, ...] = ()) -> tuple[set[str], bool, tuple[str, ...]] | None:
    """Rào có bật cho sự kiện này không? None = ngủ (agile TẮT, trạng thái lành). Ngược lại (mục đang chặn, trạng thái hỏng?, thư mục trạng thái).
    Bật khi: công tắc hiệu lực (`always` của repo hay phiên `session_id` BẬT) · trạng thái hỏng (`guard_must_stay_active`) · có `agent_id` mà
    không có file phiên khớp (tác tử con không bao giờ ngủ) · không nạp được `agile_state`. Không có tiến trình con; chỉ đọc vài file nhỏ.
    Khoá repo như `agile_hook`: `cwd` của sự kiện (hay `CLAUDE_PROJECT_DIR`, do `agile_state` đọc). Sự kiện của host không có `cwd` (Codex/
    Antigravity chỉ có thư mục lệnh) thì dùng `projects` (người gọi đưa vào), rồi thư mục tiến trình. Thư mục lệnh khác thư mục phiên thì `always`
    của repo ở thư mục lệnh cũng tính (như bản cũ dùng file dấu: thấy ở đâu cũng bật); khi harness đã xuất `CLAUDE_PROJECT_DIR` hai khoá trùng nhau."""
    try:
        st = _state_module()
    except Exception:  # noqa: BLE001 — không nạp được lớp trạng thái: đóng khi lỗi
        return set(known_exclusions()), True, ()
    from _agile_rules import OPEN_ALWAYS_BLOCKED  # nạp muộn như `known_exclusions`
    try:
        session = _text(payload.get("session_id"))
        first = _text(payload.get("cwd")) or (projects[0] if projects else None) or os.getcwd()
        states = [st.load_state(first, session)]
        for extra in projects:
            if os.path.normcase(os.path.abspath(extra)) != os.path.normcase(os.path.abspath(first)):
                states.append(st.load_state(extra, session))
        dirs = _state_dirs(st)
    except Exception:  # noqa: BLE001
        return set(known_exclusions()), True, ()
    if any(s["effective_on"] for s in states):
        return set(OPEN_ALWAYS_BLOCKED), False, dirs
    if any(s["state_problem"] or s["guard_must_stay_active"] for s in states):
        return set(known_exclusions()), True, dirs
    if _text(payload.get("agent_id")) and not states[0]["session_file_exists"]:
        return set(OPEN_ALWAYS_BLOCKED), False, dirs  # tác tử con không có file phiên: được bảo vệ, không ngủ
    return None


def _salvage(raw: str) -> dict:
    """Sự kiện không đọc được thành JSON: vớt `session_id`/`agent_id`/`cwd` bằng biểu thức chính quy để vẫn xác định được trạng thái."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (ValueError, TypeError):
        pass
    found: dict = {}
    for key in ("session_id", "agent_id", "cwd"):
        hit = re.search(r'"%s"\s*:\s*"([^"\\]*)"' % key, raw or "")
        if hit and hit.group(1):
            found[key] = hit.group(1)
    return found


def _legacy_notice(dirs: tuple[str, ...], notes: list[str]) -> None:
    """File dấu cũ còn đó: chỉ MỘT dòng nhắc (không chặn, không đọc nội dung). Dò: thư mục lệnh, thư mục phiên, gốc repo của chúng."""
    seen: list[str] = []
    for directory in dirs:
        for base in (directory, find_repo_root(directory)):
            if base and base not in seen:
                seen.append(base)
    for base in seen:
        path = os.path.join(base, *LEGACY_MARKER_PARTS)
        if os.path.isfile(path):
            notes.append("agile: file dấu cũ {} không còn tác dụng (rào nay theo công tắc agile; bật bằng /agile). Không xoá giúp.".format(path))
            return


# --- tham chiếu tới thư mục trạng thái (chống phá công tắc) --------------------------------------------------------
# NÓI THẲNG: mọi luật ở đây là so khớp chuỗi/đường. Chúng lách được bằng gián tiếp (`python -c` ghép tên từ mảnh, viết script rồi chạy sau,
# biến không biết giá trị, `getattr`, `eval`). Đây là SÀN chống tai nạn, không phải bằng chứng an ninh.

STATE_NAME = re.compile(r"(?:repo|session)-[A-Za-z0-9_.-]*\.json", re.IGNORECASE)
SWITCH_COMMANDS = frozenset({"on", "off", "stop", "always", "manual"})  # lệnh con của agile_state.py đổi công tắc; `status`/`get` chỉ đọc
SCRIPT_REF = re.compile(r"(?:^|[/.])agile_(state|hook)(?:\.py)?$", re.IGNORECASE)
ENV_VAR = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)|\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)|%([A-Za-z_][A-Za-z0-9_]*)%", re.IGNORECASE)
STATE_SIGNATURE = re.compile(r"agent-agile-team[/'\",\s]+state(?![\w-])|(?<![\w-])state[/'\",\s]+agent-agile-team(?![\w-])")
_REDIRECT_ENV = r"(?:AGENT_AGILE_STATE_DIR|CLAUDE_PROJECT_DIR)"
ENV_REDIRECT = re.compile("|".join([
    _REDIRECT_ENV + r"['\"\]\})]*\s*=(?!=)",  # NAME=x, $env:NAME = x, os.environ['NAME']=x, set NAME=x
    r"\b(?:export|unset|declare|typeset|setx|putenv|SetEnvironmentVariable)\b[^\n;|&]{0,200}?" + _REDIRECT_ENV,  # export NAME, setx NAME
    r"\b(?:Set|New|Remove|Clear)-Item\s+(?:-\w+\s+)*Env:" + _REDIRECT_ENV,  # Set-Item Env:NAME
    r"(?:^|\s)(?:-u|--unset)[\s=]+" + _REDIRECT_ENV,  # env -u NAME
]), re.IGNORECASE)
IMPORT_STATE = re.compile(
    r"\bimport\s{1,40}[\w\s,.]{0,200}?\bagile_(?:state|hook)\b|\bfrom\s+(?:[\w.]+\.)?agile_(?:state|hook)\b"
    r"|(?:__import__|import_module)\s*\(\s*['\"](?:[\w.]+\.)?agile_(?:state|hook)"
    r"|(?:spec_from_file_location|run_path)\b[^\n]{0,160}agile_(?:state|hook)", re.IGNORECASE)
DOUBLE_SLASH = re.compile(r"/{2,}")
RAW_SEPARATORS = re.compile(r"&&|\|\||[;|&\n\r]")  # như SEPARATORS nhưng KHÔNG tách ở ngoặc/dấu huyền: `(Get-Item p).Delete()` và `$(rm p)` giữ nguyên một câu
CLAUDE_SPAWN = re.compile(r"(?<![\w.-])claude(?:\.\w+)?(?![\w./-])", re.IGNORECASE)  # TK6h RF4: tên chương trình `claude` (cả `/usr/bin/claude`, `claude.cmd`), không `.claude/`
SPAWN_FLAG = re.compile(r"(?<![\w-])(?:-p|--print|--resume|-r|--continue|-c)(?![\w-])")
AGILE_SLASH = re.compile(r"(?<![\w.])/(?:agent-agile-team:)?agile(?![\w-])", re.IGNORECASE)  # lệnh gạch chéo `/agile` hay `/agent-agile-team:agile`
PY_OR_HEREDOC = re.compile(r"(?<![\w.-])(?:python[0-9.]*|py|pythonw)(?:\.exe)?(?![\w-])|<<", re.IGNORECASE)


def _expand(text: str) -> tuple[str, bool]:
    """(chuỗi với biến môi trường đã biết được thay: `$env:X`, `${X}`, `$X`, `%X%`, `~` đầu chuỗi; còn phần động chưa giải được?)."""
    unresolved = False

    def sub(match: "re.Match[str]") -> str:
        nonlocal unresolved
        value = os.environ.get(next(g for g in match.groups() if g))
        if value is None:
            unresolved = True
            return match.group(0)
        return value

    out = ENV_VAR.sub(sub, text)
    if out.startswith("~"):
        out = os.path.expanduser(out)
    if any(ch in out for ch in "$%`"):
        unresolved = True
    return out, unresolved


def _under(path: str, directory: str) -> bool:
    return path == directory or path.startswith(directory.rstrip(os.sep) + os.sep)


def _glob_covers(path: str, directory: str, ancestor: bool) -> bool:
    """Mẫu `path` (đã `normcase`, có ký tự đại diện) có thể trỏ vào thư mục trạng thái `directory`, hay (khi `ancestor`) vào một thư mục BAO nó?
    So từng thành phần bằng `fnmatch`: mẫu dài hơn hay bằng thư mục = ở trong hay chính nó; ngắn hơn = tổ tiên. `**` khớp phần còn lại."""
    pattern_parts = path.replace("\\", "/").split("/")
    dir_parts = directory.replace("\\", "/").rstrip("/").split("/")
    for pattern, name in zip(pattern_parts, dir_parts):
        if pattern == "**":
            return True
        if not fnmatch.fnmatchcase(name, pattern):
            return False
    return len(pattern_parts) >= len(dir_parts) or ancestor


def _real(full: str, ctx: "Context") -> str:
    """`realpath` có nhớ theo thư mục: mục đang có thì giải thẳng; mục chưa có thì giải thư mục cha (một lần cho cả lệnh) rồi nối tên (RF3)."""
    if os.path.lexists(full):
        return os.path.realpath(full)
    parent = os.path.dirname(full)
    if parent == full:
        return full
    real_parent = ctx.real_cache.get(parent)
    if real_parent is None:
        real_parent = ctx.real_cache[parent] = os.path.realpath(parent)
    return os.path.join(real_parent, os.path.basename(full))


def _mentions_state(text: str, ctx: "Context") -> bool:
    """Chuỗi chứa đường của thư mục trạng thái hay dấu hiệu của nó (`agent-agile-team/state`, `state/agent-agile-team`)."""
    low = DOUBLE_SLASH.sub("/", text.replace("\\", "/").lower())  # `C:\\Users\\x` (gạch ngược kép trong chuỗi mã) cũng về `c:/users/x`
    return any(d.replace("\\", "/") in low for d in ctx.state_dirs) or bool(STATE_SIGNATURE.search(low))


def _state_ref(text: str, ctx: "Context", ancestor: bool = False) -> bool:
    """`text` (đối số hay đích chuyển hướng) trỏ vào thư mục trạng thái, hay file `repo-*.json`/`session-*.json` trong đó? Giải `~`, biến môi trường,
    `..`, đường tương đối (từ thư mục lệnh), liên kết/junction (`realpath` cả đường và đường tới mục đã có). `ancestor`: cả thư mục BAO thư mục
    trạng thái (cho lệnh xoá/chuyển). Chưa tính được đường (biến lạ, đã đổi thư mục) → so theo tên file trạng thái (đóng an toàn)."""
    if not text:
        return False
    key = (text, ancestor, ctx.cwd_changed)  # RF3: cùng một chuỗi trong cùng lệnh (từ lặp) chỉ tính một lần
    if key not in ctx.ref_cache:
        ctx.ref_cache[key] = _state_ref_uncached(text, ctx, ancestor)
    return ctx.ref_cache[key]


def _state_ref_uncached(text: str, ctx: "Context", ancestor: bool) -> bool:
    expanded, unresolved = _expand(text)
    norm = expanded.replace("\\", "/")
    if _mentions_state(norm, ctx):
        return True
    if GLOB_CHARS & set(norm) and not unresolved and (os.path.isabs(norm) or not ctx.cwd_changed):  # TK6e RF2: ký tự đại diện ở BẤT KỲ thành phần nào (không chỉ cuối)
        probe = os.path.normcase(os.path.normpath(norm if os.path.isabs(norm) else os.path.join(ctx.cwd, norm)))
        if any(_glob_covers(probe, d, ancestor) for d in ctx.state_dirs):
            return True
    if unresolved or ctx.cwd_changed:
        if STATE_NAME.fullmatch(os.path.basename(norm.rstrip("/"))):
            return True
        return not os.path.isabs(norm) and _reaches_state(norm, ctx, ancestor, unresolved)
    full = os.path.normpath(norm if os.path.isabs(norm) else os.path.join(ctx.cwd, norm))
    candidates = {os.path.normcase(full)}
    try:
        candidates.add(os.path.normcase(_real(full, ctx)))
    except OSError:
        return True
    return any(_under(c, d) or (ancestor and c != os.path.dirname(c) and _under(d, c)) for c in candidates for d in ctx.state_dirs)  # gốc ổ đĩa không tính là tổ tiên


def _reaches_state(norm: str, ctx: "Context", ancestor: bool, anywhere: bool) -> bool:
    """TK6h RF1: đường TƯƠNG ĐỐI mà thư mục hiện hành không còn biết (đã `cd`, hay đường mở đầu bằng biến lạ): nó có thể nằm trong thư mục trạng thái nếu
    thư mục hiện hành là MỘT TỔ TIÊN của nó? Thử mọi tổ tiên `A` làm thư mục hiện hành: các thành phần của đường (`.`/`..` bỏ; có thể là mẫu `*`, `st*`, `**`)
    khớp từng thành phần của phần còn lại `A → thư mục trạng thái`; đường dài hơn hay bằng = ở trong hay chính nó; ngắn hơn chỉ tính khi `ancestor`
    (xoá/chuyển/cd: đường là thư mục bao nó). Một thành phần trần không có ký tự đại diện (`state`, `data`) chỉ tính khi `ancestor` và đúng tên thư mục trạng thái
    (`mv state x`, `rm state`; `git commit -m state` không tính). `anywhere` (đường có biến chưa giải): đầu đường có thể bị bỏ. Chặn nhầm có chủ đích: sau
    `cd`, lệnh ghi dùng ký tự đại diện trần (`mv * x`) hay thư mục tên trùng thư mục trạng thái (`state/…`)."""
    parts = [p for p in os.path.normcase(norm).replace("\\", "/").split("/") if p not in ("", ".", "..")]
    if not parts:
        return False
    bare = len(parts) == 1 and not GLOB_CHARS & set(parts[0])
    for directory in ctx.state_dirs:
        dir_parts = [p for p in directory.replace("\\", "/").split("/") if p]
        if bare:
            if ancestor and parts[0] == dir_parts[-1]:
                return True
            continue
        for k in range(1, len(dir_parts)):
            rest = dir_parts[k:]
            for start in (range(len(parts)) if anywhere else (0,)):
                sub = parts[start:]
                if (len(sub) >= len(rest) or ancestor) and all(p == "**" or fnmatch.fnmatchcase(r, p) for p, r in zip(sub, rest)):
                    return True
    return False


def _covers_state(text: str, ctx: "Context") -> bool:
    """Điểm bắt đầu của `find`: trong thư mục trạng thái hay bao nó. Đã đổi thư mục thì `.`/`..` cũng tính."""
    if not text:
        return False
    if _state_ref(text, ctx, ancestor=True):
        return True
    return ctx.cwd_changed and text.replace("\\", "/").strip("/") in ("", ".", "..")


def _raw_tamper(text: str) -> bool:
    """Luật trên VĂN BẢN lệnh nguyên (trước khi bỏ thân heredoc): (c) `import agile_state/agile_hook` trong lệnh có Python/heredoc,
    (d) đặt hay export `AGENT_AGILE_STATE_DIR`/`CLAUDE_PROJECT_DIR` (TK6e S2: xét từng câu lệnh, bỏ câu chỉ-đọc như `grep -r CLAUDE_PROJECT_DIR= .`)."""
    if IMPORT_STATE.search(text) and PY_OR_HEREDOC.search(text):
        return True
    if CLAUDE_SPAWN.search(text) and SPAWN_FLAG.search(text) and AGILE_SLASH.search(text):  # TK6h RF4: phiên `claude -p`/`--resume` mang session_id riêng, hook áp lệnh cho phiên đó, không cho phiên này
        return True
    if not ENV_REDIRECT.search(text):
        return False
    return any(ENV_REDIRECT.search(segment) and not _env_read_only(segment) for segment in RAW_SEPARATORS.split(text))


def _env_read_only(segment: str) -> bool:
    """Câu lệnh chỉ-đọc (tên lệnh đầu, KHÔNG bỏ tiền tố: `X=1 grep` vẫn là đặt biến) nhắc tên biến mà không đặt nó; có chuyển hướng `>`, `find -exec`,
    `awk system` thì không."""
    tokens = tokenize(segment)
    if not tokens or ">" in segment:
        return False
    name, args = _exe_name(tokens[0]), tokens[1:]
    if name == "find" and any(a in FIND_EXEC or a == "-delete" for a in args):
        return False
    if name == "awk" and "system" in segment:
        return False
    return _read_only(name, args, Context(set(), ".", light=True))


def _interpreter_name(name: str) -> bool:
    return bool(PYTHON_NAME.match(name)) or name in INTERPRETER_NAMES or name in SHELL_WRAPPERS


def _raw_state_tamper(text: str, ctx: "Context") -> bool:
    """TK6e RF1: đường thư mục trạng thái nằm trong VĂN BẢN lệnh (trước khi tách token), kể cả thân heredoc đưa vào trình thông dịch và chuỗi trong
    `python -c`/`node -e`/PowerShell `[IO.File]::Delete(…)`/`(Get-Item p).Delete()`. QUYẾT ĐỊNH: một câu lệnh KHÔNG chỉ-đọc mà nhắc tới đường đó bị chặn
    (kể cả để ghi chú trong thân heredoc đưa vào trình thông dịch); câu chỉ-đọc (`cat`, `ls`, `grep`…) và câu chép (`cp`, đích do luật tách token xét) qua.
    Chỉ nhận đường thư mục (không nhận tên file trần `session-x.json`: đã có luật tách token). Tách câu ở `&& || ; | &` và xuống dòng, không ở ngoặc."""
    joined = _join_and_strip(text, interpreters=True)
    for inner in _substitutions(joined):  # TK6h RF3: `echo $(python -c "…")`, dấu huyền, `<(…)`: nội dung thay thế được xét như một lệnh riêng, kể cả khi câu ngoài là `echo`/`printf`
        _tick()
        if inner.strip() and _raw_state_tamper(inner, ctx):
            return True
    for segment in RAW_SEPARATORS.split(joined):
        _tick()
        if not segment.strip() or not _mentions_state(_expand(segment)[0], ctx):
            continue
        tokens = tokenize(segment)
        stripped, _ = _strip_prefixes(list(tokens), Context(set(), ctx.cwd, light=True))
        if stripped:
            name, args = _exe_name(stripped[0]), stripped[1:]
            if name in COPY_COMMANDS:
                continue
            if _read_only(name, args, ctx) and name != "awk":  # `find` qua đây: `-delete`/`-exec` do `_find_item` xét theo token (cùng lý do cũ)
                continue
        return True
    return False


def _script_positions(tokens: list[str]) -> list[int]:
    """Vị trí token có thể là script ĐANG ĐƯỢC CHẠY (TK6e S1): token đầu; token đầu tiên không phải cờ ngay sau trình thông dịch Python (`python`, `python3`,
    `py -3`, kể cả `-X utf8`, `-m`); mọi token sau tên công cụ môi trường (`uv run`, `poetry run`…). `git add scripts/agile_hook.py`, `cp`, `ruff check`
    chỉ NHẮC tới script nên không tính."""
    found = [0]
    name = _exe_name(tokens[0])
    if PYTHON_NAME.match(name):
        index = 1
        while index < len(tokens) and tokens[index].startswith("-") and len(tokens[index]) > 1:
            index += 2 if tokens[index] in INTERPRETER_VALUE_FLAGS else 1
        if index < len(tokens):
            found.append(index)
    elif name in RUNNER_NAMES:
        found.extend(range(1, len(tokens)))
    return found


def _tamper_item(tokens: list[str], ctx: "Context") -> str | None:
    """TAMPER nếu một câu lệnh (a) ghi/đổi/xoá thứ nằm trong thư mục trạng thái (chuyển hướng tới đó, lệnh không chỉ-đọc có đối số trỏ tới đó, `cd` vào
    đó) hay (b) chạy `agile_state.py` với lệnh con đổi công tắc, hay chạy `agile_hook.py`. Lệnh chỉ-đọc (`cat`, `ls`, `grep`…) và `agile_state.py status|get` qua."""
    if not tokens:
        return None
    name, args = _exe_name(tokens[0]), tokens[1:]
    read_only = _read_only(name, args, ctx)
    if not read_only:
        for position in _script_positions(tokens):
            script = SCRIPT_REF.search(tokens[position].replace("\\", "/"))
            if script and (script.group(1).lower() == "hook" or any(a.lower() in SWITCH_COMMANDS for a in tokens[position + 1:])):
                return TAMPER
    ancestor = name in DELETE_COMMANDS or name in MOVE_COMMANDS or name in CD_COMMANDS  # TK6h RF1: `cd` tới tổ tiên của thư mục trạng thái cũng là phá (đường tương đối sau đó vào được)
    ref_at: list[int] = []
    index = 0
    while index < len(tokens):
        _tick()
        token = tokens[index]
        redirect = REDIRECT.match(token)
        if redirect:
            target = redirect.group(1)
            if not target and index + 1 < len(tokens):
                index += 1
                target = tokens[index]
            if _state_ref(target, ctx):
                return TAMPER
        elif ">" in token and not token.startswith("<"):  # chuyển hướng dính liền: `lệnh>đích`
            if _state_ref(token[REDIRECT_INSIDE.search(token).end():], ctx):
                return TAMPER
        elif index > 0 and not token.startswith("<") and not (token.startswith("-") and "=" not in token and ":" not in token):
            if any(_state_ref(value, ctx, ancestor) for value in (token, _arg_value(token), token.partition("=")[2])):
                ref_at.append(index)
        index += 1
    if name in COPY_COMMANDS:  # trạng thái chỉ là NGUỒN thì được chép (đọc)
        ref_at = [i for i in ref_at if i in _copy_destinations(tokens)]
    return TAMPER if ref_at and not read_only else None


class Context:
    """Trạng thái một lần phân tích: mục đang chặn, thư mục lệnh chạy, các gốc repo, thư mục trạng thái, thư mục git đang làm việc."""

    def __init__(self, active: set[str], cwd: str, state_dirs: tuple[str, ...] = (), session: str | None = None, light: bool = False) -> None:
        self.active = active
        self.state_dirs = tuple(state_dirs)
        self.cwd = os.path.abspath(cwd)
        self.light = light  # bản nhẹ cho `_strip_prefixes` (chỉ cần `enter()`): không dò gốc repo trên đĩa (~0,3 ms mỗi câu lệnh, TK6e RF3)
        self.roots = [] if light else list(dict.fromkeys(r for r in (find_repo_root(self.cwd), find_repo_root(session) if session else None) if r))
        self.root = self.roots[0] if self.roots else None
        self.ref_cache: dict[tuple, bool] = {}  # kết quả `_state_ref` theo (chuỗi, ancestor, đã đổi thư mục)
        self.real_cache: dict[str, str] = {}  # `realpath` theo thư mục (RF3: một lần gọi hệ thống mỗi token là ~0,3 ms)
        self.in_git = False if light else _is_git_path(self.cwd)  # thư mục lệnh (hay đích `cd`) nằm trong `.git`: mọi lệnh xoá/chuyển bị chặn
        self.state_cd = False  # `env -C`/`sudo -D` tới thư mục trạng thái hay tổ tiên của nó (đặt trong `_strip_prefixes`, xét ở `_segment_item`)
        self.cwd_changed = False  # đã gặp thao tác đổi thư mục (cd, pushd, env -C…, kể cả trong subshell/bash -c)
        self.tmp_moved = False  # đã gặp `mv`/`robocopy`/`cp -r`… với đích dưới `.tmp/`: phần xoá phía sau không còn ngoại lệ dọn tạm

    def enter(self) -> None:
        """Ghi nhận một thao tác đổi thư mục. Không tính đường đi (`cd` trong subshell hay vế pipeline không đổi thư mục của lệnh
        sau, `cd` tương đối nối tiếp nhau khó tính đúng): từ đây đường tương đối không giải được nữa, so theo tên (đóng an toàn)."""
        self.cwd_changed = True


def tmp_target_ok(target: str, ctx: Context) -> bool:
    """Đích xoá nằm thật sự dưới `<gốc repo>/.tmp/` (ngoại lệ dọn tạm, method/agile.md mục 5). Glob ở thành phần cuối được
    mở rộng bằng `os.listdir`: mỗi mục khớp phải nằm thật trong `.tmp/` (theo `realpath`)."""
    roots = list(ctx.roots)
    expanded = target.replace(chr(92), "/")
    if os.path.isabs(expanded) and not UNSAFE_PATH_CHARS & set(target):  # đường tuyệt đối vào `.tmp/` của cây khác (như khi file dấu cũ được dò theo đường đích)
        other = find_repo_root(os.path.dirname(os.path.normpath(expanded)))
        if other and other not in roots:
            roots.append(other)
    return any(_tmp_target_under(target, ctx, r) for r in roots)


def _tmp_target_under(target: str, ctx: Context, root: str) -> bool:
    if not target or UNSAFE_PATH_CHARS & set(target):
        return False
    norm = target.replace("\\", "/")
    if ".." in norm.split("/"):
        return False
    full = os.path.normpath(norm if os.path.isabs(norm) else os.path.join(ctx.cwd, norm))
    tmp = os.path.normpath(os.path.join(root, ".tmp"))
    full_n, tmp_n = os.path.normcase(full), os.path.normcase(tmp)
    if not full_n.startswith(tmp_n + os.sep):
        return False
    comps = full[len(tmp) + 1:].split(os.sep)
    if any(GLOB_CHARS & set(c) for c in comps[:-1]):
        return False
    is_glob = bool(GLOB_CHARS & set(comps[-1]))
    real_tmp = os.path.normcase(os.path.realpath(tmp))
    if real_tmp != os.path.normcase(os.path.join(os.path.realpath(root), ".tmp")):
        return False  # chính `.tmp` là liên kết ra nơi khác
    inside = real_tmp + os.sep
    if not is_glob:
        return os.path.normcase(os.path.realpath(full)).startswith(inside)
    parent = os.path.dirname(full)
    real_parent = os.path.normcase(os.path.realpath(parent))
    if real_parent != real_tmp and not real_parent.startswith(inside):
        return False
    try:
        names = os.listdir(parent)
    except OSError:
        return False
    pattern = comps[-1].lower()
    for entry in names:
        if fnmatch.fnmatchcase(entry.lower(), pattern):
            if not os.path.normcase(os.path.realpath(os.path.join(parent, entry))).startswith(inside):
                return False
    return True


# --- phân tích lệnh -------------------------------------------------------------------------------------------

def tokenize(segment: str) -> list[str]:
    """Tách theo khoảng trắng, nháy `'`/`"` gom token (bỏ nháy); `\\` là ký tự thường (đường Windows)."""
    tokens: list[str] = []
    buf: list[str] = []
    quote = ""
    started = False
    for ch in segment:
        if quote:
            if ch == quote:
                quote = ""
            else:
                buf.append(ch)
        elif ch in "'\"":
            quote = ch
            started = True
        elif ch.isspace():
            if buf or started:
                tokens.append("".join(buf))
            buf, started = [], False
        else:
            buf.append(ch)
    if buf or started:
        tokens.append("".join(buf))
    return tokens


def _exe_name(token: str) -> str:
    name = os.path.basename(token.replace("\\", "/")).lower()
    return name[:-4] if name.endswith((".exe", ".com")) else name


def _cluster(token: str, letters: str) -> bool:
    """Cụm cờ ngắn `-xyz` (chỉ chữ cái) chứa một trong `letters`."""
    return bool(re.fullmatch(r"-[A-Za-z]+", token)) and any(ch in token for ch in letters)


def _git_parse(args: list[str]) -> tuple[str, list[str]]:
    """(lệnh con, đối số còn lại) của một lệnh `git`, bỏ các tuỳ chọn toàn cục (`-C <dir>`, `-c k=v`…)."""
    index = 0
    while index < len(args):
        arg = args[index]
        if not arg.startswith("-"):
            return arg, args[index + 1:]
        index += 2 if arg in GIT_VALUE_OPTIONS else 1
    return "", []


def _git_config(args: list[str]) -> dict[str, str]:
    """Các `-c khoá=giá-trị` của tuỳ chọn toàn cục (khoá viết thường)."""
    found: dict[str, str] = {}
    index = 0
    while index < len(args) and args[index].startswith("-"):
        if args[index] == "-c" and index + 1 < len(args):
            key, _, value = args[index + 1].partition("=")
            found[key.lower()] = value.lower()
        index += 2 if args[index] in GIT_VALUE_OPTIONS else 1
    return found


def _git_item(args: list[str], ctx: Context) -> str | None:
    """Mẫu git còn nằm trong hook: phá cơ chế hoàn tác, mục `irreversible_delete`: `worktree remove --force`, `reflog expire|delete`,
    `gc --prune=now`, `prune` kèm `now`, `update-ref -d`, `push` xoá hay ép (`--delete`, `-d`, `--force*`, `-f`, `--mirror`, `--prune`,
    refspec `:ref` hay `+ref`), `branch -D`. Mọi lệnh git khác (đẩy thường, gộp, tag, commit, `reset`, `stash`, `clean`) không bị hook chặn:
    luật chữ ở method/git-conventions.md. Cộng `stash -a|-u` và `clean -f` (SPR-32 B3: chặn vô điều kiện, không còn phụ thuộc file dấu)."""
    sub, rest = _git_parse(args)
    config = _git_config(args)
    if sub in ("gc", "prune", "reflog", "maintenance") and any(re.fullmatch(r"gc\..*expire\w*", key) for key in config):
        return "irreversible_delete"  # `git -c gc.pruneExpire=<hạn bất kỳ> gc`: đặt hạn hết hạn qua cấu hình = `--prune=<hạn>`; không liệt kê hạn
    if sub == "stash":  # SPR-32 B3: giữ nguyên quyết định cũ (phá dữ liệu chưa theo dõi/ignore; luật chữ cấm `stash` trần): chặn `-a`/`-u` vô điều kiện
        if "--all" in rest or "--include-untracked" in rest or any(_cluster(a, "au") for a in rest):
            return "irreversible_delete"
        return None
    if sub == "clean":  # `clean -f` (kể cả `-x`/`-X`, `-c clean.requireForce=false`) xoá file chưa theo dõi: chặn; `-n`/`--dry-run` và `clean` trần qua
        opts = rest[:rest.index("--")] if "--" in rest else rest
        no_force_needed = config.get("clean.requireforce") in ("false", "0", "no", "off")
        forced = "--force" in opts or any(_cluster(a, "f") for a in opts) or no_force_needed
        dry_run = "--dry-run" in opts or any(_cluster(a, "n") for a in opts)
        if forced and any(_cluster(a, "xX") for a in opts):
            return "irreversible_delete"
        return "irreversible_delete" if forced and not dry_run else None
    if sub == "worktree":
        forced = "--force" in rest or any(_cluster(a, "f") for a in rest)
        return "irreversible_delete" if rest[:1] == ["remove"] and forced else None
    if sub == "reflog":
        return "irreversible_delete" if rest[:1] in (["expire"], ["delete"]) else None
    if sub == "gc":
        prune_set = any(a.lower().startswith(("--prune=", "--expire=")) for a in rest)  # mọi hạn tường minh (`--prune=1.second.ago`), không chỉ `now`
        return "irreversible_delete" if prune_set or any(a == "--prune" and nxt.lower() in ("now", "all") for a, nxt in zip(rest, rest[1:])) else None
    if sub == "prune":
        low = [a.lower() for a in rest]
        return "irreversible_delete" if "now" in low or "--expire" in low or any(a.startswith("--expire=") for a in low) else None
    if sub == "update-ref":
        return "irreversible_delete" if "-d" in rest or "--delete" in rest else None
    if sub == "push":
        skip = False
        for a in rest:
            if skip:
                skip = False
            elif a in ("-o", "--push-option", "--repo", "--receive-pack", "--exec"):
                skip = True
            elif a in ("--delete", "--mirror", "--prune") or a.startswith("--force") or _cluster(a, "fd") or a[:1] in (":", "+"):
                return "irreversible_delete"
        return None
    if sub == "branch":
        deleting = "--delete" in rest or any(_cluster(a, "d") for a in rest)
        forced = "--force" in rest or any(_cluster(a, "f") for a in rest)
        return "irreversible_delete" if any(_cluster(a, "D") for a in rest) or (deleting and forced) else None
    return None


def _delete_parts(name: str, args: list[str]) -> tuple[bool, list[str]]:
    """(có cờ đệ quy?, đích). Nhận `rm` kiểu POSIX (cụm cờ chứa r/R, `--recursive`), PowerShell (`-r…` viết tắt của -Recurse), `/s` của cmd;
    đích lấy từ `_ps_split` (đối số vị trí, `-Path`, `-LiteralPath`, cả dạng dính `-Path:x`)."""
    recursive = False
    for arg in args:
        low = arg.lower()
        if arg == "--":
            break
        if low in ("/s", "/q") and name in ("rmdir", "rd", "del", "erase"):
            recursive = recursive or low == "/s"
        elif arg.startswith("-") and len(arg) > 1:
            if low == "--recursive":
                recursive = True
            elif name == "rm" and re.fullmatch(r"-[rRfivIdPx]+", arg):
                recursive = recursive or "r" in low
            elif re.fullmatch(r"-r[a-z]*(:.*)?", low):
                recursive = True
    return recursive, [value for _, value in _ps_split([name] + args).src]


def _changes_dir(name: str, token: str) -> bool:
    """`env -C dir`/`env -Cdir`/`env --chdir[=dir]`/`sudo -D dir`/`sudo -Ddir`/`sudo --chdir[=dir]` (cả viết tắt `--ch…` của GNU)."""
    short = {"env": "-C", "sudo": "-D"}.get(name)
    if short is None:
        return False
    return token.startswith(short) or token.startswith("--ch") or bool(re.fullmatch(r"-[A-Za-z]+" + short[1], token))


def _chdir_value(name: str, token: str, following: str) -> str:
    """Thư mục mà `env -C`/`--chdir`, `sudo -D`/`--chdir` đổi tới: dạng `--chdir=dir`, `--chdir dir`, `-Cdir`, `-C dir`, cụm `-iC dir`."""
    if token.startswith("--"):
        return token.partition("=")[2] if "=" in token else following
    short = {"env": "C", "sudo": "D"}[name]
    if token == "-" + short or token.endswith(short) and re.fullmatch(r"-[A-Za-z]+", token):
        return following
    return token[2:]


def _strip_prefixes(tokens: list[str], ctx: Context) -> tuple[list[str], bool]:
    """Bỏ tiền tố kèm cờ/đối số của nó (`timeout 60`, `env -i VAR=x`, `sudo -u x`, `nice -n 5`, `xargs -0`…).
    Trả (token còn lại, có gán GIT_DIR/GIT_WORK_TREE?)."""
    redirected = False
    while tokens:
        head = tokens[0]
        assign = ENV_ASSIGN.match(head)
        if assign:
            redirected = redirected or assign.group(1) in GIT_DIR_VARS
            tokens = tokens[1:]
            continue
        if head.lower() in LEAD_WORDS:
            tokens = tokens[1:]
            continue
        name = _exe_name(head)
        if name not in PREFIXES:
            break
        value_opts, positional = PREFIXES[name]
        index = 1
        while index < len(tokens):
            token = tokens[index]
            if token == "--":
                index += 1
                break
            if name == "env" and token == "-S" and index + 1 < len(tokens):  # env -S "git push": chuỗi là lệnh
                tokens = tokenize(tokens[index + 1]) + tokens[index + 2:]
                index = 0
                break
            assign = ENV_ASSIGN.match(token)
            if assign and name in ("env", "sudo"):
                redirected = redirected or assign.group(1) in GIT_DIR_VARS
                index += 1
            elif token.startswith("-") and len(token) > 1:
                if _changes_dir(name, token):  # env -C/--chdir, sudo -D/--chdir (mọi dạng, kể cả dính): đổi thư mục như cd
                    target = _chdir_value(name, token, tokens[index + 1] if index + 1 < len(tokens) else "")
                    if target and _state_ref(target, ctx, ancestor=True):  # TK6h RF1: như `cd` tới thư mục trạng thái hay tổ tiên của nó
                        ctx.state_cd = True
                    ctx.enter()
                    cluster = bool(re.fullmatch(r"-[A-Za-z]+" + ("C" if name == "env" else "D"), token))
                    index += 2 if token in CHDIR_OPTIONS[name] or cluster else 1
                else:
                    takes = token in value_opts or (bool(re.fullmatch(r"-[A-Za-z]{2,}", token)) and "-" + token[-1] in value_opts)
                    index += 2 if takes else 1
            else:
                break
        else:
            tokens = []
            break
        if index == 0:
            continue
        tokens = tokens[index + positional:]
    return tokens, redirected


def _find_item(args: list[str], ctx: Context, depth: int) -> str | None:
    if "-delete" in args:
        return "irreversible_delete"
    starts: list[str] = []
    for arg in args:
        if arg.startswith("-") or arg in ("(", ")", "!", ","):
            break
        starts.append(arg)
    for index, arg in enumerate(args):
        if arg in FIND_EXEC:
            rest = args[index + 1:]
            item = _segment_item(rest, ctx, depth)
            if item:
                return item
            stripped, _ = _strip_prefixes(list(rest), Context(set(), ctx.cwd, light=True))
            if stripped and not _read_only(_exe_name(stripped[0]), stripped[1:], ctx):
                if any(_covers_state(t, ctx) for t in (starts or ["."])):
                    return TAMPER
            if stripped and _exe_name(stripped[0]) in DELETE_COMMANDS:  # `find … -exec rm {} +`: mọi điểm bắt đầu phải nằm trong `.tmp/`
                if ctx.cwd_changed or not all(tmp_target_ok(t, ctx) for t in (starts or ["."])):
                    return "irreversible_delete"
            return None
    return None


def _writes_file(name: str, args: list[str]) -> bool:
    """TK6h RF2: lệnh nằm trong danh sách chỉ-đọc nhưng cờ hay đối số làm nó GHI file: `sort -o`/`--output`, `uniq vào ra`, `xxd vào ra` (và `-r`),
    `find -fprint*`/`-fls`, `awk -i inplace`/`print > file`/`system(…)`. Lệnh bị loại khỏi nhóm chỉ-đọc nên đối số trỏ vào thư mục trạng thái bị chặn."""
    positional = [a for a in args if not a.startswith("-")]
    if name == "sort":
        return any(a == "--output" or a.startswith("--output=") or (re.fullmatch(r"-[A-Za-z]+", a) is not None and "o" in a) for a in args)
    if name in ("uniq", "xxd"):
        return len(positional) >= 2
    if name == "find":
        return any(a.lower() in FIND_WRITE for a in args)
    if name == "awk":
        return any(re.fullmatch(r"-i\w*", a) or "inplace" in a or ">" in a or "system" in a for a in args)
    return False


def _git_writes_file(args: list[str]) -> bool:
    """`git diff|log|show --output=<file>` (cũng `--output <file>`) ghi kết quả ra file."""
    return any(a == "--output" or a.startswith("--output=") for a in args)


def _read_only(name: str, args: list[str], ctx: Context) -> bool:
    if name in READ_ONLY_COMMANDS:
        return not _writes_file(name, args)
    if name == "sed":
        return not any(a == "--in-place" or a.startswith("--in-place=") or (a.startswith("-") and _cluster(a.split("=")[0], "i")) or a.startswith("-i") for a in args)
    if name == "git":
        return _git_parse(args)[0] in READ_ONLY_GIT and not _git_writes_file(args)
    return False


_COLON_FLAG = re.compile(r"-([a-z]+):(.*)", re.IGNORECASE | re.DOTALL)


def _colon_value(token: str, names: str) -> str | None:
    """Giá trị của cờ PowerShell dạng dính `-Tên:giá-trị` khi tên khớp mẫu `names` (không phân biệt hoa thường); không khớp → None."""
    found = _COLON_FLAG.fullmatch(token)
    if found and re.fullmatch(names, found.group(1).lower()):
        return found.group(2).strip("'\"")
    return None


def _arg_value(token: str) -> str:
    """Đường thật của một đối số: bỏ phần `-Destination:`/`-Path:`/`-LiteralPath:` dính liền nếu có."""
    value = _colon_value(token, r"dest[a-z]*|path|p[a-z]*|literalpath|lit[a-z]*")
    return token if value is None else value


_PS_COMMON_VALUES = ("erroraction", "warningaction", "informationaction", "errorvariable", "warningvariable", "informationvariable",
                     "outvariable", "outbuffer", "pipelinevariable")
_PS_COMMON_SWITCHES = ("verbose", "debug")
_PS_PARAMS = {  # loại cmdlet → (tham số CÓ giá trị, cờ công tắc)
    "remove": (("path", "literalpath", "filter", "include", "exclude", "stream", "credential"), ("recurse", "force", "confirm", "whatif", "usetransaction")),
    "move": (("path", "literalpath", "destination", "filter", "include", "exclude", "credential"), ("force", "passthru", "confirm", "whatif", "usetransaction")),
    "rename": (("path", "literalpath", "newname", "credential"), ("force", "passthru", "confirm", "whatif", "usetransaction")),
    "copy": (("path", "literalpath", "destination", "filter", "include", "exclude", "credential", "fromsession", "tosession"),
             ("container", "force", "passthru", "recurse", "confirm", "whatif", "usetransaction")),
}
_PS_ALIASES = {"ea": "erroraction", "wa": "warningaction", "ia": "informationaction", "ev": "errorvariable", "wv": "warningvariable",
               "iv": "informationvariable", "ov": "outvariable", "ob": "outbuffer", "pv": "pipelinevariable", "lp": "literalpath",
               "pspath": "path", "cf": "confirm", "wi": "whatif", "db": "debug", "vb": "verbose"}
_PS_KIND = {**dict.fromkeys(("rm", "ri", "del", "erase", "rmdir", "rd", "remove-item"), "remove"),
            **dict.fromkeys(("mv", "mi", "move", "move-item"), "move"),
            **dict.fromkeys(("ren", "rename", "rni", "rename-item"), "rename"),
            **dict.fromkeys(("cp", "cpi", "copy", "copy-item"), "copy")}


def _ps_param(kind: str, word: str) -> str | None:
    """Tên tham số PowerShell đầy đủ cho `-word` (khớp tiền tố duy nhất, không phân biệt hoa thường, hay bí danh); mơ hồ hay lạ → None."""
    low = _PS_ALIASES.get(word.lower(), word.lower())
    values, switches = _PS_PARAMS[kind]
    names = values + switches + _PS_COMMON_VALUES + _PS_COMMON_SWITCHES
    if low in names:
        return low
    found = [n for n in names if n.startswith(low)]
    return found[0] if len(found) == 1 else None


class _PsArgs:
    """Kết quả phân tích tham số của rm/mv/ren/cp và cmdlet tương ứng. Mỗi mục là (vị trí token, giá trị): `src` NGUỒN, `dst` ĐÍCH,
    `new` TÊN MỚI (Rename-Item), `other` mọi giá trị còn lại đã tiêu thụ (Include/Filter/Exclude/…: vẫn xét như thứ có thể thuộc `.git`)."""

    def __init__(self, kind: str | None) -> None:
        self.kind = kind
        self.src: list[tuple[int, str]] = []
        self.dst: list[tuple[int, str]] = []
        self.new: list[tuple[int, str]] = []
        self.other: list[tuple[int, str]] = []


def _ps_split(tokens: list[str]) -> _PsArgs:
    """MỘT bộ phân tích tham số cho mọi cmdlet xoá/chuyển/đổi tên/chép (và bí danh, bản POSIX): nhận `-Tên:giá-trị` và `-Tên giá-trị`
    (tiền tố duy nhất, hoa thường tuỳ ý; nháy đã bị `tokenize` bỏ), `-t`/`--target-directory`; tách tham số có giá trị khỏi cờ công tắc
    để suy ra NGUỒN, ĐÍCH, TÊN MỚI. Tiền tố mơ hồ (`-f`, `-p`) coi là cờ công tắc: token sau vẫn là đối số vị trí (chặn thừa, không hở)."""
    kind = _PS_KIND.get(_exe_name(tokens[0])) if tokens else None
    parts = _PsArgs(kind)
    if kind is None:
        return parts
    values = _PS_PARAMS[kind][0] + _PS_COMMON_VALUES
    cmd_flags = _exe_name(tokens[0]) in ("rmdir", "rd", "del", "erase")
    positional: list[tuple[int, str]] = []
    literal = False
    index = 1
    while index < len(tokens):
        token, low = tokens[index], tokens[index].lower()
        if literal:
            positional.append((index, token))
        elif token == "--":
            literal = True
        elif low in ("-t", "--target-directory") and index + 1 < len(tokens):
            index += 1
            parts.dst.append((index, tokens[index]))
        elif low.startswith("--target-directory="):
            parts.dst.append((index, token.split("=", 1)[1]))
        elif cmd_flags and low in ("/s", "/q"):
            pass
        elif token.startswith("--") or (token.startswith("-") and len(token) > 1):
            found = None if token.startswith("--") else _COLON_FLAG.fullmatch(token)
            canon = None if token.startswith("--") else _ps_param(kind, found.group(1) if found else token[1:])
            value = found.group(2).strip("'\"") if found else None
            at = index
            if value is None and canon in values and index + 1 < len(tokens):
                index += 1
                value, at = tokens[index], index
            if value is not None:
                bucket = parts.dst if canon == "destination" else parts.new if canon == "newname" else \
                    parts.src if canon in ("path", "literalpath", None) else parts.other
                bucket.append((at, value))
        else:
            positional.append((index, token))
        index += 1
    if kind == "rename":  # chỗ trống theo thứ tự: Path rồi NewName (bỏ chỗ đã gán bằng tên); thừa → coi là nguồn
        for item in positional:
            if not parts.src:
                parts.src.append(item)
            elif not parts.new:
                parts.new.append(item)
            else:
                parts.src.append(item)
    elif kind == "remove":
        parts.src += positional
    elif positional and not parts.dst:  # move/copy: đối số vị trí cuối là ĐÍCH nếu chưa có `-Destination`/`-t`; một mình thì vừa nguồn vừa đích (chặn thừa)
        parts.dst.append(positional[-1])
        parts.src += positional[:-1] or ([positional[-1]] if not parts.src else [])
    else:
        parts.src += positional
    return parts


def _copy_destinations(tokens: list[str]) -> set[int]:
    """Vị trí token là ĐÍCH của cp/Copy-Item/Move-Item (`-Destination`, `-t`, hay đối số vị trí cuối), theo `_ps_split`."""
    return {index for index, _ in _ps_split(tokens).dst}


def _heredoc_marks(line: str, quote: str) -> tuple[list["re.Match[str]"], str]:
    """Các `<<`/`<<-` (không phải `<<<`) nằm NGOÀI nháy đơn/kép và ngoài comment `#` của một dòng; trả kèm trạng thái nháy
    còn mở cuối dòng (chuỗi nhiều dòng)."""
    marks: list["re.Match[str]"] = []
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\" and quote == '"':
                index += 2
                continue
            if char == quote:
                quote = ""
            index += 1
        elif char in "'\"":
            quote = char
            index += 1
        elif char == "\\":
            index += 2
        elif char == "#" and (index == 0 or line[index - 1].isspace()):
            break
        elif line.startswith("<<<", index):
            index += 3
        elif line.startswith("<<", index):
            mark = HEREDOC.match(line, index)
            marks.append(mark) if mark else None
            index = mark.end() if mark else index + 2
        else:
            index += 1
    return marks, quote


def _substitutions(body: str) -> list[str]:
    """Nội dung các `$(…)`, `<(…)`, `>(…)` (ngoặc cân bằng, bỏ `$((…))`) và cặp dấu huyền trong `body`: thứ shell sẽ chạy khi mở rộng thân heredoc."""
    found: list[str] = []
    index = 0
    while index < len(body):
        if body.startswith(("$(", "<(", ">("), index) and not body.startswith("$((", index):
            depth, end = 1, index + 2
            while end < len(body) and depth:
                depth += (body[end] == "(") - (body[end] == ")")
                end += 1
            found.append(body[index + 2:end - 1 if depth == 0 else end])
            index = end
        elif body[index] == "`":
            end = body.find("`", index + 1)
            end = len(body) if end < 0 else end
            found.append(body[index + 1:end])
            index = end + 1
        else:
            index += 1
    return found


def _pipes_into_interpreter(rest: str) -> bool:
    """Phần còn lại của dòng sau `<<` có ống dẫn vào trình thông dịch (`| python`, `| sudo node -`)?"""
    for stage_text in PIPE.split(rest)[1:]:
        stage, _ = _strip_prefixes(tokenize(re.split(r"&&|;|\n|\|\|", stage_text)[0]), Context(set(), ".", light=True))
        if stage and _interpreter_name(_exe_name(stage[0])):
            return True
    return False


def _strip_heredoc_bodies(text: str, interpreters: bool = False) -> str:
    """Thân heredoc đưa vào trình thông dịch không phải shell (`python -`, `node -`, `cat >`) là dữ liệu, không phân tích như lệnh;
    đưa vào `bash`/`sh`/`pwsh`/eval (kể cả `cat <<EOF | bash`) thì giữ lại để xét như lệnh lồng. Chỉ nhận `<<` ngoài nháy và comment;
    heredoc không có dòng kết thúc khớp đúng nhãn thì giữ nguyên thân để phân tích. `interpreters` (TK6e RF1): giữ cả thân đưa vào `python`/`node`/`perl`…
    (cho luật tìm đường thư mục trạng thái trong mã). Nhãn không nháy (`<<X`, `<<-X`): shell vẫn mở rộng
    `$(…)` và dấu huyền trong thân nên các lệnh đó được trích ra phân tích; nhãn có nháy (`<<'X'`, `<<"X"`, `<<\\X`) thì bỏ hẳn thân."""
    lines = text.split("\n")
    out: list[str] = []
    index = 0
    quote = ""
    while index < len(lines):
        _tick()
        line = lines[index]
        out.append(line)
        index += 1
        marks, quote = _heredoc_marks(line, quote)
        if not marks:
            continue
        stage, _ = _strip_prefixes(tokenize(SEPARATORS.split(line[:marks[0].start()])[-1]), Context(set(), ".", light=True))
        reads_shell = bool(stage) and (_exe_name(stage[0]) in SHELL_WRAPPERS | EVAL_COMMANDS or (interpreters and _interpreter_name(_exe_name(stage[0]))))
        reads_shell = reads_shell or bool(PIPE_INTO_SHELL.search(line[marks[-1].end():]))
        reads_shell = reads_shell or (interpreters and _pipes_into_interpreter(line[marks[-1].end():]))  # TK6h RF3: `cat <<EOF | python` (thân là mã, không phải dữ liệu)
        for mark in marks:
            delimiter = mark.group(2) or mark.group(3) or mark.group(4)
            body: list[str] = []
            closed = False
            while index < len(lines):
                current = lines[index]
                index += 1
                if (current.lstrip("\t") if mark.group(1) else current).rstrip("\r") == delimiter:
                    closed = True
                    break
                body.append(current)
            if reads_shell or not closed:
                out.extend(body)
            elif "\\" not in mark.group(0) and not (mark.group(2) or mark.group(3)):
                out.extend(_substitutions("\n".join(body)))  # nhãn không nháy: shell mở rộng $(…) và dấu huyền trong thân
    return "\n".join(out)


def _join_and_strip(text: str, interpreters: bool = False) -> str:
    """Nối dòng (dấu gạch ngược hay dấu huyền + xuống dòng) TRƯỚC khi dò heredoc (để `bash` + gạch ngược + xuống dòng + `<<EOF` vẫn thấy `bash`), bỏ thân heredoc
    của trình không phải shell, rồi nối dòng thêm một lần cho phần còn lại. Hệ quả chấp nhận: dấu huyền/gạch ngược cuối dòng trong thân
    heredoc có nháy cũng bị nối, nên thân đó có thể không còn dòng kết thúc riêng và bị phân tích (chặn nhầm, an toàn)."""
    return LINE_CONTINUATION.sub(" ", _strip_heredoc_bodies(LINE_CONTINUATION.sub(" ", text), interpreters))


def _in_tmp_name(path: str) -> bool:
    """Đường có thành phần `.tmp` (đích chuyển/chép vào vùng tạm)."""
    return ".tmp" in [c.lower() for c in path.replace("\\", "/").split("/")]


def _is_git_path(path: str) -> bool:
    """Đích xoá thuộc `.git`: có thành phần đúng `.git`, hay glob khớp `.git` (bắt đầu bằng dấu chấm như `.g*`, hoặc có từ 3 ký tự thường như
    `?git`, `[.]git`; glob chỉ toàn ký tự đại diện như `*` không tính)."""
    for comp in path.replace("\\", "/").split("/"):
        low = comp.lower()
        if low == ".git":
            return True
        if GLOB_CHARS & set(low) and fnmatch.fnmatchcase(".git", low):
            if low.startswith(".") or len(low.translate({ord(c): None for c in "*?[]"})) >= 3:
                return True
    return False


def _moves_into_tmp(tokens: list[str]) -> bool:
    """`mv`/`move`/`Move-Item`/`ren`/`Rename-Item`/`robocopy`, hay `cp -r`/`Copy-Item -Recurse`, có ĐÍCH dưới `.tmp/`: chuyển/chép cây vào vùng tạm
    rồi xoá ở đó là cách đưa `.git` hay file đang theo dõi ra khỏi cây mà không bị coi là xoá ngoài `.tmp/`."""
    if not tokens:
        return False
    name, args = _exe_name(tokens[0]), tokens[1:]
    if name == "robocopy":
        positional = [a for a in args if not ROBOCOPY_FLAG.fullmatch(a) and not a.startswith("-")]
        return len(positional) > 1 and _in_tmp_name(positional[1])
    if name in COPY_RECURSIVE_NAMES:
        flags = [a for a in args if a.startswith("-")]
        if name == "cp":
            recursive = any(re.fullmatch(r"-[A-Za-z]*[rRa][A-Za-z]*", a) or a.lower() == "--recursive" for a in flags)
        else:
            recursive = any(re.fullmatch(r"-r[a-z]*", a.lower()) for a in flags)
        if not recursive:
            return False
    elif name not in MOVE_COMMANDS:
        return False
    parts = _ps_split(tokens)
    if parts.kind == "rename":  # đổi tên cây nằm trong `.tmp/` (hay thành tên trong `.tmp/`) tính như chuyển trong vùng tạm
        return any(_in_tmp_name(value) for _, value in parts.src + parts.new)
    return any(_in_tmp_name(value) for _, value in parts.dst)


def _git_source_moved(tokens: list[str]) -> bool:
    """`mv`/`move`/`Move-Item`/`ren`/`Rename-Item`/`robocopy` có NGUỒN thuộc `.git`: đưa cơ chế hoàn tác ra khỏi cây ngay cả khi đích không ở
    `.tmp/` hay phần xoá nằm ở lệnh riêng (`mv .git .tmp/x/g`, rồi `rm -rf .tmp/x`). Sao chép (`cp`, `Copy-Item`) không tính: nguồn còn nguyên;
    sao chép vào `.tmp/` rồi xoá ở đó đã bị `_moves_into_tmp` chặn."""
    if not tokens:
        return False
    name, args = _exe_name(tokens[0]), tokens[1:]
    if name == "robocopy":
        positional = [a for a in args if not ROBOCOPY_FLAG.fullmatch(a) and not a.startswith("-")]
        return bool(positional) and _is_git_path(positional[0])
    if name not in MOVE_COMMANDS:
        return False
    parts = _ps_split(tokens)
    checked = parts.src + parts.other + (parts.new if parts.kind == "rename" else [])  # tên mới là `.git` = thay `.git`; đích của mv thì không tính
    return any(_is_git_path(value) for _, value in checked)


def _recursive_listing(name: str, args: list[str]) -> list[str] | None:
    """`Get-ChildItem`/`gci`/`ls`/`dir` có cờ đệ quy: danh sách đường nó liệt kê (rỗng = thư mục hiện tại); không phải → None."""
    if name not in LISTING_COMMANDS:
        return None
    if not any(a.startswith("-") and re.fullmatch(r"-r[a-z]*", a.lower()) for a in args):
        return None
    return [a for a in args if not a.startswith("-")]


def _robocopy_purge_item(args: list[str], ctx: Context) -> str | None:
    """`robocopy … /MIR` (hay `/PURGE`) xoá ở đích mọi thứ không có ở nguồn: chỉ cho qua khi đích nằm trong `.tmp/`."""
    if not any(a.lower() in ("/mir", "/purge") for a in args):
        return None
    positional = [a for a in args if not ROBOCOPY_FLAG.fullmatch(a) and not a.startswith("-")]
    if len(positional) > 1 and not ctx.cwd_changed and tmp_target_ok(positional[1], ctx):
        return None
    return "irreversible_delete"


def _segment_item(tokens: list[str], ctx: Context, depth: int) -> str | None:
    tokens, _ = _strip_prefixes(tokens, ctx)
    if ctx.state_cd:
        return TAMPER
    if not tokens:
        return None
    item = _tamper_item(tokens, ctx) or _command_item(tokens, ctx, depth)
    if _moves_into_tmp(tokens):
        ctx.tmp_moved = True  # từ đây phần xoá phía sau (cùng chuỗi) không còn ngoại lệ dọn `.tmp/`
    return item


def _nested_string(text: str, ctx: Context, depth: int) -> str | None:
    """Chuỗi được đưa vào shell (eval, ống vào bash): xét như lệnh lồng; lồng quá MAX_UNWRAP lớp thì chặn."""
    if not text.strip():
        return None
    if depth >= MAX_UNWRAP:
        return NESTED
    return _analyze(text, ctx, depth + 1)


def _pipe_to_shell(text: str, ctx: Context, depth: int) -> str | None:
    """`echo "git push" | bash`: vế trước ống (bỏ tên lệnh đầu) là chuỗi đưa vào shell."""
    parts = PIPE.split(text)
    for index in range(1, len(parts)):
        stage, _ = _strip_prefixes(tokenize(re.split(r"&&|;|\n", parts[index])[0]), Context(set(), ctx.cwd, light=True))
        if not stage:
            continue
        name = _exe_name(stage[0])
        takes_script = any(a.lower() in WRAPPER_FLAGS or re.fullmatch(r"-[a-z]*c[a-z]*", a) for a in stage[1:])
        if (name in SHELL_WRAPPERS or name in EVAL_COMMANDS) and not takes_script:
            source = tokenize(re.split(r"&&|;|\n|\|\|", parts[index - 1])[-1])
            item = _nested_string(" ".join(source[1:]), ctx, depth)
            if item:
                return item
    return None


def _command_item(tokens: list[str], ctx: Context, depth: int) -> str | None:
    name, args = _exe_name(tokens[0]), tokens[1:]
    if name in CD_COMMANDS:
        ctx.enter()
        ctx.in_git = ctx.in_git or any(_is_git_path(_arg_value(a)) for a in args)
        return None
    if name in EVAL_COMMANDS:
        return _nested_string(" ".join(args), ctx, depth)
    if name in SHELL_WRAPPERS:
        if "<<<" in args and args.index("<<<") + 1 < len(args):  # bash <<< "git push"
            return _nested_string(" ".join(args[args.index("<<<") + 1:]), ctx, depth)
        for index, arg in enumerate(args):
            if arg.lower() in WRAPPER_FLAGS or re.fullmatch(r"-[a-z]*c[a-z]*", arg):
                return _analyze(" ".join(args[index + 1:]), ctx, depth + 1) if depth < MAX_UNWRAP else NESTED
        return None
    if name == "busybox" and args:  # `busybox rm -rf x`: applet là lệnh thật
        return _command_item(args, ctx, depth)
    if name == "git":
        return _git_item(args, ctx)
    if name == "find":
        return _find_item(args, ctx, depth)
    if _git_source_moved(tokens):
        return "irreversible_delete"
    if ctx.in_git and (name in DELETE_COMMANDS or name in MOVE_COMMANDS):  # `cd .git && rm objects/pack/*`: đường tương đối trỏ vào `.git`
        return "irreversible_delete"
    if name == "robocopy":
        return _robocopy_purge_item(args, ctx)
    if name in DELETE_COMMANDS:
        recursive, targets = _delete_parts(name, args)
        if any(_is_git_path(t) for t in targets + [v for _, v in _ps_split(tokens).other]):  # xoá thứ thuộc `.git` (kể cả không đệ quy): phá cơ chế hoàn tác
            return "irreversible_delete"
        if not recursive:
            return None
        if targets and not ctx.cwd_changed and not ctx.tmp_moved and all(tmp_target_ok(t, ctx) for t in targets):
            return None
        return "irreversible_delete"
    return None


def _analyze(text: str, ctx: Context, depth: int = 0) -> str | None:
    """Mục loại đầu tiên mà `text` (có thể là lệnh ghép) vi phạm và đang bật; None nếu không."""
    text = _join_and_strip(text)  # nối dòng `git \` + xuống dòng; bỏ thân heredoc của trình không phải shell
    item = _pipe_to_shell(text, ctx, depth)
    if item:
        return item
    if "irreversible_delete" in ctx.active and IO_DELETE.search(text):  # `[IO.Directory]::Delete(…, $true)`, `(Get-Item x).Delete($true)`: không đọc được đích
        return "irreversible_delete"
    parts = SEP_KEEP.split(text)  # [lệnh, dấu ngăn, lệnh, …]
    listing: list[str] | None = None  # đường mà một `Get-ChildItem -Recurse` phía trước ống dẫn đang liệt kê
    state_listed = False  # câu ngay trước ống dẫn liệt kê thư mục trạng thái hay thư mục bao nó (`ls <S>* | xargs rm`, TK6e RF2)
    for index in range(0, len(parts), 2):
        _tick()
        if index and parts[index - 1] in CHAIN_BREAKS:
            listing = None
        piped_from_state = state_listed and index > 0 and parts[index - 1] == "|"
        state_listed = False
        tokens = tokenize(parts[index])
        item = _segment_item(list(tokens), ctx, depth)
        stripped, _ = _strip_prefixes(list(tokens), Context(set(), ctx.cwd, light=True))
        if stripped and not item:
            name = _exe_name(stripped[0])
            if piped_from_state and (name in DELETE_COMMANDS or name in MOVE_COMMANDS):
                return TAMPER
            lists = name in LISTING_COMMANDS or name == "find" or name in ("get-item", "gi")
            state_listed = lists and any(_state_ref(a, ctx, ancestor=True) for a in stripped[1:] if not a.startswith("-"))
            paths = _recursive_listing(name, stripped[1:])
            if paths is not None:
                listing = paths
            elif listing is not None and name in DELETE_COMMANDS and not _delete_parts(name, stripped[1:])[1]:
                if not (listing and not ctx.cwd_changed and all(tmp_target_ok(t, ctx) for t in listing)):
                    item = "irreversible_delete"  # `Get-ChildItem … -Recurse | Remove-Item`: xoá đệ quy qua ống dẫn
        if item and (item in SPECIAL_ITEMS or item in ctx.active):
            return item
    return None


# --- sự kiện ----------------------------------------------------------------------------------------------------

def _commands(payload: dict) -> list[str]:
    """Mọi chuỗi lệnh ứng viên (khoá của ba host); danh sách `["bash","-lc","<script>"]` của Codex thì lấy phần script."""
    found: list[str] = []
    containers = []
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        containers.append(tool_input)
    call = payload.get("toolCall")
    if isinstance(call, dict) and isinstance(call.get("args"), dict):
        containers.append(call["args"])
    for container in containers:
        for key in COMMAND_KEYS:
            value = container.get(key)
            if isinstance(value, str):
                found.append(value)
            elif isinstance(value, list) and value and all(isinstance(v, str) for v in value):
                wrapped = len(value) >= 3 and _exe_name(value[0]) in SHELL_WRAPPERS and value[1].lower() in WRAPPER_FLAGS
                found.append(" ".join(value[2:]) if wrapped else " ".join(value))
    return found


def _tool_name(payload: dict) -> str | None:
    name = payload.get("tool_name")
    call = payload.get("toolCall")
    if name is None and isinstance(call, dict):
        name = call.get("name")
    return name if isinstance(name, str) else None


def _event_dirs(payload: dict) -> tuple[str, str]:
    """(thư mục chạy lệnh, thư mục phiên). Thư mục lệnh: khoá cấp công cụ (`workdir`, `cwd`, `Cwd`) trước, rồi `cwd` của phiên,
    rồi thư mục tiến trình; khoá tương đối ghép với thư mục phiên."""
    session = payload.get("cwd") if isinstance(payload.get("cwd"), str) and payload.get("cwd") else None
    sources = []
    if isinstance(payload.get("tool_input"), dict):
        sources.append(payload["tool_input"])
    call = payload.get("toolCall")
    if isinstance(call, dict) and isinstance(call.get("args"), dict):
        sources.append(call["args"])
    tool = None
    for source in sources:
        for key in CWD_KEYS:
            if isinstance(source.get(key), str) and source[key]:
                tool = source[key]
                break
        if tool:
            break
    if tool and session and not os.path.isabs(tool):
        tool = os.path.join(session, tool)
    command_dir = tool or session or os.getcwd()
    return command_dir, session or command_dir


def _write_paths(payload: dict) -> list[str]:
    """Đường đích của công cụ ghi file: giá trị chuỗi ở khoá đường (mọi độ sâu) cộng dòng vá của Codex."""
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in PATH_KEYS and isinstance(value, str):
                    found.append(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str):
            for line in node.splitlines():
                line = line.lstrip()
                for prefix in PATCH_PREFIXES:
                    if line.startswith(prefix):
                        found.append(line[len(prefix):].strip())

    walk(payload)
    return found


def _deny(fmt: str, reason: str, stdout: TextIO, stderr: TextIO) -> int:
    if fmt == "antigravity":
        stdout.write(json.dumps({"decision": "deny", "reason": reason}, ensure_ascii=False) + "\n")
        return 0
    stderr.write(reason + "\n")
    return 2


def _allow(fmt: str, stdout: TextIO) -> int:
    if fmt == "antigravity":
        stdout.write("{}\n")
    return 0


def reason_for(item: str, broken: bool) -> str:
    if item == TAMPER:
        return "agile: công tắc agile là rào — chỉ người dùng gõ /agile stop mới tắt được; lệnh không chạy"
    if item == DEADLINE:
        return "agile: guard deadline: command too long to check — lệnh không chạy"
    if item == NESTED:
        return "agile: lệnh lồng quá {} lớp shell, không phân tích được — cần người dùng nói trong chat — lệnh không chạy".format(MAX_UNWRAP)
    lead = "agile: trạng thái hỏng, " if broken else "agile: "
    return "{}'{}' cần người dùng nói trong chat — lệnh không chạy".format(lead, item)


class _Failed(Exception):
    """Ngoại lệ sau khi đã đọc được sự kiện: mang nhãn để in lý do."""

    def __init__(self, label: str, dirs: tuple[str, ...] = ()) -> None:
        super().__init__(label)
        self.label = label
        self.dirs = dirs


def _evaluate(raw: str, notes: list[str]) -> str | None:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("payload is not an object")
    dirs: tuple[str, ...] = ()
    try:
        dirs = _event_dirs(payload)
        command_dir, session_dir = dirs
        _legacy_notice(dirs, notes)
        found = activation(payload, (session_dir, command_dir))
        if found is None:
            return None  # agile TẮT và trạng thái lành: thoát ngay
        active, broken, state_dirs = found
        name = _tool_name(payload)
        if name is not None and name.lower() in WRITE_TOOLS:
            scratch = Context(set(), command_dir, state_dirs)
            if any(_state_ref(p, scratch) for p in _write_paths(payload)):
                return reason_for(TAMPER, broken)
            return None
        if name is not None and name.lower() not in SHELL_TOOLS:
            return None
        for text in _commands(payload):
            context = Context(active, command_dir, state_dirs, session_dir)
            if _raw_tamper(text) or _raw_state_tamper(text, context):
                return reason_for(TAMPER, broken)
            item = _analyze(text, context)
            if item:
                return reason_for(item, broken)
        return None
    except _Deadline:
        raise
    except Exception as exc:
        raise _Failed(type(exc).__name__, dirs) from exc


def _unparsed_reason(label: str, raw: str, dirs: tuple[str, ...] = ()) -> str | None:
    """Đầu vào hỏng hay ngoại lệ: chặn nếu rào đang bật (hay không xác định được), không thì cho qua. `dirs`: thư mục sự kiện nếu đã biết."""
    try:
        if activation(_salvage(raw), dirs) is None:
            return None
    except Exception:  # noqa: BLE001 — không xác định được thì đóng
        pass
    return "agile: hook gặp lỗi ({}) khi agile đang bật — lệnh không chạy".format(label)


def main(argv: list[str] | None = None, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    parser = argparse.ArgumentParser(description="Rào máy agile (PreToolUse).")
    parser.add_argument("--format", choices=FORMATS, required=True)
    args = parser.parse_args(argv)
    debug = os.environ.get("AGILE_GUARD_DEBUG", "") not in ("", "0")
    reason = None
    raw = ""
    notes: list[str] = []
    global _deadline
    _deadline = time.monotonic() + deadline_seconds(os.environ)
    try:
        raw = stdin.read()
        reason = _evaluate(raw, notes)
    except _Deadline:
        reason = reason_for(DEADLINE, False)
    except _Failed as failed:
        if debug:
            import traceback  # lazy: debug only (SPR-32 B4 start-up cost)
            traceback.print_exc(file=stderr)
        reason = _unparsed_reason(failed.label, raw, failed.dirs)
    except Exception as exc:  # JSON hỏng, đầu vào không đọc được: vớt session_id bằng biểu thức chính quy
        if debug:
            import traceback  # lazy: debug only (SPR-32 B4 start-up cost)
            traceback.print_exc(file=stderr)
        reason = _unparsed_reason(type(exc).__name__, raw)
    finally:
        _deadline = None  # nội bộ main: test gọi hàm phân tích trực tiếp không bị hạn cũ làm hỏng
    if reason is None:
        for note in notes[:1]:  # một dòng nhắc file dấu cũ, không chặn
            stderr.write(note + "\n")
        return _allow(args.format, stdout)
    return _deny(args.format, reason, stdout, stderr)


def _format_arg(argv: list[str]) -> str:
    for index, arg in enumerate(argv):
        flag, equals, value = arg.partition("=")
        if len(flag) > 2 and "--format".startswith(flag):
            return value if equals else (argv[index + 1] if index + 1 < len(argv) else "")
    return ""


def _last_resort(argv: list[str]) -> int:  # pragma: no cover — lưới cuối khi chính `main` văng
    fmt = "antigravity" if _format_arg(argv) == "antigravity" else "claude"
    try:
        reason = _unparsed_reason("fatal", "")
        return _allow(fmt, sys.stdout) if reason is None else _deny(fmt, reason, sys.stdout, sys.stderr)
    except BaseException:  # noqa: BLE001
        return 0 if fmt == "antigravity" else 2


if __name__ == "__main__":  # pragma: no cover
    try:
        for stream in (sys.stdin, sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
        code = _last_resort(sys.argv) if sys.version_info < (3, 9) else main()  # Python quá cũ: chỉ xác định trạng thái, không phân tích
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001
        code = _last_resort(sys.argv)
    sys.exit(code)
