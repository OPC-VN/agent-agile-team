# tier-golden — bộ ca vàng phân giải tier (BẢN NHÁP L0)

Một bộ ca dùng chung cho bộ phân giải Node (`system/bridges/lib/models.mjs`) và bộ Python (`scripts/tier_resolve.py`):
cả hai đọc `table.json` + `catalog.json`, chạy từng dòng `cases.jsonl`, so với `expected.json`. Chỉ model **giả**
(không tên model thật). Hợp đồng phân giải: ADR-008 (`docs/architecture/adr/ADR-008-tier-resolution-contract.md`).

Trạng thái: nháp theo quyết định 22/11/2026; L1 chốt tên trường khi viết `role-catalog.json` thật. Sửa luật phân giải
thì đổi bộ này **trước**.

Thứ tự báo lỗi khi một ca vi phạm nhiều điều (cả Node và Python phải theo): `unknown_role` → `legacy_alias_forbidden_in_role_turn` → `unknown_tier` → `tier_reserved_human_only` → `catalog_table_mismatch` → `role_tier_mismatch`. Ca c05 (tier 5) và c08 (tier 9) đều nằm ngoài dải của advisor nên kết quả phụ thuộc thứ tự này.
Alias cũ `T1 → 4` mất thông tin (T1 cũ gồm cả Analyst, Architect, Tech Reviewer, nay ở tier 3); chỉ dùng cho hồ sơ cũ.

Ca bổ sung 22/11 (L1a): `c09` kẹp effort Antigravity (pin 5 → 3 nhờ `fallback.antigravity = clamp_to_max` trong `table.json`); `c10` effort 5 trên Claude không kẹp; `c11` vai `human-arbiter` có tier mặc định 5 và không truyền tier → `tier_reserved_human_only`. Ca `kind:"snapshot"` (`c12` hỏng, `c13` cũ — băm đầu vào lệch, `c14` thiếu file) kiểm bên **đọc snapshot**, không đi qua bộ phân giải; Python phải cho cùng mã. Trường `effort` trong ca = pin effort_level.

Ca bổ sung 22/11 (L1b, CO3 phương án b): **tier hiệu lực** của vai = `roles.<vai>.tier` của `table.json` nếu có, không thì `tier_default` của catalog. Hiệu lực ngoài dải catalog → `catalog_table_mismatch` (snapshot `degraded`). Tier truyền theo lượt khác tier hiệu lực chỉ hợp lệ khi có pin (`effort` hoặc model), không thì `role_tier_mismatch`. `c15` tier "03" không pin → `role_tier_mismatch`; `c16` tier "04" = 4 (Node dùng `Number(raw)` rồi khóa `String(n)`; chuỗi "4.0" vẫn `unknown_tier`); `c17` bảng đặt `roles.qa.tier = 1` (trong dải, khác mặc định 2) → tier 1; `c18` bảng đặt `roles.business-reviewer.tier = 2` ngoài dải [3,4] → `catalog_table_mismatch`; `c19` như c15 nhưng có pin effort 4 → ok. Vai kế thừa (ADR-008 #10) không có ô riêng trong bảng thì tra `roles.<cha>.tier` (một tầng) rồi mới `tier_default`: `c20` (vai con của `reviewer-base`) ra tier 4 vì bảng nâng vai cha lên 4, `c21` chính vai cha.

**Giới hạn đã biết, quyết ở L2:** tier lượt khác hiệu lực mà vai có ô `roles.<vai>.tier` khác trong bảng vẫn dừng ở `role_tier_mismatch` của `resolveRoleProfile` ngay cả khi có pin; chưa sửa, chờ quyết định ở L2.

Mã chỉ bộ Python có (Node chưa định nghĩa; không có trong `expected.json`): `snapshot_override_unsupported` (chế độ `opcos`: snapshot chỉ giữ tier mặc định theo vai nên `--tier` khác mặc định, `--effort` hay `--model` bị từ chối, không bỏ qua lặng lẽ), `catalog_missing`, `defaults_missing`, `defaults_invalid`, `write_failed` (hai mã cuối của `tier_setup.py`). Ở chế độ `opcos`, c05 (tier 5) và c08 (tier 9) ra `snapshot_override_unsupported` chứ không phải mã ca vàng, vì ca vàng chạy ở chế độ riêng; `expected.json` không mâu thuẫn nên không cần khóa `opcos_expected`.
