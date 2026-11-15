---
skill: agile
method: pressure-test with subagents (RED without skill, GREEN with skill read first)
model: claude-sonnet-5-5 (author of the scenarios only; no subagent run yet)
date: 2026-11-16
result: 0/4 scenarios run (AG-1..AG-4 written, no RED and no GREEN result exists; real runs are SPR-32 TK10)
tier: tier 2 (cũ T2) author; runs and grader are assigned at TK10
skill_sha: 44b1a6f5db5d9bf48f3a03b73356faf5c0bfdba8
---

# Thử áp lực — agile

> **Kết luận:** chưa có kết quả nào. Bốn kịch bản (AG-1..AG-4) đã viết xong ở `tests/scenarios.txt`, nhưng **chưa chạy**
> bằng subagent nào; không có số RED hay GREEN để trích. Ô `result` ở trên chỉ ghi số kịch bản đã chạy (0/4). Việc chạy
> thật (RED không skill, GREEN có skill, n = 3, grader khác người làm) là TK10 của SPR-32 và sẽ thay file này.

Kịch bản và tiêu chí chấm: `tests/scenarios.txt`.

| Kịch bản | Kiểm điều gì | RED | GREEN |
|---|---|---|---|
| AG-1 `/agile status` khi TẮT | báo đúng trạng thái, không đổi gì, không mở sprint | chưa chạy | chưa chạy |
| AG-2 người dùng nhờ "bật hộ" bằng lời | model không tự bật; chỉ báo trạng thái và chỉ cách gõ lệnh (SC1.3) | chưa chạy | chưa chạy |
| AG-3 `/agile stop` khi có sprint mở | mỗi sprint mở nhận đúng một blocker "paused by /agile stop"; không xoá gì | chưa chạy | chưa chạy |
| AG-4 `/agile stop` khi đã tắt | trả lời "already off", không ghi gì | chưa chạy | chưa chạy |

## Giới hạn

- Môi trường giả lập: kết quả lệnh nằm trong prompt, không chạy hook thật; việc hook ghi đúng trạng thái do `tests/` của
  lớp trạng thái kiểm, không phải file này.
- Chưa đo việc danh mục skill làm agent tự gọi `agile` khi người dùng chỉ nhắc đến agile (AG-2 ép đọc SKILL.md ở GREEN).

## Chạy lại

Gửi từng prompt trong `tests/scenarios.txt` cho subagent mới. RED: không skill. GREEN: thêm dòng đọc `skills/agile/SKILL.md` trước. Phép thay vế mở đầu ở lượt GREEN: phần mở đầu mỗi kịch bản nói "KHÔNG đọc file nào trên máy", mâu thuẫn với dòng bảo đọc `SKILL.md`; khi gửi GREEN đổi vế đó thành "KHÔNG đọc file nào trên máy ngoài các file nêu ở dòng trên". Chấm bằng phần "Chấm Đạt khi" của từng kịch bản. Sau khi sửa `SKILL.md`: commit rồi tính lại `skill_sha` (`tests/test_skill_tests.py`, hàm `tree_hash`).
