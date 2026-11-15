#!/usr/bin/env python3
"""Agile switch state: per-session ON/OFF, repo-level `always`, status view. Stdlib only.

Usage:
    python scripts/agile_state.py <get|on|off|always|manual|stop|status> [--session ID] [--project DIR] [--json]

State lives OUTSIDE the project (SPEC A9): Windows `%LOCALAPPDATA%\\agent-agile-team\\state`, elsewhere
`$XDG_STATE_HOME/agent-agile-team` or `~/.local/state/agent-agile-team`; override `AGENT_AGILE_STATE_DIR`.
Files: `repo-<key>.json` (always, manual, notes) and `session-<id>.json` (agile, mode, source, ...).

The CLI always writes `source: script`; only `scripts/agile_hook.py` passes `source: hook` (SC1.8). Anyone able to
write the same fields can still forge it; `status` flags a non-hook ON instead of claiming it is impossible.

Exit codes: 0 ok, 1 I/O failure, 2 bad usage. A hook importing this module must never let an exception through.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

APP = "agent-agile-team"
ENV_STATE_DIR = "AGENT_AGILE_STATE_DIR"
STALE_DAYS = 14
OPEN_STATUSES = ("drafting", "awaiting_gate_1", "in_progress", "verifying", "blocked", "awaiting_gate_2")
COMMANDS = ("get", "on", "off", "always", "manual", "stop", "status")
SESSION_ID_MAX = 128
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
NOT_YET = "not available yet"


# --- Locations -------------------------------------------------------------------------------------------


def platform_state_dir(environ=None, os_name=None, home=None) -> Path:
    """Default state dir for the platform; ignores the override variable (used to assert it stays untouched)."""
    env = os.environ if environ is None else environ
    os_name = os.name if os_name is None else os_name
    home = Path(home) if home is not None else Path.home()
    if os_name == "nt":
        base = env.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / APP / "state"
    xdg = env.get("XDG_STATE_HOME")
    base = xdg if xdg else str(home / ".local" / "state")
    return Path(base) / APP


def state_dir(environ=None) -> Path:
    env = os.environ if environ is None else environ
    override = env.get(ENV_STATE_DIR)
    if override:
        return Path(override)
    return platform_state_dir(env)


def sanitize_session_id(session_id) -> str | None:
    """File-name-safe form of a session id. `None` for missing/empty. Unsafe ids map to `x-<sha256 prefix>` (no
    separators, no `..`, deterministic, distinct per input) instead of being used raw (SC4.5)."""
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    if len(session_id) <= SESSION_ID_MAX and _SAFE_ID.fullmatch(session_id):
        return session_id
    digest = hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:24]
    return "x-" + digest


def _norm(path) -> str:
    return os.path.normcase(os.path.realpath(str(path)))


def _read_small(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None


def find_git_common_dir(project) -> Path | None:
    """Git common dir found by reading `.git` in-process: a directory, or a file `gitdir: ...` (linked worktree or
    submodule) followed through `commondir`. Never a relative path. `None` when no `.git` is found."""
    start = Path(os.path.abspath(str(project)))
    for folder in [start, *start.parents]:
        dot = folder / ".git"
        try:
            if dot.is_dir():
                return Path(os.path.realpath(str(dot)))
            if dot.is_file():
                text = _read_small(dot) or ""
                if not text.startswith("gitdir:"):
                    return None
                gitdir = Path(text[len("gitdir:"):].strip())
                if not gitdir.is_absolute():
                    gitdir = folder / gitdir
                commondir = _read_small(gitdir / "commondir")
                if commondir:
                    common = Path(commondir)
                    gitdir = common if common.is_absolute() else gitdir / common
                return Path(os.path.realpath(str(gitdir)))
        except OSError:
            return None
    return None


def repo_key(project) -> str:
    """Stable key of the repository: sha256 prefix of the normalised absolute git common dir; a non-git directory
    falls back to its normalised absolute path (SC4.2). A repo and its linked worktrees share the key (SC4.1)."""
    common = find_git_common_dir(project)
    if common is not None:
        material = "git:" + _norm(common)
    else:
        material = "path:" + _norm(os.path.abspath(str(project)))
    return hashlib.sha256(material.encode("utf-8", "replace")).hexdigest()[:16]


def repo_file(project, directory: Path | None = None) -> Path:
    return (directory or state_dir()) / f"repo-{repo_key(project)}.json"


def session_file(session_id, directory: Path | None = None) -> Path | None:
    sid = sanitize_session_id(session_id)
    if sid is None:
        return None
    return (directory or state_dir()) / f"session-{sid}.json"


# --- Atomic JSON files -----------------------------------------------------------------------------------


def now_iso(now: float | None = None) -> str:
    stamp = time.time() if now is None else now
    return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> tuple[dict | None, str | None]:
    """(data, problem). Missing file -> (None, None). Corrupt/unreadable -> (None, text). Transient Windows sharing
    errors are retried before being reported."""
    last = None
    for attempt in range(20):
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            return None, None
        except PermissionError as exc:  # a writer is replacing the file right now (Windows)
            last = exc
            time.sleep(0.01)
            continue
        except OSError as exc:
            return None, f"{path.name}: unreadable ({exc.__class__.__name__})"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None, f"{path.name}: corrupt (not valid UTF-8 JSON)"
        if not isinstance(data, dict):
            return None, f"{path.name}: corrupt (top level is not an object)"
        return data, None
    return None, f"{path.name}: unreadable ({last.__class__.__name__ if last else 'busy'})"


def write_json_atomic(path: Path, data: dict) -> None:
    """Temp file in the same dir + `os.replace`, retried on PermissionError (SC4.7)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    try:
        with open(tmp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(100):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 99:
                    raise
                time.sleep(0.01)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


# --- State -----------------------------------------------------------------------------------------------


def load_state(project, session_id=None, directory: Path | None = None) -> dict:
    """Current switch state. Corrupt/unreadable state => agile OFF, `state_problem` set and
    `guard_must_stay_active` True (SC4.3). Never raises for file problems."""
    directory = directory or state_dir()
    problems = []
    repo, p1 = read_json(repo_file(project, directory))
    if p1:
        problems.append(p1)
    repo = repo or {}
    sid = sanitize_session_id(session_id)
    sess = {}
    if sid is not None:
        sess_data, p2 = read_json(directory / f"session-{sid}.json")
        if p2:
            problems.append(p2)
        sess = sess_data or {}
    always = repo.get("always") is True
    repo_manual = repo.get("manual") is True
    session_on = sess.get("agile") is True
    mode = "manual" if (repo_manual or sess.get("mode") == "manual") else "auto"
    effective = (always or session_on) and not problems
    non_hook = bool((session_on and sess.get("source") != "hook") or (always and repo.get("always_source") != "hook"))
    sources = []
    if session_on:
        sources.append(sess.get("source") or "unknown")
    if always:
        sources.append(repo.get("always_source") or "unknown")
    return {
        "repo_key": repo_key(project),
        "session": sid if sid is not None else "unknown",
        "session_known": sid is not None,
        "session_agile": session_on and not problems,
        "always": always and not problems,
        "manual_flag": repo_manual,
        "mode": mode,
        "source": "+".join(sorted(set(sources))) if sources else "-",
        "non_hook_on": non_hook and effective,
        "effective_on": effective,
        "state_problem": "; ".join(problems) if problems else None,
        "guard_must_stay_active": bool(effective or problems),
        "prompt_id": sess.get("prompt_id"),
        "transcript_path": sess.get("transcript_path"),
        "ts": sess.get("ts"),
        "last_hook": sess.get("last_hook"),
        "session_file_exists": bool(sess) or (sid is not None and (directory / f"session-{sid}.json").exists()),
    }


def _update_repo(project, directory: Path, changes: dict, note: str | None = None) -> None:
    path = repo_file(project, directory)
    data, _problem = read_json(path)
    data = data or {}
    data.update(changes)
    data["schema"] = 1
    if note:
        notes = [n for n in data.get("notes", []) if isinstance(n, str)]
        notes.append(note)
        data["notes"] = notes[-10:]
    write_json_atomic(path, data)


def _update_session(session_id, directory: Path, changes: dict) -> None:
    path = session_file(session_id, directory)
    if path is None:
        return
    data, _problem = read_json(path)
    data = data or {}
    data.update(changes)
    data["schema"] = 1
    data["session_id"] = sanitize_session_id(session_id)
    write_json_atomic(path, data)


def touch_session(session_id, directory: Path | None = None, now: float | None = None) -> None:
    """Record `last_hook` (a hook ran for this session) without changing the switch. A corrupt file is left alone so
    the problem stays visible (and the guard stays active) until `stop` repairs it."""
    directory = directory or state_dir()
    path = session_file(session_id, directory)
    if path is None:
        return
    _data, problem = read_json(path)
    if problem:
        return
    _update_session(session_id, directory, {"last_hook": now_iso(now)})


def apply_command(cmd: str, project, session_id=None, source: str = "script", prompt_id=None,
                  transcript_path=None, directory: Path | None = None, now: float | None = None) -> dict:
    """Apply `on|off|always|manual|stop`. Returns {"changed", "message", "state", "open_sprints"}.

    `source` is `script` for the CLI and `hook` only when `agile_hook.py` calls this on a human-typed command.
    `on` and `manual` need a session; `always` and `stop` also work at repo level."""
    if cmd not in ("on", "off", "always", "manual", "stop"):
        raise ValueError(f"unknown command: {cmd}")
    directory = directory or state_dir()
    sid = sanitize_session_id(session_id)
    ts = now_iso(now)
    meta = {"source": source, "prompt_id": prompt_id, "transcript_path": transcript_path, "ts": ts}
    before = load_state(project, session_id, directory)
    if cmd in ("on", "off") and sid is None:
        raise ValueError(f"'{cmd}' needs --session (agile is per session)")
    message = ""
    if cmd == "on":
        _update_session(sid, directory, dict(meta, agile=True, mode="auto"))
        message = "agile ON for this session (mode auto)"
    elif cmd == "off":
        _update_session(sid, directory, dict(meta, agile=False, mode="auto"))
        message = "agile OFF for this session"
    elif cmd == "manual":
        if sid is not None:
            _update_session(sid, directory, dict(meta, agile=True, mode="manual"))
            message = "agile ON for this session (mode manual)"
        else:
            _update_repo(project, directory, {"manual": True, "manual_source": source, "manual_ts": ts},
                         f"{ts} manual set by {source}")
            message = "manual mode stored for this repo (session unknown)"
    elif cmd == "always":
        _update_repo(project, directory, {"always": True, "always_source": source, "always_ts": ts},
                     f"{ts} always set by {source}")
        message = "agile ON now and in later sessions of this repo (always)"
    else:  # stop: never refused
        already = not (before["effective_on"] or before["mode"] == "manual") and not before["state_problem"]
        if already:
            message = "already off"
        else:
            _update_repo(project, directory, {"always": False, "manual": False, "always_source": None,
                                              "manual_source": None}, f"{ts} stopped by {source}")
            if sid is not None:
                _update_session(sid, directory, dict(meta, agile=False, mode="auto"))
            message = "agile stopped: session switch, manual mode and always are cleared"
    after = load_state(project, session_id, directory)
    return {"changed": message != "already off", "message": message, "state": after,
            "open_sprints": open_sprints(project)["sprints"] if cmd == "stop" else None}


def cleanup_stale(directory: Path | None = None, days: int = STALE_DAYS, now: float | None = None) -> list:
    """Delete `session-*.json` (and orphan temp files) older than `days` directly inside the state dir.
    Never `repo-*.json`, never anything else, never recursive, never a link. Returns removed names."""
    directory = directory or state_dir()
    cutoff = (time.time() if now is None else now) - days * 86400
    removed = []
    try:
        names = os.listdir(directory)
    except OSError:
        return removed
    for name in names:
        is_session = name.startswith("session-") and name.endswith(".json")
        is_tmp = name.startswith(".") and name.endswith(".tmp")
        if not (is_session or is_tmp):
            continue
        path = directory / name
        try:
            if path.is_symlink() or not path.is_file() or os.path.getmtime(path) >= cutoff:
                continue
            path.unlink()
            removed.append(name)
        except OSError:
            continue
    return removed


# --- Project view (read-only) ----------------------------------------------------------------------------


def _find_root(project) -> Path | None:
    start = Path(os.path.abspath(str(project)))
    for folder in [start, *start.parents]:
        if (folder / c.CONFIG_NAME).is_file():
            return folder
    return None


def open_sprints(project) -> dict:
    """Open sprints read from the ledger folders named by `.agile.json`. Absence of config or sprints is not an
    error (SC3.2). Returns {"root", "config", "ledger", "sprints", "notes"}."""
    out = {"root": None, "config": None, "ledger": "none (no .agile.json)", "sprints": [], "notes": []}
    root = _find_root(project)
    if root is None:
        return out
    out["root"] = root
    try:
        cfg = c.load_config(root)
    except c.ConfigError as exc:
        out["ledger"] = f"unreadable .agile.json ({exc})"
        return out
    out["config"] = cfg
    problems = c.config_problems(cfg)
    if problems:
        out["ledger"] = "invalid .agile.json: " + "; ".join(problems)
        return out
    try:
        base = c.artifact_path(root, cfg, "")
        pattern = cfg["paths"]["sprint_dir"].replace("{date}", "*").replace("{slug}", "*")
        folders = sorted(p for p in base.glob(pattern) if p.is_dir())
    except (OSError, ValueError) as exc:
        out["ledger"] = f"cannot scan sprint folders ({exc.__class__.__name__})"
        return out
    out["ledger"] = "present"
    for folder in folders:
        state = next((folder / n for n in ("PROGRESS.md", "SPRINT.md") if (folder / n).is_file()), None)
        if state is None:
            continue
        try:
            fm = c.parse_frontmatter(c.read_text(state))
        except (c.SubsetError, OSError, UnicodeDecodeError):
            out["notes"].append(f"{folder.name}: frontmatter not readable")
            continue
        data = fm.data if fm else {}
        if data.get("status") not in OPEN_STATUSES or not c.parse_id(data.get("sprint")):
            continue
        try:
            shown = folder.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            shown = folder.name
        out["sprints"].append({"sprint": data.get("sprint"), "status": data.get("status"),
                               "title": str(data.get("title", "")), "folder": shown, "frontmatter": data})
    out["sprints"].sort(key=lambda s: (c.parse_id(s["sprint"]) or ("", -1))[1], reverse=True)
    return out


def role_counts(sprint: dict | None):
    """roles / agents / models counted from the sprint PROGRESS frontmatter `roles`; `None` = not measured."""
    roles = (sprint or {}).get("frontmatter", {}).get("roles")
    if not isinstance(roles, dict) or not roles:
        return None
    labels = []
    for value in roles.values():
        if isinstance(value, list) and len(value) >= 2:
            labels.append(str(value[1]))
    return {"roles": len(roles), "agents": len(labels), "models": len(set(labels))}


def legacy_markers(project) -> list:
    found = []
    seen = set()
    start = Path(os.path.abspath(str(project)))
    candidates = [start]
    common = find_git_common_dir(start)
    if common is not None:
        candidates.append(common.parent)
    for folder in candidates:
        marker = folder / ".tmp" / "autopilot.json"
        key = _norm(marker)
        if key not in seen and marker.is_file():
            seen.add(key)
            found.append(marker.as_posix())
    return found


def build_status(project, session_id=None, directory: Path | None = None) -> dict:
    st = load_state(project, session_id, directory)
    info = open_sprints(project)
    cfg = info["config"] or {}
    routing = cfg.get("routing")
    routing_mode = routing.get("mode") if isinstance(routing, dict) and routing.get("mode") else "-"
    newest = info["sprints"][0] if info["sprints"] else None
    fm = (newest or {}).get("frontmatter", {})
    cap = fm.get("session_cap")
    used = fm.get("session_used")
    if cap is not None:
        cap_line = f"{used if used is not None else '?'} / {cap} (report only, nothing blocks on it)"
    else:
        cap_line = "n/a"
    if not st["session_known"]:
        hook_seen = "unknown (no session id; repo-level view)"
    else:
        hook_seen = f"yes ({st['last_hook']})" if st["last_hook"] else "no"
    return {
        "session": st["session"],
        "agile": {"on": st["effective_on"], "mode": st["mode"], "always": st["always"], "source": st["source"],
                  "session_on": st["session_agile"], "non_hook_on": st["non_hook_on"]},
        "secure": NOT_YET, "tier": NOT_YET, "team": NOT_YET,
        "open_sprints": [{k: v for k, v in s.items() if k != "frontmatter"} for s in info["sprints"]],
        "ledger": info["ledger"],
        "routing_mode": routing_mode,
        "locale": str(cfg.get("locale") or "vi (default)"),
        "counts": role_counts(newest) or "not measured",
        "counts_from": newest["sprint"] if newest and role_counts(newest) else None,
        "session_cap": cap_line,
        "hook_seen": hook_seen,
        "legacy_markers": legacy_markers(project),
        "state_problem": st["state_problem"],
        "guard_must_stay_active": st["guard_must_stay_active"],
        "notes": info["notes"],
    }


def render_status(status: dict) -> str:
    a = status["agile"]
    lines = ["agile status"]
    session = status["session"] if status["session"] != "unknown" else "unknown (repo-level view; pass --session)"
    lines.append(f"  session: {session}")
    lines.append(f"  agile: {'ON' if a['on'] else 'OFF'} (mode {a['mode']}, always {'yes' if a['always'] else 'no'},"
                 f" source {a['source']})")
    if a["non_hook_on"]:
        lines.append("  WARNING non-hook ON: the switch was set by a script, not by the human-typed command hook")
    lines.append(f"  secure: {status['secure']}")
    lines.append(f"  tier: {status['tier']}")
    lines.append(f"  team: {status['team']}")
    if status["open_sprints"]:
        for s in status["open_sprints"]:
            lines.append(f"  open sprint: {s['sprint']} [{s['status']}] {s['title']} ({s['folder']})")
    else:
        lines.append("  open sprint: none")
    lines.append(f"  ledger: {status['ledger']}")
    lines.append(f"  routing.mode: {status['routing_mode']}")
    lines.append(f"  locale: {status['locale']}")
    counts = status["counts"]
    if isinstance(counts, dict):
        lines.append(f"  roles/agents/models: {counts['roles']}/{counts['agents']}/{counts['models']}"
                     f" (from {status['counts_from']} PROGRESS)")
    else:
        lines.append(f"  roles/agents/models: {counts}")
    lines.append(f"  session cap: {status['session_cap']}")
    lines.append(f"  hook seen this session: {status['hook_seen']}")
    for marker in status["legacy_markers"]:
        lines.append(f"  notice: legacy marker {marker} exists; it no longer switches anything (not deleted)")
    if status["state_problem"]:
        lines.append(f"  state problem: {status['state_problem']} (agile OFF, guard stays active)")
    for note in status["notes"]:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


# --- CLI -------------------------------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agile_state.py", description="Agile switch state.")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--session", default=None, help="session id (from the SessionStart context)")
    parser.add_argument("--project", default=None, help="project directory (default: current directory)")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv=None) -> int:
    c.utf8_stdio()
    args = _build_parser().parse_args(argv)
    project = args.project or os.getcwd()
    session = args.session
    if session is not None and sanitize_session_id(session) is None:
        print("agile_state: empty --session", file=sys.stderr)
        return 2
    try:
        if args.command == "get":
            state = load_state(project, session)
            if args.as_json:
                print(json.dumps(state, ensure_ascii=False, indent=2))
            else:
                print(f"agile: {'ON' if state['effective_on'] else 'OFF'} mode={state['mode']} "
                      f"always={'yes' if state['always'] else 'no'} source={state['source']} session={state['session']}")
                if state["state_problem"]:
                    print(f"state problem: {state['state_problem']} (guard stays active)")
            return 0
        if args.command == "status":
            status = build_status(project, session)
            print(json.dumps(status, ensure_ascii=False, indent=2) if args.as_json else render_status(status))
            return 0
        try:
            result = apply_command(args.command, project, session, source="script")
        except ValueError as exc:
            print(f"agile_state: {exc}", file=sys.stderr)
            return 2
        sprints = result["open_sprints"]
        if args.as_json:
            out = {"message": result["message"], "changed": result["changed"], "state": result["state"]}
            if sprints is not None:
                out["open_sprints"] = [{k: v for k, v in s.items() if k != "frontmatter"} for s in sprints]
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(result["message"])
            if sprints is not None:
                print(json.dumps([{k: v for k, v in s.items() if k != "frontmatter"} for s in sprints],
                                 ensure_ascii=False))
        return 0
    except OSError as exc:
        print(f"agile_state: I/O failure ({exc.__class__.__name__}: {exc})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
