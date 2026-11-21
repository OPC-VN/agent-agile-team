---
id: SPR-05-task
doc: task
title: Sửa chữ gợi ý ô mã đơn trống ở màn hình tra đơn
sprint: SPR-05
request: RQ-006
feature: FS-001
status: done
size: tiny
risk: normal
risk_tags: []
review_round: 0
gate_1: approved
gate_1_at: 2026-01-24 09:00 +07
gate_1_quote: "đạt theo lời giao: đổi chữ gợi ý ô mã đơn trống thành Nhập mã đơn, chỉ đổi chữ"
verdict: pass
gate_2: pass
gate_2_at: 2026-01-24 15:00 +07
gate_2_quote: "nghiệm thu ngầm — không phản đối tới 2026-01-24 15:00 +07"
roles:
  analyst: [T1, agent-a]
  implementer: [T2, agent-e]
  tech-reviewer: [T1, agent-d]
created: 2026-01-24
updated: 2026-01-24
---

# Sửa chữ gợi ý ô mã đơn trống ở màn hình tra đơn — Việc đơn lẻ (TASK)

<!-- Cỡ RẤT NHỎ: một file TASK.md hai phần Kế hoạch / Kết quả. Cổng 1 = "đạt theo lời giao"; Cổng 2 gộp vào lời báo cuối,
     nghiệm thu ngầm ghi trung thực. Mẫu: templates/sprint/TASK.md (dựng bằng `init --tiny`). -->

> **Kết luận:** ô mã đơn trống ở màn hình tra đơn đã hiện gợi ý "Nhập mã đơn"; test giao diện xanh, agent khác kiểm xong; Đạt.

## 1. Kế hoạch

<!-- Lời giao trích nguyên văn · mục tiêu một dòng · mỗi SC đo được · mỗi TK trỏ SC, kèm cách kiểm và hoàn tác. -->

- **Lời giao:** "đổi chữ gợi ý ô mã đơn trống thành Nhập mã đơn, chỉ đổi chữ" (RQ-006, tính năng FS-001).
- **Mục tiêu:** ô mã đơn trống ở màn hình tra đơn hiện đúng chữ gợi ý "Nhập mã đơn".

Kế hoạch có 1 **success criterion** (SC) và 1 **task** (TK):

- **SC1 (chữ đúng):** test giao diện so khớp chữ gợi ý của ô mã đơn trống bằng "Nhập mã đơn".
- **TK1 (đổi chữ gợi ý) → SC1:** Implementer · T2. Cách kiểm: test giao diện xanh. Hoàn tác: `git revert`.

## 2. Kết quả

<!-- Nhật ký ngắn của việc đã làm · mỗi SC một VR do agent khác chạy · hoàn tác · Cổng 2. -->

- **2026-01-24 10:00 +07** — Implementer đổi chữ gợi ý trong `ui/lookup_order.html` và chữ kỳ vọng trong test; test xanh.
- **2026-01-24 10:20 +07** — Tech Reviewer (agent khác) chạy lại test và đọc diff: chỉ đổi chữ gợi ý.

Kết quả có 1 **verification result** (VR):

| Mã | Kiểm cái gì | Lệnh / thao tác | Kết quả | Người kiểm |
|---|---|---|---|---|
| VR1 (test chữ gợi ý) | SC1 | `pytest tests/test_ui.py` → 1 passed | Đạt | Tech Reviewer · agent-d |

- **Hoàn tác / đã đổi gì:** chữ gợi ý trong `ui/lookup_order.html`; hoàn tác bằng `git revert`.
- **Cổng 2:** gộp vào lời báo cuối; nghiệm thu ngầm — không phản đối tới 2026-01-24 15:00 +07.
