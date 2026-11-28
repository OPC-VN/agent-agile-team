# Khuôn dự án Rust — workspace mẫu và bảng lint

Đọc khi: dựng dự án/workspace Rust mới, thêm crate, hoặc hỏi «vì sao lint này đỏ». Khuôn mẫu ở [`assets/workspace-template/`](../assets/workspace-template/); chép cả thư mục vào repo đích rồi đổi tên crate.

## Workspace mẫu gồm gì

| File | Vai trò |
|---|---|
| `Cargo.toml` | Workspace, `resolver = "3"` (mặc định của edition 2024), `members = ["crates/*"]`, bảng `[workspace.lints]` |
| `rust-toolchain.toml` | Ghim kênh `stable` + `clippy`, `rustfmt`. **Không** ghim `rust-analyzer`: đó là công cụ của IDE, không phải điều kiện build |
| `clippy.toml` | `allow-unwrap-in-tests`, `allow-expect-in-tests`, `allow-panic-in-tests` (xem bên dưới) |
| `deny.toml` | Cho phép `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`, `Unicode-3.0`; cấm registry/git lạ; lỗ hổng và crate bị yanked = deny; crate nội bộ `publish = false` không cần khai license |
| `AGENTS.md` | Mẫu cho repo đích: đường manifest, feature, lệnh xác minh, quy ước `target` |
| `crates/cli` | CLI chỉ dùng std (không phụ thuộc ngoài, build được offline): exit 0/1/2 + một dòng JSON có `kind`, có test đơn vị và test chạy binary |
| `.gitignore` | Bỏ `target/` |

`Cargo.lock`: mẫu **không** kèm; `cargo` tự sinh ở lần build đầu. Repo đích có binary thì **commit** `Cargo.lock`; thư viện thuần có thể bỏ.

## Bảng lint và lý do

| Lint | Mức | Vì sao |
|---|---|---|
| `clippy::unwrap_used`, `panic`, `todo`, `unimplemented`, `dbg_macro` | deny | Lỗi phải đi qua `Result`; ba macro sau là «chưa xong» hoặc gỡ lỗi quên xoá |
| `clippy::undocumented_unsafe_blocks` | warn | Mỗi `unsafe` phải có `// SAFETY:` nêu bất biến |
| `clippy::await_holding_lock` | warn | Giữ khoá `std` qua `.await` gây deadlock |
| `clippy::ptr_arg` | warn | `&Vec<T>`/`&String` thay vì `&[T]`/`&str` |
| `rust::unsafe_code`, `unsafe_op_in_unsafe_fn` | warn | Mọi `unsafe` thành điểm nổi bật; thao tác unsafe trong `unsafe fn` vẫn phải bọc khối riêng |

Mức `warn` trở thành lỗi nhờ cổng `-D warnings`. Crate không có FFI thêm `#![forbid(unsafe_code)]` ở gốc crate (mẫu làm vậy).

Cố ý **không** đặt: `clippy::print_stdout` (CLI cần stdout cho máy đọc), cả nhóm `restriction`, lint `expect_used`. Mọi `#[allow(...)]` phải có `reason = "…"`.

## Kế thừa — dòng dễ quên nhất

Mỗi crate khai `[lints] workspace = true`. Thiếu dòng đó thì bảng lint **không có hiệu lực mà không ai biết**.

**Phép thử bắt buộc khi dựng khuôn mới:** thêm một `.unwrap()` vào mã sản phẩm của crate con rồi chạy `cargo clippy --all-targets -- -D warnings`; phải đỏ (`error: used unwrap() on a Result value`). Bỏ dòng thử đi sau khi thấy đỏ.

## `.unwrap()` và `.expect()` — một quy tắc

- `.unwrap()` cấm ở mã sản phẩm (lint bắt).
- `.expect("…")` chỉ khi bất biến đã được chứng minh bằng mã ngay trước đó, và thông điệp nêu chính bất biến. Cấm trên dữ liệu từ người dùng, file, mạng.
- Không đặt lint `expect_used`; reviewer kiểm quy tắc này.
- Trong test: `clippy.toml` cho phép `unwrap`, `expect`, `panic!` (khoá `allow-panic-in-tests` có hiệu lực trên clippy 0.1.100; bỏ khoá thì `panic!` trong test bị `deny`). `allow-expect-in-tests` chỉ có tác dụng khi repo tự bật `expect_used`; để sẵn.

## Kiểm và hook

- Cổng kiểm trước khi gộp: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test`, `cargo deny --offline check` (tải cơ sở cảnh báo một lần ngoài sandbox: `cargo deny fetch`).
- git pre-commit (khi repo có `Cargo.toml`): **chỉ `cargo fmt --check`**. Clippy trong pre-commit có thể kéo một lần biên dịch nguội dài hàng phút.
- **Không** có hook PostToolUse chạy cargo/fmt/clippy trên bất kỳ nền tảng nào (lý do ở `build-loop.md`).
- `rustfmt.toml`: dùng mặc định, không tạo file.
- Không sửa `[lints]`, `clippy.toml`, `deny.toml` để qua kiểm; cần nới thì ghi quyết định riêng.
