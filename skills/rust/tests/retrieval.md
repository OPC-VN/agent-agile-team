---
skill: rust
method: retrieval
model: sonnet
tier: T3
skill_sha: f4b069218ee6204d49818242ec3cb31859b4e8c0
date: 2026-11-28
result: "strict 7/7 (+0 partial, 0 fail) — at threshold (≥4/5 scenario questions strict pass and the boundary question strict pass); points-right 7/7"
agent_ids:
  answers: a35ce509c7cfcc81f
---

Đã đọc: `<gốc worktree>/skills/rust/SKILL.md`, cùng `references/idioms-and-errors.md` và `references/testing-and-tooling.md`

# Thử truy xuất - rust

> **Kết luận:** strict 7/7 (+0 partial, 0 fail), đạt ngưỡng (câu tình huống Đạt hẳn 6/6, câu ranh giới Đạt). Cả 6 câu tình huống trỏ đúng mục và mục có nội dung quyết định; câu ranh giới (Tauri) trỏ đúng sang `tauri-desktop` và không bịa.

**Giới hạn của lượt này:** lượt đầu tiên của skill này, một lượt (n = 1). Người soạn câu hỏi, viết cột kỳ vọng và chấm là cùng một agent; cột kỳ vọng ghi vào file nháp trước khi giao chủ thể (thứ tự: ghi kỳ vọng, giao chủ thể, chấm) nhưng câu hỏi soạn từ nội dung skill nên dễ chạm đúng mục, điểm số không độc lập. Chủ thể là subagent mới (không đọc `tests/`, không đọc skill khác), được dặn nói thẳng khi skill không có phần câu hỏi cần.

| # | Câu hỏi | Mục kỳ vọng | Mục agent trỏ | Kết quả |
|---|---|---|---|---|
| 1 | Mình có hàm `fn process(items: &Vec<String>, path: &String)` và trong `impl Worker` vừa lặp `self.items.iter()` vừa gọi `self.log_event(..)` (`&mut self`) nên compiler báo lỗi mượn; mình đang chèn `.clone()` khắp nơi. Chữ ký hàm sửa thế nào, và gỡ xung đột mượn không clone bằng cách nào? | `references/idioms-and-errors.md` › 1; `SKILL.md` › 2.1 | `references/idioms-and-errors.md` › 1; `SKILL.md` › 2.1 | Đạt (thiếu ví dụ mã cụ thể cho `log_event`) |
| 2 | Struct `Request` có `is_loading: bool`, `data: Option<Payload>`, `error: Option<String>` và `email: String` kiểm định dạng lặp ở 6 chỗ. Thiết kế lại thế nào để trạng thái sai không biểu diễn được? Đổi `u32` sang `u16` dùng gì thay `as`? | `references/idioms-and-errors.md` › 2; `SKILL.md` › 2.2 | `references/idioms-and-errors.md` › 2; `SKILL.md` › 2.2 | Đạt |
| 3 | Thư viện crate sẽ publish (semver ổn định) và binary CLI dùng nó: chọn kiểu lỗi cho từng phần ra sao (`thiserror`, `anyhow`, struct Error ẩn kind)? Còn `std::fs::read_to_string(cfg_path).unwrap()` xử lý thế nào? | `references/idioms-and-errors.md` › 3; `SKILL.md` › 2.3 | `references/idioms-and-errors.md` › 3; `SKILL.md` › 2.3 | Đạt |
| 4 | Task `tokio::spawn` giữ `std::sync::MutexGuard` qua `.await`, gọi `std::fs` đọc file lớn và `std::thread::sleep(1s)`, bọc trong `tokio::select!` với `timeout`; thỉnh thoảng treo runtime. Sửa từng chỗ ra sao, chọn kênh nào cho một phản hồi một yêu cầu và cho giá trị cấu hình mới nhất? | `references/idioms-and-errors.md` › 4; `SKILL.md` › 2.5 | `references/idioms-and-errors.md` › 4; `SKILL.md` › 2.5 | Đạt (thiếu mã mẫu `spawn_blocking`) |
| 5 | Chốt cấu hình CI cho workspace Rust nhiều crate và feature flag: lint khai báo ở đâu thay vì `#![deny(warnings)]`, chuỗi lệnh kiểm trước bàn giao, cần chạy gì thêm khi có `unsafe`, kiểm tổ hợp feature thế nào? | `references/testing-and-tooling.md` › 3, › 4; `SKILL.md` › 3 | `references/testing-and-tooling.md` › 3, › 4; `SKILL.md` › 3 | Đạt (không có tệp workflow CI mẫu) |
| 6 | Viết test cho `parse_port` có 12 ca đầu vào và hàm trả `Result<_, MyError>`; cần thư mục tạm, không gọi mạng thật. Chia tầng test thế nào, viết ca bảng và assert lỗi ra sao, thư mục tạm dùng gì? | `references/testing-and-tooling.md` › 1, › 2 | `references/testing-and-tooling.md` › 1, › 2 | Đạt (thiếu cú pháp chi tiết `rstest`, `proptest`, `insta`) |
| 7 | Mình bọc một web UI trong Tauri v2: giới hạn `remote.urls` trong capability cho server loopback cổng 7788, và sidecar Python phải chết theo app chính bằng Windows Job Object. Cấu hình capabilities và Job Object cụ thể ra sao? | mục khác: skill `tauri-desktop` (từ `SKILL.md` › 1) | mục khác: skill `tauri-desktop` (từ `SKILL.md` › 1, › 5), không bịa cấu hình | Đạt |

Cách chấm (một thước cho mọi tệp truy xuất): **Đạt** = trỏ đúng mục và mục đó có nội dung trả lời quyết định chính của câu (phần phụ còn thiếu ghi trong ngoặc và ở mục cuối); **Một phần** = trỏ đúng nơi nhưng nội dung thiếu cho quyết định chính; **Không đạt** = trỏ sai hoặc bịa. Ngưỡng PLAN TK11: tỉ lệ câu tình huống Đạt ≥ 4/5 (80 %) và câu ranh giới Đạt; câu ranh giới tính riêng. `result` ghi số Đạt hẳn (`strict`) và số Một phần; `points-right` là Đạt + Một phần, tức số câu trỏ đúng nơi.

## Thiếu nội dung / mâu thuẫn

- Câu 1: ví dụ mã tách mượn khi gọi `&mut self` trong lúc lặp; khi nào tách thành hàm tự do.
- Câu 4: mã mẫu `spawn_blocking`; cơ chế giải thích vì sao runtime treo.
- Câu 5: tệp workflow CI mẫu, ma trận hệ điều hành và toolchain.
- Câu 6: cú pháp chi tiết `rstest`, `proptest`, `insta`; cách giả lập mạng.
- Cột kỳ vọng ghi trước được áp nguyên; không sửa skill sau lượt này.
