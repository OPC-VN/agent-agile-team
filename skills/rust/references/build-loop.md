# Vòng biên dịch — sửa Rust đến khi xanh, trên Windows và trong sandbox

Đọc khi: chạy `cargo` để xác minh, sửa lỗi biên dịch, hoặc giao việc Rust cho subagent/phiên khác. Mọi số đo ghi «theo tài liệu, chưa đo» thì chưa kiểm trên máy.

## Quy tắc chung (mọi nền tảng)

- Tải phụ thuộc **một lần ngoài sandbox** (`cargo fetch --locked`), sau đó mọi lệnh chạy `--frozen`. Repo mới chưa có `Cargo.lock` thì `--locked` báo lỗi «cannot create the lock file»: lần đầu chạy `cargo generate-lockfile` (hoặc `cargo fetch` không cờ), commit `Cargo.lock`, rồi mới dùng `--locked`/`--frozen`.
- Thứ tự: `cargo check` → sửa **lỗi biên dịch đầu tiên** → `cargo test <tên_ca>` → `cargo fmt --check` → `cargo clippy --all-targets -- -D warnings` → bộ test của repo (kèm `cargo test --doc` nếu có doctest).
- **Trần vòng sửa:** sau 3 vòng không tiến thì dừng và báo; không «xanh giả» (không `#[allow]` không lý do, không `.unwrap()` để qua kiểu, không nới lint hay bỏ test).
- **Thư mục `target`:** mặc định **một `target` chung theo repo** cho việc tuần tự (kể cả nhiều worktree làm nối tiếp). **Tách riêng** bằng `CARGO_TARGET_DIR` khi có hai tiến trình cargo chạy đồng thời trên cùng repo (subagent/worktree song song, hoặc rust-analyzer chạy nền). Lý do: build nguội một cây phụ thuộc lớn (hàng trăm gói) có thể vượt cả hạn lệnh lẫn ngưỡng im lặng của công cụ gọi. Vượt trần dung lượng của repo thì báo, **không tự `cargo clean`** ngoài vùng tạm của task. Chưa đo: thời gian chờ khoá `target`; sản phẩm cuối trùng tên đè nhau giữa hai worktree dùng chung `target`.
- Build nguội đo riêng, không tính vào vòng sửa. Với crate lớn dùng `cargo check -p <crate>`.
- **Không có hook chạy cargo sau mỗi lần sửa** (hook PostToolUse): phải chờ sau mỗi lần sửa, đỏ giữa chừng khi mã chưa xong, fmt đổi file sau lưng agent, và đổi file cấu hình hook có thể buộc nền tảng yêu cầu duyệt lại.
- Lệnh `cargo` treo mãi thường do một tiến trình con còn sống giữ ống đầu ra (xem `windows-pitfalls.md`, mục chờ tiến trình con).

## Giới hạn từng nền tảng

| Nền tảng | Giới hạn | Cách làm |
|---|---|---|
| Claude Code | Bash mặc định 2 phút, tối đa 10 phút (theo tài liệu, chưa đo). Subagent «chỉ đọc» chạy `cargo check` vẫn chạy `build.rs`/proc-macro và ghi `target` | Lệnh dài chạy nền rồi đọc kết quả; build ấm trước khi giao subagent |
| Codex | Sandbox Windows chặn mạng. Ba bề mặt (CLI trực tiếp, Desktop, qua cầu gọi chéo) có quyền khác nhau; quyền của phiên tương tác không suy ra quyền lệnh con qua cầu. Cầu có thể **lọc biến môi trường kế thừa**. Qua cầu: hạn khởi điểm khoảng 5 phút, trần 20 phút, không commit | Đặt `CARGO_TARGET_DIR` **trong** phiên chạy Cargo. Xác nhận phiên qua cầu đọc được bộ nhớ đệm và ghi được `target`, thư mục tạm, đầu ra build script (chưa kiểm). Phiên chỉ đọc nhận log từ lượt thực thi riêng. Chia lượt nhỏ |
| Antigravity | Qua cầu `agy` quyền là nhị phân: `read` khoá terminal, `workspace` mở toàn bộ. Cầu dừng lượt khi **im lặng 90 s**, trần 20 phút. Prompt + schema tối đa **30 000 ký tự**. Sandbox CLI chặn mạng | Build ấm trước; lệnh lâu để chạy nền theo cơ chế của `agy`; log lỗi và diff dài ghi file `.tmp/` rồi trỏ đường dẫn; `cargo check -p <crate>` |

Các giới hạn của hai nền tảng cuối là giá trị cấu hình của cầu tại thời điểm viết; đọc lại cầu của dự án nếu cần số chính xác.
