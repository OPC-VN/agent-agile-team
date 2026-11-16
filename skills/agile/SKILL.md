---
name: agile
description: Use when the user types /agile (or /agent-agile-team:agile) with an optional argument always, manual, stop or status, or explicitly asks to turn the agile process on or off (bật agile, tắt agile, dừng agile) or to show its status (agile đang bật hay tắt). Not for a session that only carries the SessionStart agile line, and not for ordinary work.
metadata:
  group: "process"
  roles: "all"
---

# agile: the switch and its status

> **Conclusion:** the agile process (intake, SPEC and PLAN, two gates, sprint ledgers) runs only while the switch is ON.
> A human turns it on or off by typing `/agile`; this skill **reads and reports** the state and does the bookkeeping after
> `stop`. It never turns the process on by itself. Exact status fields: [references/status.md](references/status.md).

## 1. Who changes the state

| Typed by the human | Effect (applied by the hook, before the model answers) |
|---|---|
| `/agile` | ON for this session, mode auto: the Gate Delegate signs Gate 1 and Gate 2 |
| `/agile always` | ON for every session of this repository |
| `/agile manual` | ON, and the human signs Gate 1 and Gate 2 |
| `/agile stop` | OFF: clears the session switch, manual mode and `always` |
| `/agile status` | no change, report only |

The state is written only by the hook that reads the human-typed command. **This skill never writes ON, `always` or
`manual`**, and it never runs `agile_state.py on|off|always|manual` itself. A model-initiated call (the Skill tool used
without a typed `/agile`, or a user message that only mentions agile) reports the status and tells the user: the
sanctioned way to switch is to type `/agile` (or `/agile always`, `/agile manual`, `/agile stop`) themselves.

## 2. Steps

1. **Read the state line.** The SessionStart hook put a line such as `agile: ON|OFF (...) session_id=<id>` in the context.
   Take `<id>` from it exactly as printed (do not change its case). No line (hook not installed or not run): say so, use
   the repo-level view (omit `--session`).
2. **Run the status against the user's project, not the plugin.** The plugin root (`${CLAUDE_PLUGIN_ROOT}` when the host
   sets it) only tells you where the script is; never `cd` into it and never pass the plugin folder as the project:
   `python "<plugin root>/scripts/agile_state.py" status --session <id> --project "<project dir>"`
   where `<project dir>` is `$CLAUDE_PROJECT_DIR` when that variable is set, else the session's working directory. (Whether
   the Bash tool exports `CLAUDE_PROJECT_DIR` is not measured; the script also reads it itself and, when it is set, it wins.)
   The output has a `project:` line: check it names the user's project. Report the output in the shape of
   `references/status.md`, in the user's language. **Show the exact command line you ran** (or, after `/agile stop`, the
   `status` line that you read) in the reply, copied with the real `--session <value>` and `--project <value>`; "the status
   already ran" without the line does not count. Every run of `agile_state.py status` or `stop` is shown this way.
3. **Check that the hooks of this plugin ran in this session.** If there is no `agile:` state line in the context (step 1),
   or `status` prints `hook seen this session: no`, the SessionStart and prompt hooks did not run here. Then **do not
   say "agile ON"** (nor "agile OFF" as a confirmed fact): say the hooks did not run in this session, so a typed `/agile`
   changed nothing and the guard is dormant, and tell the user what to check: `python` is on PATH (the hooks call `python`;
   on macOS and Linux with only `python3` they cannot start, so `python` must be on PATH or a `python` link installed) and
   the plugin is enabled; then start a new session. Report the rest of the `status` output as read. Never turn ON yourself to compensate.
4. **Check the state matches what was typed.** If the user typed `/agile`, `always`, `manual` or `stop` and the status does
   not show the matching state (the hook did not run, the argument was not in the whitelist, or the state shows a problem),
   say exactly that and **stop there**. Do not run `on`, `off`, `always`, `manual` or `stop` yourself to "fix" it, and
   do not edit state files. Tell the user to retype the command or check the hook install.
5. **`status` argument or a question about state:** report and finish. No other action.

## 3. After `/agile stop`

The hook prints nothing to you; the outcome is recorded in the state and shown by `status` as the line
`last command: stop changed=yes|no prompt_id=... ts=...`. Use it only when the user typed `/agile stop` in this turn.

1. **Read `last command`.** `changed=no` means agile was already off: answer "already off" and change nothing (no
   blocker, no file edit). A missing line, a command other than `stop`, or a status showing ON means the stop did not
   happen: say so and stop there (step 4 of section 2).
2. **`changed=yes` and at least one `open sprint:` line:** for **each** open sprint append **one** blocker row to the
   blocker section (section 3, "Vướng mắc") of that sprint's `PROGRESS.md`: the next free `BR-NN`, text
   `paused by /agile stop`, today's date, status `mở`. A sprint with `SPRINT.md` instead of `PROGRESS.md` gets the same
   one row in its blocker part. With no open sprint write nothing.
3. Edit nothing else. Delete nothing: sprint folders, ledgers, SPEC, PLAN, REPORT and `.agile.json` stay as they are.
4. Say which sprints were paused and that nothing was removed; resuming means typing `/agile` again and clearing the `BR`.

## 4. What ON and OFF change for the agent

- **ON:** load the agile process document, [method/agile.md](../../method/agile.md), and apply the skills `intake`, `running-sprint` and `closing-sprint`. In `manual` mode the human signs Gate 1
  and Gate 2; the Gate Delegate does not. Floor rules in `AGENTS.md` stay in force in every mode.
- **OFF:** do not open sprints, do not register `RQ-` items, do not run gates or write sprint documents (the one blocker
  row of section 3 is the only exception), and do not call the process skills on your own. Ordinary work, Git rules,
  secret rules and the floor rules in `AGENTS.md` still apply. If the user asks for something sprint-sized while OFF,
  say the agile process is off and that `/agile` turns it on.

## 5. Errors and limits

| Situation | Do |
|---|---|
| No `agile:` state line, or `hook seen this session: no` | do not claim ON or OFF as confirmed; say the hooks did not run in this session; list what to check (step 3 of section 2) |
| `status` prints `state problem` | report it verbatim; the guard stays active; `/agile stop` repairs it |
| `status` prints `WARNING non-hook ON` | report it: the switch was not set by the human-typed command; do not reset it yourself |
| `project:` is not the user's project | rerun with the right `--project`; do not report the wrong view |
| Session id unknown | use the repo-level view and say the view is not per-session |
| User asks the model to "just turn it on" | decline the write, give the typed command |
