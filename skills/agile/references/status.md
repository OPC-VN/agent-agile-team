# agile status: output fields

`python "<plugin root>/scripts/agile_state.py" status --session <id> --project "<project dir>"` prints (`--project` omitted means the current directory) (add `--json` for the same data as JSON). One
line per field; fields not yet available print `not available yet`.

| Line | Meaning |
|---|---|
| `session` | session id, or `unknown (repo-level view; pass --session)` |
| `project` | the project directory the state was keyed on (`CLAUDE_PROJECT_DIR` wins when it is set); must be the user's project |
| `agile` | `ON` or `OFF`, with mode (`auto` or `manual`), `always yes/no`, and `source` of the switch (`hook`, `script`, `unknown`, several joined by `+`, or `-` when nothing is set) |
| `switch set` | printed only when ON: `prompt_id`, `ts` of the write, and a note that `source` is self-declared and not verified |
| `last command` | the last command the hook or CLI applied to this session: `none`, or `<command> changed=yes\|no prompt_id=.. ts=..`; for `stop`, `changed=no` means already off |
| `WARNING non-hook ON` | printed only when ON was not written by the hook; report it, never reset it |
| `secure` | `not available yet` (the secure variant does not exist in this release) |
| `tier` | `not available yet` |
| `team` | `not available yet` |
| `open sprint` | one line per open sprint: id, status, title, folder; or `none` |
| `ledger` | `present`, `none (no .agile.json)`, or the reason `.agile.json` or the folders cannot be read |
| `routing.mode` | from `.agile.json`, `-` when unset |
| `locale` | from `.agile.json`, `vi (default)` when unset |
| `roles/agents/models` | counted from the newest open sprint PROGRESS, or `not measured` |
| `session cap` | `used / cap` from the newest open sprint (report only, nothing blocks on it), or `n/a` |
| `hook seen this session` | whether the SessionStart hook has recorded this session |
| `notice: legacy marker` | a leftover marker file from the former process name exists in `.tmp/`; it switches nothing and is not deleted |
| `state problem` | the state file is unreadable or invalid; agile counts as OFF and the guard stays active |
| `note` | a sprint folder whose frontmatter could not be read |

Exit codes of the script: 0 ok, 1 I/O failure, 2 bad usage. Report numbers and ids as printed; do not add values that the
output does not contain. Missing `.agile.json` or no sprints is normal, not an error.
