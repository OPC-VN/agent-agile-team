---
name: agile
description: Use when the user types /agile (or /agent-agile-team:agile) with an optional argument always, manual, stop or status, or asks to turn the agile process on or off (bật agile, tắt agile, dừng agile) or to see its status (agile đang bật hay tắt); also when the session context says agile is ON or OFF and the agent must know what that changes.
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
| `/agile` | ON for this session, mode auto: autopilot gates are signed by the Gate Delegate |
| `/agile always` | ON for every session of this repository |
| `/agile manual` | ON, and the human signs Gate 1 and Gate 2 |
| `/agile stop` | OFF: clears the session switch, manual mode and `always` |
| `/agile status` | no change, report only |

The state is written only by the hook that reads the human-typed command. **This skill never writes ON, `always` or
`manual`**, and it never runs `agile_state.py on|off|always|manual` itself. A model-initiated call (the Skill tool used
without a typed `/agile`, or a user message that only mentions agile) reports the status and tells the user: the
sanctioned way to switch is to type `/agile` (or `/agile always`, `/agile manual`, `/agile stop`) themselves.

## 2. Steps

1. **Read the state line.** The SessionStart hook put a line such as `agile: ON|OFF ... session_id=<id>` in the context.
   Take `<id>` from it. No line (hook not installed or not run): say so, use the repo-level view (omit `--session`).
2. **Run the status.** From the plugin root (the folder that holds `scripts/`; `${CLAUDE_PLUGIN_ROOT}` when the host sets it):
   `python scripts/agile_state.py status --session <id> --project .`
   Report the output in the shape of `references/status.md`, in the user's language.
3. **Check the state matches what was typed.** If the user typed `/agile`, `always`, `manual` or `stop` and the status does
   not show the matching state (the hook did not run, the argument was not in the whitelist, or the state shows a problem),
   say exactly that and **stop there**. Do not run `on`, `off`, `always`, `manual` or `stop` yourself to "fix" it, and
   do not edit state files. Tell the user to retype the command or check the hook install.
4. **`status` argument or a question about state:** report and finish. No other action.

## 3. After `/agile stop`

Once the status confirms OFF (or the hook reported `already off`):

1. If the hook said **already off**, answer "already off" and change nothing.
2. Otherwise read the open sprints from the status (`open sprint:` lines; `agile_state.py stop --json` lists them too
   when run by the hook). For **each** open sprint append **one** blocker row to the blocker section (section 3, "Vướng
   mắc") of that sprint's `PROGRESS.md`: the next free `BR-NN`, text `paused by /agile stop`, today's date, status `mở`.
3. Edit nothing else. Delete nothing: sprint folders, ledgers, SPEC, PLAN, REPORT and `.agile.json` stay as they are.
   A sprint with `SPRINT.md` instead of `PROGRESS.md` gets the same one row in its blocker part.
4. Say which sprints were paused and that nothing was removed; resuming means typing `/agile` again and clearing the `BR`.

## 4. What ON and OFF change for the agent

- **ON:** load the agile process document, `method/agile.md` (plain path, not a link: the file arrives with the law
  series), and apply the skills `intake`, `running-sprint` and `closing-sprint`. In `manual` mode the human signs Gate 1
  and Gate 2; the Gate Delegate does not. Floor rules in `AGENTS.md` stay in force in every mode.
- **OFF:** do not open sprints, do not register `RQ-` items, do not run gates or write sprint documents, and do not call the
  process skills on your own. Ordinary work, Git rules, secret rules and the floor rules in `AGENTS.md` still apply.
  If the user asks for something sprint-sized while OFF, say the agile process is off and that `/agile` turns it on.

## 5. Errors and limits

| Situation | Do |
|---|---|
| `status` prints `state problem` | report it verbatim; the guard stays active; `/agile stop` repairs it |
| `status` prints `WARNING non-hook ON` | report it: the switch was not set by the human-typed command; do not reset it yourself |
| Session id unknown | use the repo-level view and say the view is not per-session |
| User asks the model to "just turn it on" | decline the write, give the typed command |
