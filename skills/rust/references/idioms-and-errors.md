# Rust Idioms, Error Handling, Async & FFI

## Contents
- [1. Ownership, Borrowing và Lifetimes](#1-ownership-borrowing-và-lifetimes) — Khi xử lý lỗi mượn và tránh `.clone()`
- [2. Type-Driven Design và Idioms](#2-type-driven-design-và-idioms) — Khi thiết kế kiểu dữ liệu và chuyển đổi
- [3. Xử lý lỗi và Chính sách Panic](#3-xử-lý-lỗi-và-chính-sách-panic) — Khi chọn `thiserror`, `anyhow` hay `Option`
- [4. Async Tokio và Concurrency](#4-async-tokio-và-concurrency) — Khi viết task async, mutex và thread
- [5. FFI và An toàn Process Windows](#5-ffi-và-an-toàn-process-windows) — Khi dùng `unsafe`, `extern "C"` hoặc `Command`

## 1. Ownership, Borrowing và Lifetimes

- **Chữ ký hàm rẻ nhất ở đầu vào:** nhận `&str` thay vì `&String`, `&[T]` thay vì `&Vec<T>`, `Option<&T>` thay vì `&Option<T>`, `impl AsRef<Path>` cho đường dẫn chỉ đọc.
- **Nhận theo giá trị khi cần sở hữu:** nếu hàm lưu trữ hoặc đẩy dữ liệu sang thread khác, nhận `String` hoặc `T` để caller tự quyết định move hay clone.
- **Tách mượn theo trường (Borrow splitting):** thay vì gọi nhiều method `&mut self` chồng chéo, destructure struct một lần (`let Self { items, log, .. } = self;`) hoặc dùng `slice::split_at_mut`.
- **`mem::take` và `mem::replace`:** khi đang giữ `&mut` và cần lấy ra giá trị sở hữu (như đổi variant enum tại chỗ), dùng `std::mem::take` để thay bằng `Default` mà không cấp phát.
- **`Cow<'_, str>`:** dùng khi nhánh phổ biến trả về lát cắt mượn (`Cow::Borrowed`) và chỉ nhánh hiếm mới cấp phát (`Cow::Owned`).
- **Struct ưu tiên sở hữu:** trừ các view ngắn hạn, giữ `String`/`Vec<u8>` trong struct thay vì gắn lifetime `'a` xuyên suốt nhiều tầng API.

## 2. Type-Driven Design và Idioms

- **Dùng `enum` thay cặp cờ `bool`/`Option`:** nếu 2 trường `Option` luôn có đúng 1 trường `Some`, gộp thành `enum` 2 nhánh để loại bỏ trạng thái vô lý lúc biên dịch.
- **Parse ở biên, không validate lặp lại:** giữ trường bên trong newtype ở trạng thái riêng tư (`struct Email(String);`) và chỉ cho tạo qua `Email::parse(&str) -> Result<Self, EmailError>`.
- **Derive trước, viết tay sau:** ưu tiên `#[derive(Debug, Clone, PartialEq, Eq, Hash)]`; chỉ tự viết `Debug` khi cần che secret, hoặc tự viết `Default`/`PartialEq` khi có bất biến đặc biệt. Không derive `Eq` cho kiểu chứa `f32`/`f64` và không derive `Copy` cho kiểu lớn hoặc quản lý tài nguyên.
- **Chuyển đổi an toàn:** triển khai `From` (cho phép gọi `Into`) khi không thể thất bại; dùng `TryFrom` cho chuyển đổi có thể lỗi hoặc thu hẹp số học (`u16::try_from(val)`), tránh `as` âm thầm cắt bit.

## 3. Xử lý lỗi và Chính sách Panic

| Tình huống | Lựa chọn chuẩn | Lý do |
|---|---|---|
| Crate nội bộ / tập lỗi đóng | `enum` + `#[derive(thiserror::Error)]` | Khớp nhánh rõ ràng, dùng `#[from]` và `#[source]` giữ chuỗi nguyên nhân |
| Public library ổn định semver | `pub struct Error { kind: ErrorKind }` | Ẩn `ErrorKind` riêng tư, thêm lỗi mới không phá vỡ code downstream |
| Binary / CLI / App tầng trên | `anyhow::Result<T>` + `.context(...)` | Gọn ở biên ứng dụng, gắn ngữ cảnh chuỗi lỗi cho người vận hành |
| Không tìm thấy không cần lý do | `Option<T>` | Tránh tạo kiểu lỗi rỗng vô nghĩa |

- **Chính sách Panic:** panic chỉ dành cho lỗi lập trình (bất biến nội bộ vỡ) hoặc test; input từ người dùng, file, socket hoặc IPC phải luôn trả `Result`.

## 4. Async Tokio và Concurrency

- **Không chặn executor:** thao tác file đồng bộ, nén, mã hoá nặng hoặc `std::thread::sleep` làm treo toàn bộ worker thread; chuyển sang `tokio::task::spawn_blocking` hoặc `rayon`.
- **Tránh giữ lock qua `.await`:** `std::sync::MutexGuard` không phải `Send`; drop guard trong block `{ ... }` trước khi `.await`, hoặc dùng `tokio::sync::Mutex` khi bắt buộc giữ khóa qua `.await`.
- **Thu nhỏ kích thước Future:** thả buffer lớn trước `.await` để state machine không phình to khi đẩy vào `tokio::spawn` hoặc `JoinSet`.
- **An toàn huỷ (Cancellation safety):** mọi future đều có thể bị drop tại bất kỳ `.await` nào trong `tokio::select!` hoặc `timeout`; gom bước không thể đảo ngược thành một thao tác nguyên tử hoặc hỗ trợ tiếp tục lại.
- **Chọn đúng kênh đồng bộ:** `mpsc` (nhiều gửi một nhận), `oneshot` (một phản hồi), `watch` (chỉ cần giá trị mới nhất), `broadcast` (mọi receiver nhận đủ thông điệp). Với atomic, chỉ dùng `Acquire`/`Release` khi hai thread đồng bộ theo cặp; nếu lý luận ordering dài quá 2 câu, đổi sang `Mutex`.

## 5. FFI và An toàn Process Windows

- **Cách ly biên `extern "C"`:** giữ 100 % logic nghiệp vụ ở crate Rust an toàn; tầng FFI chỉ kiểm tra null pointer, giải mã `CStr`/`CString`, bọc `catch_unwind` và chuyển panic thành mã lỗi.
- **Mỗi con trỏ có chủ sở hữu rõ:** heap cấp phát bằng `Box::into_raw` phải có hàm giải phóng tương ứng `Box::from_raw` trong cùng crate; dùng `MaybeUninit<T>` thay cho `mem::zeroed()`.
- **Spawn process an toàn trên Windows:** truyền tham số qua `.arg(...)` (từng đối số riêng, không ghép chuỗi qua `cmd /C` để tránh command injection); trên Windows desktop dùng `std::os::windows::process::CommandExt::creation_flags(0x0800_0000)` (`CREATE_NO_WINDOW`) khi chạy tiến trình nền để không nháy cửa sổ console.
