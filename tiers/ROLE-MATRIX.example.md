# Ma trận vai × vendor (bản mẫu)

> **Kết luận:** bản mẫu công khai của ma trận vai → tier · model · effort cho ba harness; file thật nằm ở lớp riêng, do công cụ của lớp đó sinh từ bảng tier — không sửa tay; repo chỉ giữ `<model-id>`.

| Vai | Tier | Vendor | Model | Effort | Effort native | Ghi chú |
|---|---|---|---|---|---|---|
| Analyst | 3 | claude | `<model-id>` | 3 | `high` | ô tier 3 |
| Analyst | 3 | codex | `<model-id>` | 3 | `high` | ô tier 3 |
| Analyst | 3 | antigravity | `<model-id>` | 3 | `high` | ô tier 3 |
| Architect | 3 | claude | `<model-id>` | 3 | `high` | ô tier 3 |
| Architect | 3 | codex | `<model-id>` | 3 | `high` | ô tier 3 |
| Architect | 3 | antigravity | `<model-id>` | 3 | `high` | ô tier 3 |
| Implementer | 2 | claude | `<model-id>` | 3 | `high` | ô tier 2 |
| Implementer | 2 | codex | `<model-id>` | 3 | `high` | ô tier 2 |
| Implementer | 2 | antigravity | `<model-id>` | 3 | `high` | ô tier 2 |
| QA | 2 | claude | `<model-id>` | 3 | `high` | ô tier 2 |
| QA | 2 | codex | `<model-id>` | 3 | `high` | ô tier 2 |
| QA | 2 | antigravity | `<model-id>` | 3 | `high` | ô tier 2 |
| Researcher | 1 | claude | `<model-id>` | 2 | `medium` | override roles.researcher |
| Researcher | 1 | codex | `<model-id>` | 2 | `medium` | override roles.researcher |
| Researcher | 1 | antigravity | `<model-id>` | 2 | `medium` | override roles.researcher |
| Business Reviewer | 4 | claude | `<model-id>` | 3 | `high` | ô tier 4 |
| Business Reviewer | 4 | codex | `<model-id>` | 3 | `high` | ô tier 4 |
| Business Reviewer | 4 | antigravity | `<model-id>` | 3 | `high` | ô tier 4 |
| Tech Reviewer | 3 | claude | `<model-id>` | 3 | `high` | override roles.tech-reviewer |
| Tech Reviewer | 3 | codex | `<model-id>` | 3 | `high` | ô tier 3 |
| Tech Reviewer | 3 | antigravity | `<model-id>` | 3 | `high` | ô tier 3 |
| Gate Delegate | 4 | claude | `<model-id>` | 3 | `high` | ô tier 4 |
| Gate Delegate | 4 | codex | `<model-id>` | 3 | `high` | ô tier 4 |
| Gate Delegate | 4 | antigravity | `<model-id>` | 3 | `high` | ô tier 4 |
| Advisor | 4 | claude | `<model-id>` | 3 | `high` | ô tier 4 |
| Advisor | 4 | codex | `<model-id>` | 3 | `high` | ô tier 4 |
| Advisor | 4 | antigravity | `<model-id>` | 3 | `high` | ô tier 4 |

## Thang 1–5 → native

| Mức | claude | codex | antigravity |
|---|---|---|---|
| 1 | `low` | `low` | `low` |
| 2 | `medium` | `medium` | `medium` |
| 3 | `high` | `high` | `high` |
| 4 | `xhigh` | `xhigh` | `high` (3↓, fallback) |
| 5 | `max` (+ultracode: cờ chế độ) | `max` | `high` (3↓, fallback) |

## Known

| Vendor | Model đã xem, cố ý không xếp |
|---|---|
| claude | — |
| codex | — |
| antigravity | — |
