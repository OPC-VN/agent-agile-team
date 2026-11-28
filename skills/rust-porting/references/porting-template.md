# Khuôn `PORTING.md`

Chép khuôn này vào repo (cạnh mã port), điền, và cập nhật mỗi lần qua cổng. Ô để trống là việc chưa xong.

## 1. Tổng quan

- Bản cũ: tên, ngôn ngữ, phiên bản/commit, cách chạy.
- Bản Rust: crate, đường dẫn.
- Lý do port (một câu): …
- Người chịu trách nhiệm: …

## 2. Ánh xạ API cũ → mới

Mỗi hàm, lệnh hay tham số của bản cũ có một dòng.

| API/lệnh cũ | API Rust mới | Khác biệt cần biết (kiểu dữ liệu, lỗi, thứ tự) | Trạng thái (chưa / đang / qua cổng) |
|---|---|---|---|
| | | | |

## 3. Ánh xạ test

| Test/ca cũ | Golden hoặc test mới | Ghi chú | Trạng thái |
|---|---|---|---|
| | | | |

Ca cũ không có test: ghi "chưa có test cũ" và thêm ca golden mới từ chạy bản cũ.

## 4. Bug gốc giữ lại có chủ đích

Hành vi sai của bản cũ mà bản Rust **cố ý** giữ để không đổi kết quả cho người dùng. Sửa chúng là việc riêng, sau khi port xong.

| Mã | Hành vi sai của bản cũ | Ca golden chứng minh | Vì sao giữ | Khi nào sửa |
|---|---|---|---|---|
| | | | | |

Khác biệt nào giữa hai bản mà không nằm trong bảng này đều là lỗi của bản Rust.

## 5. Điều kiện cổng (đơn vị nào cũng áp)

Sáu điều kiện ở `SKILL.md` mục 4. Ghi thêm điều kiện riêng của dự án, trỏ về `AGENTS.md`/`CLAUDE.md` của repo thay vì chép luật vào đây.

## 6. Lịch chu kỳ 4 tuần

| Giai đoạn | Từ ngày | Đến ngày | Việc | Kết quả sai khác |
|---|---|---|---|---|
| Phát lại (tuần 1–2) | | | chạy song song, bản cũ là chuẩn | |
| Bật (tuần 3–4) | | | Rust mặc định, bản cũ chờ | |

Mỗi sai khác: ngày, ca, nguyên nhân, cách xử lý (sửa Rust / thêm vào mục 4).

## 7. Điều kiện tắt bản cũ

Đủ cả:
- [ ] Mọi dòng mục 2 và 3 ở trạng thái qua cổng.
- [ ] Hết chu kỳ 4 tuần với 0 sai khác chưa giải thích.
- [ ] Đường lùi nêu rõ: cách bật lại bản cũ trong một bước.
- [ ] Người dùng đã đồng ý bằng lời trong chat (xoá bản cũ không đảo ngược).
