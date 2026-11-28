# skills/

Skill để **phẳng**: `skills/<tên>/SKILL.md` (+ `references/`, `tests/`, `scripts/`), vì harness chỉ dò một
cấp. Nhóm ghi trong frontmatter `metadata.group` và trong mục lục dưới. Frontmatter tiếng Anh
(`description` chỉ ghi **điều kiện kích hoạt**, bắt đầu bằng "Use when…"), thân tiếng Việt. Test Python
đặt trong `scripts/` của skill được `pytest` gom (`testpaths` trong `pyproject.toml`).

## 1. Quy ước frontmatter

| Khoá | Bắt buộc | Giá trị |
|---|---|---|
| `name` | có | trùng tên thư mục |
| `description` | có | điều kiện kích hoạt, "Use when…" |
| `metadata.group` | có | `process` (Quy trình) · `technique` (Kỹ thuật) · `verification` (Kiểm định) · `communication` (Giao tiếp & tối ưu) · `meta` (Meta) |
| `metadata.roles` | có | chuỗi các vai dùng skill, ngăn bởi dấu phẩy (`"implementer, qa"`), hoặc `"all"` |
| `metadata.kind` | không | `reference` — skill tham chiếu kỹ thuật (mẫu, bảng tra), không có luật sắt hay cổng; vắng = skill kỷ luật/quy trình |

## 2. Thử áp lực

- Skill **kỷ luật/quy trình** (có luật sắt hoặc cổng — không có `metadata.kind: reference`) **bắt buộc**
  có `tests/pressure.md`: 3 kịch bản thử áp lực, chạy bằng subagent không có skill (ghi lỗi) rồi có skill
  (phải đạt). Cách viết: skill `writing-skills`, `references/testing.md`.
- Skill **tham chiếu kỹ thuật** (`metadata.kind: reference`) không kiểm áp lực mà kiểm **truy xuất** (agent
  tìm đúng mục khi cần): bắt buộc có `tests/retrieval.md` đã chạy. Ngưỡng truy xuất là **mục tiêu kiểm** —
  `skills/writing-skills/references/testing.md` mục 9 (≥80 % câu tình huống Đạt hẳn **và** câu ranh giới Đạt);
  chưa phải skill nào cũng đạt. Skill dưới ngưỡng ghi trạng thái ở mục 4 (cột `below threshold`) và còn việc để lại
  (bổ sung nội dung rồi chạy lại); đừng đọc "có tệp thử" thành "đã đạt ngưỡng".
- `security-audit`, `web-qa` là skill **chỉ báo cáo** (không sửa gì); kịch bản thật cần cả một repo hoặc
  trình duyệt dựng sẵn, nên thử áp lực bằng prompt tự chứa (đã chạy ở SPR-02, xem mục 4).
- Frontmatter của `pressure.md`/`retrieval.md`: `result` và `model` là kết quả đã chạy (không phải `not run`/
  `pending`/`chưa chạy`/`dự kiến`), `date`; mọi file có thêm `tier` và `skill_sha` (băm cây skill trừ
  `tests/`), không miễn theo ngày. `tests/test_skill_tests.py` kiểm các điều này.
- `tests/scenarios.txt` (tuỳ chọn): **nguyên văn** prompt các kịch bản đã chạy, để chạy lại được. Đuôi `.txt`
  để `check` không quét như tài liệu; file chứa khoá, mật khẩu hay token làm mồi thì dòng thứ hai ghi rõ
  chúng là **GIÁ TRỊ GIẢ**.

**Hiện trạng thử:** 42 trong 42 skill có tệp thử đã chạy; `agile` 17/18 lượt GREEN theo cách đọc chặt (SPR-33 TK7, n = 2, AG-1..AG-8, AG-5 r2 trượt vế rào máy; 18/18 chỉ khi đọc nới; RED chỉ cho 4 ca mới AG-6, AG-6b, AG-7, AG-8: 3/8); kết quả trước (TK6g): `agile` 9/10 lượt GREEN (n = 2, chưa có lượt RED, AG-5 1/2) — bảng ở mục 4.

## 3. Mục lục — 42 skill

### Quy trình

| Skill | Dùng khi |
|---|---|
| [intake](intake/SKILL.md) | tiếp nhận yêu cầu: một tin gom không chờ trả lời (mục tiêu, câu hỏi phản biện, khuyến nghị bậc, mở sprint hay làm thẳng) cùng tin mở agile (tự bật, người ký cổng là Gate Delegate) → ghi `RQ-`, định cỡ/rủi ro, 11 điểm thiếu ngữ cảnh → ASSUMPTION/`CQ` |
| [shaping-spec](shaping-spec/SKILL.md) | 3 đường Spike/Bounded/Architectural, viết SPEC, gom `CQ`, không code trước Cổng 1 |
| [writing-plan](writing-plan/SKILL.md) | `TK` có file + giao diện + bước RED→GREEN→commit, trọng tâm review ≤5 |
| [running-sprint](running-sprint/SKILL.md) | hai chế độ thực thi, brief/review theo việc, phán quyết, 4 điều kiện dừng, 3 vòng khuyến nghị |
| [closing-sprint](closing-sprint/SKILL.md) | tiền kiểm → REPORT/Cổng 2 → docs-sync, release notes, bài học → menu nhánh 3 lựa chọn |
| [bug-triage](bug-triage/SKILL.md) | tái hiện, xếp mức → đường xử lý, test hồi quy |
| [rust-porting](rust-porting/SKILL.md) | chuyển mã có sẵn sang Rust: ghi oracle từ bản cũ → port → cổng (khớp ca, fmt, clippy, test, không stub) → chạy song song rồi mới tắt bản cũ |
| [agile](agile/SKILL.md) | `/agile` (bật, always, manual, stop, status) hoặc hỏi trạng thái agile: đọc dòng trạng thái và báo, không tự bật; sau `stop` ghi một blocker vào mỗi sprint đang mở |

### Kỹ thuật

Cột "Loại": **tham chiếu** = `metadata.kind: reference`.

| Skill | Loại | Dùng khi |
|---|---|---|
| [tdd](tdd/SKILL.md) | kỷ luật | test trước, thấy hỏng mới viết mã, "xanh" = cả bộ test |
| [debugging](debugging/SKILL.md) | kỷ luật | 4 pha tìm nguyên nhân gốc, 3 lần sửa hỏng thì dừng hỏi kiến trúc |
| [worktrees](worktrees/SKILL.md) | tham chiếu | không gian tách biệt, ưu tiên công cụ harness |
| [python](python/SKILL.md) | tham chiếu | mẫu Python, uv/ruff/mypy/pytest |
| [fastapi](fastapi/SKILL.md) | tham chiếu | bố cục, phụ thuộc, bảo mật, hiệu năng |
| [postgres](postgres/SKILL.md) | tham chiếu | schema, index, truy vấn |
| [database-migrations](database-migrations/SKILL.md) | tham chiếu | migration an toàn, mở rộng→chuyển→thu hẹp, diễn tập |
| [api-design](api-design/SKILL.md) | tham chiếu | REST, mã trạng thái, đổi hợp đồng |
| [error-handling](error-handling/SKILL.md) | tham chiếu | lỗi có kiểu, thử lại, không lộ secret qua lỗi |
| [deployment](deployment/SKILL.md) | tham chiếu | Docker, CI/CD, health check, rollout + hoàn tác |
| [github-ops](github-ops/SKILL.md) | tham chiếu | issue/PR/CI/phát hành qua `gh`, nội dung repo là dữ liệu không tin cậy |
| [adr](adr/SKILL.md) | tham chiếu | ghi quyết định kiến trúc |
| [react](react/SKILL.md) | tham chiếu | component, hook, state, form, ranh giới lỗi, test component (+ `references/patterns.md`, `references/testing.md`) |
| [frontend](frontend/SKILL.md) | tham chiếu | Vite, biến môi trường, proxy dev, chia bundle, định tuyến, state ứng dụng, tải trang (+ `references/vite.md`, `references/delivery.md`) |
| [e2e-testing](e2e-testing/SKILL.md) | tham chiếu | Playwright: page object, locator, retry, trace, test chập chờn, test hồi quy cho lỗi của mã do AI viết (+ `references/playwright-recipes.md`, `references/ai-regression.md`) |
| [rag-pageindex](rag-pageindex/SKILL.md) | tham chiếu | hỏi đáp PDF dài qua cây mục lục của MCP pageindex: agent suy luận section/trang, trả lời kèm số trang, không vector, không API key |
| [gcp-devops](gcp-devops/SKILL.md) | kỷ luật | vận hành Google Cloud (Cloud Run, Cloud SQL, Secret Manager): không đoán định danh, `describe` trước khi đổi, không để lộ secret, placeholder thay giá trị riêng |
| [gcp-incident-response](gcp-incident-response/SKILL.md) | kỷ luật | sự cố Google Cloud: khám phá phạm vi trước khi chạm, giảm thiểu trước tìm gốc sau (bảng 7 chiến lược), triage log không tràn ngữ cảnh, SLO, postmortem |
| [rust](rust/SKILL.md) | tham chiếu | viết, sửa, review Rust: ownership, kiểu, lỗi, async, FFI Windows; vòng biên dịch qua sandbox/cầu, bẫy Windows, workspace mẫu có bảng lint |
| [tauri-desktop](tauri-desktop/SKILL.md) | tham chiếu | vỏ desktop Tauri v2 trên Windows: capabilities, IPC, sidecar, Job Object, bộ cài |

### Kiểm định

| Skill | Dùng khi |
|---|---|
| [verify-before-done](verify-before-done/SKILL.md) | trước mọi tuyên bố xong/đạt, khi ghi `VR` |
| [code-review](code-review/SKILL.md) | định tuyến reviewer, cổng xác minh, brief reviewer, tiếp nhận review |
| [plan-review](plan-review/SKILL.md) | review PLAN trước Cổng 1, từ cỡ vừa |
| [security-review](security-review/SKILL.md) | code thêm bề mặt tấn công, đích của security escalation |
| [security-audit](security-audit/SKILL.md) | audit cả repo, chỉ chạy khi được giao |
| [web-qa](web-qa/SKILL.md) | kiểm trên trình duyệt, chỉ báo cáo |
| [hooks-guardrails](hooks-guardrails/SKILL.md) | luật phải luôn đúng thì để máy giữ bằng hook xác định: chặn path, quét khoá trước commit, Stop-hook chạy test tuỳ chọn; không hook nào gọi model (+ `references/templates.md`, `scripts/protect_paths.py`) |

### Giao tiếp & tối ưu

| Skill | Dùng khi |
|---|---|
| [response-style](response-style/SKILL.md) | chọn độ dài, cấu trúc, giọng khi trả lời người hay agent; trỏ sang `explain` khi người đọc chưa hiểu |
| [explain](explain/SKILL.md) | `/explain` hoặc "chưa hiểu / tại sao / nói dễ hiểu hơn": viết lại tin gần nhất bằng lời dễ hiểu, giữ nguyên dữ kiện, xong về súc tích |
| [progress-report](progress-report/SKILL.md) | `/progress-report` hoặc "báo cáo tiến độ / đang làm tới đâu": đọc ROADMAP → SPRINTS → REQUESTS → hồ sơ sprint → Git, trả một báo cáo chuẩn bảy phần (tổng quan, việc còn nợ, bảng 5 sprint xong, 5 sắp tới, lộ trình ≤20, đề xuất bước tiếp); chỉ đọc |
| [id-convention](id-convention/SKILL.md) | đặt, đọc, nhắc chéo, kiểm mã mục trong tài liệu sprint và chat |
| [token-economy](token-economy/SKILL.md) | phiên dài, output lớn, subagent báo cáo, nén ngữ cảnh, tuyên bố tiết kiệm token |

### Meta

| Skill | Dùng khi |
|---|---|
| [writing-skills](writing-skills/SKILL.md) | tạo/sửa skill, viết description hoặc thử áp lực, đề xuất nâng bài học thành skill, chẩn đoán phiên/sprint chạy sai |
| [eval-harness](eval-harness/SKILL.md) | tiêu chí đạt/hỏng và kiểm hồi quy cho tính năng có gọi mô hình của sản phẩm (đánh giá kết quả mô hình, không phải thử áp lực skill) |

## 4. Hiện trạng thử — 42 skill

Đọc từ frontmatter của tệp thử, không từ trí nhớ (`tests/test_skill_tests.py` đối chiếu bảng này với frontmatter). Tệp kỷ luật:
cột `result` là đoạn đầu (số kịch bản Đạt), chi tiết RED và GREEN ở chính tệp. Tệp truy xuất: một thước chung — `strict` là
số câu Đạt hẳn trên tổng số câu (kèm số Một phần và Không đạt), `points-right` là Đạt + Một phần (số câu trỏ đúng nơi),
`at/below threshold` là so với ngưỡng ở `skills/writing-skills/references/testing.md` mục 9; định nghĩa đầy đủ ở mỗi `retrieval.md`.
`below threshold` nghĩa là skill còn thiếu nội dung, không phải agent trỏ sai. `date` 2026-10-03 là lần chạy hoặc chạy lại ở SPR-02, 2026-10-04 ở SPR-04, trên bản skill hiện tại
(`claude-sonnet-5-5`, tier T3); mọi tệp đều có `tier` và `skill_sha`.

| Skill | Loại | Tệp thử | `result` | `date` |
|---|---|---|---|---|
| [bug-triage](bug-triage/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 scenarios GREEN pass at n = 3 (KB1-KB3 at three runs per phase, GREEN 3/3, 3/3, 3/3 runs Đạt, RED 0/3, 0/3, 3/3 runs Đạt so KB1 and KB2 gave way and KB3 passed as-is, kept as regression; the grader is the same model family as the subjects, CQ3) | 2026-10-04 |
| [closing-sprint](closing-sprint/tests/pressure.md) | kỷ luật | `pressure.md` | 6/6 pass (OFF-4 2/2, ON-1 2/2, STOP-1 2/2); SPR-32 TK6d 2026-11-16, n = 2 per case, GREEN only, grader opus independent of the runner; RED baseline in evidence/red-baseline.md (TK2: STOP-1 0/2); simulated state line | 2026-11-16 |
| [intake](intake/tests/pressure.md) | kỷ luật | `pressure.md` | 8/8 pass (OFF-1 2/2, OFF-2 2/2, ON-1 2/2, STOP-1 2/2); SPR-32 TK6d 2026-11-16, n = 2 per case, GREEN only, grader opus independent of the runner (not blind to the case: it saw the CHẤM block); RED baseline in evidence/red-baseline.md (TK2: OFF-2 0/2, STOP-1 0/2); simulated state line | 2026-11-16 |
| [running-sprint](running-sprint/tests/pressure.md) | kỷ luật | `pressure.md` | 0/2 fail on the SPR-37 TK5 re-run 2026-11-25 (STOP-1 only, GREEN, n = 2, subjects sonnet, grader opus independent of the runner; both runs fail criterion 4: no BR2 is written in the single simulated turn because references/agile.md item 9.4 puts the BR after waiting for the safe point; criteria 1, 2, 3 and 5 pass, criterion 6 has two readings and does not change the result; two earlier runs that forbade reading references/agile.md were discarded as a method error; OFF-3, ON-1 and the rs-* cases were not re-run on this skill_sha); previous: 4/6 pass (OFF-3 2/2, ON-1 2/2, STOP-1 0/2 FAIL on criterion 6 only); re-run 2026-11-22 on the tree after the role-tag line was added to SKILL.md step 4.1 and references/brief.md, n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; STOP-1 miss recorded as a failure, not softened. Previous run: 5/6 pass (OFF-3 2/2, ON-1 1/2 FAIL, STOP-1 2/2); SPR-32 TK6g re-run 2026-11-16 on the final text (ledger columns listed, BR2 format), n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; ON-1 r1 fails criterion 2 again (it says only 'sáu cột' and never names role, tier, model; grader: close call); history: TK6f 5/6 (same ON-1 r1 miss), TK6d 4/6; SPR-32 TK6f re-run 2026-11-16 on the edited text, n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; ON-1 uses the relaxed criteria 2 and 3: r1 fails criterion 2 (reply does not say the ledger row carries role, tier, model; grader: borderline); history: TK6d 4/6 (ON-1 0/2 on the strict TDD and effort criteria); RED baseline in evidence/red-baseline.md (TK2: STOP-1 0/2); simulated state line | 2026-11-25 |
| [shaping-spec](shaping-spec/tests/pressure.md) | kỷ luật | `pressure.md` | 6/6 GREEN pass on the current tree (rerun 2026-11-13 at n = 1 on sp-4, sp-7, sp-8, sp-9, sp-12 both texts, after SPR-20 TK6 added the Người quyết column); earlier 1/1 GREEN pass (sp-12, both texts); RED on af1ad4f 0/1 pass (sp-12 v2); old scenarios 4/4 | 2026-11-13 |
| [writing-plan](writing-plan/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass on the current tree (rerun 2026-11-13 at n = 1, wp-1..wp-3, after SPR-20 TK6 added the Người quyết column; wp-5 not rerun); RED 0/3 pass (3 partial); wp-5 bổ sung RED fail, GREEN pass after exact-label fix (2026-10-22) | 2026-11-13 |
| [adr](adr/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 6/7 (+1 partial, 0 fail), at threshold; points-right 7/7 | 2026-10-04 |
| [api-design](api-design/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 3/7 (+4 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [database-migrations](database-migrations/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 2/7 (+5 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [debugging](debugging/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass | 2026-10-04 |
| [deployment](deployment/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 6/7 (+1 partial, 0 fail), at threshold; points-right 7/7 | 2026-10-24 |
| [e2e-testing](e2e-testing/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 2/7 (+5 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [error-handling](error-handling/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 0/7 (+7 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [fastapi](fastapi/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 2/7 (+5 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [frontend](frontend/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 2/7 (+5 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [github-ops](github-ops/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 1/7 (+6 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [postgres](postgres/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 4/7 (+2 partial, 1 fail), below threshold; points-right 6/7 | 2026-10-04 |
| [python](python/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 3/7 (+4 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [react](react/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 3/7 (+4 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [rust](rust/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 9/10 (+1 partial, 0 fail), at threshold; points-right 10/10 | 2026-11-28 |
| [rust-porting](rust-porting/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass | 2026-11-28 |
| [tauri-desktop](tauri-desktop/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 7/7 (+0 partial, 0 fail), at threshold; points-right 7/7 | 2026-11-28 |
| [tdd](tdd/tests/pressure.md) | kỷ luật | `pressure.md` | 4/4 GREEN pass | 2026-10-04 |
| [worktrees](worktrees/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 4/7 (+3 partial, 0 fail), below threshold; points-right 7/7 | 2026-10-04 |
| [rag-pageindex](rag-pageindex/tests/retrieval.md) | tham chiếu | `retrieval.md` | strict 7/7 (+0 partial, 0 fail), at threshold; points-right 7/7 | 2026-10-26 |
| [code-review](code-review/tests/pressure.md) | kỷ luật | `pressure.md` | 1/2 GREEN pass theo chữ, 2/2 theo ý (cr-1, cr-12 mới, n = 1, SPR-38 2026-11-28) | 2026-11-28 |
| [plan-review](plan-review/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass on the current tree (rerun 2026-11-07 at n = 1; 0 partial; RED not rerun, scenarios unchanged) | 2026-11-07 |
| [security-audit](security-audit/tests/pressure.md) | kỷ luật | `pressure.md` | 9/9 GREEN pass (n = 3 per scenario, 3/3 scenarios sa-1 to sa-3); RED 0/9 pass (9 partial); SPR-47 CO8 added one sentence to section 5 (daily mode, no hypothesis appendix) | 2026-11-01 |
| [security-review](security-review/tests/pressure.md) | kỷ luật | `pressure.md` | 3/4 GREEN pass theo chữ và theo ý (sec-1, sec-3b, sec-4; sec-2b một phần); SPR-19 2026-11-12, n = 1 mỗi ca | 2026-11-12 |
| [verify-before-done](verify-before-done/tests/pressure.md) | kỷ luật | `pressure.md` | 7/7 GREEN pass on the current tree (ver-7 new, ver-1 to ver-6 rerun) | 2026-10-23 |
| [web-qa](web-qa/tests/pressure.md) | kỷ luật | `pressure.md` | 4/4 GREEN pass on the current tree (wq-7 new, wq-1 to wq-3 rerun at n = 1) plus a real design-compare run that matched its expectation | 2026-10-23 |
| [id-convention](id-convention/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass | 2026-11-07 |
| [response-style](response-style/tests/pressure.md) | kỷ luật | `pressure.md` | 30/32 nhãn ước tính ở nhánh sửa (93,8 %) so 5/11 nhánh cũ (45,5 %), UAT chốt SPR-28; Fable phán quyết Đạt có điều kiện, chờ Đức gật bảng chấm | 2026-11-28 |
| [agile](agile/tests/pressure.md) | kỷ luật | `pressure.md` | 6/6 pass on the SPR-37 TK5 re-run 2026-11-25 (GREEN only, n = 2: AG-1 2/2, AG-5 2/2, AG-8 2/2; the original AG-8 r2 is not counted: the grader scored it a miss on a script name that the orchestrator may have miscopied when forwarding it and the original answer was not stored, so AG-8 r2 was re-run with a fresh subject and passed; AG-2, AG-3, AG-4, AG-6, AG-6b and AG-7 were not re-run on this skill_sha); previous: 17/18 pass strict (AG-1 2/2, AG-2 2/2, AG-3 2/2, AG-4 2/2, AG-5 1/2, AG-6 2/2, AG-6b 2/2, AG-7 2/2, AG-8 2/2); strict reading: AG-5 r2 never says the machine guard is inactive, the omission TK6g failed it for (criterion unchanged), and the grader passed it leniently, so 18/18 holds only under a lenient reading; SPR-33 TK7 re-run 2026-11-16 on the skill text with the ask-once locale step 6 (commit 7949864), n = 2 per case, GREEN for all nine cases, RED for the four new cases only (3/8, so the new cases discriminate except AG-7, whose prompt shows the flag); subjects sonnet, grader opus independent of the runner, one strict GREEN failure (AG-5 r2) and three other borderline passes listed in the TK7 section; previous result: 9/10 pass (AG-1 2/2, AG-2 2/2, AG-3 2/2, AG-4 2/2, AG-5 1/2 FAIL); SPR-32 TK6g re-run 2026-11-16 on the final text (blocker id BR<number>), n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; AG-5 r2 fails the clause 'say the hook did not run in this session (typed /agile changed nothing, machine guard not active)': it hedged ('rất có thể', 'có thể chưa đổi gì') and never said the guard is inactive; history: TK6f 9/10 (AG-3 r2 wrote BR-01/BR-03, format only), TK6d 7/8 (AG-3 r2 never showed --project); SPR-32 TK6f re-run 2026-11-16 on the edited skill text, n = 2 per case, GREEN only, subjects sonnet, grader opus independent of the runner; AG-3 r2 fails the clause 'exactly one new blocker (BR1 for SPR-41, BR3 for SPR-40)': it wrote BR-01/BR-03 (grader: format only, the command line with --session and --project was shown); history: TK6d 7/8 on the earlier text (AG-3 r2 never showed the --project value); simulated status output | 2026-11-25 |
| [explain](explain/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass; SC4 nền đạt sẵn (CM-4/CM-4b không phân biệt được); vòng sửa 1: CM-3 3/3, CM-4/4b/6 n = 1 Đạt (CM-6 chưa có RED); vòng sửa 2: nạp thật khớp skill 4/4, CM-3 nạp thật 0/3 nghiêm (không đọc thân skill); vòng sửa 3: gỡ nhiễm, CM-3 ép đọc 2/3 nghiêm; vòng sửa 4: bản mẫu đổi miền, CM-3 ép đọc 0/3 nghiêm (N+1 chỉ ẩn dụ) | 2026-11-13 |
| [token-economy](token-economy/tests/pressure.md) | kỷ luật | `pressure.md` | 4/4 GREEN pass on the current tree (rerun 2026-10-26 at n = 1; 0 partial; RED not rerun, scenarios unchanged) | 2026-10-26 |
| [progress-report](progress-report/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass; n = 2 per case, RED n = 1 per case, RED 0/3 failed the seven-part structure (all three already kept the honest facts); simulated ledger and Git data | 2026-11-17 |
| [eval-harness](eval-harness/tests/pressure.md) | kỷ luật | `pressure.md` | 4/4 GREEN pass on the current tree (eh-9 new; eh-1, eh-3, eh-4 rerun at n = 1) | 2026-10-24 |
| [writing-skills](writing-skills/tests/pressure.md) | kỷ luật | `pressure.md` | 1/1 GREEN pass theo chữ và theo ý (KB8, n = 3 sau sửa SPR-19: 3/3 chữ, 3/3 ý); KB1–KB7 không chạy lại; SPR-19 2026-11-12 | 2026-11-12 |
| [hooks-guardrails](hooks-guardrails/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass; RED 0/3 pass (3 partial) | 2026-10-23 |
| [gcp-devops](gcp-devops/tests/pressure.md) | kỷ luật | `pressure.md` | 3/3 GREEN pass theo ý, 0/3 Đạt hẳn theo chữ (3 Đạt một phần); SPR-19 2026-11-12, n = 1 mỗi ca | 2026-11-12 |
| [gcp-incident-response](gcp-incident-response/tests/pressure.md) | kỷ luật | `pressure.md` | 2/3 GREEN pass theo chữ và ý (gi-1, gi-2); gi-3 0/4 chữ, 0/4 ý (Đạt một phần); đối chứng ×3 trên cây chính trước TK5 (thân như d603a73): chữ 0/3, ý 3/3, khác điều kiện chấm, chưa kết luận lùi hay không; SPR-19 2026-11-12, n = 1 mỗi ca (gi-3 ×4) | 2026-11-12 |

Agent reviewer chuyên đề: [docs/agents.md](../docs/agents.md). Gặp tên cũ trong hồ sơ lịch sử:
[docs/MIGRATION.md](../docs/MIGRATION.md).
