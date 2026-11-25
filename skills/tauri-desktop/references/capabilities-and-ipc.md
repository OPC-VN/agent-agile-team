# Tauri v2 Capabilities, Config & IPC Contract

## Contents
- [1. Cấu hình `tauri.conf.json` v2 và CSP](#1-cấu-hình-tauriconfjson-v2-và-csp) — Khi thiết lập config gốc và CSP
- [2. `capabilities/default.json` tối thiểu quyền](#2-capabilitiesdefaultjson-tối-thiểu-quyền) — Khi cấp quyền plugin hoặc `remote.urls`
- [3. Hợp đồng Command, State và Events](#3-hợp-đồng-command-state-và-events) — Khi thiết kế giao tiếp Frontend ↔ Rust
- [4. Progressive Enhancement Bridge](#4-progressive-enhancement-bridge) — Khi frontend chạy chung web và Tauri
- [5. Chốt chặn Path và Secret ở tầng Rust](#5-chốt-chặn-path-và-secret-ở-tầng-rust) — Khi lệnh nhận đường dẫn hoặc mở URL

## 1. Cấu hình `tauri.conf.json` v2 và CSP

- Tauri v2 dùng schema `"$schema": "https://schema.tauri.app/config/2"` với cấu trúc `app` tách biệt khỏi `tauri` cũ của v1.
- Tách rõ `build.devUrl` (Vite/server dev) và `build.frontendDist` (thư mục build tĩnh hoặc trỏ loopback có kiểm soát).
- Luôn cấu hình `app.security.csp` chặt chẽ (không dùng `'unsafe-eval'`; chỉ mở `connect-src` tới đúng cổng loopback nếu app gọi API cục bộ).

## 2. `capabilities/default.json` tối thiểu quyền

- Mọi quyền IPC đều bị chặn nếu không khai báo trong `src-tauri/capabilities/*.json`.
- Gắn đúng tên cửa sổ (`"windows": ["main"]`) và nếu webview nạp trang từ server cục bộ, giới hạn `remote.urls` theo cổng cố định hoặc dải loopback rõ ràng:

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Least-privilege desktop capabilities for main window",
  "windows": ["main"],
  "remote": {
    "urls": ["http://127.0.0.1:7788/*", "http://localhost:7788/*"]
  },
  "permissions": [
    "core:default",
    "notification:default",
    {
      "identifier": "dialog:allow-open",
      "allow": [{ "path": "$DOCUMENT/**" }]
    }
  ]
}
```

- **Tránh:** dùng `core:window:default` hoặc `shell:allow-execute` không có `scope` tham số; tuyệt đối không cấp `fs:scope` vào `$HOME/**` hay thư mục chứa secret.

## 3. Hợp đồng Command, State và Events

- **Commands (1-1 request/response):** giữ chữ ký nhỏ, đầu vào `Deserialize`, đầu ra `Result<T, CommandError>` có `Serialize`. Tác vụ nặng dùng `async fn` để không đóng băng luồng chính WebView2.
- **State quản lý bởi Tauri:** dùng `app.manage(AppState::new(...))` và tiêm qua `state: tauri::State<'_, AppState>`; nếu dùng `Mutex`, giữ lock trong phạm vi ngắn nhất trước khi trả về.
- **Events (1-n broadcast):** dùng `app.emit("domain:event", payload)` cho cập nhật bất đồng bộ (trạng thái sidecar, tiến độ); đặt tên event ổn định theo namespace.
- **Tạo type an toàn (tuỳ chọn):** với dự án nhiều command, cân nhắc `tauri-specta` để sinh TypeScript types tự động, tránh lệnh `invoke<any>` lệch kiểu.

## 4. Progressive Enhancement Bridge

- Nếu frontend được build bằng Vite/React riêng cho Tauri: giữ `"withGlobalTauri": false` và import trực tiếp từ `@tauri-apps/api/core`, `@tauri-apps/api/event`.
- Nếu vỏ Tauri bọc một web UI sẵn có (vừa chạy trên trình duyệt thường, vừa chạy trong Tauri): bật `"withGlobalTauri": true` (chỉ kết hợp với `remote.urls` loopback tin cậy) và viết lớp bọc kiểm tra `window.__TAURI_INTERNALS__` (hoặc `window.__TAURI__`) để fallback êm khi mở trên trình duyệt ngoài.

## 5. Chốt chặn Path và Secret ở tầng Rust

- Không bao giờ tin đường dẫn, tên file hoặc URL thô từ frontend gửi qua `invoke`.
- Trước khi thao tác file trong Rust command:
  1. Chuẩn hoá đường dẫn (`fs::canonicalize` hoặc kiểm từng component không chứa `Component::ParentDir`).
  2. Kiểm tra đường dẫn nằm trong thư mục cho phép của ứng dụng.
  3. Từ chối thẳng mọi đường dẫn chạm `.secret`, `.env`, `*.pem`, `*.key`, `auth.json`, `oauth_creds.json`.
- Với lệnh mở URL ngoài (`tauri-plugin-opener`): chỉ chấp nhận scheme `https://` hoặc `http://localhost`, chặn `file://`, `javascript:` hoặc `ms-msdt:`.
