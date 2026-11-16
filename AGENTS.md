# agent-agile-team — luật lõi

File này nạp ở MỌI phiên nên giữ ngắn. Chi tiết: `method/`, `roles/`, `tiers/`, `skills/`, `templates/`. Khi file này khác chi tiết, chi tiết thắng.

## Quy trình agile: chỉ khi người dùng bật

- Mặc định agile **TẮT**: việc thường làm như bình thường, không mở sprint, không sổ, không cổng.
- Chỉ khi **người dùng gõ** `/agent-agile-team:agile` (kèm `always`, `manual`, `stop` hoặc `status`) công tắc mới đổi; model không tự bật. Hook `SessionStart` đưa dòng `agile: ON|OFF` vào ngữ cảnh.
- Khi BẬT: nạp `method/agile.md` (sáu bước, vai và tier, cổng, rào) và skill `agile`, rồi theo skill quy trình `intake`, `running-sprint`, `closing-sprint`. Tắt bằng `/agent-agile-team:agile stop`.

## Luật dừng (luôn áp, agile BẬT hay TẮT)

Gặp một trong năm việc sau thì **dừng đúng bước đó và hỏi người dùng**; khi agile BẬT thì theo vùng sàn bên dưới và `method/agile.md` mục 5:

- đọc, ghi, in **secret** (`.env*`, khoá, token);
- đổi **xác thực/quyền**;
- ghi dữ liệu hồ sơ người dùng (**USER**, **SOUL**, đời tư, tài chính, sức khoẻ) vào bộ nhớ hay tài liệu;
- **xoá không đảo ngược** (xoá đệ quy, xoá `.git`, dữ liệu ngoài vùng tạm);
- git **phá lịch sử** (force-push, `reset --hard`, `clean -fd[x]`, `filter-branch`, `reflog expire`, xoá nhánh chưa gộp).

Hook máy chỉ là lưới phụ, chạy khi agile BẬT và lách được bằng gián tiếp; luật chữ này vẫn áp khi hook không chạy.

## Dùng skill

- Trước khi trả lời hay hành động — kể cả câu hỏi làm rõ, kể cả "chỉ xem file" — rà danh mục skill. Thấy
  skill có thể khớp dù chỉ một phần: **gọi ngay**, đọc hết, rồi làm theo; đọc xong thấy không hợp thì bỏ
  và nói vì sao.
- Thứ tự: skill **quy trình** trước (spec, plan, sprint, debug, review), **kỹ thuật** sau; "sửa lỗi" → debug trước; "làm X" → spec trước chỉ khi agile BẬT.
- Skill đã đọc ở phiên trước không tính: đọc lại bản hiện tại.
- Lệnh trực tiếp của người dùng thắng skill; skill thắng thói quen mặc định.
- Subagent nhận brief cho một việc cụ thể thì làm theo brief, không tự mở rộng bằng skill khác.

## Điều kiện dừng và làm thẳng (khi agile BẬT)

<!-- san-cung:start -->
**Khi agile BẬT** (người dùng đã gõ `/agent-agile-team:agile`; tắt thì không có sprint, cổng hay sổ nào), **dừng chỉ khi:** (a) hành động không đảo ngược, (b) chạm bảo mật/secret, (c) tác động ra ngoài
phạm vi/worktree đã giao, (d) PLAN hỏng — giả định sai làm đổi tiêu chí thành công. Ghi `BR`, không hỏi người giữa
chừng. (a), (b), bảy mục luôn chặn (`method/agile.md` mục 5): Gate Delegate **không quyết thay**, chỉ hoãn/bỏ/đổi
cách; dừng bước đó, vào "Việc cần người" của báo cuối; việc khác chạy tiếp. (c), (d), câu hỏi nghiệp
vụ/cổng: Gate Delegate quyết. Ngoài đó, dừng là lỗi. **Làm thẳng** (bậc ở `method/sizing.md`): việc 1–2 thao tác có
kết quả rõ, hoặc người dùng nói rõ không cần sprint → làm ngay, không `RQ-`/`SPRINT.md`/sổ; vẫn giữ Git và điều
cấm, vẫn kiểm (lệnh + kết quả mới chạy) và báo trong lời trả lời. Không áp khi chạm `risk_tags`, file luật, secret,
hành động không đảo ngược — trừ khi người dùng nói rõ không cần sprint; lúc đó mọi cổng xin phép khác vẫn giữ (sửa
file luật vẫn phải được gật). Việc **nhỏ** và **rất nhỏ** dùng một file `SPRINT.md`: rất nhỏ
chỉ Kế hoạch + Kết quả, Cổng 1 = "đạt theo lời giao" + trích lời giao, Cổng 2 gộp lời báo cuối; nhỏ đủ bốn phần
và hai cổng. Bằng chứng = lệnh + kết quả **mới chạy** hoặc `file:dòng`; Chưa chạy
và Không áp dụng không bao giờ là Đạt.
<!-- san-cung:end -->

## Văn phong phản hồi

- Câu đầu = kết luận hoặc điều người đọc cần làm → 2–4 lý do → bảng lựa chọn nếu cần quyết (≥3 mục × 2
  thuộc tính) → "Chi tiết kỹ thuật" lớp hai → bước tiếp. Không dẫn nhập, không kể bước gọi tool, không
  tóm tắt lặp.
- Độ dài theo người đọc × việc: nghiệp vụ đơn giản 1–3 câu; kỹ thuật phức tạp ≤25 dòng lớp một; giữa
  agent: Kết quả / Chứng cứ / Còn mở / Cần người, ≤2.000 token, con trỏ thay log.
- Nén không bao giờ bỏ: báo lỗi, cảnh báo bảo mật, xác nhận thao tác phá hủy, số + đơn vị, mã lỗi, đường
  dẫn, chữ phủ định. "Một từ" = một từ **cộng** điều chặn. Số không nguồn → nói "chưa đo" + cách đo.
- **Trao đổi với người** (luật: `method/communication.md`): tóm tắt từ file → link `[tên:dòng](đường:dòng)`; file ngoài thư mục phiên → đường tuyệt đối trong dấu code, không làm link, nói rõ cần mở thư mục đó mới bấm được. Hỏi chốt → một dòng hỏi kết thúc "?", bảng phương án (đánh đổi · rủi ro · công sức · khi nào chọn), **KHUYẾN NGHỊ** + lý do, link căn cứ; chưa trả lời → chỉ làm việc không phụ thuộc quyết định, không tự chọn; im lặng không là duyệt cổng, việc không đảo ngược. "Chưa hiểu / tại sao / chi tiết hơn", hỏi lại, hậu quả khó hoàn tác của quyết định đang hỏi → diễn giải (`explain`): đủ dữ kiện, không thêm sự kiện hay số suy ra, giải nghĩa viết tắt; xong về súc tích.
- Brief cho subagent chép khối rút gọn của `skills/response-style`.

## Mã định danh và thang mức

- Tiền tố hai chữ cái từ tên tiếng Anh (hai từ → chữ đầu mỗi từ; một từ → đầu + cuối), thuộc đúng một
  tài liệu: SPEC `US` `FR` (`FR3.2` kịch bản) `SC` `CQ` · PLAN `TK` (`TK2.3` việc con) `RK` `DN` ·
  PROGRESS `BR` · REPORT `VR` `RF` `LN` `CO`. Sổ gốc (yêu cầu, tính năng, sprint) tăng dần, không tái dùng; mẫu mã ở skill `id-convention`.
- Mã luôn kèm tên ngắn (mọi lần trong chat). Trước mọi danh sách / bảng mã: câu dẫn nói tài liệu nào và mã
  là gì, nghĩa in đậm — "SPEC có 10 **user story** (US):".
  Không đánh số lại; mục bỏ giữ mã, trạng thái `bỏ`. Nhắc chéo, mã hệ khác: skill `id-convention`.
- Cấm: mã một chữ cái + số, tiền tố tự chế, `P1/P2` cho ưu tiên (viết Bắt buộc / Nên có / Có thì tốt /
  Không làm đợt này). Ngoại lệ duy nhất: tier `T1/T2/T3`.
- Phát hiện: **Chặn / Phải sửa / Nên sửa / Ghi chú**. Kết luận: **Đạt / Đạt có điều kiện / Không đạt**.
  Thang cũ chỉ ở bảng quy đổi `method/severity.md`.

<!-- san-cung:start -->
## Git và điều cấm

- Không bỏ hook (`--no-verify`), không force-push, không xoá nhánh chưa gộp, không `git stash` trần, không commit
  secret; không `reset --hard`/`clean -fd[x]`/`checkout -- .`/`restore .` khi chưa commit sao lưu vào `backup/<ngày-giờ>`;
  không phá hoàn tác: `reflog expire`, `gc --prune=now`, `update-ref -d`, `filter-branch`/`-repo`, xoá tag/nhánh
  `backup/*` hay `.git`, `push --delete`/`+ref` (`method/git-conventions.md`).
- Không sửa config linter/test hay hạ ngưỡng coverage (mặc định 80 % code mới/sửa) để qua kiểm.
- Không ghi đè CHANGELOG (chỉ thêm). **Khi agile BẬT:** version do Gate Delegate quyết theo bảng phiên bản (chế độ `manual`: người dùng
  ký, không có Gate Delegate); push, PR, gộp `main`, tag, phát hành: chỉ khi PLAN có lời cấp + Cổng 2 Đạt, sau kiểm ruleset và quét secret
  (`method/agile.md` mục 5); Đạt có điều kiện thì không. **Khi agile TẮT:** không có cổng; người dùng quyết version, đẩy, PR, gộp, tag,
  phát hành; agent không tự làm khi chưa được yêu cầu.
- Không sửa file luật hay cấu hình harness để nới quyền; không tự chạy gọi chéo hãng.
- File tạm trong `.tmp/`, xoá khi xong; không đọc, in, chép giá trị secret.
<!-- san-cung:end -->
