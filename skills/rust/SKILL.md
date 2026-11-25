---
name: rust
description: Use when writing, reviewing, or refactoring Rust code, designing Rust crates or modules, configuring Cargo/clippy/rustfmt/tests, handling ownership/borrowing/lifetimes, error types (thiserror/anyhow), async Tokio concurrency, or Windows FFI/process safety. Not for Tauri v2 desktop shell, WebView2 IPC, capabilities, or installers (that is `tauri-desktop`).
metadata:
  group: "technique"
  kind: "reference"
  roles: "implementer, qa, tech-reviewer"
---

# Rust — viết code an toàn, idiomatic và kiểm thử

> **Kết luận:** code Rust ưu tiên **kiểu dữ liệu chặt, sở hữu rõ ràng, lỗi tường minh**: không `.unwrap()`/`.expect()` ở luồng sản phẩm, mượn dữ liệu trước khi `.clone()`, tách logic lõi khỏi biên FFI/hạ tầng. Bộ công cụ chuẩn: `cargo fmt`, `cargo check`, `cargo clippy`, `cargo test` (viết test trước theo skill `tdd`).

## 1. Khi nào dùng và ranh giới

- **Dùng khi:** viết mới, sửa hoặc review code Rust; thiết kế crate/module; cấu hình `Cargo.toml`, clippy, test; xử lý ownership/lifetimes, lỗi `thiserror`/`anyhow`, async Tokio, concurrency hoặc FFI/process Windows.
- **Không dùng cho:** vỏ desktop Tauri v2, WebView2 IPC, `capabilities`, sidecar Tauri hoặc bộ cài `.msi`/NSIS — chuyển sang skill `tauri-desktop`.

## 2. Nguyên tắc lõi

### 2.1. Sở hữu trước `.clone()`
- Truyền `&str`, `&[T]`, `impl AsRef<Path>` khi hàm chỉ đọc; truyền theo giá trị khi hàm cần sở hữu (lưu trữ, gửi qua thread/task).
- Cấm dùng `.clone()` chỉ để tắt lỗi borrow checker; mỗi `.clone()` giữ lại phải giải thích được trong một câu.
- Xử lý xung đột mượn bằng tách trường struct (borrow splitting), `mem::take`/`mem::replace` hoặc `Cow<'_, str>` cho nhánh ít cấp phát.

### 2.2. Thiết kế theo kiểu (Type-driven design) & Idioms
- Dùng `enum` thay nhiều cờ `bool`/`Option` phụ thuộc lẫn nhau để trạng thái sai không biểu diễn được.
- Bọc kiểu nguyên thủy bằng newtype (`struct UserId(u64)`) và hàm `parse` ở biên thay vì kiểm tra lặp lại ở nhiều nơi.
- Ưu tiên biểu thức (`match`, `let ... else`), iterator pipeline và `From`/`TryFrom` thay cho ép kiểu `as` dễ mất dữ liệu.

### 2.3. Lỗi tường minh và chính sách Panic
- Dùng `Result` và toán tử `?` truyền lỗi tới tầng có quyền quyết định (thử lại, báo lỗi, thoát); dùng `Option` chỉ khi vắng mặt là lý do duy nhất.
- Thư viện/crate lõi dùng `thiserror`; ứng dụng/binary dùng `anyhow` ở tầng trên cùng (không đưa `anyhow` vào public API thư viện).
- Cấm `.unwrap()`/`.expect()` trên dữ liệu từ người dùng, file hay mạng; chỉ dùng trong test, hoặc khi bất biến đã chứng minh bằng mã trước đó kèm `.expect("lý do bất biến")`.

### 2.4. `unsafe` tối thiểu và an toàn FFI
- Chỉ viết `unsafe` cho: (1) biên FFI, (2) điểm nóng hiệu năng đã đo bằng profiler, (3) primitive ngôn ngữ không thể diễn đạt an toàn.
- Mọi khối `unsafe` phải có comment `// SAFETY:` nêu rõ bất biến mà caller bảo đảm; mọi `pub unsafe fn` phải có mục `# Safety`.
- Ở biên `extern "C"`: giữ logic trong crate Rust thuần, dùng `#[repr(C)]`/`#[repr(transparent)]` và bọc `catch_unwind` để không unwind panic qua FFI.

### 2.5. Async Tokio và Concurrency
- Cấm giữ `std::sync::MutexGuard` qua điểm `.await` (gây deadlock); hãy drop guard trước `.await` hoặc dùng `tokio::sync::Mutex`.
- Đẩy I/O đồng bộ hoặc CPU nặng sang `tokio::task::spawn_blocking` hoặc `rayon`, không dùng `std::thread::sleep` trong task async.
- Ưu tiên truyền thông điệp qua channel (`mpsc`, `oneshot`, `watch`) và `std::thread::scope` trước khi dùng trạng thái chia sẻ `Arc<Mutex<T>>`.

## 3. Bộ công cụ và kiểm định chuẩn

```bash
cargo fmt --check
cargo check --all-targets
cargo clippy --all-targets --all-features -- -D warnings   # nếu repo đã có [lints], giữ đúng mức repo cấu hình
cargo test --all-targets --all-features
```

- Khi sửa `unsafe` hoặc atomics: chạy thêm `cargo miri test` (nếu môi trường có nightly; nếu thiếu thì báo `not_run`, không tự cài toolchain).
- Rà nhanh điểm panic tiềm ẩn trước khi báo xong: `rg '\.unwrap\(\)|\.expect\(' --glob '!**/tests/**' src/`.
- Không thêm `#![allow(...)]` để giấu cảnh báo; nếu cần miễn trừ có chủ đích, dùng `#[expect(lint, reason = "...")]` (Rust ≥ 1.81) hoặc `#[allow(...)]` kèm comment lý do.

## 4. Đọc gì khi nào

| Cần | Đọc |
|---|---|
| Ownership, borrowing, `Cow`, `mem::take`, `thiserror` vs `anyhow`, async `Send + Sync`, cancellation và an toàn FFI/process Windows | [idioms-and-errors.md](references/idioms-and-errors.md) |
| Phân tầng unit/integration/`proptest`/`insta`, workspace `Cargo.toml`, `[lints.clippy]`, `rustfmt`, feature flags và kiểm tra CI | [testing-and-tooling.md](references/testing-and-tooling.md) |

## 5. Liên quan và nguồn

- **Skill:** `tdd` (test trước), `debugging`, `error-handling`, `tauri-desktop`, `security-review`, `code-review`, `verify-before-done`.
- **Nguồn:** chắt lọc ý từ `rewrite-rs/skills` @ `3401e9684` (BSD-3-Clause).
