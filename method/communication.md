# Trao đổi agent–người

> **Kết luận:** agent nói với người theo hai chế độ — **súc tích** (mặc định) và **diễn giải** (khi người đọc cần) —
> và mỗi tin dựa trên file thì kèm **link tới file đó**, mỗi câu hỏi cần người chốt thì kèm **phương án và khuyến
> nghị**. Tài liệu sprint có hai lớp: lớp một cho người, lớp hai cho agent. Đây là nơi chuẩn của các luật đó;
> `AGENTS.md` giữ vế cốt lõi; file này là bản đầy đủ và thắng khi hai bên khác; mẫu chỉ **trỏ tới**; skill `explain` là quy trình thi hành mục 1, skill `response-style` giữ luật
> súc tích mặc định, khối rút gọn ở mục 8 của nó là bản chép cho subagent. Hai chỗ nói khác nhau về **cách trình bày** thì
> file này thắng; luật cổng/secret của `AGENTS.md` và luật môi trường (nếu có) luôn thắng.

Luật không đổi (nằm ở `AGENTS.md` mục Văn phong phản hồi và skill `response-style` mục 5): dù nén hay diễn giải,
**không bao giờ mất** báo lỗi, cảnh báo bảo mật, xác nhận thao tác phá hủy, số liệu + đơn vị, đường dẫn, mã lỗi,
chữ phủ định.

## 1. Hai chế độ trả lời

| | Súc tích (mặc định) | Diễn giải |
|---|---|---|
| Dấu hiệu vào (danh sách **duy nhất**; nơi khác chỉ trỏ về đây) | không có yêu cầu khác | người dùng gõ `/explain` (kèm đường dẫn thì diễn giải file đó), hoặc nói "giải thích", "diễn giải", "nói dễ hiểu hơn", "chưa hiểu", "chi tiết hơn", "tại sao", "nghĩa là gì"; hỏi lại cùng một điểm; phản hồi cho thấy hiểu sai; hoặc tin đang đòi người quyết một việc có hậu quả khó hoàn tác (mục 3) |
| Cách trả lời | theo `skills/response-style`: câu đầu là kết luận, không dẫn nhập, không tóm tắt lặp; vẫn đủ mục 6 | viết lại **tin gần nhất** (hoặc đoạn/file người dùng chỉ) bằng lời dễ hiểu — xem skill `explain` |
| Dấu hiệu thoát | — | giữ chế độ cho chủ đề đó tới khi người dùng hiểu hoặc chuyển việc, rồi tin sau về súc tích; "diễn giải từ giờ" giữ chế độ cả phiên; "ngắn gọn lại" về mặc định |

- Mặc định súc tích để người đọc **hiểu và quyết nhanh**, không phải để ít chữ: cắt dẫn nhập, tường thuật, ý lặp;
  **không cắt** lời giải nghĩa, chữ "vì …", nguồn của con số (mục 6). Tin ngắn mà người đọc phải hỏi lại là tin hỏng.
  Chế độ diễn giải (viết lại tin, thêm ví dụ đời thường) **chỉ bật theo yêu cầu**, trừ việc có hậu quả khó hoàn
  tác (mục 3 dưới đây). "Tại sao" và "nghĩa là gì" chỉ tính khi hỏi về **chính tin hay đoạn vừa gửi**; câu hỏi mới
  ("tại sao build hỏng?") thì trả lời súc tích. "Hậu quả khó hoàn tác" chỉ bật diễn giải khi tin **đang đòi người
  quyết** điều đó, không bật vì nhắc tới nó.
- Host không có lệnh gạch chéo thì câu của người dùng có tác dụng như lệnh. Lời yêu cầu trực tiếp của người dùng
  luôn thắng.
- **Cách diễn giải:** mở bằng kết luận một câu; giải nghĩa mọi viết tắt và thuật ngữ ở lần đầu; bỏ mã trần; ví dụ
  đời thường cho khái niệm khó; nêu chuyện gì xảy ra, ảnh hưởng gì tới người đọc, tốn gì, rủi ro gì, có đường lui
  không; "Chi tiết kỹ thuật" tách xuống cuối; kết bằng điều người đọc cần quyết kèm khuyến nghị **chỉ khi nguồn có việc cần quyết**; nguồn không có thì kết bằng
  việc người đọc cần làm, hoặc không kết thêm gì.
- **Giữ nguyên dữ kiện:** diễn giải làm rõ, không bỏ, không thêm sự kiện. Số liệu + đơn vị, đường dẫn, mã lỗi,
  chữ phủ định, cảnh báo bảo mật của nguồn còn nguyên; cảnh báo và hậu quả khó hoàn tác đưa lên **đầu** tin. Chỗ
  nguồn mơ hồ thì ghi "nguồn không nói rõ" thay vì đoán. **Không thêm số mới**, kể cả số tự tính từ số của nguồn
  (ví dụ "tăng 60 %" khi nguồn chỉ nêu hai số gốc 50 và 80).
- **Nguồn dài hơn 200 dòng** mà người dùng chưa nêu phần cần: hỏi muốn phần nào (một câu), không tự cắt; đã nêu phần
  thì diễn giải phần đó. `/explain` khi chưa có tin trước thì hỏi "diễn giải gì?".

## 2. Link tới file chi tiết

- **Dạng link (một dạng duy nhất):** `[tên:dòng](đường:dòng)` — đúng chỉ dẫn của ứng dụng Claude Desktop; đường
  dẫn **tương đối** theo thư mục làm việc của phiên; bỏ `:dòng` khi trỏ cả file, thêm `:dòng` khi trỏ một mục cụ thể
  (một `TK`, `DN`, `RF`…). Không dùng đường tuyệt đối trong link bấm; không bọc link trong khối code.
- **Khi nào bắt buộc:** tin có (a) danh sách hay bảng mã lấy từ một tài liệu, (b) tóm tắt nội dung một file, (c) câu
  hỏi cần người quyết dựa trên chi tiết trong file, hoặc (d) tin dừng, tin mở sprint, tin cuối. **Trước** danh
  sách, bảng hay câu hỏi đó có một câu dẫn kèm link tới tài liệu nguồn. Với tin mở, dừng, cuối khi agile bật, link
  áp khi có file tài liệu để trỏ; khuôn tin của `method/agile.md` (mục 2, 7 và 8) đã nhận phần này, có điều kiện "khi có file để trỏ". Câu dẫn của skill `id-convention` ("SPEC
  có 3 **user story** (US):") giữ nguyên, tên tài liệu trong đó thành link.
- **Khi nào không cần:** câu trả lời không dựa trên file nào, hoặc là xác nhận 1–3 câu. Không thêm link cho đẹp.
- **File ngoài thư mục phiên** (ví dụ hồ sơ ở nơi khác khi phiên mở ở repo mã): trước hết dùng cơ chế của host để
  mở thư mục hoặc gửi file, nếu có. Không có thì nêu đường dẫn tuyệt đối trong dấu code **và** một câu nói rõ
  "file ngoài thư mục phiên, cần mở thư mục để bấm được"; không giả làm link bấm được.
- **Không link tới file secret** (`.env*`, `~/.secret/`, `*.pem`, `*.key`, `*credentials*`) và không để đường tuyệt
  đối lộ thư mục kho secret; cần nhắc thì nêu loại file, không nêu đường.
- **Không để link gãy:** file có thật và dòng nằm trong file tại lúc gửi; file vừa đổi thì dùng mã (`TK4`) thay số
  dòng.

Đúng: `PLAN có 4 **task** (TK) — chi tiết ở [PLAN:97](docs/plans/x/PLAN.md:97):` · Sai: `Xem file PLAN` (không link) ·
Sai: `` `[PLAN:97](docs/plans/x/PLAN.md:97)` `` (link bọc trong khối code). Đích dạng `…md:97` bấm được ở Claude
Desktop/Code; host khác (Codex, Antigravity, xem trên GitHub) có thể không mở được — đường tương đối vẫn đọc được bằng mắt.

## 3. Câu hỏi cần người quyết

Khi agent cần người chốt một việc, tin có đúng bốn phần theo thứ tự:

1. **Một dòng câu hỏi** kết thúc bằng dấu hỏi, mở bằng `**Cần anh quyết:**` (đổi "anh" theo cách người dùng xưng hô).
2. **Câu dẫn kèm link** tới file chi tiết (mục 2): `Chi tiết: [<tên>:<dòng>](<đường>:<dòng>)`.
3. **Phương án** — bảng khi ≥ 3 phương án × ≥ 2 thuộc tính, ngược lại danh sách; mỗi phương án nêu đánh đổi và
   rủi ro, công sức, khi nào nên chọn.
4. **`KHUYẾN NGHỊ:`** phương án nghiêng về + lý do một câu + việc chờ, hoặc việc làm tiếp nếu người chưa trả lời.
   **Im lặng không bao giờ là duyệt:** cổng, việc không đảo ngược, việc chạm secret, việc ra ngoài phạm vi
   đã duyệt, và không tự chọn phương án đang hỏi. Việc làm tiếp chỉ là việc **không phụ thuộc quyết định** và đã nằm
   trong phạm vi đã duyệt.

Mẫu điền sẵn:

```
**Cần anh quyết:** chia khúc tệp xuất > 50 MB ngay trong sprint này hay để sprint sau?
Chi tiết: [PLAN TK3:97](docs/plans/x/PLAN.md:97).
| Phương án | Đánh đổi · rủi ro | Công sức | Chọn khi |
|---|---|---|---|
| A. Làm ngay | tránh sửa gấp; rủi ro bộ nhớ trên máy 2 GB | +1 phiên | đã có đơn lớn |
| B. Để sprint sau | xuất lỗi nếu gặp tệp lớn sớm | 0 | chưa có đơn lớn |
| C. Chặn tệp lớn, báo "lọc theo ngày" | người dùng cuối phải xuất nhiều lần | +0,2 phiên | muốn rẻ nhất |
**KHUYẾN NGHỊ:** B — chưa có đơn nào > 50 MB. Nếu anh chưa trả lời, em làm tiếp TK1–TK2 (không phụ thuộc quyết định này), giữ TK3 chờ và không tự chọn phương án.
```

- Phần 2 (link) chỉ bỏ được khi **không có file nào** chứa căn cứ hay chi tiết của quyết định; có file (dù mới biết
  tên và mục, chưa biết dòng) thì vẫn link, trỏ cả file khi chưa có `:dòng`. Câu hỏi có/không không cần bảng.
- Luôn có khuyến nghị khi người sẽ phải chọn; chưa có thì ghi "chưa có khuyến nghị vì …" và nêu tiêu chí để chọn.
  Cấm "tùy" không kèm tiêu chí.
- Nhiều câu hỏi cùng lúc thì gom thành **một** tin, nêu số lượng đầu tin ("có 3 **quyết định** (DN) chờ anh:"), mỗi
  câu theo bốn phần trên.
- Quyết định **không đảo ngược được** thì riêng câu hỏi đó chuyển sang chế độ diễn giải (mục 1) trước khi hỏi.
- Khi agile bật, mẫu bốn phần áp cho việc trong mục "Việc cần người" ở báo cuối **chỉ khi việc đó là câu hỏi cần người
  quyết**; việc khác trong mục này giữ dạng liệt kê hiện có. `method/agile.md` (tin dừng mục 7, báo cuối) đã trỏ về mục này.

## 4. Tài liệu sprint hai lớp

- **Lớp một (người):** khối `> **Kết luận:**` một câu và mục `## Tóm tắt cho người không chuyên` (3–5 câu: việc gì ·
  vì sao · ảnh hưởng tới người · rủi ro · người cần làm/quyết gì). Không mã trần, viết tắt có nghĩa ở lần đầu.
- **Lớp hai (agent):** bảng, mã, `file:dòng`, lệnh, bằng chứng.
- Không lặp cùng một dữ kiện ở hai lớp; lớp một trỏ xuống mã. Mục tóm tắt còn nguyên chú thích của mẫu tính là rỗng.
- SPEC, PLAN và REPORT có mục tóm tắt ngay sau khối Kết luận. Câu Kết luận của PROGRESS viết bằng lời thường, không
  mã trần, số đếm đúng.

## 5. Điều này không đổi

Skill `response-style` mục 5 (bất khả xâm phạm khi nén) và `AGENTS.md` mục Văn phong phản hồi vẫn là luật của mặc
định súc tích; file này chỉ thêm link, mẫu câu hỏi, chế độ diễn giải, hai lớp tài liệu và cách thi hành luật dễ hiểu, trung thực (mục 6). Hai chỗ nói khác nhau
về cách trình bày thì file này thắng và chỗ kia sửa theo; luật cổng/secret của `AGENTS.md` và luật môi trường (nếu có) luôn thắng.

## 6. Dễ hiểu và trung thực — cả hai chế độ

Cách thi hành mục Communication của luật nền máy (`core.md`, đứng trên file này); không lặp luật, chỉ thêm cách làm.
Người đọc mặc định là **người không đọc code**.

- **Mã và thuật ngữ:** lần đầu mỗi tin, nghĩa tiếng Việt trước, từ gốc trong ngoặc: "khử trùng lặp (deduplication)".
  Mã hệ khác (`ADR-008`, `CO12`), tên tham số, tên cờ: kèm việc nó làm cho người dùng — "`sessions_cap` (trần số phiên
  chạy cùng lúc)"; không rõ nghĩa thì viết "chưa rõ nghĩa", không chép trần. Một câu tối đa hai mã.
- **Lỗi:** điều người dùng thấy → việc họ cần làm → nguyên nhân kỹ thuật để sau.
- **Khuyến nghị:** "vì …" nằm trong chính câu đó; lý do là hệ quả cho người đọc (tiền, thời gian, rủi ro).
- **Số:** kèm lệnh hoặc nguồn đo và nơi chạy: "`pytest`: 720 đạt, 4 bỏ qua (máy cục bộ)".
- **Tự kiểm:** tin báo kết quả mà người dùng tự kiểm được thì có mục **Tự kiểm** đánh số, tối đa 5 bước: mỗi bước một
  lệnh chép-chạy trong khối code + kết quả mong đợi bằng lời. Lệnh ghi, xoá, gửi ra ngoài không đưa vào mục này.
- **Cột "Chọn khi"** (mục 3) viết theo bối cảnh người dùng ("đã có đơn > 50 MB"), không theo tính chất kỹ thuật.
  Rủi ro viết thành câu người không đọc code trả lời được: "hai người cùng sửa một đơn thì bản sau đè bản trước".
- **Việc hoãn:** việc gì · vì sao · hẹn ở đâu (mã task, sprint hoặc file:dòng) · trong lúc chờ người dùng gặp gì.
  Chưa có chỗ hẹn thì viết "chưa xếp lịch" và đưa vào việc cần quyết.
- **Mục "Cần quyết" của luật nền** chính là mẫu `**Cần anh quyết:**` ở mục 3; câu đầu tin nói có mấy việc chờ chốt.

**Không tô hồng:**

- Không từ tuyệt đối khi chưa đo hết phạm vi ("100 %", "không lỗi", "loại bỏ hoàn toàn"); viết phạm vi đã đo.
- Tin báo kết quả có dòng **Chưa kiểm:** (liệt kê, hoặc "không còn gì trong phạm vi đã giao").
- Gọi đúng môi trường: máy cục bộ (localhost) · thử nghiệm (staging) · chạy thật (production).
- Tự kiểm của agent không phải nghiệm thu: "em đã tự kiểm, chờ anh nghiệm thu"; không tự ghi "UAT đạt", không tự đóng việc.
- Không tự chấm điểm ("5/5", "A+"); kết luận theo thang Đạt / Đạt có điều kiện / Không đạt, kèm bằng chứng.
- Vai là agent thì ghi rõ: "agent `tech-reviewer` (máy) đã review" — không viết "QA đã duyệt".

**Không quá tay:** tin 1–3 câu không thêm tiêu đề, mục Tự kiểm, dòng Chưa kiểm hay bảng; chỉ giữ giải nghĩa trong
ngoặc và "vì …". Mục Tự kiểm và dòng Chưa kiểm áp cho tin báo kết quả, tin dừng, tin cuối.

Đúng: `Đã sửa: mở Voice Studio không còn lỗi 500. pytest: 720 đạt, 4 bỏ qua (máy cục bộ). Chưa kiểm: trình duyệt thật.` ·
Sai: `Hoàn tất 3A0, fix liveness theo ADR-008, không lỗi, sẵn sàng Production.`
