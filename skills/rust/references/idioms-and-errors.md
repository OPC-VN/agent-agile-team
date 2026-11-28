# Rust Idioms, Error Handling, Async & FFI

## Contents
- [1. Ownership, Borrowing và Lifetimes](#1-ownership-borrowing-và-lifetimes) — Khi xử lý lỗi mượn và tránh `.clone()`
- [2. Type-Driven Design và Idioms](#2-type-driven-design-và-idioms) — Khi thiết kế kiểu dữ liệu và chuyển đổi
- [3. Xử lý lỗi và Chính sách Panic](#3-xử-lý-lỗi-và-chính-sách-panic) — Khi chọn `thiserror`, `anyhow` hay `Option`
- [4. Async Tokio và Concurrency](#4-async-tokio-và-concurrency) — Khi viết task async, mutex và thread
- [5. FFI và An toàn Process Windows](#5-ffi-và-an-toàn-process-windows) — Khi dùng `unsafe`, `extern "C"` hoặc `Command`
- [6. Huỷ tác vụ async, hạn giờ và giới hạn song song](#6-huỷ-tác-vụ-async-hạn-giờ-và-giới-hạn-song-song) — Khi cần dừng task, đặt timeout, giới hạn số việc chạy cùng lúc
- [7. Lỗi borrow checker hay gặp](#7-lỗi-borrow-checker-hay-gặp) — Khi compiler báo `E0499`, `E0502`, `E0505`, `E0506`, `E0597`, `E0716`

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
- **FFI Win32 chi tiết** (chuỗi UTF-16, `GetLastError`, bọc `HANDLE`, module FFI mỏng, `#[allow(unsafe_code, reason)]`): xem mục «Quy tắc FFI Win32» ở [windows-pitfalls.md](windows-pitfalls.md).

## 6. Huỷ tác vụ async, hạn giờ và giới hạn song song

Huỷ trong Tokio là **hợp tác**: drop một future hoặc `abort()` một task chỉ dừng nó tại điểm `.await` kế tiếp. Chọn công cụ theo bảng:

| Cần | Dùng | Lưu ý |
|---|---|---|
| Dừng vòng lặp khi có tín hiệu huỷ | `tokio::select!` với một nhánh chờ huỷ | Nhánh thua bị drop; xem *an toàn huỷ* ở mục 4. Thêm `biased;` nếu muốn kiểm huỷ trước |
| Cờ huỷ chia cho nhiều task | `CancellationToken` (crate `tokio-util`): `clone()` cho mỗi task, `cancel()` một lần, task chờ `token.cancelled().await`; `child_token()` để huỷ theo tầng | Không muốn thêm crate: `tokio::sync::watch::channel(false)`, task chờ `rx.changed()` |
| Huỷ cả nhóm task | `JoinSet`: `spawn` vào nhóm, `abort_all()`, rồi `join_next().await` đến hết để thu dọn | `abort_all` chỉ yêu cầu; task bị huỷ trả `JoinError` có `is_cancelled()`; drop `JoinSet` cũng abort mọi task trong nhóm |
| Hạn giờ cho một việc | `tokio::time::timeout(dur, fut).await` trả `Err(Elapsed)` khi quá hạn và drop `fut` | Chỉ an toàn nếu `fut` an toàn huỷ; hết hạn không có nghĩa tác dụng phụ đã dừng |
| Giới hạn số việc chạy cùng lúc | `Semaphore`: `sem.clone().acquire_owned().await` rồi giữ `permit` suốt thời gian làm việc | Đừng `spawn` không giới hạn rồi mới nghĩ chuyện giới hạn; permit tự trả khi drop |

**`spawn_blocking` không huỷ được giữa chừng.** `JoinHandle::abort()` trên tác vụ blocking chỉ bỏ chờ kết quả; closure vẫn chạy đến hết trên thread của nó (và runtime không tắt nhanh khi còn tác vụ blocking). Muốn dừng sớm, đưa cờ huỷ (`Arc<AtomicBool>` hoặc một bản `CancellationToken` đã clone, kiểm bằng `is_cancelled()`) vào closure và **kiểm cờ trong vòng lặp blocking**, thoát sớm khi cờ bật.

**Không giữ `std::sync::MutexGuard` qua `.await`** (xem mục 4): future thành `!Send` nên không `spawn` được, và nếu biên dịch được vẫn dễ deadlock; drop guard trước `.await` hoặc dùng `tokio::sync::Mutex`.

Minh hoạ (chưa biên dịch thử; giả định `tokio` với feature `rt`, `time`, `macros`, `sync` và `tokio-util`):

```rust
use std::{sync::Arc, time::Duration};
use tokio::{sync::Semaphore, task::JoinSet, time::timeout};
use tokio_util::sync::CancellationToken;

async fn run_all(items: Vec<u32>, token: CancellationToken) {
    let limit = Arc::new(Semaphore::new(4));
    let mut set = JoinSet::new();
    for item in items {
        let permit = limit.clone().acquire_owned().await.expect("semaphore không bị đóng");
        let token = token.clone();
        set.spawn(async move {
            let _permit = permit; // trả permit khi task kết thúc
            tokio::select! {
                _ = token.cancelled() => None,
                r = timeout(Duration::from_secs(30), work(item)) => r.ok(),
            }
        });
    }
    // Dừng sớm từ nơi khác: token.cancel(); set.abort_all();
    while set.join_next().await.is_some() {}
}

async fn work(_item: u32) {}
```

Phần blocking: `spawn_blocking(move || { for chunk in data { if token.is_cancelled() { break; } process(chunk); } })`.

## 7. Lỗi borrow checker hay gặp

| Mã | Nghĩa một dòng | Cách sửa thường dùng |
|---|---|---|
| `E0499` | Hai `&mut` tới cùng giá trị sống cùng lúc | Thu hẹp phạm vi mượn thứ nhất (khối `{}` hoặc dùng xong rồi mới mượn lại); tách theo trường hoặc `split_at_mut`; dùng chỉ số thay vì giữ tham chiếu |
| `E0502` | Mượn `&mut` khi còn `&` đang dùng (hoặc ngược lại), hay gặp khi lặp rồi sửa chính tập đó | Gom việc cần sửa vào `Vec` rồi áp dụng sau vòng lặp; dùng `retain`/`drain`; copy giá trị nhỏ ra trước khi mượn `&mut` |
| `E0505` | Move giá trị ra khi nó còn đang bị mượn | Kết thúc phần dùng tham chiếu trước khi move; hoặc nhận bản sở hữu từ đầu; `clone` chỉ khi giải thích được |
| `E0506` | Gán lại giá trị khi một tham chiếu tới nó còn sống | Dùng xong tham chiếu rồi mới gán; lấy bản sao giá trị cần giữ trước khi gán; `mem::replace` khi cần giá trị cũ |
| `E0597` | Tham chiếu sống lâu hơn giá trị nó trỏ tới (giá trị bị drop cuối khối) | Đưa giá trị ra phạm vi ngoài, hoặc trả về giá trị sở hữu thay vì tham chiếu; với thread/task dùng `move` và dữ liệu sở hữu (`Arc`) hoặc `thread::scope` |
| `E0716` | Tham chiếu tới giá trị tạm bị drop cuối câu lệnh | Gán giá trị tạm vào biến `let` trước rồi mượn biến đó (`let s = make(); let r = s.as_str();`) |
