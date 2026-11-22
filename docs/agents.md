# agents/

Agent chuyên đề, mỗi agent một file `<tên>.md`. Agent **chỉ đọc** (không sửa code, không chạy lệnh ghi; cây làm việc "sạch" = `git status --short` rỗng, và khi chạy kiểm
thì dùng cờ không ghi cache nếu có, như `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`), riêng
`build-fixer` được sửa file (chỉ sửa đúng chỗ lỗi build đòi, chỉ dùng khi build đang đỏ). Reviewer, analyzer và
`code-explorer` là agent **khác** người làm, được Tech Reviewer (hoặc Analyst, Architect với `code-explorer`) kéo
theo trigger (skill `code-review`, thẻ `roles/verifier/`). Frontmatter không ghi `model:`; model thực tế do bảng tier của môi trường quyết. Nguồn và giấy phép: xem `NOTICE`.

## Mục lục — 16 agent

| Agent | Kéo khi |
|---|---|
| [python-reviewer](../agents/python-reviewer.md) | code Python đổi: bảo mật, xử lý lỗi, type hint, idiom, đồng thời |
| [fastapi-reviewer](../agents/fastapi-reviewer.md) | ứng dụng FastAPI đổi: route, schema, dependency, async, auth, CORS, OpenAPI — soát sẵn sàng chạy thật |
| [database-reviewer](../agents/database-reviewer.md) | SQL, migration, schema, index, RLS hay hiệu năng CSDL đổi (PostgreSQL trước); không có Write/Edit |
| [security-reviewer](../agents/security-reviewer.md) | diff chạm đầu vào người dùng, xác thực/phân quyền, endpoint, secret, tích hợp ngoài — đích của security escalation |
| [silent-failure-hunter](../agents/silent-failure-hunter.md) | code bắt, bọc, thử lại hay fallback lỗi — săn lỗi bị nuốt, fallback sai, mất ngữ cảnh lỗi |
| [comment-analyzer](../agents/comment-analyzer.md) | code thêm/sửa comment, docstring, tài liệu API — kiểm khớp code, đủ ý, không mục |
| [rag-pipeline-reviewer](../agents/rag-pipeline-reviewer.md) | pipeline RAG đổi: kho vector, chunking, embedding, rerank, trích dẫn, bộ đánh giá |
| [code-explorer](../agents/code-explorer.md) | cần hiểu tính năng có sẵn trước khi đổi: lần điểm vào, luồng chạy, tầng, phụ thuộc thành bản đồ `file:dòng`; chỉ đọc |
| [code-reviewer](../agents/code-reviewer.md) | review độc lập tổng quát một diff trước khi gộp (bảo mật, đúng, chất lượng, test), lọc theo độ chắc chắn, được trả 0 phát hiện |
| [test-analyzer](../agents/test-analyzer.md) | thay đổi thêm/sửa hành vi: kiểm test có thật sự phủ — nhánh và đường lỗi chưa test, assert không bắt hồi quy, mẫu flaky; không viết test |
| [typescript-reviewer](../agents/typescript-reviewer.md) | TypeScript/JavaScript đổi: an toàn kiểu, đúng async, xử lý lỗi, bảo mật Node, idiom |
| [react-reviewer](../agents/react-reviewer.md) | component React/Next.js đổi (`.tsx`/`.jsx`): hook, state, ranh giới server/client, a11y, hiệu năng render, bảo mật React; chạy cạnh `typescript-reviewer` |
| [build-fixer](../agents/build-fixer.md) | build, compile, import hay kiểm kiểu đang đỏ và cần sửa nhỏ nhất để xanh — **agent duy nhất được sửa file**; không nuốt lỗi, không bỏ/xoá test, không nới config; dừng sau 3 lần sửa hỏng |

## Ba agent vai quyết định (chỉ khi agile BẬT)

| Agent | Thẻ vai | Làm gì |
|---|---|---|
| [business-reviewer](../agents/business-reviewer.md) | [roles/verifier/business-reviewer.md](../roles/verifier/business-reviewer.md) | đọc sản phẩm như người dùng, báo `RF` đối chiếu `US`/`FR`/`SC` trước Cổng 2 |
| [gate-delegate](../agents/gate-delegate.md) | [roles/verifier/gate-delegate.md](../roles/verifier/gate-delegate.md) | ghi kết luận Cổng 1/2 thay người dùng khi có lời cấp; không phải người làm |
| [advisor](../agents/advisor.md) | [roles/advisor/advisor.md](../roles/advisor/advisor.md) | phản biện SPEC/PLAN trước Cổng 1; chỉ khuyến nghị |

Ba agent này chỉ đọc, thân mỏng, chỉ trỏ về thẻ vai. Các vai lõi còn lại (researcher, qa, implementer…) không có file agent riêng,
nên khi agile BẬT, giao việc qua subagent chung (`general-purpose`, `claude`, `Plan`, `Explore` hoặc để trống) phải mở đầu brief bằng thẻ
`[AAT role=<vai>]` (vai là tên trong `tiers/role-catalog.json`); `tier_hook` đọc thẻ đầu tiên và ép model theo vai như khi giao bằng tên agent.
`[AAT role=direct]` dành cho việc làm thẳng, không ép model. Thiếu thẻ bị chặn `role_tag_required`, vai lạ bị chặn `unknown_role`;
lối thoát: thêm thẻ, dùng `role=direct`, hoặc `/agent-agile-team:agile stop`. Agent có tên trong catalog và agent của plugin khác giữ nguyên.
