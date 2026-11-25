# Rust Testing, Cargo & Tooling

## Contents
- [1. Phân tầng kiểm thử Rust](#1-phân-tầng-kiểm-thử-rust) — Khi chọn loại test phù hợp
- [2. Viết test sạch và tất định](#2-viết-test-sạch-và-tất-định) — Khi tổ chức ca test và assert lỗi
- [3. Cấu hình Workspace và Lints](#3-cấu-hình-workspace-và-lints) — Khi thiết lập `Cargo.toml` và clippy
- [4. Feature Flags, MSRV và Kiểm định CI](#4-feature-flags-msrv-và-kiểm-định-ci) — Khi kiểm nhiều tổ hợp build

## 1. Phân tầng kiểm thử Rust

| Dạng test | Nơi đặt | Khi nào dùng |
|---|---|---|
| Unit test | `#[cfg(test)] mod tests` trong file nguồn | Kiểm hàm thuần, nhánh biên, hoặc cần truy cập thành phần riêng tư |
| Integration test | `tests/*.rs` | Kiểm public API đúng góc nhìn người dùng crate ngoài |
| Doc test | `///` doc comment | Ví dụ sử dụng thực tế; không biến doc test thành unit test ẩn |
| Property test | `proptest` | Kiểm bất biến trên toàn miền đầu vào (round-trip encode/decode) |
| Snapshot test | `insta` | Kiểm output cấu trúc lớn (JSON, báo cáo, mã sinh tự động) |

- **Luật TDD:** viết test trước và quan sát test **đỏ đúng lý do** trước khi viết code sửa. Bug phát hiện ở production phải có unit/integration test tái hiện đúng tầng phát sinh lỗi.
- **Mã phân nhánh theo OS:** nhánh `#[cfg(windows)]` chỉ được coi là đã kiểm khi thực sự chạy `cargo test` trên Windows.

## 2. Viết test sạch và tất định

- **Table-driven test:** gom nhiều ca tương đồng thành mảng `(input, expected)` và ghi rõ `"input: {input:?}"` trong `assert_eq!` để nhìn ra ngay ca hỏng. Dùng `rstest` khi mỗi ca cần tên test riêng.
- **Assert hành vi và biến thể lỗi:** dùng `matches!(err, MyError::InvalidInput { .. })` hoặc helper kiểm tra loại lỗi; tránh assert chuỗi `Display` vốn dễ đổi câu chữ.
- **Tất định tuyệt đối:** không gọi mạng thật trong unit/integration test; inject clock, RNG seed cố định và tạo thư mục tạm riêng qua `tempfile::TempDir` (tự dọn khi drop).

```rust
#[test]
fn parses_ports_table() {
    let cases = [("8080", Ok(8080)), ("0", Err(())), ("abc", Err(()))];
    for (raw, expected) in cases {
        assert_eq!(parse_port(raw).map_err(|_| ()), expected, "raw={raw:?}");
    }
}
```

## 3. Cấu hình Workspace và Lints

- **Workspace thống nhất:** dùng `[workspace.package]` và `[workspace.dependencies]` ở `Cargo.toml` gốc để đồng bộ version, `edition` và `rust-version` (MSRV) giữa các crate.
- **Khai báo lint trong `Cargo.toml`:** thay vì gắn `#![deny(warnings)]` trong `lib.rs` (dễ vỡ khi nâng compiler), cấu hình `[lints.rust]` và `[lints.clippy]` tại manifest để local và CI chạy cùng một chuẩn:

```toml
[workspace.lints.rust]
unsafe_op_in_unsafe_fn = "warn"

[workspace.lints.clippy]
await_holding_lock = "warn"
borrowed_box = "warn"
ptr_arg = "warn"
undocumented_unsafe_blocks = "warn"
```

- **Định dạng chỉ file đã sửa:** dùng `cargo fmt --check`; nếu repo cũ có file chưa format từ trước, chỉ chạy `rustfmt <file>` trên file thuộc phạm vi task để không làm nhiễu git diff.

## 4. Feature Flags, MSRV và Kiểm định CI

- **Feature chỉ cộng thêm (Additive only):** bật thêm một feature không được làm hỏng API hay hành vi của code đang dùng feature mặc định; tránh feature loại trừ lẫn nhau.
- **Kiểm đủ tổ hợp feature:** chạy cả build mặc định, `--no-default-features` (nếu hỗ trợ) và `--all-features`; với workspace nhiều feature dùng `cargo hack check --feature-powerset` nếu có cài đặt.
- **Lệnh kiểm định đầy đủ trước khi bàn giao:**

```bash
cargo fmt --check
cargo clippy --all-targets --all-features
cargo test --all-targets --all-features
cargo test --doc
```

- **Kiểm tra an toàn & chuỗi cung ứng (khi thêm crate mới):** dùng `cargo deny check` hoặc `cargo audit` (nếu dự án cấu hình) để kiểm tra giấy phép và lỗ hổng bảo mật; không tự ý cài công cụ mới vào máy người dùng khi không được giao.
