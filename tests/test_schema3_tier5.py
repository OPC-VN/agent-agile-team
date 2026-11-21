"""Kiểm tra Schema 3 tier_scale=2 (Tier 1-5), dynamic agile_specialist theo group, và _signer_independence."""

import json
from pathlib import Path

import pytest

import _common as c
import check
import init
from conftest import write_lf


SCHEMA3_TIERS = {
    "schema": 3,
    "tier_scale": 2,
    "tiers": {
        "1": {"purpose": "lookup-research", "models": {"claude": "claude-haiku-5-5"}, "effort": 1},
        "2": {"purpose": "execution-qa", "models": {"claude": "claude-sonnet-5-5"}, "effort": 2},
        "3": {"purpose": "architecture-review", "models": {"claude": "claude-opus-5-5"}, "effort": 3},
        "4": {"purpose": "judgment-governance", "models": {"claude": "claude-fable-5-2"}, "effort": 3},
        "5": {"purpose": "reserved-human-only", "models": {}, "effort": None},
    },
    "roles": {
        "analyst": {"category": "agile_core", "group": "executor", "tier": "3"},
        "architect": {"category": "agile_core", "group": "executor", "tier": "3"},
        "implementer": {"category": "agile_core", "group": "executor", "tier": "2"},
        "qa": {"category": "agile_core", "group": "executor", "tier": "2"},
        "researcher": {"category": "agile_core", "group": "executor", "tier": "1"},
        "business-reviewer": {"category": "agile_core", "group": "verifier", "tier": "4"},
        "tech-reviewer": {"category": "agile_core", "group": "verifier", "tier": "3"},
        "gate-delegate": {"category": "agile_core", "group": "verifier", "tier": "4"},
        "advisor": {"category": "agile_core", "group": "advisor", "tier": "4"},
        "perf-specialist": {"category": "agile_specialist", "group": "verifier", "tier": "3"},
        "db-helper": {"category": "agile_specialist", "group": "executor", "tier": "2"},
        "growth-strategist": {"category": "custom", "group": "generalist", "tier": "2"},
    },
}


def _setup_tiers(tmp_path: Path, monkeypatch) -> Path:
    tp = tmp_path / "tiers.json"
    tp.write_text(json.dumps(SCHEMA3_TIERS), encoding="utf-8")
    monkeypatch.setenv("AGENT_AGILE_TIERS", str(tp))
    return tp


def _write_minimal_spec(root: Path, scale: int = 2) -> None:
    write_lf(
        root / "SPEC.md",
        f"""---
id: SPR-90-spec
doc: spec
title: Spec thu nghiem
sprint: SPR-90
request: null
feature: null
status: approved
size: medium
risk: normal
tier_scale: {scale}
gate_1: approved
gate_1_at: 2026-11-21
gate_1_quote: ok
links:
  plan: PLAN.md
roles:
  analyst: [3, agent-analyst]
  architect: [3, agent-arch]
  business-reviewer: [4, agent-biz]
created: 2026-11-21
updated: 2026-11-21
---

# Spec thu nghiem — Đặc tả (SPEC)

> **Kết luận:** Spec mẫu kiểm tra Schema 3.

## Tóm tắt cho người không chuyên

Kiểm tra Schema 3.

## Bối cảnh

Kiểm tra.

## Câu chuyện người dùng

SPEC có 1 **user story** (US):

| Mã | Câu chuyện | Ưu tiên |
|---|---|---|
| US1 (thử) | Thử | Bắt buộc |

## Yêu cầu chức năng

SPEC có 1 **functional requirement** (FR):

### FR1 — Thử (→ US1)

- **FR1.1 (thử):** KHI chạy THÌ đạt.

## Tiêu chí thành công

SPEC có 1 **success criterion** (SC):

| Mã | Tiêu chí | Cách đo |
|---|---|---|
| SC1 (thử) | Đạt | Test |

## Ngoài phạm vi

Không có.

## Câu hỏi cần làm rõ

Không có.
""",
    )


def test_tier_scale_2_roles_and_dynamic_specialists_split_by_group(tmp_path, monkeypatch):
    _setup_tiers(tmp_path, monkeypatch)
    _write_minimal_spec(tmp_path)
    plan = tmp_path / "PLAN.md"
    write_lf(
        plan,
        """---
id: SPR-90-plan
doc: plan
title: Schema 3 Tier 1-5 plan
sprint: SPR-90
request: null
feature: null
status: approved
size: medium
risk: normal
tier_scale: 2
gate_1: approved
gate_1_at: 2026-11-21
gate_1_quote: ok
links:
  spec: SPEC.md
roles:
  architect: [3, agent-arch]
  implementer: ["2", agent-impl]
  perf-specialist: [3, agent-perf]
  db-helper: [2, agent-db]
created: 2026-11-21
updated: 2026-11-21
---

# Schema 3 — Kế hoạch

> **Kết luận:** Thử nghiệm bảng Schema 3 và vai chuyên đề động theo group.

## Tóm tắt cho người không chuyên

Kiểm tra tương thích `tier_scale: 2`.

## Mục tiêu

- **Mục tiêu sprint:** Kiểm tra phân vai động.
- **Kết quả mong muốn / xong khi:** Không báo lỗi sai vai.
- **Rủi ro cần chú ý:** Rủi ro thấp.

## Kiến trúc

Đơn giản.

## Ràng buộc chung

Không có.

## File luật và file sàn cứng sẽ chạm

| File | Mục/vùng | Sửa gì và ảnh hưởng | Việc `TK` |
|---|---|---|---|

## Trọng tâm review

Kiểm tra split group.

## Việc

PLAN có 1 **task** (TK):

### TK1 (thử) (→ FR1)

- **Vai:** Architect · Tier 3 · effort 3.
- **Đầu vào:** `SPEC.md`. **Đầu ra:** `x.py`.
- **Bước:** Thử.
- **Cách kiểm:** Test.

## Rủi ro

Không có.

## Quyết định cần người

Không có.

## Ước lượng

1 phiên.
""",
    )
    res = check.check_paths([plan])
    assert res.exit_code == 0, [f"{f.rule}: {f.message}" for f in res.findings]

    # custom role in sprint frontmatter must still be rejected as roles-invalid
    bad_plan = tmp_path / "PLAN-CUSTOM.md"
    write_lf(bad_plan, plan.read_text(encoding="utf-8").replace("db-helper: [2, agent-db]", "growth-strategist: [2, agent-g]"))
    res_bad = check.check_paths([bad_plan])
    assert any(f.rule == "roles-invalid" for f in res_bad.findings)

    # executor (db-helper) + verifier (perf-specialist) sharing same agent label => self-review!
    sr_plan = tmp_path / "PLAN-SR.md"
    write_lf(sr_plan, plan.read_text(encoding="utf-8").replace("agent-db", "agent-perf"))
    res_sr = check.check_paths([sr_plan])
    assert any(f.rule == "self-review" for f in res_sr.findings)


def test_tier_scale_2_signer_independence_and_verifier_tier_floor(tmp_path, monkeypatch):
    _setup_tiers(tmp_path, monkeypatch)
    _write_minimal_spec(tmp_path)
    plan = tmp_path / "PLAN.md"
    write_lf(
        plan,
        """---
id: SPR-91-plan
doc: plan
title: Signer independence tier_scale 2
sprint: SPR-91
request: null
feature: null
status: approved
size: medium
risk: normal
risk_tags: []
tier_scale: 2
gate_1: approved
gate_1_at: 2026-11-21 10:00 +07
gate_1_mode: delegated
gate_1_quote: "duyệt thay: đạt"
links:
  spec: SPEC.md
roles:
  architect: [3, agent-arch]
  gate-delegate: [4, agent-gate]
created: 2026-11-21
updated: 2026-11-21
---

# Signer check

> **Kết luận:** Kiểm tra đảo bất đẳng thức tier ký cổng.

## Tóm tắt cho người không chuyên

Kiểm tra ký cổng.

## Mục tiêu

- **Mục tiêu sprint:** Kiểm tra người ký tier yếu hơn người làm.
- **Kết quả mong muốn / xong khi:** Bắt lỗi chính xác.
- **Rủi ro cần chú ý:** Rủi ro thấp.

## Kiến trúc

Không đổi.

## Ràng buộc chung

Không có.

## File luật và file sàn cứng sẽ chạm

| File | Mục/vùng | Sửa gì và ảnh hưởng | Việc `TK` |
|---|---|---|---|

## Trọng tâm review

Signer tier.

## Việc

PLAN có 1 **task** (TK):

### TK1 (thử) (→ FR1)

- **Đầu vào:** `SPEC.md`. **Đầu ra:** `y.py`.

## Bản ghi duyệt thay

- Phương án chọn: chạy.
- Phương án bị loại: dừng.
- Nếu sai thì tốn gì: sửa lại.

## Rủi ro

Không có.

## Quyết định cần người

Không có.

## Ước lượng

- Trần phiên: 15.
""",
    )
    ev = tmp_path / "evidence"
    ev.mkdir()
    write_lf(ev / "gate-1-verdict.md", "duyệt thay: đạt\n")

    # Add delegation block in frontmatter for signer at tier 2 (weaker than worker tier 3!)
    weak_text = plan.read_text(encoding="utf-8").replace(
        "gate_1_mode: delegated\n",
        "gate_1_mode: delegated\ndelegation:\n  by: agent-gate\n  tier: 2\n  level: gate_1\n  grant: \"duyệt thay Cổng 1 SPR-91\"\n  grant_at: 2026-11-21 09:00 +07\n  scope: [gate_1]\n  expires: sprint_end\n  sessions_cap: 15\n  files: []\n",
    ).replace("gate-delegate: [4, agent-gate]", "gate-delegate: [2, agent-gate]")
    weak_plan = tmp_path / "PLAN.md"
    write_lf(weak_plan, weak_text)
    res_weak = check.check_paths([weak_plan])
    codes = {f.rule for f in res_weak.findings}
    assert "gate-signer-independence" in codes, [f.message for f in res_weak.findings]
    assert "roles-invalid" in codes

    # Valid signer tier 4 >= worker tier 3
    strong_text = weak_text.replace("  tier: 2\n", "  tier: 4\n").replace("gate-delegate: [2, agent-gate]", "gate-delegate: [4, agent-gate]")
    write_lf(weak_plan, strong_text)
    res_strong = check.check_paths([weak_plan])
    assert res_strong.exit_code == 0, [f"{f.rule}: {f.message}" for f in res_strong.findings]


def test_init_reset_roles_supports_tier_1_to_5():
    src = "---\nroles:\n  architect: [3, agent-a]\n  implementer: [\"2\", agent-b, \"note\"]\n  analyst: [T1, agent-c]\n---\nbody\n"
    out = init.reset_roles(src)
    assert "  architect: [3, pending]" in out
    assert "  implementer: [2, pending]" in out
    assert "  analyst: [T1, pending]" in out
