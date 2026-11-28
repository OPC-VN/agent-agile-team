# Oracle bằng file golden

Oracle là đầu ra thật của **bản cũ**. Lưu bằng file thường để đọc, so, sửa được bằng bất kỳ công cụ nào, không phụ thuộc thư viện.

## 1. Cấu trúc thư mục

```
tests/golden/
  <tên-ca>/
    cmd               # lệnh hoặc tham số đã dùng (một dòng mỗi tham số)
    input.*           # dữ liệu vào (nếu có)
    expected.stdout
    expected.stderr   # nếu có
    expected.exit     # mã thoát, một số
    expected.files/   # file bản cũ đã ghi ra (nếu có)
  META.md             # bản cũ: phiên bản/commit, ngày ghi, máy, lệnh ghi
```

Tên ca nói hành vi (`rong-input`, `unicode-ten-file`, `duong-dan-windows`). Mỗi ca một thư mục, một hành vi.

## 2. Ghi oracle (chạy bản cũ)

1. Khoá phiên bản bản cũ (commit hoặc bản cài); ghi vào `META.md`.
2. Viết một script ghi chạy bản cũ trên từng ca và lưu stdout, stderr, mã thoát, file sinh ra vào thư mục ca. Script này chỉ gọi bản cũ, không bao giờ gọi bản Rust.
3. Chạy hai lần, so hai lượt với nhau. Lệch → phần lệch là không ổn định (giờ, số ngẫu nhiên, thứ tự map): chuẩn hoá (mục 4) hoặc bỏ khỏi so sánh và ghi lý do trong `META.md`.
4. Commit golden như dữ liệu của test. Golden chỉ đổi khi có lý do chính đáng (bản cũ đổi) và người quyết định ghi lại oracle; không đổi để cho test qua.

## 3. So đầu ra (chạy bản Rust)

Bộ test duyệt từng thư mục ca, chạy bản Rust với cùng `cmd` và `input`, rồi so với `expected.*`. Khi lệch, in tên ca và vài dòng diff đầu, không in cả file lớn. Mã thoát so riêng, không lẫn vào stdout.

Test phải thất bại khi thư mục ca thiếu `expected.*`: ca không có đáp án không được tính là qua.

## 4. Chuẩn hoá trước khi so

Chuẩn hoá **cả hai phía** bằng cùng một hàm; hàm chỉ làm những việc dưới đây, mỗi việc ghi trong `META.md`:

| Vấn đề | Chuẩn hoá |
|---|---|
| Xuống dòng `\r\n` và `\n` (Windows) | đổi hết thành `\n` |
| Dấu phân cách đường dẫn `\` và `/` | đổi thành `/`; không đổi chữ hoa thường |
| Tiền tố `\\?\` do `canonicalize` trên Windows | bỏ tiền tố khi so |
| Đường dẫn tuyệt đối của máy | thay bằng nhãn cố định (`<ROOT>`, `<TMP>`) |
| Thời gian, số ngẫu nhiên, mã tiến trình | thay bằng nhãn, hoặc loại khỏi so |
| BOM đầu file, mã hoá | đọc cả hai phía cùng một mã hoá (UTF-8); ghi rõ nếu bản cũ ra mã hoá khác |

Không chuẩn hoá thêm để "cho khớp": khoảng trắng, thứ tự dòng, số thập phân là hành vi thật, lệch là lệch. Mỗi quy tắc chuẩn hoá mới phải có ca chứng minh nó chỉ che phần không ổn định.

## 5. Khi nào dùng crate `insta`

`insta` (thư viện snapshot test) là **lựa chọn**, không bắt buộc. Cân nhắc khi đầu ra là cấu trúc lớn khó so tay và nhóm muốn duyệt thay đổi bằng lệnh review của nó. Lưu ý: snapshot do `insta` sinh từ **bản Rust** chỉ là oracle nếu nội dung ban đầu lấy từ bản cũ; để `insta` tự chấp nhận đầu ra Rust lần đầu là dán đáp án. Thêm crate là thêm phụ thuộc: theo `AGENTS.md`/`CLAUDE.md` của repo về việc thêm gói. Không cần thì dùng golden thường.
