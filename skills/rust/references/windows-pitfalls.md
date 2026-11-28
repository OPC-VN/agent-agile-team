# Cạm bẫy Rust trên Windows

Đọc khi: mã Rust đụng đường dẫn, file hệ thống, tiến trình con, FFI Win32, hoặc build/test treo, lỗi «access denied» khi thay exe.

> Dự án có luật riêng về đường dẫn, secret, cây đám mây thì theo luật dự án (`AGENTS.md`/`CLAUDE.md` của repo).

| Cạm bẫy | Biểu hiện | Cách xử lý |
|---|---|---|
| **UTF-16 ở biên syscall** | Windows dùng UTF-16 (có thể chứa cặp thay thế lẻ không hợp lệ); `String` Rust là UTF-8. Đường dẫn hợp lệ trên đĩa có thể không chuyển được sang `String` | Giữ `OsStr`/`OsString`/`Path`/`PathBuf` xuyên suốt; chỉ chuyển sang `&str` ở biên hiển thị (`to_string_lossy`) hoặc khi đã kiểm. Với FFI dùng `OsStrExt::encode_wide` (`std::os::windows::ffi`) và thêm NUL cuối; ưu tiên hàm `...W`, tránh `...A` |
| **Tiền tố `\\?\` và đường dài** | `fs::canonicalize` trả đường dạng `\\?\C:\...`; một số công cụ và API không hiểu tiền tố này. Đường > 260 ký tự cần `\\?\` hoặc bật hỗ trợ đường dài | Phân biệt `\\?\C:\...` (đường dài **cục bộ**) với `\\?\UNC\server\share\...` (đường **mạng**, UNC); đừng coi cả hai là «cục bộ». Khi cần đường hiển thị/đưa cho tiến trình khác, cân nhắc crate `dunce` hoặc tự bỏ tiền tố khi an toàn. So sánh đường: chuẩn hoá cả hai vế cùng một cách, không phân biệt hoa-thường |
| **Junction và symlink** | `canonicalize` theo junction và trả đích (thường dạng UNC/`\\?\`). Kiểm `..` hay `starts_with` trên đường chưa chuẩn hoá **không đủ** để chặn thoát vùng cho phép qua junction | Để giữ một thư mục gốc: chuẩn hoá cả gốc và đích bằng `canonicalize` rồi mới `starts_with`; hoặc kiểm từng thành phần đường bằng `symlink_metadata`/`FILE_ATTRIBUTE_REPARSE_POINT` và từ chối reparse point. Kiểm lúc dùng (mở file rồi kiểm tay cầm) chắc hơn kiểm trước rồi mở (TOCTOU) Cách kiểm đúng: chuẩn hoá **cả hai vế** cùng cách rồi so **theo thành phần** bằng `Path::starts_with` (không so tiền tố chuỗi: `C:\work` khớp nhầm `C:\workspace-x`), từ chối reparse point bằng `symlink_metadata`, và kiểm trên tay cầm đã mở để tránh TOCTOU. |
| **File placeholder ổ đám mây** | File OneDrive/SharePoint/Drive «chỉ trên đám mây» hiện như file thường nhưng **đọc là kéo file về** (chậm, tốn dung lượng/băng thông, có thể treo) | Trước khi đọc nội dung, kiểm thuộc tính `FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS` / `RECALL_ON_OPEN` / `OFFLINE` qua `MetadataExt::file_attributes`; gặp placeholder thì dừng/hỏi, không tự đọc hàng loạt. Quét cây: bỏ qua nội dung, chỉ đọc metadata |
| **Exe bị khoá khi thay** | Không ghi đè/xoá được `.exe`/`.dll` đang chạy («Access is denied», os error 5/32) — cả binary mà test vừa chạy hay `cargo run` trước đó | Dừng tiến trình đang giữ file trước khi build lại; nếu cần tự cập nhật: đổi tên exe đang chạy sang tên khác rồi ghi file mới, dọn bản cũ ở lần chạy sau. Đừng retry vòng lặp vô hạn |
| **Defender / SmartScreen** | Quét thời gian thực làm build/test chậm hoặc thỉnh thoảng khoá file vừa ghi; exe lạ tải về bị SmartScreen chặn | Thử lại có giới hạn khi gặp lỗi khoá ngắn; không tắt Defender và không thêm loại trừ để chạy cho nhanh; ghi nhận build chậm là do quét nếu đo được. Binary không ký có thể bị cảnh báo — việc ký là quyết định phát hành, không phải của vòng build |
| **Mã hoá console** | Console cũ dùng code page OEM (CP437/CP850, 1252…); `println!` UTF-8 hiện chữ vỡ, và PowerShell 5.1 đọc stdout của tiến trình con bằng code page hệ thống | Với output máy đọc: ghi UTF-8 ra stdout và đặt đọc UTF-8 phía nhận; ra console người xem: `SetConsoleOutputCP(65001)` hoặc chấp nhận vỡ chữ. Không dùng ký tự Unicode làm giao thức giữa tiến trình |
| **Chờ tiến trình con còn sống** | `Start-Process -Wait` (PowerShell) chờ **cả cây tiến trình con**; một con nền như `mspdbsrv.exe` (máy chủ PDB do trình liên kết MSVC bật) sống lâu hơn lệnh build → lệnh treo dù build xong. Tương tự: đợi EOF trên ống mà con nền còn giữ đầu ghi | Tránh `-Wait` cho lệnh build có thể sinh con nền; chạy bằng toán tử gọi trực tiếp (`& cargo ...`) hoặc `Start-Process` không `-Wait` rồi chờ đúng PID cha (`Wait-Process -Id`) có hạn. Trong Rust: `Child::wait` chỉ chờ tiến trình con trực tiếp; đặt hạn bằng luồng/`wait_timeout`, và không để con thừa kế tay cầm ống ngoài ý muốn |

## Quy tắc FFI Win32

- **Chuỗi UTF-16 có NUL cuối và sống đủ lâu.** Dựng `Vec<u16>` bằng `OsStr::encode_wide().chain(std::iter::once(0)).collect()`; giữ vector trong biến cục bộ **suốt lời gọi**, không truyền `.as_ptr()` của giá trị tạm đã bị drop. Chuỗi có NUL ở giữa phải bị từ chối trước khi gọi.
- **Kiểm giá trị trả về rồi đọc lỗi ngay.** Mỗi hàm có quy ước riêng: `GetFileAttributesW` trả `INVALID_FILE_ATTRIBUTES`, `CreateFileW` trả `INVALID_HANDLE_VALUE`, nhiều hàm khác trả `0`/null. So đúng giá trị lỗi của hàm đó, rồi đọc `GetLastError()` (hoặc `std::io::Error::last_os_error()`) **ngay sau lời gọi**, trước mọi việc khác (cấp phát, log) vì chúng có thể ghi đè mã lỗi. Đổi thành `Result`, không trả giá trị thô lên tầng trên.
- **Bọc `HANDLE` trong kiểu có `Drop`.** `struct OwnedHandle(HANDLE);` với `Drop` gọi `CloseHandle` một lần; không `Clone`, không `Copy`; hàm tạo kiểm `INVALID_HANDLE_VALUE`/null. Nhờ vậy đường lỗi (`?`, panic) cũng đóng tay cầm.
- **`// SAFETY:` nêu bất biến cụ thể**, không chép lại chữ «unsafe». Tốt: «`wide` kết thúc bằng NUL và còn sống đến hết lời gọi; con trỏ không null». Xấu: «gọi API Windows nên an toàn».
- **Gom `unsafe` vào một module mỏng** (ví dụ `sys` hoặc `win32`) trả về API an toàn (`fn file_attributes(&Path) -> io::Result<u32>`); phần còn lại của crate không có `unsafe`.
- **Miễn trừ lint có chủ đích.** Khi workspace đặt `unsafe_code = "warn"`, chỉ module FFI mới có `#![allow(unsafe_code, reason = "Win32 FFI boundary")]` (hoặc `#[allow(...)]` trên từng mục) kèm lý do; không nới ở cấp crate hay workspace.

Minh hoạ (chưa biên dịch thử; giả định crate `windows-sys` với feature `Win32_Storage_FileSystem`):

```rust
use std::{io, os::windows::ffi::OsStrExt, path::Path};
use windows_sys::Win32::Storage::FileSystem::{GetFileAttributesW, INVALID_FILE_ATTRIBUTES};

pub fn file_attributes(path: &Path) -> io::Result<u32> {
    let wide: Vec<u16> = path.as_os_str().encode_wide().chain(std::iter::once(0)).collect();
    // SAFETY: `wide` kết thúc bằng NUL và sống đến hết lời gọi; con trỏ không null.
    let attrs = unsafe { GetFileAttributesW(wide.as_ptr()) };
    if attrs == INVALID_FILE_ATTRIBUTES {
        return Err(io::Error::last_os_error()); // đọc lỗi ngay sau lời gọi
    }
    Ok(attrs)
}
```

## Ghi nhớ khi viết FFI/tiến trình

- Mọi lời gọi Win32 kiểm giá trị trả về và `GetLastError` ngay sau lời gọi; bọc tay cầm (`HANDLE`) trong kiểu có `Drop` đóng tay cầm.
- Lệnh con dựng từ đối số tách riêng (`Command::arg`), không ghép chuỗi lệnh; ghi rõ cách xử lý dấu `"` và khoảng trắng nếu phải đi qua `cmd.exe`/PowerShell.
- `unsafe` chỉ ở biên mỏng, mỗi khối có `// SAFETY:` (xem `idioms-and-errors.md`).
