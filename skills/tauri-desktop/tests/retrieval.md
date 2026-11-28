---
skill: tauri-desktop
method: retrieval
model: sonnet
tier: T3
skill_sha: 51f75988c334449d8fe8df0391b1cd74772821e1
date: 2026-11-28
result: "strict 7/7 (+0 partial, 0 fail) — at threshold (≥4/5 scenario questions strict pass and the boundary question strict pass); points-right 7/7"
agent_ids:
  answers: ae8ac4fb71cc76eb8
---

Đã đọc: `<gốc worktree>/skills/tauri-desktop/SKILL.md`, cùng `references/capabilities-and-ipc.md` và `references/sidecar-and-windows.md`

# Thử truy xuất - tauri-desktop

> **Kết luận:** strict 7/7 (+0 partial, 0 fail), đạt ngưỡng (câu tình huống Đạt hẳn 6/6, câu ranh giới Đạt). Cả 6 câu tình huống trỏ đúng mục và mục có nội dung quyết định; câu ranh giới (Rust thuần) trỏ đúng sang `rust` và không bịa.

**Giới hạn của lượt này:** lượt đầu tiên của skill này, một lượt (n = 1). Người soạn câu hỏi, viết cột kỳ vọng và chấm là cùng một agent; cột kỳ vọng ghi vào file nháp trước khi giao chủ thể (thứ tự: ghi kỳ vọng, giao chủ thể, chấm) nhưng câu hỏi soạn từ nội dung skill nên dễ chạm đúng mục, điểm số không độc lập. Chủ thể là subagent mới (không đọc `tests/`, không đọc skill khác), được dặn nói thẳng khi skill không có phần câu hỏi cần.

| # | Câu hỏi | Mục kỳ vọng | Mục agent trỏ | Kết quả |
|---|---|---|---|---|
| 1 | Webview Tauri v2 nạp UI từ server cục bộ `http://127.0.0.1:7788`. Capability khai `remote.urls` thế nào, có nên bật `withGlobalTauri`, và permission nào cần tránh cấp (`shell:allow-execute`, `fs:*`)? | `references/capabilities-and-ipc.md` › 2, › 4; `SKILL.md` › 2.1 | `references/capabilities-and-ipc.md` › 2, › 4; `SKILL.md` › 2.1, › 3 | Đạt |
| 2 | Một `#[tauri::command]` nhận đường dẫn file từ frontend để đọc, và một command khác mở URL ngoài bằng opener. Cần chặn gì ở tầng Rust, theo bước nào, cho phép scheme nào, từ chối file nào? | `references/capabilities-and-ipc.md` › 5; `SKILL.md` › 2.2 | `references/capabilities-and-ipc.md` › 5; `SKILL.md` › 2.2 | Đạt (thiếu xử lý symlink và đường UNC) |
| 3 | Sidecar Python của app Tauri trên Windows nháy cửa sổ console, và khi app crash hoặc bị tắt bằng Task Manager thì Python vẫn sống, giữ cổng TCP. Giải pháp cụ thể là gì (cờ, API, handle sống bao lâu)? | `references/sidecar-and-windows.md` › 1, › 2; `SKILL.md` › 2.3 | `references/sidecar-and-windows.md` › 1, › 2; `SKILL.md` › 2.3 | Đạt (thiếu thứ tự gọi API Win32 và mã mẫu `unsafe`) |
| 4 | Muốn close-to-tray, chặn mở app lần hai (focus lại cửa sổ cũ) và đăng ký global shortcut mà không sập app khi phím bị app khác chiếm. Làm từng phần thế nào? | `references/sidecar-and-windows.md` › 3, › 4; `SKILL.md` › 2.4 | `references/sidecar-and-windows.md` › 3, › 4; `SKILL.md` › 2.3, › 2.4 | Đạt (thiếu mã mẫu đầy đủ) |
| 5 | Chuẩn bị bộ cài Windows: chọn NSIS hay MSI, `bundle.externalBin` đặt tên binary sidecar ra sao, `webviewInstallMode`, và checklist trước phát hành? | `references/sidecar-and-windows.md` › 5, › 1 | `references/sidecar-and-windows.md` › 5, › 1; `SKILL.md` › 3 | Đạt (thiếu giá trị cụ thể của `webviewInstallMode` và cách ký số) |
| 6 | Thiết kế giao tiếp frontend và Rust cho app có tác vụ nặng và cập nhật tiến độ sidecar: command hay event dùng khi nào, kiểu lỗi trả về, quản lý state có Mutex, có cách sinh type TypeScript tự động không? | `references/capabilities-and-ipc.md` › 3 | `references/capabilities-and-ipc.md` › 3; `SKILL.md` › 2.2 | Đạt (thiếu mẫu `CommandError` và cách dùng `tauri-specta`) |
| 7 | Trong một crate Rust thuần (không phải Tauri), enum lỗi định dùng `thiserror` nhưng binary cần `anyhow` ở tầng trên cùng; và task tokio giữ `std::sync::MutexGuard` qua `.await`. Chọn lỗi và sửa deadlock thế nào? | mục khác: skill `rust` (từ `SKILL.md` › 1) | mục khác: skill `rust` (từ `SKILL.md` › 1, › 5), không bịa nội dung | Đạt |

Cách chấm (một thước cho mọi tệp truy xuất): **Đạt** = trỏ đúng mục và mục đó có nội dung trả lời quyết định chính của câu (phần phụ còn thiếu ghi trong ngoặc và ở mục cuối); **Một phần** = trỏ đúng nơi nhưng nội dung thiếu cho quyết định chính; **Không đạt** = trỏ sai hoặc bịa. Ngưỡng PLAN TK11: tỉ lệ câu tình huống Đạt ≥ 4/5 (80 %) và câu ranh giới Đạt; câu ranh giới tính riêng. `result` ghi số Đạt hẳn (`strict`) và số Một phần; `points-right` là Đạt + Một phần, tức số câu trỏ đúng nơi.

## Thiếu nội dung / mâu thuẫn

- Câu 2: xử lý symlink và đường UNC, cách xác định thư mục cho phép.
- Câu 3: tên API Win32 và thứ tự gọi, mã mẫu `unsafe`.
- Câu 4: mã mẫu đầy đủ, quyền tray và global-shortcut trong capabilities.
- Câu 5: giá trị cụ thể của `webviewInstallMode`, cách ký số.
- Câu 6: mẫu `CommandError`, cách dùng `tauri-specta`.
- Cột kỳ vọng ghi trước được áp nguyên; không sửa skill sau lượt này.
