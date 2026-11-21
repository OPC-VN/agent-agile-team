# tier-golden — bộ ca vàng phân giải tier (BẢN NHÁP L0)

Một bộ ca dùng chung cho bộ phân giải Node (`system/bridges/lib/models.mjs`) và bộ Python (`scripts/tier_resolve.py`):
cả hai đọc `table.json` + `catalog.json`, chạy từng dòng `cases.jsonl`, so với `expected.json`. Chỉ model **giả**
(không tên model thật). Hợp đồng phân giải: ADR-008 (`docs/architecture/adr/ADR-008-tier-resolution-contract.md`).

Trạng thái: nháp theo quyết định 22/11/2026; L1 chốt tên trường khi viết `role-catalog.json` thật. Sửa luật phân giải
thì đổi bộ này **trước**.

Thứ tự báo lỗi khi một ca vi phạm nhiều điều (cả Node và Python phải theo): `unknown_role` → `legacy_alias_forbidden_in_role_turn` → `unknown_tier` → `tier_reserved_human_only` → `role_tier_mismatch`. Ca c05 (tier 5) và c08 (tier 9) đều nằm ngoài dải của advisor nên kết quả phụ thuộc thứ tự này.
Alias cũ `T1 → 4` mất thông tin (T1 cũ gồm cả Analyst, Architect, Tech Reviewer, nay ở tier 3); chỉ dùng cho hồ sơ cũ.

Ca bổ sung 22/11 (L1a): `c09` kẹp effort Antigravity (pin 5 → 3 nhờ `fallback.antigravity = clamp_to_max` trong `table.json`); `c10` effort 5 trên Claude không kẹp; `c11` vai `human-arbiter` có tier mặc định 5 và không truyền tier → `tier_reserved_human_only`. Ca `kind:"snapshot"` (`c12` hỏng, `c13` cũ — băm đầu vào lệch, `c14` thiếu file) kiểm bên **đọc snapshot**, không đi qua bộ phân giải; Python phải cho cùng mã. Trường `effort` trong ca = pin effort_level.

Ca bổ sung 22/11 (L1b): `c15`/`c16` tier viết "03"/"04" = tier 3/4 (Node dùng `Number(raw)` rồi khóa `String(n)`); chuỗi "4.0" vẫn là `unknown_tier`.

Mã chỉ bộ Python có (Node chưa định nghĩa; không có trong `expected.json`): `snapshot_override_unsupported` (chế độ `opcos`: snapshot chỉ giữ tier mặc định theo vai nên `--tier` khác mặc định, `--effort` hay `--model` bị từ chối, không bỏ qua lặng lẽ), `catalog_missing`, `defaults_missing`, `defaults_invalid`, `write_failed` (hai mã cuối của `tier_setup.py`). Ở chế độ `opcos`, c05 (tier 5) và c08 (tier 9) ra `snapshot_override_unsupported` chứ không phải mã ca vàng, vì ca vàng chạy ở chế độ riêng; `expected.json` không mâu thuẫn nên không cần khóa `opcos_expected`.
