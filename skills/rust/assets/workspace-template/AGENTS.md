# AGENTS.md — dự án Rust (mẫu)

Sao chép file này vào gốc repo rồi điền các chỗ `<...>`.

## Bố cục
- Manifest gốc: `Cargo.toml` (workspace, resolver 3, edition 2024). Crate nằm ở `crates/*`.
- Mỗi crate khai `[lints] workspace = true`; thiếu dòng này thì bảng lint không có hiệu lực.
- Bộ feature: `<liệt kê feature, hoặc "không có">`.

## Lệnh xác minh (chạy từ gốc repo, theo thứ tự)
```
cargo check --all-targets
cargo test <tên_ca>
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
cargo deny --offline check
```
Tải phụ thuộc một lần (`cargo fetch --locked`) rồi thêm `--frozen` cho các lệnh sau khi môi trường không có mạng. Lần đầu (chưa có `Cargo.lock`): chạy `cargo generate-lockfile`, commit `Cargo.lock`, rồi mới dùng `--locked`/`--frozen`.

## Quy ước
- `target/` dùng chung theo repo cho việc tuần tự; hai tiến trình cargo chạy đồng thời thì đặt `CARGO_TARGET_DIR` riêng cho mỗi bên. Không tự `cargo clean` ngoài vùng tạm của task.
- Cấm `.unwrap()`, `panic!`, `todo!`, `unimplemented!`, `dbg!` ở mã sản phẩm. `.expect("...")` chỉ khi bất biến đã chứng minh bằng mã ngay trước, thông điệp nêu bất biến; cấm trên dữ liệu người dùng/file/mạng.
- Mọi `#[allow(...)]` phải có `reason = "..."`. Không nới `[lints]`, `clippy.toml`, `deny.toml` để qua kiểm.
- Crate CLI: exit 0 = ok, 1 = lỗi chạy, 2 = dùng sai; stdout một dòng JSON có `kind`.
