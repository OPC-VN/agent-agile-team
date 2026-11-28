---
skill: rust
method: retrieval
model: sonnet
tier: T3
skill_sha: c7877af77a65c934d68bb4c5853e72097eb5e789
date: 2026-11-28
result: "strict 10/10 (+0 partial, 0 fail) — at threshold (≥4/5 scenario questions strict pass and the boundary question strict pass); points-right 10/10"
agent_ids:
  answers: a7ccd5d6a02e218a0
  answers_previous_sha_7a924cfa: a5729ba430ddb3ef2
  answers_previous_sha_1222f98c: a80fd20648004b2f6
  answers_previous_sha_6e57013f: a0603729097c6c7db
  answers_previous_sha_a500b5af: a975ec91c0176cccc
---

Đã đọc: `skills/rust/SKILL.md`, `references/idioms-and-errors.md`, `references/testing-and-tooling.md`, `references/build-loop.md`, `references/windows-pitfalls.md`, `references/project-baseline.md`, và `skills/tauri-desktop/` (SKILL.md, hai reference) cho câu 7

# Thử truy xuất - rust

> **Kết luận:** strict 10/10 (+0 partial, 0 fail), đạt ngưỡng (câu tình huống Đạt hẳn 9/9, câu ranh giới Đạt). Cả 10 câu trỏ đúng mục; ba câu cho ba reference thêm ở SPR-38 (`build-loop.md`, `windows-pitfalls.md`, `project-baseline.md`) trỏ đúng và có nội dung quyết định.

**Giới hạn của lượt này:** lượt thứ sáu cùng ngày, trên skill_sha `c7877af7` (SPR-39: mô tả mở bằng «Use when writing Rust code», thêm mục 6–7 vào `idioms-and-errors.md` và mục «Quy tắc FFI Win32» vào `windows-pitfalls.md`); chủ thể mới `a7ccd5d6a02e218a0` (qa, không đọc `tests/`) trỏ đúng 10/10 và chấm Đạt theo cột kỳ vọng cũ; câu 4 nay trỏ thêm mục 6 (huỷ, `spawn_blocking`). Một lượt (n = 1), người chấm là agent triển khai TK1/TK2 chứ không phải người soạn câu hỏi. Các lượt trước: lượt thứ năm cùng ngày, trên skill_sha `7a924cfa` (chỉ đổi một liên kết thư mục ở bảng «Đọc gì khi nào» của `SKILL.md` thành chữ dạng mã, cho bộ chép Antigravity); lượt thứ tư trên skill_sha `1222f98c` (đổi tên file mẫu `AGENTS.md` → `AGENTS.template.md`, chủ thể `a80fd20648004b2f6`) cũng strict 10/10; lượt thứ ba trên skill_sha `6e57013f` (chủ thể `a0603729097c6c7db`) cũng strict 10/10. Lượt ba (sau sửa review vòng 1: bước tạo `Cargo.lock` lần đầu, CLI mẫu dùng `args_os`, câu chốt cách so đường dẫn ở `windows-pitfalls.md`). Lượt thứ hai (skill_sha `a500b5af`, chủ thể `a975ec91c0176cccc`) cho strict 9/10, câu 9 Một phần vì thiếu đúng câu chốt đó; câu chốt được thêm vì lượt hai chỉ ra, nên câu 9 lượt ba không còn độc lập với lượt hai. Một lượt mỗi skill_sha (n = 1). Câu 1–7 giữ nguyên lượt đầu; câu 8–10 mới ở SPR-38. Người soạn câu hỏi, viết cột kỳ vọng và chấm là cùng một agent (điều phối OpcOS SPR-99); cột kỳ vọng ghi vào file nháp trước khi giao chủ thể. Chủ thể là subagent mới (không đọc `tests/`, không đọc skill khác ngoài `tauri-desktop` khi được trỏ), đánh dấu «(tự suy)» chỗ skill không ghi (câu 2 tên nhánh enum, câu 4 `tokio::time::sleep`).

| # | Câu hỏi | Mục kỳ vọng | Mục agent trỏ | Kết quả |
|---|---|---|---|---|
| 1 | Mình có hàm `fn process(items: &Vec<String>, path: &String)` và trong `impl Worker` vừa lặp `self.items.iter()` vừa gọi `self.log_event(..)` (`&mut self`) nên compiler báo lỗi mượn; mình đang chèn `.clone()` khắp nơi. Chữ ký hàm sửa thế nào, và gỡ xung đột mượn không clone bằng cách nào? | `references/idioms-and-errors.md` › 1; `SKILL.md` › 2.1 | `references/idioms-and-errors.md` › 1; `SKILL.md` › 2.1 | Đạt (thiếu ví dụ mã cụ thể cho `log_event`) |
| 2 | Struct `Request` có `is_loading: bool`, `data: Option<Payload>`, `error: Option<String>` và `email: String` kiểm định dạng lặp ở 6 chỗ. Thiết kế lại thế nào để trạng thái sai không biểu diễn được? Đổi `u32` sang `u16` dùng gì thay `as`? | `references/idioms-and-errors.md` › 2; `SKILL.md` › 2.2 | `references/idioms-and-errors.md` › 2; `SKILL.md` › 2.2 | Đạt |
| 3 | Thư viện crate sẽ publish (semver ổn định) và binary CLI dùng nó: chọn kiểu lỗi cho từng phần ra sao (`thiserror`, `anyhow`, struct Error ẩn kind)? Còn `std::fs::read_to_string(cfg_path).unwrap()` xử lý thế nào? | `references/idioms-and-errors.md` › 3; `SKILL.md` › 2.3 | `references/idioms-and-errors.md` › 3; `SKILL.md` › 2.3 | Đạt |
| 4 | Task `tokio::spawn` giữ `std::sync::MutexGuard` qua `.await`, gọi `std::fs` đọc file lớn và `std::thread::sleep(1s)`, bọc trong `tokio::select!` với `timeout`; thỉnh thoảng treo runtime. Sửa từng chỗ ra sao, chọn kênh nào cho một phản hồi một yêu cầu và cho giá trị cấu hình mới nhất? | `references/idioms-and-errors.md` › 4; `SKILL.md` › 2.5 | `references/idioms-and-errors.md` › 4; `SKILL.md` › 2.5 | Đạt (thiếu mã mẫu `spawn_blocking`) |
| 5 | Chốt cấu hình CI cho workspace Rust nhiều crate và feature flag: lint khai báo ở đâu thay vì `#![deny(warnings)]`, chuỗi lệnh kiểm trước bàn giao, cần chạy gì thêm khi có `unsafe`, kiểm tổ hợp feature thế nào? | `references/testing-and-tooling.md` › 3, › 4; `SKILL.md` › 3 | `references/testing-and-tooling.md` › 3, › 4; `SKILL.md` › 3 | Đạt (không có tệp workflow CI mẫu) |
| 6 | Viết test cho `parse_port` có 12 ca đầu vào và hàm trả `Result<_, MyError>`; cần thư mục tạm, không gọi mạng thật. Chia tầng test thế nào, viết ca bảng và assert lỗi ra sao, thư mục tạm dùng gì? | `references/testing-and-tooling.md` › 1, › 2 | `references/testing-and-tooling.md` › 1, › 2 | Đạt (thiếu cú pháp chi tiết `rstest`, `proptest`, `insta`) |
| 7 | Mình bọc một web UI trong Tauri v2: giới hạn `remote.urls` trong capability cho server loopback cổng 7788, và sidecar Python phải chết theo app chính bằng Windows Job Object. Cấu hình capabilities và Job Object cụ thể ra sao? | mục khác: skill `tauri-desktop` (từ `SKILL.md` › 1) | mục khác: skill `tauri-desktop` (từ `SKILL.md` › 1, › 5), không bịa cấu hình | Đạt |
| 8 | Agent đang sửa một crate qua cầu gọi Codex có sandbox chặn mạng và trần thời gian; build nguội vượt trần, hai subagent chạy `cargo` cùng lúc trên một repo thì chờ khoá. Nên tải phụ thuộc thế nào, đặt thư mục `target` ra sao, thứ tự lệnh và khi nào dừng? | `references/build-loop.md` | `references/build-loop.md` (Quy tắc chung, bảng Giới hạn — dòng Codex) | Đạt |
| 9 | Hàm kiểm «file người dùng chọn nằm trong thư mục cho phép» dùng `canonicalize` cả hai đường rồi so tiền tố chuỗi; trên Windows có junction, đường UNC và file OneDrive chưa tải về. Những bẫy nào và kiểm đúng ra sao? | `references/windows-pitfalls.md` | `references/windows-pitfalls.md` (`\\?\`, junction, placeholder) | Đạt |
| 10 | Dựng repo Rust mới nhiều crate: cấm `unwrap`/`panic`/`todo` ở mã sản phẩm cho mọi crate, cho phép trong test, cổng giấy phép/RustSec, pre-commit thế nào; làm sao chắc crate con kế thừa lint? | `references/project-baseline.md` + `assets/workspace-template/` | `references/project-baseline.md` (Bảng lint, Kế thừa, Kiểm và hook); `assets/workspace-template/` | Đạt |

Cách chấm (một thước cho mọi tệp truy xuất): **Đạt** = trỏ đúng mục và mục đó có nội dung trả lời quyết định chính của câu (phần phụ còn thiếu ghi trong ngoặc và ở mục cuối); **Một phần** = trỏ đúng nơi nhưng nội dung thiếu cho quyết định chính; **Không đạt** = trỏ sai hoặc bịa. Ngưỡng PLAN TK11: tỉ lệ câu tình huống Đạt ≥ 4/5 (80 %) và câu ranh giới Đạt; câu ranh giới tính riêng. `result` ghi số Đạt hẳn (`strict`) và số Một phần; `points-right` là Đạt + Một phần, tức số câu trỏ đúng nơi.

## Thiếu nội dung / mâu thuẫn

- Câu 1: ví dụ mã tách mượn khi gọi `&mut self` trong lúc lặp; khi nào tách thành hàm tự do.
- Câu 4: mã mẫu `spawn_blocking`; cơ chế giải thích vì sao runtime treo.
- Câu 5: tệp workflow CI mẫu, ma trận hệ điều hành và toolchain.
- Câu 6: cú pháp chi tiết `rstest`, `proptest`, `insta`; cách giả lập mạng.
- Câu 4: tên hàm thay `std::thread::sleep` trong task async (skill chỉ cấm, không nêu `tokio::time::sleep`).
- Câu 9: ở lượt hai (skill_sha `a500b5af`) câu này chỉ được chấm nửa điểm vì thiếu câu chốt «so theo thành phần bằng `Path::starts_with` sau khi chuẩn hoá cả hai vế»; câu chốt đã thêm vào `windows-pitfalls.md` (commit `bf2d3fe`), lượt ba và bốn xác nhận.
- Câu 8: thời gian chờ khoá `target` khi hai tiến trình cargo chạy đồng thời vẫn ghi «chưa đo» ở `build-loop.md`.
- Cột kỳ vọng ghi trước được áp nguyên; không sửa skill sau lượt này.
