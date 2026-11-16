#!/usr/bin/env python3
"""Locale status and settings (SPR-33): which locale a sprint document set uses, and where it was chosen.

Usage:
    python scripts/locale_cli.py status [--root DIR] [--locale L] [--sprint-file FILE] [--non-interactive] [--json]
    python scripts/locale_cli.py set --scope user|repo --locale L [--root DIR] [--json]

Resolution (D5, implemented by _labels.resolve_locale): --locale, then the `locale` key in the front matter of
--sprint-file, then `locale` in the repo's .agile.json, then `locale` in the user config, then `vi`.

The user config is `user-config.json` in the agile state directory (the path comes from agile_state.state_dir(), so
AGENT_AGILE_STATE_DIR applies); keys `locale` and `locale_asked`. `status` reports `ask_needed` only when no layer
declares a locale, the user was never asked, and the session is interactive (none of AGENT_AGILE_NONINTERACTIVE or
CI is set, no --non-interactive). A non-interactive run resolves the locale and writes nothing. Answering, or going
on without an answer, is `set --scope user` (the no-answer path passes `vi`); it records locale_asked = true.

Writes are atomic (temp file in the same directory, then os.replace). A corrupt or unreadable user-config.json
resolves to `vi` and is reported in `problems`; `set --scope user` replaces it. `--scope repo` edits only the
`locale` key of an existing .agile.json and keeps every other key.

A non-interactive `set --scope user` (flag, CI or AGENT_AGILE_NONINTERACTIVE) writes nothing and exits 0 with
`written: false` and a reason, so a headless "no answer" never marks the user as asked. `set --scope repo` is a
deliberate configuration choice and is written in any session. It looks for .agile.json at --root and above it, but never past the
repository root (the first folder with .git; without any .git only --root itself counts), refuses with exit 2
otherwise, rewrites it with 2-space indent (keys and their order are kept, hand formatting is not), and replaces a symlinked
config with a regular file (os.replace swaps the link, not its target). A `locale` key that is JSON null in
.agile.json or in the user config counts as an invalid value (like config_problems), not as "not declared".

Exit codes: 0 ok, 1 I/O failure, 2 bad usage (unknown locale, no .agile.json for --scope repo, ...).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels  # noqa: E402
import agile_state  # noqa: E402

USER_CONFIG_NAME = "user-config.json"
CONFIG_NAME = ".agile.json"  # same name as _common.CONFIG_NAME; _common is not imported to keep start-up light
NONINTERACTIVE_ENV = ("AGENT_AGILE_NONINTERACTIVE", "CI")


class UsageError(Exception):
    """Bad input: exit code 2."""


_NULL_VALUE = "null"  # stands in for a JSON null so that resolve_locale skips it with a reason, never as "absent"


def _layer_value(data: dict):
    if "locale" not in data:
        return None
    value = data["locale"]
    return _NULL_VALUE if value is None else value


def user_config_path() -> Path:
    return agile_state.state_dir() / USER_CONFIG_NAME


def is_interactive(non_interactive_flag: bool = False, environ=None) -> bool:
    env = os.environ if environ is None else environ
    if non_interactive_flag:
        return False
    return not any(str(env.get(name) or "").strip() for name in NONINTERACTIVE_ENV)


def write_atomic(path: Path, text: str, mode: int = 0o600) -> None:
    """Write text (UTF-8, no BOM) next to its target and swap it in with os.replace; the original survives a failure.
    The temp file is created exclusively with `mode` (0o600 by default; a repo config passes its own mode)."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    # O_EXCL: never write through a file or link somebody else put at the temp name; a failed open removes nothing.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(tmp, flags, mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def read_user_config():
    """(dict, None) when readable or missing ({} for missing); ({}, problem text) when corrupt or unreadable."""
    path = user_config_path()
    try:
        data, problem = agile_state.read_json(path)
    except OSError as exc:
        return {}, f"{USER_CONFIG_NAME}: unreadable ({exc.__class__.__name__})"
    if problem:
        return {}, problem
    return (data or {}), None


def user_locale_value():
    """The raw `locale` of the user config (None when it declares none); a missing or corrupt file declares nothing."""
    data, _problem = read_user_config()
    return _layer_value(data)


def find_repo_config(start: Path):
    """Nearest .agile.json at or above start, or None (read-only lookups: `status`)."""
    current = start.resolve()
    for folder in (current, *current.parents):
        candidate = folder / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def _is_repo_root(folder: Path) -> bool:
    return (folder / ".git").exists()


def find_repo_config_bounded(start: Path):
    """The .agile.json that `set --scope repo` may rewrite: at `start`, or above it but not past the repository root (the
    first folder at or above `start` that holds `.git`). Without any `.git` only `start` itself counts, so the walk never
    reaches a home folder or another repository."""
    current = start.resolve()
    chain = [current]
    boundary = None
    for folder in (current, *current.parents):
        if _is_repo_root(folder):
            boundary = folder
            break
    if boundary is not None:
        chain = [f for f in (current, *current.parents) if f == boundary or boundary in f.parents]
    for folder in chain:
        candidate = folder / CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def read_repo_config(path: Path):
    """(dict, None) or ({}, problem text)."""
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as exc:
        return {}, f"{CONFIG_NAME}: unreadable or not valid JSON ({exc.__class__.__name__})"
    if not isinstance(data, dict):
        return {}, f"{CONFIG_NAME}: top level is not an object"
    return data, None


_FRONT_LOCALE = re.compile(r"^locale[ \t]*:[ \t]*(.*)$")  # applied to a right-stripped line (_front_locale): linear


def _front_locale(line: str):
    """The raw value of a `locale:` front matter line, without surrounding blanks; None when the line is another key."""
    match = _FRONT_LOCALE.match(line.rstrip(" \t"))
    return match.group(1) if match else None


def read_sprint_locale(path: Path):
    """The raw `locale` value of a document's front matter (None when absent); frozen at sprint open."""
    try:
        lines = path.read_bytes().decode("utf-8").split("\n")
    except (OSError, ValueError):
        raise UsageError(f"--sprint-file {str(path)[:80]!r} cannot be read")
    if not lines or lines[0].strip() != "---":
        return None
    found = None
    for line in lines[1:]:
        if line.strip() == "---":
            return found  # closed front matter
        value = _front_locale(line.rstrip("\r"))
        if value is not None and found is None:
            found = value.strip("'\"")
    return None  # never closed: what was read is body text, not front matter


def gather(args, interactive: bool) -> dict:
    """Everything `status` reports; reads only, never writes."""
    problems = []
    root = Path(args.root).resolve() if args.root else Path.cwd()
    explicit = args.locale
    if explicit is not None and not _labels.valid_locale(explicit):
        raise UsageError(f"--locale {explicit[:40]!r} is not shipped (shipped: {', '.join(_labels.shipped())})")
    sprint = read_sprint_locale(Path(args.sprint_file)) if args.sprint_file else None
    repo_path = find_repo_config(root)
    repo_value = None
    if repo_path is not None:
        repo_data, problem = read_repo_config(repo_path)
        if problem:
            problems.append(problem)
        repo_value = _layer_value(repo_data)
    state_problem = agile_state.state_dir_problem()
    if state_problem:
        problems.append(state_problem)
    user_data, problem = read_user_config()
    if problem:
        problems.append(problem)
    user_value = _layer_value(user_data)
    resolution = _labels.resolve_locale(explicit, sprint, repo_value, user_value)
    asked = user_data.get("locale_asked") is True
    ask_needed = resolution.source == "default" and not asked and interactive
    return {
        "locale": resolution.locale,
        "source": resolution.source,
        "ask_needed": ask_needed,
        "interactive": interactive,
        "locale_asked": asked,
        "ignored": [{"layer": layer, "value": value if isinstance(value, str) else repr(value)[:40], "reason": reason}
                    for layer, value, reason in resolution.ignored],
        "problems": problems,
        "shipped": list(_labels.shipped()),
        "user_config": str(user_config_path()),
        "repo_config": str(repo_path) if repo_path else None,
    }


def render_status(info: dict) -> str:
    lines = [f"locale: {info['locale']} (from {info['source']})",
             f"ask needed: {'yes' if info['ask_needed'] else 'no'} "
             f"(asked before: {'yes' if info['locale_asked'] else 'no'}, interactive: {'yes' if info['interactive'] else 'no'})",
             f"user config: {info['user_config']}",
             f"repo config: {info['repo_config'] or '(none found)'}"]
    for item in info["ignored"]:
        lines.append(f"ignored {item['layer']} value {item['value']!r}: {item['reason']}")
    for problem in info["problems"]:
        lines.append(f"problem: {problem}")
    return "\n".join(lines)


def do_set(args, interactive: bool = True) -> dict:
    locale = args.locale
    if not _labels.valid_locale(locale):
        raise UsageError(f"--locale {str(locale)[:40]!r} is not shipped (shipped: {', '.join(_labels.shipped())})")
    if args.scope == "user":
        if not interactive:
            return {"scope": "user", "locale": locale, "written": False,
                    "reason": "non-interactive run: nothing recorded, so a later interactive session still asks once"}
        data, problem = read_user_config()
        data = dict(data)
        data["locale"] = locale
        data["locale_asked"] = True
        path = user_config_path()
        write_atomic(path, _dump(data))
        return {"scope": "user", "locale": locale, "locale_asked": True, "written": True, "path": str(path),
                "replaced_problem": problem}
    root = Path(args.root).resolve() if args.root else Path.cwd()
    path = find_repo_config_bounded(root)
    if path is None:
        raise UsageError(f"no {CONFIG_NAME} found at {str(root)[:120]!r} or between it and the repository root (the folder with "
                         ".git); --scope repo never edits a config outside the repository; pass --root of an initialised repo")
    data, problem = read_repo_config(path)
    if problem:
        raise UsageError(f"{problem}; fix it before setting the repo locale")
    data["locale"] = locale
    try:
        keep_mode = path.stat().st_mode & 0o777
    except OSError:
        keep_mode = 0o644
    write_atomic(path, _dump(data), mode=keep_mode)
    return {"scope": "repo", "locale": locale, "written": True, "path": str(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="locale_cli.py", description="Show or set the document locale (vi or en).")
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status", help="resolve the locale and say whether the user should be asked")
    st.add_argument("--root", help="project directory (default: current directory)")
    st.add_argument("--locale", help="explicit locale, highest priority")
    st.add_argument("--sprint-file", help="sprint document whose front matter may declare locale")
    st.add_argument("--non-interactive", action="store_true", help="never ask; resolve and write nothing")
    st.add_argument("--json", action="store_true", dest="as_json")
    se = sub.add_parser("set", help="store a locale in the user config or the repo .agile.json")
    se.add_argument("--scope", required=True, choices=("user", "repo"))
    se.add_argument("--locale", required=True)
    se.add_argument("--root", help="project directory for --scope repo (default: current directory)")
    se.add_argument("--non-interactive", action="store_true", help="with --scope user: write nothing (like CI or AGENT_AGILE_NONINTERACTIVE)")
    se.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            info = gather(args, is_interactive(args.non_interactive))
            print(json.dumps(info, ensure_ascii=False, indent=2) if args.as_json else render_status(info))
        else:
            result = do_set(args, is_interactive(args.non_interactive))
            if args.as_json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif result["written"]:
                print(f"{result['scope']} locale set to {result['locale']} ({result['path']})")
            else:
                print(f"not written: {result['reason']}")
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except _labels.LabelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: I/O failure: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
