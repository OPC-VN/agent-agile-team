---
title: Rust standard — short rules
type: method
status: active
updated: 2026-11-28
---


# Chuẩn Rust

> **Kết luận:** Rust bản **stable** ghim bằng `rust-toolchain.toml`, bảng lint đặt ở **workspace** và mỗi crate
> kế thừa, cổng kiểm **`cargo fmt --check` + `clippy -D warnings` + test**, `unsafe` hiếm và luôn có chứng minh,
> lỗi có kiểu (`thiserror` ở thư viện, `anyhow` ở binary), coverage **80 % code mới/sửa**. Chuẩn này giữ luật
> ngắn; mẫu code, lý do và ví dụ nằm ở skill `rust` (và `tdd`, `error-handling`). Bổ sung cho luật chung trong
> `common/`.

## Công cụ và lint

- `rust-toolchain.toml` ghim stable kèm `clippy`, `rustfmt` (không ghim `rust-analyzer`). `rustfmt.toml` để mặc định.
- Mỗi crate khai `[lints] workspace = true`. **Phép thử:** thêm một `.unwrap()` vào mã sản phẩm của crate con →
  `cargo clippy -- -D warnings` phải đỏ; thiếu dòng kế thừa thì bảng lint vô hiệu mà không ai biết.
- Cấu hình lint không bị sửa để qua kiểm (`AGENTS.md`).

| Nơi khai | Lint | Mức |
|---|---|---|
| `[workspace.lints.clippy]` | `unwrap_used`, `panic`, `todo`, `unimplemented`, `dbg_macro` | `deny` |
| `[workspace.lints.clippy]` | `undocumented_unsafe_blocks`, `await_holding_lock`, `ptr_arg` | `warn` (cổng `-D warnings` biến thành lỗi) |
| `[workspace.lints.rust]` | `unsafe_code`, `unsafe_op_in_unsafe_fn` | `warn` |
| gốc crate không có FFI | `#![forbid(unsafe_code)]` | cấm hẳn |
| `clippy.toml` | `allow-unwrap-in-tests`, `allow-expect-in-tests` = `true`; nới `panic` trong test | — |

- **Không** đặt `print_stdout` (CLI cần stdout máy đọc); không bật cả nhóm `restriction`.
- Mọi `#[allow(...)]` có `reason = "…"`.
- `deny.toml`: chỉ giấy phép trong danh sách cho phép (`MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`,
  `ISC`, `Unicode-3.0`), cấm registry lạ, lỗ hổng là `deny`.
- pre-commit chỉ `cargo fmt --check`; clippy, test, deny, độ phủ chạy ở cổng kiểm trước khi gộp.

## `unwrap` và `expect` — một quy tắc

- `.unwrap()` **cấm** ở mã sản phẩm (lint bắt).
- `.expect("…")` chỉ khi bất biến đã được chứng minh bằng mã ngay trước đó và thông điệp **nêu bất biến**; cấm
  trên dữ liệu từ người dùng, file, mạng. Không có lint `expect_used` — reviewer kiểm (agent `rust-reviewer`).
- Test được dùng cả hai.

## `unsafe` và FFI

- `unsafe` chỉ ở module nhỏ, tách riêng; mỗi khối có `// SAFETY:` nêu bất biến và vì sao đúng ở chỗ đó.
- Bọc FFI bằng giao diện an toàn: kiểm giá trị trả về lỗi, cấp phát và giải phóng cùng một phía, không để panic
  lan qua ranh giới `extern "C"`, `#[repr(C)]` cho kiểu qua ranh giới.
- Không `transmute` để qua trình biên dịch; không khai `Send`/`Sync` tay khi không có lập luận.

## Lỗi

- Thư viện: kiểu lỗi có tên bằng `thiserror`; binary: `anyhow` kèm ngữ cảnh (`.context(…)`) ở biên.
- Không nuốt lỗi (`let _ =`, `.ok()` che lỗi); lỗi tả bằng điều người dùng thấy (skill `error-handling`).

## Async

- Không gọi chặn trong `async fn` (I/O đồng bộ, `sleep` của thread, `Command::output`) → `spawn_blocking` hay bản async.
- Không giữ khoá đồng bộ qua `.await`; mọi tác vụ `spawn` có chủ chờ hoặc huỷ.

## Windows

- Tiến trình con: danh sách đối số (không ghép chuỗi qua shell), đóng stdin khi chạy nền, có hạn chờ, dọn tiến trình con.
- Đường dẫn: kiểm giới hạn bằng đường đã chuẩn hoá và tính junction, UNC, tiền tố `\\?\`; không so chuỗi thô.
- Stdout dành cho dữ liệu máy đọc, log sang stderr; mã exit theo hợp đồng của công cụ.

## Kiểm thử

- Dùng `cargo test`; test trước code (skill `tdd`); ngưỡng **80 % code mới/sửa** (`common/testing.md`).
- Test đường lỗi và biên, không chỉ đường vui; test không phụ thuộc thứ tự hay thời gian thật.
- Chi tiết: skill `rust`.

## Xem thêm

Skill `rust`, `error-handling`, `tdd`; agent `rust-reviewer`, `silent-failure-hunter`.
