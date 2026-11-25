---
name: tauri-desktop
description: Use when building, configuring, or reviewing a Tauri v2 desktop application shell in Rust — WebView2 window lifecycle, capabilities/permissions (remote.urls, least-privilege IPC), Rust commands and events, Python/Node sidecar management (Windows Job Object zero-zombie), system tray, global shortcuts, native file dialogs, notifications, or Windows MSI/NSIS bundling. Not for general Rust language idioms or non-Tauri crates (that is `rust`).
metadata:
  group: "technique"
  kind: "reference"
  roles: "implementer, architect, tech-reviewer"
---

# Tauri v2 Desktop — vỏ ứng dụng Windows mỏng, an toàn và ổn định

> **Kết luận:** giữ Tauri ở vai trò **vỏ desktop mỏng**, đặt logic nghiệp vụ ở backend hoặc crate Rust độc lập. Mọi quyền WebView đi qua `capabilities/*.json` tối thiểu quyền, sidecar Windows gắn Job Object `KILL_ON_JOB_CLOSE`, và đường dẫn/secret luôn được chặn ở tầng Rust.

## 1. Khi nào dùng và ranh giới

- **Dùng khi:** thiết kế, viết hoặc review lớp vỏ desktop Tauri v2 (đặc biệt trên Windows WebView2): `tauri.conf.json`, `capabilities/default.json`, `#[tauri::command]`, event, sidecar Python/Node, system tray, global shortcut, dialog, notification, single-instance, bộ cài `.msi`/NSIS.
- **Không dùng cho:** thành ngữ ngôn ngữ Rust, ownership, `thiserror`/`anyhow` hay Tokio thuần (dùng skill `rust`); code giao diện web React/Vite (dùng skill `frontend` và `react`).

## 2. Nguyên tắc kiến trúc vỏ mỏng (Desktop Windows)

### 2.1. Origin và Capabilities tối thiểu quyền
- **Đóng gói tĩnh vs Loopback:** ưu tiên `frontendDist` nội bộ kèm CSP chặt; nếu bọc server cục bộ qua `remote.urls` trong capability, chỉ cho phép đúng origin loopback (`http://127.0.0.1:<port>`, `http://localhost:<port>`), cấm mở wildcard `*` hay `http://*`.
- **Capabilities theo cửa sổ:** Tauri v2 mặc định từ chối mọi API hệ thống; chỉ cấp đúng permission cần thiết trong `src-tauri/capabilities/default.json`, gắn rõ `windows: ["main"]` và thu hẹp `scope` đường dẫn/lệnh/URL.
- **Thu hẹp bề mặt IPC:** đặt `"withGlobalTauri": false` khi frontend dùng `@tauri-apps/api`; chỉ bật `true` khi cần progressive enhancement từ trang server thuần không bundler.

### 2.2. Hợp đồng IPC và Chốt chặn ở tầng Rust
- Tách logic ra crate/module thuần; `#[tauri::command]` chỉ validate tham số, gọi logic lõi và trả lỗi serializable (kiểu lỗi đơn giản hoặc enum có `Serialize`).
- Mọi thao tác đọc/ghi/mở file từ lệnh IPC hoặc plugin `fs`/`opener` phải chuẩn hoá đường dẫn ở Rust, chặn `..` path traversal và từ chối tuyệt đối thư mục/file nhạy cảm (`.secret*`, `.env*`, `*.pem`, `*.key`).

### 2.3. Sidecar Zero-Zombie trên Windows
- Spawn sidecar ẩn cửa sổ console bằng `CREATE_NO_WINDOW` (`0x0800_0000`) và gắn handle tiến trình con vào **Windows Job Object** có cờ `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Khi app chính thoát hoặc bị tắt đột ngột, hệ điều hành tự dọn toàn bộ cây tiến trình con.
- Kết hợp `tauri-plugin-single-instance` để chặn mở trùng app và focus lại cửa sổ chính khi người dùng mở lần hai.

### 2.4. Tray, Global Shortcut và Tính năng Desktop
- Chặn sự kiện `CloseRequested` khi cần chế độ **close-to-tray** (`window.hide()` thay vì thoát app), kèm menu tray tường minh để mở lại hoặc thoát sạch (dọn sidecar trước khi `app.exit(0)`).
- Đăng ký `global-shortcut` phải xử lý lỗi nhẹ nhàng (log cảnh báo và tiếp tục chạy nếu phím tắt bị app khác chiếm), cấm `.unwrap()` làm sập app lúc khởi động.

## 3. Kiểm tra nhanh trước khi xong

```bash
cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets
cargo test --manifest-path src-tauri/Cargo.toml
```

- Rà `src-tauri/tauri.conf.json` (CSP, `devUrl`/`frontendDist`, cấu hình `bundle.targets` gồm `nsis`/`msi`).
- Rà `src-tauri/capabilities/*.json`: không cấp `shell:allow-execute` hay `fs:allow-*` không có `scope`.
- Kiểm thực tế vòng đời Windows: mở app → kiểm tra Task Manager không nháy console → tắt đột ngột app chính → xác nhận tiến trình sidecar tắt theo hoàn toàn.

## 4. Đọc gì khi nào

| Cần | Đọc |
|---|---|
| `tauri.conf.json` v2, `capabilities/default.json`, `remote.urls`, `withGlobalTauri`, hợp đồng `#[tauri::command]` + events và bảo vệ path/secret | [capabilities-and-ipc.md](references/capabilities-and-ipc.md) |
| Sidecar Python/Node (`CREATE_NO_WINDOW`), Job Object `KILL_ON_JOB_CLOSE`, single-instance, tray, global-shortcut fallback, dialog/notification và MSI/NSIS | [sidecar-and-windows.md](references/sidecar-and-windows.md) |

## 5. Liên quan và nguồn

- **Skill:** `rust`, `frontend`, `react`, `security-review`, `code-review`, `verify-before-done`.
- **Nguồn:** chắt lọc ý từ `full-stack-skills/tauri-skills` @ `77b57c491` (Apache-2.0) kết hợp thực chiến Tauri v2 Desktop Windows.
