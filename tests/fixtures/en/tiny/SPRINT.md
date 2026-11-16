---
id: SPR-02-sprint
doc: sprint
locale: en
title: Fix the spelling of the not-found message
sprint: SPR-02
request: RQ-003
feature: FS-001
status: verifying
size: tiny
risk: normal
risk_tags: []
review_round: 1
gate_1: approved
gate_1_at: 2026-01-20 09:40 +07
gate_1_quote: "fix the wording on the order lookup screen"
verdict: pending
gate_2: pending
gate_2_at: null
gate_2_quote: null
roles:
  analyst: [T1, agent-a]
  implementer: [T2, agent-e]
  tech-reviewer: [T1, agent-d]
created: 2026-01-20
updated: 2026-01-20
---

# Fix the error wording — Combined sprint (SPRINT)

> **Conclusion:** fix the wording of the error message; waiting for verification.

## 1. Work plan

- **Goal:** the error message on the order lookup screen is spelled correctly.

The plan has 1 **success criterion** (SC) and 1 **task** (TK):

- **SC1 (right wording):** the UI test matches the exact sentence "Order not found".
- **TK1 (fix the error message) → SC1:** Implementer · T2. Rollback: `git revert`.

## 2. Result

The result has 1 **verification result** (VR):

| Code | What is checked | Command / action | Result | Checked by |
|---|---|---|---|---|
| VR1 (error message test) | SC1 | `pytest tests/test_ui.py` | Not run | Tech Reviewer · agent-d |

- **Log:** the Implementer fixed the error message.
