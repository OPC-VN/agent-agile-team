#!/usr/bin/env python3
"""Tier hook (ADR-008 #6-#8, RQ-435 L2a): PreToolUse on `Agent|Task`; forces the model of a Claude subagent by its role.

Usage: python tier_hook.py            (event JSON on stdin; output JSON on stdout; always exit 0)

MANDATORY TURN (definition): a turn is mandatory exactly when agile is ON for the event: the `always` switch of the repo or the
`session_id` of the event is switched on (`agile_state.load_state(...)["effective_on"]`, the same state the agile guard reads).
When agile is OFF the hook sleeps: no output, no receipt, exit 0. When the state cannot be read (corrupt file, unloadable layer) the
turn is NOT treated as mandatory: the hook passes with a warning (ADR-008 #8: hard block only on a mandatory turn).

Flow when agile is ON:
  1. `tool_input.subagent_type` (only the prefix `agent-agile-team:` is dropped; another plugin's prefix keeps the name outside the
     catalog) is looked up in the role catalog (`tier_resolve`). A name outside the catalog passes untouched (receipt `pass`).
     If the catalog cannot be loaded, only the nine core roles (CORE_ROLES, hard-coded here for exactly this case) are denied;
     any other agent passes with a warning.
  2. `tier_resolve.resolve(role, "claude")`: OpcOS mode reads the snapshot, standalone mode resolves from the user table.
  3. The resolved model id becomes the `model` of the Agent tool. The tool takes ALIASES: the id is mapped through an explicit table
     (BUILTIN_ALIASES, extended by the JSON object in `AGENT_AGILE_MODEL_ALIASES`; keys must look like model ids and values must be one
     of ALIAS_VALUES, a bad entry is ignored with a warning). An id outside it is `model_unmappable` and is denied, never guessed.
     `updatedInput` carries EVERY key of the old `tool_input` plus `model` (it replaces the whole input).
  3b. Role card (CO16): when the type is general-purpose, claude, Plan, Explore or empty, the role comes from the first `[AAT role=<role>]`
     tag in `tool_input.prompt` (receipt `role_source` = `tag`; an agent file gives `agent`). A known role goes through steps 2-3 exactly like
     the agent of that role; `role=direct` passes with decision `pass_direct` (no model forced); an unknown role is denied `unknown_role`; no tag
     is denied `role_tag_required`. With an unusable catalog the tag is checked against CORE_ROLES only.
  4. Any resolution error is a `deny`; the reason names the code and a way out (`/agent-agile-team:agile stop`, or fix the cause).

Receipt: one JSONL line per run, append, no prompt text and no secret. Place: `tier-receipts.jsonl` in the folder of the newest open
sprint (`agile_state.open_sprints`); without an open sprint `<repo root or cwd>/.tmp/tier-receipts.jsonl`, and only when `git check-ignore`
(3 s timeout) confirms the file is ignored; an error or doubt means no write and a warning.
Fields: schema, ts, session_id, sprint, role, tier, requested_model, actual_model (always null: the hook does not see the real model),
model_identity_status (always `unverified`; the real model of Claude comes from modelUsage, OUTSIDE v1), enforcement `hook`, resolver,
snapshot_revision, role_source agent|tag|null, decision allow|deny|pass|pass_direct, error_code, claude_code_version (from `claude_code_version` of the event or the env
`CLAUDE_CODE_VERSION` when it looks like a version, else null; never guessed), alias_table_source (`default` or `env`).
A write failure never breaks the turn; on a mandatory turn it adds a warning (`systemMessage`) for an allow or deny decision, once per
session_id (marker file in the temp folder, or `AGENT_AGILE_TIER_WARN_DIR`); never for a `pass`.

Known trade-off: when the role catalog is unusable, roles that only inherit a core role (python-reviewer, the specialists ...) are not
forced to a model, because the nine core roles are the only names the hook can still recognise (accepted).

Limits: Codex and Antigravity are not forced by this hook ("rule + check afterwards"); only the Claude Agent tool is.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tier_resolve as tr  # noqa: E402

# Explicit id -> alias table; an id outside it is never guessed (model_unmappable).
# Source of the fable/opus rows: measured 22/11/2026 in a Claude Code session: Agent tool `model: "fable"` gave real model
# claude-fable-5-2 and `model: "opus"` gave claude-opus-5-5 (message.model in the subagent transcript). Measure again when the Claude Code
# version changes. Haiku/sonnet rows: m06 aliases of Sprint 0 (Claude Code 2.1.310). claude-fable-5-1 is deliberately NOT mapped.
BUILTIN_ALIASES = {
    "claude-haiku-5-5": "haiku",
    "claude-sonnet-5-5": "sonnet",
    "claude-opus-5-5": "opus",
    "claude-fable-5-2": "fable",
}
ALIAS_VALUES = ("haiku", "sonnet", "opus", "fable")
# Used ONLY to decide a deny when the role catalog cannot be loaded (the catalog is the source of truth otherwise).
CORE_ROLES = ("researcher", "qa", "implementer", "analyst", "architect", "tech-reviewer", "business-reviewer", "gate-delegate", "advisor")
PLUGIN_PREFIX = "agent-agile-team:"
RECEIPT_NAME = "tier-receipts.jsonl"
HOOK_NAMES = ("Agent", "Task")
# Role-card path (CO16): a delegation through a generic subagent type must say its role in the first `[AAT role=<role>]` tag of the prompt.
# The tag counts only on the FIRST non-empty line of the prompt (anchored); case-insensitive, extra spaces allowed; the role is lower-cased.
GENERIC_TYPES = ("general-purpose", "claude", "plan", "explore")
ROLE_TAG_RE = re.compile(r"\[AAT\s+role\s*=\s*([A-Za-z0-9-]+)\s*\]", re.IGNORECASE)
TAG_START_RE = re.compile(r"\[AAT(?![A-Za-z0-9])", re.IGNORECASE)
NOT_TAGGABLE = ("human-arbiter",)
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([-.+][0-9A-Za-z.-]+)?$")


def _text(value):
    return value if isinstance(value, str) and value else None


def model_aliases(env=None):
    """(table, env_keys, warnings). Env entries need a model-id-shaped key and a value in ALIAS_VALUES; others are ignored with a warning."""
    env = os.environ if env is None else env
    table = dict(BUILTIN_ALIASES)
    used: set = set()
    warnings: list = []
    raw = env.get("AGENT_AGILE_MODEL_ALIASES")
    if raw:
        try:
            extra = json.loads(raw)
        except ValueError:
            extra = None
        if not isinstance(extra, dict):
            warnings.append("AGENT_AGILE_MODEL_ALIASES is not a JSON object; ignored")
            extra = {}
        for key, value in extra.items():
            if isinstance(key, str) and tr._MODEL_ID_RE.match(key) and value in ALIAS_VALUES:
                table[key] = value
                used.add(key)
            else:
                warnings.append(f"AGENT_AGILE_MODEL_ALIASES entry {str(key)[:40]!r} ignored (key must be a model id, value one of {'|'.join(ALIAS_VALUES)})")
    return table, used, warnings


def agile_state_for(payload: dict):
    """(effective_on, problem). problem is a short text when the state cannot be read."""
    try:
        import agile_state as st

        cwd = _text(payload.get("cwd")) or os.getcwd()
        state = st.load_state(cwd, _text(payload.get("session_id")))
        if state.get("state_problem"):
            return False, state["state_problem"]
        return bool(state["effective_on"]), None
    except Exception as exc:  # noqa: BLE001 - an unreadable state is a warning, not a block
        return False, type(exc).__name__


def agent_name(subagent_type):
    """The subagent name with the prefix of THIS plugin dropped; another plugin's prefix stays (so it is outside the catalog)."""
    name = _text(subagent_type)
    name = name.strip().lower() if name else None
    if not name:
        return None
    return name[len(PLUGIN_PREFIX):] if name.startswith(PLUGIN_PREFIX) else name


def first_line_tag(prompt):
    """(role, malformed). Only the first non-empty line of the prompt is read; role is lower-cased."""
    for line in (prompt or "").splitlines():
        line = line.strip()
        if not line:
            continue
        found = ROLE_TAG_RE.match(line)
        if found:
            return found.group(1).lower(), False
        return None, bool(TAG_START_RE.match(line))
    return None, False


def role_of(subagent_type, catalog: dict):
    name = agent_name(subagent_type)
    return name if name and name in catalog["roles"] else None


def claude_code_version(payload: dict, env) -> str | None:
    for value in (payload.get("claude_code_version"), env.get("CLAUDE_CODE_VERSION")):
        if isinstance(value, str) and _VERSION_RE.match(value.strip()):
            return value.strip()
    return None


def exit_hint(code: str, env=None) -> str:
    """Way out for a deny, chosen by the error code (and by which table variables are set). Always names the switch that turns agile off."""
    env = os.environ if env is None else env
    stop = "turn agile off with /agent-agile-team:agile stop"
    if code.startswith("snapshot_"):
        return (f"Fix: run `node system/bridges/lib/tier-snapshot.mjs snapshot`, or unset AGENT_AGILE_TIER_SNAPSHOT and open a new session; or {stop}.")
    if code in ("tiers_file_missing", "model_tier_unavailable"):
        if env.get("AGENT_AGILE_TIERS") or env.get("AGENT_AGILE_TIER_SNAPSHOT"):
            return ("Fix: correct or unset AGENT_AGILE_TIERS (the right path is %OPCOS_ROOT%/system/workshop/records/agent-agile-team/tiers.json) "
                    f"or set AGENT_AGILE_TIER_SNAPSHOT, then RESTART the app/session; or {stop}.")
        return f"Fix: run scripts/tier_setup.py (standalone install), then open a new session; or {stop}."
    if code == "role_tag_malformed":
        return f"Fix: write the first line as [AAT role=<role>], or [AAT role=direct]; or {stop}."
    if code.startswith("catalog_"):
        return f"Fix: restore tiers/role-catalog.json or point AGENT_AGILE_ROLE_CATALOG at it; or {stop}."
    if code == "model_unmappable":
        return f"Fix: add the alias through AGENT_AGILE_MODEL_ALIASES (after measuring it) or measure the model id again; or {stop}."
    return f"Fix the cause named above, or {stop}."


def receipt_target(payload: dict):
    """(path, sprint, fallback). Folder of the newest open sprint, else <root or cwd>/.tmp (fallback True)."""
    cwd = _text(payload.get("cwd")) or os.getcwd()
    root = None
    try:
        import agile_state as st

        found = st.open_sprints(cwd)
        root = found.get("root")
        if root is not None and found.get("sprints"):
            top = found["sprints"][0]
            return Path(root) / top["folder"] / RECEIPT_NAME, top["sprint"], False
    except Exception:  # noqa: BLE001
        pass
    return Path(root or cwd) / ".tmp" / RECEIPT_NAME, None, True


def tmp_is_ignored(path: Path) -> bool:
    """True only when git confirms `.tmp/tier-receipts.jsonl` is ignored. Any error, timeout or doubt is False."""
    try:
        done = subprocess.run(["git", "check-ignore", "-q", f".tmp/{RECEIPT_NAME}"], cwd=str(path.parent.parent), timeout=3,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return done.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def write_receipt(path: Path, record: dict) -> str | None:
    """Append one line. Returns an error text or None."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return None
    except OSError as exc:
        return type(exc).__name__


def _first_warning(session_id) -> bool:
    """True the first time a receipt warning is due for this session_id (marker file); without a session id it is always due."""
    sid = re.sub(r"[^A-Za-z0-9._-]", "_", session_id)[:80] if session_id else None
    if not sid:
        return True
    try:
        import tempfile

        folder = Path(os.environ.get("AGENT_AGILE_TIER_WARN_DIR") or tempfile.gettempdir())
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / f"agent-agile-tier-receipt-warned-{sid}"
        if marker.exists():
            return False
        marker.write_text("1", encoding="utf-8")
    except OSError:
        return True
    return True


def decide(payload: dict, env=None) -> dict | None:
    """Pure decision. None = sleep (agile OFF / not our tool). Else {"output", "receipt", "mandatory", "write", "warnings"}."""
    if payload.get("tool_name") not in HOOK_NAMES:
        return None
    env = os.environ if env is None else env
    on, problem = agile_state_for(payload)
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    rec = {"schema": 1, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session_id": _text(payload.get("session_id")),
           "sprint": None, "role": None, "tier": None, "requested_model": _text(tool_input.get("model")), "actual_model": None,
           "model_identity_status": "unverified", "enforcement": "hook", "resolver": None, "snapshot_revision": None,
           "decision": "pass", "error_code": None, "claude_code_version": claude_code_version(payload, env),
           "alias_table_source": "default", "role_source": None}
    if problem is not None:
        rec["error_code"] = "agile_state_unreadable"
        warn = f"tier hook: agile state unreadable ({problem}); subagent model not enforced"
        return {"output": {"systemMessage": warn}, "receipt": rec, "mandatory": False, "write": False, "warnings": []}
    if not on:
        return None
    aliases, env_keys, warnings = model_aliases(env)
    name = agent_name(tool_input.get("subagent_type"))
    tag = None
    if name is None or name in GENERIC_TYPES:
        tag, malformed = first_line_tag(_text(tool_input.get("prompt")))
        if malformed:
            return _deny(rec, "role_tag_malformed", "thẻ sai định dạng, dạng đúng: [AAT role=<vai>]", warnings, env)
        if tag is None:
            return _deny(rec, "role_tag_required", "a generic subagent needs a role: start the brief with `[AAT role=<role>]` "
                         "(valid roles are the names in tiers/role-catalog.json, e.g. researcher, implementer, qa, tech-reviewer), "
                         "or `[AAT role=direct]` for direct work with no sprint role", warnings, env)
        if tag == "direct":
            rec.update(decision="pass_direct", role_source="tag")
            return {"output": None, "receipt": rec, "mandatory": True, "write": True, "warnings": warnings}
    try:
        catalog = tr.load_catalog(tr.catalog_path(env))
    except tr.TierError as exc:
        if tag is not None:
            # every tag other than `direct` is denied: the tag cannot be checked without the catalog
            rec.update(role=tag if tag in CORE_ROLES else None, role_source="tag")
            return _deny(rec, exc.code, f"{exc.message}; the role tag {tag!r} cannot be checked. Use `[AAT role=direct]` for direct work", warnings, env)
        if name in CORE_ROLES:
            rec.update(role=name, role_source="agent")
            return _deny(rec, exc.code, exc.message, warnings, env)
        rec["error_code"] = exc.code
        warnings.append(f"tier hook: role catalog unusable ({exc.code}); subagent model not enforced for {name or 'this agent'}")
        return {"output": None, "receipt": rec, "mandatory": True, "write": True, "warnings": warnings}
    if tag is not None:
        if tag in NOT_TAGGABLE or tag not in catalog["roles"]:
            valid = ", ".join(sorted(r for r in catalog["roles"] if r not in NOT_TAGGABLE))
            return _deny(rec, "unknown_role", f"role {tag!r} in the [AAT role=...] tag is not a known role; valid roles: {valid}; "
                         "use `[AAT role=direct]` for direct work with no sprint role", warnings, env)
        role = tag
    else:
        role = role_of(tool_input.get("subagent_type"), catalog)
    if role is None:
        return {"output": None, "receipt": rec, "mandatory": True, "write": True, "warnings": warnings}
    rec.update(role=role, role_source="tag" if tag else "agent")
    res = tr.resolve(role, "claude", env=env)
    if res["status"] != "ok":
        return _deny(rec, res["code"], res.get("message", res["code"]), warnings, env)
    rec.update(tier=res["tier"], resolver=res["resolver"])
    try:
        rec["snapshot_revision"] = tr.detect_mode(env)["snapshot"].get("revision") if res["mode"] == "opcos" else None
    except Exception:  # noqa: BLE001
        rec["snapshot_revision"] = None
    alias = aliases.get(res["model"])
    if not alias:
        return _deny(rec, "model_unmappable", f"model id {res['model']!r} has no alias in the explicit table; not guessed", warnings, env)
    if res["model"] in env_keys:
        rec["alias_table_source"] = "env"
    updated = dict(tool_input)
    updated["model"] = alias
    rec["decision"] = "allow"
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                  "permissionDecisionReason": f"agile tier: role {role} tier {res['tier']} -> model {alias}",
                                  "updatedInput": updated}}
    return {"output": out, "receipt": rec, "mandatory": True, "write": True, "warnings": warnings}


def _deny(rec: dict, code: str, message: str, warnings: list, env=None) -> dict:
    rec.update(decision="deny", error_code=code)
    reason = f"agile tier: {code}: {message}. Subagent not started (agile is ON, tier is mandatory). {exit_hint(code, env)}"
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}
    return {"output": out, "receipt": rec, "mandatory": True, "write": True, "warnings": warnings}


def main(stdin=None, stdout=None) -> int:
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        payload = json.loads(stdin.read() or "{}")
        if not isinstance(payload, dict):
            return 0
        result = decide(payload)
    except Exception:  # noqa: BLE001 - never break a turn on a hook bug
        return 0
    if result is None:
        return 0
    notes = list(result.get("warnings") or [])
    if result.get("write", True):
        path, sprint, fallback = receipt_target(payload)
        result["receipt"]["sprint"] = sprint
        err = None
        if fallback and not tmp_is_ignored(path):
            err = "no open sprint and .tmp is not confirmed git-ignored"
        else:
            err = write_receipt(path, result["receipt"])
        if err and result["mandatory"] and result["receipt"]["decision"] not in ("pass", "pass_direct") and _first_warning(result["receipt"]["session_id"]):
            notes.append(f"tier hook: receipt not written ({err})")
    output = result["output"]
    if notes:
        output = dict(output or {})
        output["systemMessage"] = " ".join(filter(None, [output.get("systemMessage"), *notes]))
    if output:
        stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
