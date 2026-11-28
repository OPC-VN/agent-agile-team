---
name: rust-porting
description: Use when porting code to Rust, or rewriting or migrating existing code to it (port to Rust, rewrite in Rust, migrate to Rust, "chuyển sang Rust", "viết lại bằng Rust"), when a legacy tool must be replaced by a Rust version with identical behavior, or when deciding whether a Rust port is done and the old version can be switched off. Not for writing new Rust code or fixing Rust compile errors (that is `rust`), nor the Tauri desktop shell (`tauri-desktop`).
metadata:
  group: "process"
  roles: "architect, implementer, qa, tech-reviewer"
---

# Port sang Rust — giữ nguyên hành vi, chứng minh bằng oracle

> **Kết luận:** port chỉ "xong" khi bản Rust cho **đúng kết quả của bản cũ trên mọi ca đã ghi** (oracle) và bản cũ chỉ tắt sau một chu kỳ chạy song song không sai khác. Cảm giác "chạy được" không phải bằng chứng; chỉ có ca ghi sẵn, lệnh vừa chạy và kết quả vừa đọc mới là bằng chứng.

## 1. Khi nào dùng và ranh giới

- **Dùng khi:** chuyển một công cụ, module hay thư viện đang chạy (Python, PowerShell, Node…) sang Rust mà hành vi phải giữ nguyên; quyết định "port xong chưa", "tắt bản cũ được chưa".
- **Không dùng khi:** viết Rust mới từ đầu, sửa lỗi biên dịch, thiết kế crate → skill `rust`. Vỏ desktop Tauri → `tauri-desktop`. Làm lại có đổi hành vi có chủ đích → coi là tính năng mới, theo `tdd` và quy trình sprint.
- Luật riêng của dự án (mã thoát, đường dẫn, secret, cây đám mây) → theo `AGENTS.md`/`CLAUDE.md` của repo; skill này không thay.

## 2. Thuật ngữ

- **Oracle (bản chuẩn đối chiếu):** đầu ra thật của bản cũ cho một bộ ca vào, ghi lại thành file. Bản Rust phải khớp nó.
- **Golden file:** file thường chứa đầu vào và đầu ra mong đợi của một ca (cấu trúc ở [oracle-golden](references/oracle-golden.md)).
- **`PORTING.md`:** tài liệu sống của việc port: ánh xạ API cũ → mới, ánh xạ test, bug gốc giữ lại, lịch chu kỳ (khuôn ở [porting-template](references/porting-template.md)).

## 3. Quy trình (mỗi bước có điểm dừng)

1. **Khoanh phạm vi.** Liệt kê hành vi bên ngoài của bản cũ: đầu vào, đầu ra, mã thoát, file ghi ra, thứ tự, lỗi. Tạo `PORTING.md` từ khuôn. *Dừng nếu:* chưa biết chạy lại bản cũ ở đâu (không ghi được oracle thì không port).
2. **Ghi oracle.** Chạy **bản cũ** trên bộ ca (gồm ca lỗi, ca rỗng, ca Unicode, ca biên, ca đường dẫn Windows) và lưu golden. Ghi lệnh, phiên bản bản cũ, ngày. *Dừng nếu:* đầu ra không lặp lại được giữa hai lần chạy (có giờ, số ngẫu nhiên, thứ tự không cố định): chuẩn hoá hoặc loại phần đó trước.
3. **Ánh xạ.** Điền bảng API cũ → mới và test cũ → test mới. Mỗi hàm/lệnh của bản cũ có một dòng; không dòng nào để trống.
4. **Port từng đơn vị nhỏ** (một hàm, một lệnh con) theo vòng `tdd`: test golden đỏ trước, rồi mã Rust tối thiểu. Viết Rust theo skill `rust`.
5. **Cổng "xong một đơn vị"** (mục 4). Chưa qua cổng thì không sang đơn vị kế.
6. **Chạy song song.** Chạy bản cũ và bản Rust trên dữ liệu thật, so đầu ra, ghi sai khác. Mọi sai khác phải thành một trong hai: sửa Rust, hoặc ghi vào danh sách "bug gốc giữ lại" kèm lý do.
7. **Bật, rồi tắt.** Bật bản Rust làm mặc định, giữ bản cũ làm đường lùi; chỉ tắt bản cũ khi đủ điều kiện ở `PORTING.md` (chu kỳ 4 tuần, mục 5). *Dừng và hỏi người dùng* trước khi xoá bản cũ: xoá không đảo ngược.

## 4. Cổng "xong một đơn vị port"

Đủ cả sáu, mỗi mục có lệnh vừa chạy và kết quả:

| # | Điều kiện | Cách chứng minh |
|---|---|---|
| 1 | Khớp mọi ca golden | chạy bộ test golden: 0 ca lệch |
| 2 | Định dạng | `cargo fmt --check` sạch |
| 3 | Lint | `cargo clippy --all-targets -- -D warnings` sạch, không nới cấu hình |
| 4 | Test | `cargo test` toàn bộ xanh (không chỉ nhóm vừa viết) |
| 5 | Không stub | tìm macro chưa-làm (`unimplemented` và macro cùng loại), nhánh trả giá trị cố định: 0 kết quả trong mã sản phẩm |
| 6 | Không dán đáp án | mã sản phẩm không chứa nội dung golden hay bảng tra khớp ca; đổi một ca vào thì kết quả đổi đúng theo logic |

Báo "xong" theo `verify-before-done`. Review theo `code-review` (agent `rust-reviewer` nếu có).

## 5. Chu kỳ 4 tuần

Hai tuần **phát lại** (chạy song song, bản cũ là chuẩn, đối chiếu mỗi lần chạy) rồi hai tuần **bật** (Rust là mặc định, bản cũ đứng chờ). Tắt bản cũ chỉ khi **0 sai khác chưa giải thích** suốt chu kỳ. Một sai khác mới ở tuần bất kỳ → sửa, rồi chạy lại chu kỳ từ đầu.

## 6. Điều cấm (xanh giả)

- Dán đáp án oracle vào mã Rust hay gài bảng tra để qua ca.
- Macro chưa-làm (`unimplemented` và loại tương tự), hàm rỗng, hay trả giá trị cố định cho "xong sau".
- Xoá, `#[ignore]` hoặc làm yếu ca khó thay vì sửa mã.
- Nới clippy/rustfmt, thêm `#[allow]` hàng loạt để qua cổng.
- Ghi lại oracle bằng **bản Rust** (oracle phải từ bản cũ).
- "Sửa" bug gốc âm thầm: mọi chỗ khác bản cũ phải nằm trong `PORTING.md`.

## 7. Đọc gì khi nào

| Tình huống | Đọc |
|---|---|
| Lập `PORTING.md`, ánh xạ API/test, lịch chu kỳ | [porting-template](references/porting-template.md) |
| Ghi golden, so đầu ra, EOL/đường dẫn Windows, có dùng `insta` không | [oracle-golden](references/oracle-golden.md) |
| Viết mã Rust, lỗi, ownership, clippy | skill `rust` |
| Viết test trước, nhìn test đỏ | skill `tdd` |
| Trước khi báo xong | skill `verify-before-done` |
| Review diff port | skill `code-review` |
