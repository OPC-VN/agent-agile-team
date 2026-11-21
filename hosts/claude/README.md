# Dùng agent-agile-team với Claude Code

> **Kết luận:** cài plugin để có 39 skill và 13 agent (chỉ đọc, riêng `build-fixer` được sửa — T2); thêm một dòng `@import` tới `AGENTS.md` vào
> file luật cấp người dùng để luật lõi có mặt ở **mọi** phiên. Áp cho Claude Code ở terminal, IDE và tab
> **Code** của ứng dụng Claude.

## 1. Luật lõi

- Phiên mở **trong thư mục repo**: repo cố ý không có `CLAUDE.md` (`claude plugin validate --strict` đỏ nếu có). Luật
  lõi vào qua dòng import cấp người dùng ở dưới — đã có dòng đó thì không cần làm gì thêm. Chưa có thì Claude Code
  ≥ 2.1.277 tự đọc `AGENTS.md`, nhưng chỉ khi thư mục làm việc và mọi thư mục cha không có `CLAUDE.md`,
  `.claude/CLAUDE.md` hay `CLAUDE.local.md` (`~/.claude/CLAUDE.md` không tính), và mục *Project instructions*
  trong `/config` chưa tắt. Không thoả hai điều đó thì tạo `.claude/CLAUDE.md` cục bộ chứa đúng một dòng
  `@../AGENTS.md` (đường `@` tính từ file chứa nó); `.gitignore` đã bỏ qua file này để nó không vào repo. Gõ
  `/memory` trong phiên để xem luật đã nạp từ đâu.
- Phiên ở **dự án khác** (cách dùng thường ngày): thêm một dòng vào file luật cấp người dùng
  `~/.claude/CLAUDE.md`, trỏ tới bản clone của repo, ví dụ:

  ```text
  @~/agent-agile-team/AGENTS.md
  ```

  Đây là file luật của người dùng — agent nói rõ sẽ thêm dòng nào, ở đâu, rồi **chờ người dùng đồng ý**.
  Luật lõi có ngân sách ≤120 dòng, ≤10 KB (`check.py --self` đo) vì nó là thuế token của mọi phiên.

## 2. Skill và agent — cài plugin

```bash
claude plugin marketplace add ~/agent-agile-team          # bản clone cục bộ — macOS, bash
claude plugin install agent-agile-team@agent-agile-team
```

```powershell
claude plugin marketplace add "$HOME\agent-agile-team"    # Windows PowerShell — 5.1 không mở `~`
claude plugin install agent-agile-team@agent-agile-team
```

Đã có quyền đọc repo trên GitHub thì thay dòng đầu bằng `claude plugin marketplace add https://github.com/OPC-VN/agent-agile-team.git`.
Skill hiện với tên có tiền tố `agent-agile-team:` (ví dụ `agent-agile-team:intake`), nên không đè skill cùng tên của plugin khác.
Claude Code có skill dựng sẵn tên trần `code-review` và `security-review`; gọi tên trần sẽ ra bản dựng sẵn. Skill và
luật của repo trỏ nhau bằng tên trần (không phụ thuộc harness — `writing-skills` mục 6), nên trên Claude, khi một skill
nói "skill `code-review`" hay "skill `security-review`", gọi `agent-agile-team:code-review` /
`agent-agile-team:security-review`.

Thử khi đang sửa repo, không cài lại plugin:

```bash
claude --plugin-dir ~/agent-agile-team                    # macOS, bash
```

```powershell
claude --plugin-dir "$HOME\agent-agile-team"              # Windows PowerShell
```

**Công tắc agile.** Agile **tắt mặc định**. Người dùng gõ `/agent-agile-team:agile` (hoặc `/agile`) để bật cho phiên này; `always` nhớ cho repo,
`manual` để người ký hai cổng, `stop` tắt (sprint đang mở nhận một vướng mắc `paused by /agile stop`, hồ sơ giữ nguyên), `status` chỉ xem.
Hook `UserPromptExpansion` (`scripts/agile_hook.py`) đọc lệnh người gõ và ghi trạng thái vào thư mục state của nền tảng qua
`scripts/agile_state.py` (không còn file dấu `.tmp/autopilot.json`); hook `SessionStart` đưa dòng trạng thái vào ngữ cảnh. Đường ghi BẬT được phép duy nhất là hook trên lệnh do người dùng gõ; model không được tự bật (skill `agile` không ghi ON), nhưng chương trình nào gọi được Bash vẫn chạy được `scripts/agile_state.py`, và `source` do bên ghi tự khai: bản ghi như vậy `status` đánh dấu `non-hook ON`.

**Hook của plugin.** `hooks/hooks.json` đăng ký ba sự kiện, mỗi hook dạng `command` + `args` (`python` chạy thẳng, không qua `sh` hay Git Bash): `SessionStart` và `UserPromptExpansion` chạy `scripts/agile_hook.py`; `PreToolUse` (`Bash|PowerShell` và `Write|Edit|MultiEdit|NotebookEdit`, không `onFailure`: thiếu `python` thì hook lỗi mở, đã đo) chạy `scripts/agile_guard.py` — guard chỉ chặn khi agile **bật**, agile tắt thì thoát 0 và không làm gì. Đã đo ở sprint này (Windows, claude 2.1.325): dạng `args` chạy khi PATH không có `sh`, tiến trình cha là `claude.exe`, mốc khởi động 143 ms; máy Windows không có Git là **Chưa chạy**. Cần lệnh tên `python` trên PATH: trên macOS/Linux chỉ có `python3` thì **Chưa chạy** (chưa đo), hook sẽ không khởi động được; lối dự phòng dạng chuỗi là launcher `scripts/agile-hook.sh` (`sh "${CLAUDE_PLUGIN_ROOT}/scripts/agile-hook.sh" --format claude`, thử `python3`/`python`/`py -3`; trên Windows cần Git Bash, chậm hơn khoảng 40 ms) — Đức chọn dùng thay thế hay không, file vẫn nằm trong repo nhưng không được gọi. Chi tiết luật: [method/agile.md](../../method/agile.md), [hooks/hooks.json](../../hooks/hooks.json), [scripts/README.md](../../scripts/README.md).
Codex và Antigravity chưa có hook này: xem [method/agile.md](../../method/agile.md).

**Lệnh mục tiêu.** `/agent-agile-team:agile-goal` (kèm `SPR-NN` nếu cần) in sẵn khối `/goal` để chạy tiếp sprint đang mở; lệnh chỉ in, người dùng phải gửi khối đó trong chat. Dừng agile dùng `/agile stop` (thay cho câu dừng và lệnh dừng riêng của bản 0.11.0).

## 3. Kiểm, cập nhật, gỡ

- **Kiểm:** mở phiên **mới**, hỏi agent "luật lõi agent-agile-team nói gì về hai cổng?" — trả lời đúng là luật
  đã nạp; gõ `/agent-agile-team:` để thấy danh sách skill. Trong thư mục repo:
  `python scripts/check.py --self` (macOS: `python3`) phải ra `Đạt`.
- **Cập nhật:** `git pull --ff-only` trong bản clone, rồi
  `claude plugin marketplace update agent-agile-team` và
  `claude plugin update agent-agile-team@agent-agile-team`.
- **Gỡ:** `claude plugin uninstall agent-agile-team@agent-agile-team`, rồi bỏ dòng `@import` ở mục 1 (hỏi người
  dùng trước). Gỡ không xoá sổ gốc hay tài liệu sprint của dự án đã áp dụng.

## 4. Điểm cắm

Bảng tier, danh sách từ cấm, nơi lưu bài học, cầu gọi chéo: [`hosts/README.md`](../README.md) mục 2.
