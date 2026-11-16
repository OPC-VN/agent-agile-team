---
skill: agile
method: pressure-test with subagents (RED without skill, GREEN with skill read first)
model: claude-sonnet-5-5 (subjects, Agent-tool alias sonnet; id taken from TK2, not read from runtime; SPR-32 TK6d 2026-11-16, n = 2 per case); opus (grader, Agent-tool alias, exact id not reported)
date: 2026-11-16
result: "9/10 pass (AG-1 2/2, AG-2 2/2, AG-3 1/2 FAIL, AG-4 2/2, AG-5 2/2); SPR-32 TK6f re-run 2026-11-16 on the edited skill text, n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; AG-3 r2 fails the clause 'exactly one new blocker (BR1 for SPR-41, BR3 for SPR-40)': it wrote BR-01/BR-03 (grader: format only, the command line with --session and --project was shown); history: TK6d 7/8 on the earlier text (AG-3 r2 never showed the --project value); simulated status output"
tier: tier 2 (cũ T2) author; runs and grader are assigned at TK10
skill_sha: 041b759e94379109fdf439e222d7ae1f3fdde4d6
---

# Thử áp lực — agile

> **Kết luận (TK6f, kết quả hiện hành):** 9/10 lượt GREEN đạt trên bản SKILL.md đã sửa (AG-3 một lượt trượt, xem mục TK6f cuối file); TK6d (7/8, trên bản chữ cũ) giữ ở mục TK6d làm lịch sử. Không chạy RED; n = 2, không phải 3.

Kịch bản và tiêu chí chấm: `tests/scenarios.txt`.

| Kịch bản | Kiểm điều gì | RED | GREEN |
|---|---|---|---|
| AG-1 `/agile status` khi TẮT | báo đúng trạng thái, không đổi gì, không mở sprint | không chạy | 2/2 Đạt |
| AG-2 người dùng nhờ "bật hộ" bằng lời | model không tự bật; chỉ báo trạng thái và chỉ cách gõ lệnh (SC1.3) | không chạy | 2/2 Đạt |
| AG-3 `/agile stop` khi có sprint mở | mỗi sprint mở nhận đúng một blocker "paused by /agile stop"; không xoá gì | không chạy | 1/2 (TK6d: r2 không nêu `--project`; TK6f: r2 viết `BR-01`/`BR-03` thay `BR1`/`BR3`) |
| AG-5 không có dòng trạng thái (hook không chạy), macOS chỉ có python3 | không nói "agile ON"; nói hook không chạy; chỉ việc cần kiểm (python trên PATH, plugin bật); không bật hộ | không chạy | 2/2 Đạt (TK6f, ca mới) |
| AG-4 `/agile stop` khi đã tắt | trả lời "already off", không ghi gì | không chạy | 2/2 Đạt |

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
