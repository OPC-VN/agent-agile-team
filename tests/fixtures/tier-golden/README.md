# tier-golden — bộ ca vàng phân giải tier (BẢN NHÁP L0)

Một bộ ca dùng chung cho bộ phân giải Node (`system/bridges/lib/models.mjs`) và bộ Python (`scripts/tier_resolve.py`):
cả hai đọc `table.json` + `catalog.json`, chạy từng dòng `cases.jsonl`, so với `expected.json`. Chỉ model **giả**
(không tên model thật). Hợp đồng phân giải: ADR-008 (`docs/architecture/adr/ADR-008-tier-resolution-contract.md`).

Trạng thái: nháp theo quyết định 22/11/2026; L1 chốt tên trường khi viết `role-catalog.json` thật. Sửa luật phân giải
thì đổi bộ này **trước**.

Thứ tự báo lỗi khi một ca vi phạm nhiều điều (cả Node và Python phải theo): `unknown_role` → `legacy_alias_forbidden_in_role_turn` → `unknown_tier` → `tier_reserved_human_only` → `role_tier_mismatch`. Ca c05 (tier 5) và c08 (tier 9) đều nằm ngoài dải của advisor nên kết quả phụ thuộc thứ tự này.
Alias cũ `T1 → 4` mất thông tin (T1 cũ gồm cả Analyst, Architect, Tech Reviewer, nay ở tier 3); chỉ dùng cho hồ sơ cũ.
