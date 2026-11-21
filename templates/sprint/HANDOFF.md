---
id: SPR-02-handoff
doc: handoff
title: Sprint goal title
sprint: SPR-02
created: 2026-01-20
---

# Tên mục tiêu sprint — Bàn giao (HANDOFF)

<!-- Chỉ dựng khi bên giao chuyển cả sprint hay một nhóm việc cho phiên hoặc agent hãng khác. Không giao ra ngoài
     phiên thì không dựng file này: REPORT mục "Cách dùng, đã đổi gì, cách hoàn tác" vẫn là bàn giao.
     `init` không chép mẫu này; người hoặc agent tự thêm vào gốc thư mục sprint. Một file, hai phần:
       Giao → làm → Trả
       Giao: bên giao điền, ≤40 dòng, đủ để bên nhận làm mà không hỏi lại
       Trả: bên nhận điền khi xong hoặc khi dừng (phần làm diễn ra ngoài file này)
     Trước khi giao: việc tiên quyết của người còn mở mà chặn một SC Bắt buộc thì chưa giao việc đó, hoặc ghi sẵn
     "Chưa chạy — chờ người" cho SC ấy. Khác BRIEF.md: BRIEF là lời giao của người cho agent ở bước tiếp nhận;
     HANDOFF là bàn giao từ agent này sang agent khác. Không nhắc tên công cụ của một hãng cụ thể. -->

> **Kết luận:** giao … cho … ; xong khi …; kết quả trả về phần Trả của file này.

## Giao

1. **Đọc theo thứ tự:** … (đường dẫn đầy đủ, mỗi file một dòng ngắn)
2. **Nguồn sự thật:** … (khi hai nơi mâu thuẫn thì nơi nào thắng)
3. **Phạm vi:** việc … · nhánh … · thư mục được ghi … · không được đụng …
4. **Khối kiểm cố định** (chép nguyên, không sửa):

> Bốn kết quả: Đạt · Không đạt · Chưa chạy · Không áp dụng (kèm lý do); hai kết quả cuối không bao giờ là Đạt.
> Bằng chứng = lệnh + kết quả + commit + máy và giờ.
> Viết test hỏng trước khi viết mã.
> Chứng minh đang chạy đúng mã (đường thư mục và commit).
> Chạy cả bộ test trước khi báo xong.
> Gặp việc không đảo ngược, secret, ngoài phạm vi thư mục được ghi, hay giả định của kế hoạch sai: dừng, ghi lý do vào phần Trả, không đoán.

5. **Dừng khi nào:** … (ngoài khối kiểm: điều kiện dừng riêng của việc này)
6. **Ghi trả vào đâu:** … (phần Trả của file này; báo cáo dài thì đường dẫn file)
7. **Tự kiểm không thay review độc lập:** bên nhận tự kiểm xong vẫn chờ người hoặc agent khác review.

## Trả

- **Đã đổi gì:** … (file, commit)
- **Cách chạy:** … (lệnh kiểm và kết quả mong đợi)
- **Hoàn tác:** … (lệnh hoặc commit cần hoàn)
- **Bằng chứng:** … (trỏ `file:dòng` hoặc lệnh kèm kết quả, commit, máy và giờ)
