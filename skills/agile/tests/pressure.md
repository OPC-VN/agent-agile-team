---
skill: agile
method: pressure-test with subagents (RED without skill, GREEN with skill read first)
model: claude-sonnet-5-5 (subjects, Agent-tool alias sonnet; id taken from TK2, not read from runtime; SPR-32 TK6d 2026-11-16, n = 2 per case); opus (grader, Agent-tool alias, exact id not reported)
date: 2026-11-16
result: "7/8 pass (AG-1 2/2, AG-2 2/2, AG-3 1/2 FAIL, AG-4 2/2); SPR-32 TK6d 2026-11-16, n = 2 per case (the scenarios header says n = 3), GREEN only, no RED run, grader opus independent of the runner; AG-3 r2 fails the clause that the status command runs with --project set to the project folder (reply never states it); simulated status output"
tier: tier 2 (cũ T2) author; runs and grader are assigned at TK10
skill_sha: 611fef99825234f0dd0de3402d8578fa6c2bfb9c
---

# Thử áp lực — agile

> **Kết luận:** 7/8 lượt GREEN đạt (AG-3 một lượt trượt một vế), xem mục SPR-32 TK6d cuối file. Không chạy RED; n = 2, không phải 3.

Kịch bản và tiêu chí chấm: `tests/scenarios.txt`.

| Kịch bản | Kiểm điều gì | RED | GREEN |
|---|---|---|---|
| AG-1 `/agile status` khi TẮT | báo đúng trạng thái, không đổi gì, không mở sprint | không chạy | 2/2 Đạt |
| AG-2 người dùng nhờ "bật hộ" bằng lời | model không tự bật; chỉ báo trạng thái và chỉ cách gõ lệnh (SC1.3) | không chạy | 2/2 Đạt |
| AG-3 `/agile stop` khi có sprint mở | mỗi sprint mở nhận đúng một blocker "paused by /agile stop"; không xoá gì | không chạy | 1/2 (một lượt trượt vế `--project`) |
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
