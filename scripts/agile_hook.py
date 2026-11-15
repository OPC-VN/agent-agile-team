#!/usr/bin/env python3
"""Hook entry for the agile switch (Claude Code `--format claude`). Stdlib only; never blocks, never raises.

Reads one JSON payload on stdin:
- `SessionStart`: records `last_hook`, runs the stale-file cleanup, prints `additionalContext` with the state line
  and the `session_id` (so a skill-run `status` can pass `--session`).
- `UserPromptExpansion`: only when `command_name` equals exactly `agent-agile-team:agile`; `command_args` is
  whitelisted: "" -> on, `always`, `manual`, `stop`, `status`. Anything else changes nothing. Writes carry
  `source: hook`, `prompt_id` and `transcript_path`. `stop` is never refused.
- Any other event or malformed payload: exit 0, no change, no stdout.

Exit code is always 0 (SPEC FR5: no blocking hook). On an internal error a short line goes to stderr.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

COMMAND_NAME = "agent-agile-team:agile"
ARG_TO_COMMAND = {"": "on", "always": "always", "manual": "manual", "stop": "stop", "status": None}
MAX_STDIN = 1_000_000


def _text(value):
    return value if isinstance(value, str) else None


def _read_payload() -> dict | None:
    raw = sys.stdin.buffer.read(MAX_STDIN)
    data = json.loads(raw.decode("utf-8", "replace"))
    return data if isinstance(data, dict) else None


def state_line(project, session_id, source_event: str, directory=None) -> str:
    import agile_state as st

    state = st.load_state(project, session_id, directory)
    info = st.open_sprints(project)
    flavor = "ON" if state["effective_on"] else "OFF"
    parts = [f"mode {state['mode']}", f"always {'yes' if state['always'] else 'no'}"]
    if state["effective_on"]:
        parts.append(f"source {state['source']}")
    text = f"agile: {flavor} ({', '.join(parts)}) session_id={state['session']}"
    if info["sprints"]:
        top = info["sprints"][0]
        extra = f" +{len(info['sprints']) - 1} more" if len(info["sprints"]) > 1 else ""
        text += f" open sprint: {top['sprint']} [{top['status']}] {top['title']}{extra}"
    else:
        text += " open sprint: none"
    notices = []
    if state["state_problem"]:
        notices.append(f"state problem ({state['state_problem']}): agile is OFF, the guard stays active")
    if state["non_hook_on"]:
        notices.append("non-hook ON: the switch was set by a script, not by a human-typed command")
    if source_event == "resume" and state["session_known"] and not state["session_file_exists"] and not state["always"]:
        notices.append("no switch state found for this session id after resume; agile is OFF, type "
                       "/agent-agile-team:agile to turn it on")
    for marker in st.legacy_markers(project):
        notices.append(f"old marker {marker} exists; it no longer switches anything")
    if not state["effective_on"]:
        notices.append("type /agent-agile-team:agile to turn agile on")
    if notices:
        text += " notice: " + "; ".join(notices)
    return text


def handle_session_start(payload: dict, directory=None) -> str | None:
    import agile_state as st

    project = _text(payload.get("cwd")) or os.getcwd()
    session_id = _text(payload.get("session_id"))
    directory = directory or st.state_dir()
    st.cleanup_stale(directory)
    context = state_line(project, session_id, _text(payload.get("source")) or "", directory)  # before touching
    if session_id:
        st.touch_session(session_id, directory)
    return json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}},
                      ensure_ascii=False)


def handle_prompt_expansion(payload: dict, directory=None) -> None:
    import agile_state as st

    if payload.get("hook_event_name") != "UserPromptExpansion" or payload.get("command_name") != COMMAND_NAME:
        return
    args = payload.get("command_args")
    args = "" if args is None else args
    if not isinstance(args, str):
        return
    key = args.strip().lower()
    if key not in ARG_TO_COMMAND:
        return
    cmd = ARG_TO_COMMAND[key]
    if cmd is None:  # status: read-only, the skill prints it
        return
    session_id = _text(payload.get("session_id"))
    if not session_id:
        return
    project = _text(payload.get("cwd")) or os.getcwd()
    st.apply_command(cmd, project, session_id, source="hook", prompt_id=_text(payload.get("prompt_id")),
                     transcript_path=_text(payload.get("transcript_path")), directory=directory)


def run(payload: dict, directory=None) -> str | None:
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        return handle_session_start(payload, directory)
    if event == "UserPromptExpansion":
        handle_prompt_expansion(payload, directory)
    return None


def main(argv=None) -> int:
    try:
        payload = _read_payload()
        if payload is None:
            return 0
        out = run(payload)
        if out:
            sys.stdout.buffer.write(out.encode("utf-8") + b"\n")
            sys.stdout.flush()
    except BaseException as exc:  # a hook must never block or crash the session
        if isinstance(exc, KeyboardInterrupt):
            raise
        try:
            sys.stderr.write(f"agile_hook: ignored {exc.__class__.__name__}\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
