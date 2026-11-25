# Tauri v2 Sidecar & Windows Desktop Lifecycle

## Contents
- [1. Sidecar Python / Node.js trên Windows](#1-sidecar-python--nodejs-trên-windows) — Khi nhúng hoặc chạy server phụ đi kèm
- [2. Windows Job Object (`KILL_ON_JOB_CLOSE`) chống Zombie](#2-windows-job-object-kill_on_job_close-chống-zombie) — Khi bảo đảm sidecar tắt cùng app chính
- [3. Single Instance, System Tray và Close-to-Tray](#3-single-instance-system-tray-và-close-to-tray) — Khi quản lý cửa sổ và vòng đời chạy nền
- [4. Global Shortcut, Dialog và Notification](#4-global-shortcut-dialog-và-notification) — Khi tích hợp API hệ điều hành Windows
- [5. Đóng gói Windows MSI / NSIS](#5-đóng-gói-windows-msi--nsis) — Khi build bộ cài phát hành

## 1. Sidecar Python / Node.js trên Windows

- **Hai cách tổ chức:**
  - *Sidecar đóng gói (`externalBin`):* biên dịch/đóng gói binary theo target triple (ví dụ `my-server-x86_64-pc-windows-msvc.exe`) và khai báo trong `bundle.externalBin` (chạy qua `tauri-plugin-shell` hoặc Rust `Command`).
  - *Tiến trình quản lý trực tiếp bởi Rust:* khi sidecar cần môi trường Python/Node sẵn có hoặc virtualenv cục bộ, Rust tự tìm binary hợp lệ và gọi qua `std::process::Command`.
- **Ẩn cửa sổ console Windows:** khi spawn bằng `std::process::Command` trên Windows release build (`windows_subsystem = "windows"`), luôn gắn cờ `CREATE_NO_WINDOW`:

```rust
#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

// Khi dựng Command:
// cmd.creation_flags(CREATE_NO_WINDOW);
```

- **Thu thập log & readiness:** đọc `stdout`/`stderr` ở thread/task riêng để pipe không bị đầy gây treo sidecar; kiểm health endpoint loopback với timeout rõ ràng trước khi hiện cửa sổ chính.

## 2. Windows Job Object (`KILL_ON_JOB_CLOSE`) chống Zombie

- Trên Windows, gọi `child.kill()` trong hook thoát bình thường sẽ **không chạy** nếu app chính bị crash hoặc bị tắt bằng Task Manager, khiến Python/Node sidecar sống sót thành zombie và giữ chặt cổng TCP.
- **Giải pháp chuẩn:** tạo một Windows Job Object khi khởi động, bật `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` trong `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`, gán handle tiến trình con vào Job Object bằng `AssignProcessToJobObject`, và giữ handle Job Object đó sống suốt vòng đời `AppState`.
- Khi tiến trình Tauri kết thúc vì bất kỳ lý do gì, kernel Windows đóng handle Job Object và kết liễu toàn bộ cây tiến trình con ngay lập tức.
- Đặt toàn bộ phần `unsafe` gọi Win32 (`windows-sys` hoặc `windows`) trong một module hẹp có `// SAFETY:` và test đóng nóng trên Windows thật.

## 3. Single Instance, System Tray và Close-to-Tray

- **Single Instance (`tauri-plugin-single-instance`):** đăng ký plugin đầu tiên trong `tauri::Builder`; trong callback khi có instance thứ hai mở lên, lấy cửa sổ `"main"`, gọi `show()`, `unminimize()` và `set_focus()`.
- **System Tray:** tạo menu tối thiểu (`Mở cửa sổ`, `Thoát`) bằng `TrayIconBuilder`; sự kiện click trái khôi phục và focus cửa sổ chính.
- **Close-to-Tray:** lắng nghe `on_window_event`: nếu sự kiện là `WindowEvent::CloseRequested` và người dùng bật chạy nền, gọi `api.prevent_close()` + `window.hide()`. Chỉ thoát thật khi người dùng bấm `Thoát` ở menu tray — lúc đó dọn tài nguyên rồi gọi `app.exit(0)`.

## 4. Global Shortcut, Dialog và Notification

- **Global Shortcut an toàn:** phím tắt toàn cục trên Windows rất dễ trùng với ứng dụng khác (PowerToys, trình duyệt, phần mềm gõ). Bọc `app.global_shortcut().register(...)` trong `match` — nếu lỗi thì ghi log cảnh báo và phát event báo UI thay vì `.unwrap()` làm sập app.
- **Dialog và Notification:** dùng `tauri-plugin-dialog` (lọc `extensions` file rõ ràng) và `tauri-plugin-notification` (kiểm tra quyền trước khi gửi); khai báo chính xác permission tương ứng trong `capabilities/default.json` thay vì mở toàn bộ `default` nếu không dùng hết.

## 5. Đóng gói Windows MSI / NSIS

- Cấu hình `bundle` trong `tauri.conf.json`: đặt `identifier` duy nhất (`com.org.app`), `icon` đủ cỡ `.ico`, và `bundle.targets` (`"nsis"` cho bộ cài nhẹ hỗ trợ cài theo user không cần quyền admin, hoặc `"msi"` cho doanh nghiệp).
- Kiểm tra `webviewInstallMode` phù hợp (mặc định Windows 11 đã có sẵn WebView2 Evergreen).
- Checklist trước phát hành: chạy `cargo tauri build`, cài thử bộ cài trên máy sạch (hoặc user không phải admin), kiểm tra app mở/đóng tray, cập nhật không đụng file đang bị sidecar khoá, và cài chữ ký số (code signing) trước khi phân phối rộng rãi.
