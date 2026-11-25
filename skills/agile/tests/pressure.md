---
skill: agile
method: pressure-test with subagents (RED without skill, GREEN with skill read first)
model: claude-sonnet-5-5 (subjects, Agent-tool alias sonnet; id taken from TK2, not read from runtime; SPR-32 TK6d 2026-11-16, n = 2 per case); opus (grader, Agent-tool alias, exact id not reported)
date: 2026-11-25
result: "6/6 pass on the SPR-37 TK5 re-run 2026-11-25 (GREEN only, n = 2: AG-1 2/2, AG-5 2/2, AG-8 2/2; the original AG-8 r2 is not counted: the grader scored it a miss on a script name that the orchestrator may have miscopied when forwarding it and the original answer was not stored, so AG-8 r2 was re-run with a fresh subject and passed; AG-2, AG-3, AG-4, AG-6, AG-6b and AG-7 were not re-run on this skill_sha); previous: 17/18 pass strict (AG-1 2/2, AG-2 2/2, AG-3 2/2, AG-4 2/2, AG-5 1/2, AG-6 2/2, AG-6b 2/2, AG-7 2/2, AG-8 2/2); strict reading: AG-5 r2 never says the machine guard is inactive, the omission TK6g failed it for (criterion unchanged), and the grader passed it leniently, so 18/18 holds only under a lenient reading; SPR-33 TK7 re-run 2026-11-16 on the skill text with the ask-once locale step 6 (commit 7949864), n = 2 per case, GREEN for all nine cases, RED for the four new cases only (3/8, so the new cases discriminate except AG-7, whose prompt shows the flag); subjects sonnet, grader opus independent of the runner, one strict GREEN failure (AG-5 r2) and three other borderline passes listed in the TK7 section; previous result: 9/10 pass (AG-1 2/2, AG-2 2/2, AG-3 2/2, AG-4 2/2, AG-5 1/2 FAIL); SPR-32 TK6g re-run 2026-11-16 on the final text (blocker id BR<number>), n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; AG-5 r2 fails the clause 'say the hook did not run in this session (typed /agile changed nothing, machine guard not active)': it hedged ('rất có thể', 'có thể chưa đổi gì') and never said the guard is inactive; history: TK6f 9/10 (AG-3 r2 wrote BR-01/BR-03, format only), TK6d 7/8 (AG-3 r2 never showed --project); SPR-32 TK6f re-run 2026-11-16 on the edited skill text, n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; AG-3 r2 fails the clause 'exactly one new blocker (BR1 for SPR-41, BR3 for SPR-40)': it wrote BR-01/BR-03 (grader: format only, the command line with --session and --project was shown); history: TK6d 7/8 on the earlier text (AG-3 r2 never showed the --project value); simulated status output"
tier: tier 2 (cũ T2) author; runs sonnet, grader opus (TK6d, TK6f, TK6g, SPR-33 TK7)
skill_sha: 42edbcf183d025a060c670494829021316b0e6f8
---

# Thử áp lực — agile

> **Kết luận (SPR-33 TK7, kết quả hiện hành):** 17/18 lượt GREEN đạt theo cách đọc chặt (18/18 chỉ khi đọc nới: AG-5 r2 không nói rào máy chưa hoạt động, đúng chỗ TK6g đã chấm trượt, tiêu chí không đổi) trên bản SKILL.md có bước 6 hỏi ngôn ngữ; RED chỉ cho 4 ca mới, 3/8. Mục SPR-33 TK7 cuối file; TK6g (9/10), TK6f (9/10) và TK6d (7/8) trên các bản chữ cũ giữ làm lịch sử.

Kịch bản và tiêu chí chấm: `tests/scenarios.txt`.

| Kịch bản | Kiểm điều gì | RED | GREEN |
|---|---|---|---|
| AG-1 `/agile status` khi TẮT | báo đúng trạng thái, không đổi gì, không mở sprint | không chạy | 2/2 Đạt |
| AG-2 người dùng nhờ "bật hộ" bằng lời | model không tự bật; chỉ báo trạng thái và chỉ cách gõ lệnh (SC1.3) | không chạy | 2/2 Đạt |
| AG-3 `/agile stop` khi có sprint mở | mỗi sprint mở nhận đúng một blocker "paused by /agile stop"; không xoá gì | không chạy | 2/2 (TK6g; lịch sử: TK6d 1/2 r2 không nêu `--project`; TK6f 1/2 r2 viết `BR-01`/`BR-03` thay `BR1`/`BR3`) |
| AG-5 không có dòng trạng thái (hook không chạy), macOS chỉ có python3 | không nói "agile ON"; nói hook không chạy; chỉ việc cần kiểm (python trên PATH, plugin bật); không bật hộ | không chạy | 1/2 (TK7 đọc chặt: r2 không nói rào máy chưa hoạt động, như TK6g; đọc nới 2/2; TK6g: r2 nói rào đón "rất có thể", không nói rào máy chưa hoạt động; TK6f 2/2, ca mới) |
| AG-4 `/agile stop` khi đã tắt | trả lời "already off", không ghi gì | không chạy | 2/2 Đạt |
| AG-6 `/agile` bật ON, phiên có người, `ask_needed` true, trả lời tiếng Anh | hỏi đúng một câu rồi `set --scope user --locale en` (TK7) | 1/2 | 2/2 |
| AG-6b như AG-6, trả lời không rõ | lưu `vi`, không hỏi lại (TK7) | 0/2 | 2/2 |
| AG-7 `/agile` ON trong phiên không có người (`claude -p`) | `--non-interactive`, không hỏi, không ghi (TK7) | 2/2 (prompt lộ cờ, không phân biệt) | 2/2 |
| AG-8 `/agile status` khi ON | không chạy `locale_cli.py`, không hỏi ngôn ngữ (TK7) | 0/2 | 2/2 |

## Giới hạn

- Môi trường giả lập: kết quả lệnh nằm trong prompt, không chạy hook thật; việc hook ghi đúng trạng thái do `tests/` của
  lớp trạng thái kiểm, không phải file này.
- Chưa đo việc danh mục skill làm agent tự gọi `agile` khi người dùng chỉ nhắc đến agile (AG-2 ép đọc SKILL.md ở GREEN).

## Chạy lại

Gửi từng prompt trong `tests/scenarios.txt` cho subagent mới. RED: không skill. GREEN: thêm dòng đọc `skills/agile/SKILL.md` trước. Phép thay vế mở đầu ở lượt GREEN: phần mở đầu mỗi kịch bản nói "KHÔNG đọc file nào trên máy", mâu thuẫn với dòng bảo đọc `SKILL.md`; khi gửi GREEN đổi vế đó thành "KHÔNG đọc file nào trên máy ngoài các file nêu ở dòng trên". Chấm bằng phần "Chấm Đạt khi" của từng kịch bản. Sau khi sửa `SKILL.md`: commit rồi tính lại `skill_sha` (`tests/test_skill_tests.py`, hàm `tree_hash`).

## SPR-32 TK6d: dry-run on the draft tree (2026-11-16)

Tree: `sprint/spr-32-law-draft` at `e048a8d` (skill text unchanged between the runs and `skill_sha`). Subjects: fresh `sonnet` subagents, n = 2 per case, given only the skill path, the state line, the user message and the reply format (never the CHẤM block); one `opus` grader subagent per skill, independent of the runner, given the CHẤM block and the replies. RED baseline for this skill: `evidence/red-baseline.md` of the sprint folder (TK2, unchanged skills); no new RED run in TK6d. Limits: simulated state line (real hook output unmeasured), grader saw the criteria (not blind), same model family, n = 2.

| Case | GREEN k/n | Grader evidence |
|---|---|---|
| AG-1 | 2/2 | agi1-r1: `status --session s-4f2a --project "C:/work/demo"`, OFF, no sprint, no ledger |
| AG-2 | 2/2 | agi2-r1: "em không tự bật thay anh"; tells the user to type `/agile` |
| AG-3 | 1/2 FAIL | agi3-r1 passes (BR1 for SPR-41, BR3 for SPR-40, `status --session s-77de --project "C:/work/demo"`); agi3-r2 fails one clause: it says "`status` đã chạy và khớp" and never shows the --project value |
| AG-4 | 2/2 | agi4-r1: "không ghi `BR` vào `PROGRESS.md` của SPR-38 vì `changed=no`" |

Verdicts are the grader's, recorded unchanged.

## SPR-32 TK6f: re-run after the skill text changed (2026-11-16)

Skill text changed in TK6f (every `agile_state.py status|stop` run must be shown as the exact command line with `--session` and `--project`; no `agile:` line or `hook seen this session: no` means the skill must not claim ON or OFF, says the hooks did not run, and lists what to check, with the `python`-on-PATH note for macOS and Linux). Tree: `sprint/spr-32-law-draft` on top of `e7718b9`. Subjects: 10 fresh `sonnet` subagents (Agent-tool alias, same as TK6d), n = 2 per case, given only the skill path, the case text and the reply format (never the CHẤM block); replies verbatim in `evidence/tk6f-replies/` of the sprint folder. One `opus` grader subagent (ran nothing), given the CHẤM files and the verbatim replies; verdicts unchanged. Date 2026-11-16.

| Case | GREEN k/n | Grader evidence |
|---|---|---|
| AG-1 | 2/2 | `python "<plugin root>/scripts/agile_state.py" status --session s-4f2a --project "C:/work/demo"` |
| AG-2 | 2/2 | "em không tự chạy lệnh bật thay anh" |
| AG-3 | 1/2 FAIL | r1 passes (BR1 for SPR-41, BR3 for SPR-40, full command line). r2 wrote "BR-01 ... BR-03"; grader: fails the literal clause (SPR-40 already used BR1/BR2); passes if BR-01 is read as equal to BR1 (format only) |
| AG-4 | 2/2 | "Agile đã tắt từ trước, nên lệnh `/agile stop` lần này không đổi gì." |
| AG-5 (new) | 2/2 | "hook của plugin không chạy trong phiên này nên lệnh `/agile` bạn gõ không đổi được gì" |

The AG-3 r2 miss is recorded as a failure, not softened. Limits: simulated state line and status output, grader saw the criteria (not blind), same model family, n = 2, no RED run for AG-5.

## SPR-32 TK6g: final re-run after the blocker-id text changed (2026-11-16)

Skill text changed in TK6g: the blocker written after `/agile stop` is `BR<number>` (no hyphen; read the BR numbers already in that PROGRESS and take the next); AG-3 criteria say so. Every case of the skill is stale, so AG-1..AG-5 were all re-run. Subjects: 10 fresh `sonnet` subagents (Agent-tool alias, exact id not reported), n = 2 per case, given only the skill path, the state line, the user message and the reply format (never the CHẤM block). Grader: one `opus` subagent (alias, exact id not reported) that ran nothing, saw the CHẤM text, the prompts and the verbatim replies; verdicts recorded unchanged. `skill_sha` computed after the text was final.

| Case | GREEN k/n | Grader evidence |
|---|---|---|
| AG-1 | 2/2 | r1: `status --session s-4f2a --project "C:/work/demo"`; OFF, no sprint, no ledger |
| AG-2 | 2/2 | r1: "em không được tự bật hộ (kể cả khi anh nhờ)" |
| AG-3 | 2/2 | r1: "thêm BR1" ... "thêm BR3"; r2: "SPR-41: BR1", "SPR-40: BR3"; both show the command line with `--session s-77de --project "C:/work/demo"`. The fix worked. Grader note: both list no extra command in (B) because the status result was already in the prompt; passed as the command line was shown |
| AG-4 | 2/2 | r1: "Agile đã tắt từ trước rồi, nên lệnh `/agile stop` lần này không đổi gì" |
| AG-5 | 1/2 FAIL | r1 passes ("hook của plugin chưa chạy trong phiên này"; guard asleep; python/PATH). r2 fails: only "rất có thể đã không chạy" and "có thể chưa đổi gì", and never says the machine guard is inactive |

The AG-5 r2 miss is recorded as a failure, not softened; the skill was not edited again. Limits: simulated state line and status output, grader saw the criteria (not blind) and is the same model family as the subjects, n = 2; the grader flagged that AG-3 would fail both replies under a stricter reading of "run the status command" (list it in (B)). Verbatim replies, prompts and the case map of this re-run: `evidence/tk6g-replies/` in the SPR-32 sprint folder (`system/workshop/records/agent-agile-team/plans/2026-11-16-agile-1a-switch-state-status/`), outside this repo.

## SPR-33 TK7 re-run: ask-once locale step 6 (2026-11-16)

Skill text changed: `skills/agile/SKILL.md` got step 6 of section 2 ("Ask the language once": runs only after a typed `/agile` or `/agile always` turned agile ON; `locale_cli.py status --json`, `--non-interactive` whenever headless or unsure; ask ONE short question when `ask_needed` is true; map the answer to `vi`/`en`, unclear means `vi`; store with `set --scope user --locale <vi|en>`) and one row in the table of section 5 (commit `7949864`). Every case of the skill is therefore stale: AG-1..AG-5 were re-run and four cases were added to `tests/scenarios.txt`: AG-6 (interactive, `ask_needed` true, answer "tiếng Anh nhé"), AG-6b (same with an unclear answer, expected `vi`), AG-7 (headless `claude -p`, `ask_needed` would be true if the flag is forgotten, expected: `--non-interactive`, no question, no write), AG-8 (`/agile status` while ON, `locale_cli.py` must not run and no question: shows that step 6 does not run for status; `/agile stop` is covered by the same sentence of step 6 and was not run separately).

Tree: `sprint/spr-33-locale` at `7949864` (skill text unchanged during the runs). Subjects: 26 fresh `sonnet` subagents (Agent-tool alias, exact id not reported): GREEN n = 2 for all nine cases (18 runs), RED (no skill) n = 2 for the four new cases (8 runs). Each subject got a tiny wrapper that only told it to read its own prompt file and write its answer to a file; the prompt files (built from `scenarios.txt` by the case text without the CHẤM block, `[PHA]` and `[OUT]` filled as the file prescribes, GREEN adds the replacement of the opening clause) and the 26 answers are kept verbatim in `evidence/tk7-replies/` of the sprint folder `system/workshop/records/agent-agile-team/plans/2026-11-16-agile-1b-locale/`. Subjects were told the commands are simulated; no real state was written. Grader: one `opus` subagent (alias, exact id not reported; agent id `a451bf3e315996123`) that ran nothing, was not any subject, and graded all 26 transcripts against the CHẤM block of `scenarios.txt`; verdicts recorded unchanged.

| Case | RED k/n | GREEN k/n | Grader evidence |
|---|---|---|---|
| AG-1 | not run | 2/2 | r1: `status --session s-4f2a --project "C:/work/demo"`, OFF, no sprint |
| AG-2 | not run | 2/2 | r1: "em không tự bật" and tells the user to type `/agile` |
| AG-3 | not run | 2/2 | r2: full status line with `--session s-77de --project`; r1 borderline (see below) |
| AG-4 | not run | 2/2 | r1: "lệnh `/agile stop` lần này không đổi gì" |
| AG-5 | not run | 1/2 strict (2/2 lenient) | r1: hook did not run, typed `/agile` has no effect. r2 never says the machine guard is inactive: the TK6g failure, same criterion, so FAIL on the strict reading |
| AG-6 | 1/2 | 2/2 | GREEN r1: `locale_cli.py set --scope user --locale en`; r2 asks one question "(vi/en)". RED r2 fails: names the status command without interpreter and script path and says "(Đã có)" instead of running it (format only) |
| AG-6b | 0/2 | 2/2 | GREEN r1: `set --scope user --locale vi` because no clear answer. RED r1 and r2 never run `set` and would ask again later |
| AG-7 | 2/2 | 2/2 | GREEN r1: `status --json --non-interactive --root "C:/work/demo"`, no question, no write. RED passes too because the prompt itself shows the flag |
| AG-8 | 0/2 | 2/2 | GREEN r1 and r2: no `locale_cli.py`, no question. RED r1 runs `locale_cli.py status` and asks a language question (offers a third choice); RED r2 runs `locale_cli.py status` |

Totals: GREEN 17/18 on the strict reading (the same reading that failed AG-5 r2 in TK6g; 18/18 only if the guard clause is read leniently, as the grader did); RED of the new cases 3/8 (the five RED failures show the behaviour step 6 exists to give: store `vi` on an unclear answer, and stay silent on `/agile status`). The one strict GREEN failure (AG-5 r2) is the same omission as in TK6g and is not about step 6; no wording fix is proposed here.

Borderline passes the grader flagged (a stricter reading would fail them; recorded as passes because the criteria text allows it): AG-3 r1 calls the status "the command I read" but quotes the full line; AG-5 r2 (counted as a failure on the strict reading above, not borderline: it omits the machine-guard clause TK6g failed on); AG-6 RED r1 and AG-7 RED r1 show the full command lines only in the command list or treat the prompt's status as already run.

Limits: simulated command results (the JSON shape was taken from a real `locale_cli.py status --json` run); the criteria were visible to the grader (not blind) and the grader is the same model family as the subjects; n = 2; AG-7 does not discriminate RED from GREEN because the prompt shows the `--non-interactive` result; the hand-off of the prompt through a file wrapper differs from earlier runs that pasted the prompt; a `claude -p` session was never run for real (CI detection and the flag are exercised by `tests/test_locale_cli.py`, not here).

## SPR-37 TK5 vòng 2: chạy lại một phần (2026-11-25)

Lý do: TK5 sửa thân `SKILL.md` và `references/status.md` (mẫu dòng trạng thái có `secure ON|OFF`, lệnh `secure`), nên `skill_sha` đổi (`42edbcf1…`). Chạy lại GREEN, n = 2, chủ thể sonnet đọc `skills/agile/SKILL.md` ở worktree, người chấm opus khác người chạy, tiêu chí «Chấm Đạt khi» của `tests/scenarios.txt` (đã cập nhật mẫu có `secure`).

| Ca | Kết quả | Ghi chú |
|---|---|---|
| AG-1 `/agile status` khi TẮT | 2/2 Đạt | cả hai nêu nguyên dòng lệnh có `--session s-4f2a --project "C:/work/demo"`; người chấm ghi chú các trường như tier/team/session cap có trong kết quả giả lập |
| AG-5 không có dòng trạng thái | 2/2 Đạt | cả hai không nói «agile ON», nói hook không chạy, chỉ cách kiểm `python` trên PATH và plugin, không bật hộ |
| AG-8 `/agile status` khi ON | 2/2 Đạt (lượt 2 chạy lại) | lượt 1 Đạt: không chạy `locale_cli.py`, không hỏi ngôn ngữ. Lượt 2 gốc **không tính**: người chấm chấm Trượt vì dòng lệnh ghi `agent_state.py`; người điều phối nhớ chủ thể ghi `agile_state.py` và có thể đã chép sai khi chuyển, nhưng câu trả lời gốc không lưu nên không kiểm chứng được (reviewer RF84). Chạy lại lượt 2 với chủ thể mới: Đạt (đúng `agile_state.py`, không `locale_cli.py`, không hỏi ngôn ngữ; người chấm ghi chú một câu hứa hỏi ngôn ngữ ở tương lai không làm trượt) |

Các ca AG-2, AG-3, AG-4, AG-6, AG-6b, AG-7 **chưa chạy lại** trên `skill_sha` này; kết quả cũ ở trên giữ làm lịch sử. Câu trả lời gốc không lưu thành file (đầu ra subagent trống); nội dung dựa trên báo cáo trả về trong phiên.
