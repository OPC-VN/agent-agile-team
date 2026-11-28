"""Tier resolver: golden cases c01-c14 (tests/fixtures/tier-golden), mode detection, CLI, Node snapshot interop."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import FIXTURES, REPO, run_script
import tier_resolve as tr

GOLD = FIXTURES / "tier-golden"
CASES = [json.loads(l) for l in (GOLD / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
EXPECTED = json.loads((GOLD / "expected.json").read_text(encoding="utf-8"))
NODE_SNAPSHOT_CLI = REPO.parent.parent / "system" / "bridges" / "lib" / "tier-snapshot.mjs"


def make_snapshot(tmp: Path) -> tuple[Path, Path]:
    """A good snapshot (the shape Node writes) over a copy of the golden table + catalog. Returns (snapshot, tiers copy)."""
    tiers = tmp / "tiers.json"
    shutil.copy(GOLD / "table.json", tiers)
    inputs = [tr._input_entry("tiers", str(tiers)), tr._input_entry("catalog", str(GOLD / "catalog.json"))]
    cell = {"model": "fake-claude-t2", "effort_level": 2, "effort_native": "medium",
            "sources": {"model": "tier", "effort": "tier"}, "status": "ok"}
    snap = {
        "schema": 1, "revision": 1, "generated_at": "2026-11-22T00:00:00Z", "input_hash": tr._hash_inputs(inputs),
        "inputs": inputs, "status": "ok", "errors": [], "resolver_contract": 1,
        "roles": {"implementer": {"tier": 2, "tier_range": [2, 3], "inherits": None, "group": "executor", "claude": cell}},
        "known": {},
    }
    out = tmp / "snap" / "tier-snapshot.json"
    out.parent.mkdir()
    out.write_text(json.dumps(snap), encoding="utf-8")
    return out, tiers


def run_case(case: dict, tmp: Path) -> dict:
    if case.get("kind") == "snapshot":
        snap, tiers = make_snapshot(tmp)
        kind = case["snapshot"]
        if kind == "corrupt":
            snap.write_text("{ not json", encoding="utf-8")
        elif kind == "stale":
            tiers.write_text(tiers.read_text(encoding="utf-8").replace("fake-claude-t2", "fake-claude-t2b"), encoding="utf-8")
        elif kind == "missing":
            snap.unlink()
        return tr.resolve("implementer", "claude", env={"AGENT_AGILE_TIER_SNAPSHOT": str(snap)})
    return tr.resolve(case["role"], case["vendor"], case.get("tier"), case.get("effort"),
                      env={}, table=str(GOLD / "table.json"), catalog=str(GOLD / "catalog.json"))


def test_golden_ids_match():
    assert sorted(c["id"] for c in CASES) == sorted(EXPECTED)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden(case, tmp_path):
    want = EXPECTED[case["id"]]
    got = run_case(case, tmp_path)
    assert got["status"] == want["status"], got
    if want["status"] == "error":
        assert got["code"] == want["code"]
    else:
        assert (got["tier"], got["model"], got["effort"]) == (want["tier"], want["model"], want["effort"])
        if "inherited_from" in want:
            assert got["inherited_from"] == want["inherited_from"]


def test_error_order_matches_contract_text():
    readme = (GOLD / "README.md").read_text(encoding="utf-8")
    assert " → ".join(f"`{c}`" for c in tr.ERROR_ORDER) in readme


def test_tier_word_form_and_int_accepted():
    kw = dict(env={}, table=str(GOLD / "table.json"), catalog=str(GOLD / "catalog.json"))
    assert tr.resolve("tech-reviewer", "claude", "tier 3", **kw)["tier"] == 3
    assert tr.resolve("advisor", "claude", 4, **kw)["model"] == "fake-claude-t4"


def test_snapshot_mode_reads_and_does_not_resolve(tmp_path):
    snap, _ = make_snapshot(tmp_path)
    env = {"AGENT_AGILE_TIER_SNAPSHOT": str(snap)}
    got = tr.resolve("implementer", "claude", env=env)
    assert got["status"] == "ok" and got["mode"] == "opcos" and got["model"] == "fake-claude-t2"
    # the snapshot has no codex cell and no advisor role: nothing is computed from any table
    assert tr.resolve("implementer", "codex", env=env)["code"] == "model_tier_unavailable"
    assert tr.resolve("advisor", "claude", env=env)["code"] == "unknown_role"
    assert tr.resolve("implementer", "claude", 3, env=env)["code"] == "snapshot_override_unsupported"
    assert tr.resolve("implementer", "claude", "T2", env=env)["code"] == "legacy_alias_forbidden_in_role_turn"


def test_set_but_broken_snapshot_never_falls_back_to_standalone(tmp_path):
    table = tmp_path / "tiers.json"
    shutil.copy(GOLD / "table.json", table)
    env = {"AGENT_AGILE_TIER_SNAPSHOT": str(tmp_path / "nope.json"), "AGENT_AGILE_TIERS": str(table),
           "AGENT_AGILE_ROLE_CATALOG": str(GOLD / "catalog.json")}
    got = tr.resolve("implementer", "claude", env=env)
    assert got["status"] == "error" and got["code"] == "snapshot_missing"
    assert tr.status(env)["code"] == "snapshot_missing"


def test_snapshot_with_error_status_surfaces_its_code(tmp_path):
    snap, _ = make_snapshot(tmp_path)
    data = json.loads(snap.read_text(encoding="utf-8"))
    data.update(status="error", errors=[{"code": "tiers_file_missing"}])
    snap.write_text(json.dumps(data), encoding="utf-8")
    assert tr.resolve("implementer", "claude", env={"AGENT_AGILE_TIER_SNAPSHOT": str(snap)})["code"] == "tiers_file_missing"


def test_standalone_detection_and_paths(tmp_path):
    t = tmp_path / "t.json"
    assert tr.detect_mode({"AGENT_AGILE_TIERS": str(t)}) == {"mode": "standalone", "source": str(t)}
    assert tr.standalone_table_path({"LOCALAPPDATA": str(tmp_path)}) == tmp_path / "agent-agile-team" / "tiers.json"
    assert tr.status({"AGENT_AGILE_TIERS": str(t)})["table_present"] is False


def test_standalone_missing_catalog_and_table(tmp_path):
    got = tr.resolve("implementer", "claude", env={}, table=str(GOLD / "table.json"), catalog=str(tmp_path / "none.json"))
    assert got["code"] == "catalog_missing"
    got = tr.resolve("implementer", "claude", env={}, table=str(tmp_path / "none.json"), catalog=str(GOLD / "catalog.json"))
    assert got["code"] == "tiers_file_missing"


def test_catalog_contract_mismatch(tmp_path):
    bad = json.loads((GOLD / "catalog.json").read_text(encoding="utf-8"))
    bad["resolver_contract"] = 99
    p = tmp_path / "c.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert tr.resolve("implementer", "claude", env={}, table=str(GOLD / "table.json"), catalog=str(p))["code"] == "catalog_invalid"


def test_cli_resolve_and_status(tmp_path):
    env = {"AGENT_AGILE_TIERS": str(GOLD / "table.json"), "AGENT_AGILE_ROLE_CATALOG": str(GOLD / "catalog.json"),
           "AGENT_AGILE_TIER_SNAPSHOT": ""}
    r = run_script("tier_resolve.py", "--role", "advisor", "--vendor", "codex", "--json", env=env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["model"] == "fake-codex-t4" and out["mode"] == "standalone"
    r = run_script("tier_resolve.py", "--role", "advisor", "--vendor", "claude", "--tier", "5", "--json", env=env)
    assert r.returncode == 2 and json.loads(r.stdout)["code"] == "tier_reserved_human_only"
    r = run_script("tier_resolve.py", "status", "--json", env=env)
    assert r.returncode == 0 and json.loads(r.stdout)["mode"] == "standalone"
    r = run_script("tier_resolve.py", "status", "--json", env={**env, "AGENT_AGILE_TIER_SNAPSHOT": str(tmp_path / "x.json")})
    assert r.returncode == 2 and json.loads(r.stdout)["code"] == "snapshot_missing"


@pytest.mark.skipif(not (shutil.which("node") and NODE_SNAPSHOT_CLI.is_file()), reason="Chưa chạy: Node resolver not available")
def test_reads_a_snapshot_written_by_the_node_resolver(tmp_path):
    tiers = tmp_path / "tiers.json"
    shutil.copy(GOLD / "table.json", tiers)
    out = tmp_path / "a2a" / "tier-snapshot.json"
    r = subprocess.run(["node", str(NODE_SNAPSHOT_CLI), "snapshot", "--out", str(out), "--tiers", str(tiers),
                        "--catalog", str(GOLD / "catalog.json")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    env = {"AGENT_AGILE_TIER_SNAPSHOT": str(out)}
    got = tr.resolve("python-reviewer", "antigravity", env=env)
    assert got["status"] == "ok" and got["model"] == "fake-agy-t3" and got["inherited_from"] == "tech-reviewer"
    tiers.write_text(tiers.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert tr.resolve("implementer", "claude", env=env)["code"] == "snapshot_stale"


def test_opcos_refuses_pins_instead_of_ignoring_them(tmp_path):
    snap, _ = make_snapshot(tmp_path)
    env = {"AGENT_AGILE_TIER_SNAPSHOT": str(snap)}
    assert tr.resolve("implementer", "claude", effort=5, env=env)["code"] == "snapshot_override_unsupported"
    assert tr.resolve("implementer", "claude", model="fake-x", env=env)["code"] == "snapshot_override_unsupported"
    assert tr.resolve("implementer", "claude", "04", env=env)["code"] == "snapshot_override_unsupported"
    assert tr.resolve("implementer", "claude", "02", env=env)["status"] == "ok"
    assert tr.resolve("implementer", "claude", 2.0, env=env)["status"] == "ok"


def test_tier_float_json_number_is_integer():
    kw = dict(env={}, table=str(GOLD / "table.json"), catalog=str(GOLD / "catalog.json"))
    assert tr.resolve("advisor", "claude", 4.0, **kw)["tier"] == 4
    assert tr.resolve("advisor", "claude", "4.0", **kw)["code"] == "unknown_tier"


def _table_with(tmp_path, mutate):
    t = json.loads((GOLD / "table.json").read_text(encoding="utf-8"))
    mutate(t)
    p = tmp_path / "t.json"
    p.write_text(json.dumps(t), encoding="utf-8")
    return str(p)


def test_empty_models_is_model_tier_unavailable_except_tier_5(tmp_path):
    cat = str(GOLD / "catalog.json")
    t = _table_with(tmp_path, lambda t: t["tiers"]["2"].update(models={}))
    assert tr.resolve("implementer", "claude", env={}, table=t, catalog=cat)["code"] == "model_tier_unavailable"
    # tier 5 reserved-empty only when the catalog does not stop it first
    c = json.loads((GOLD / "catalog.json").read_text(encoding="utf-8"))
    c["human_only"] = []
    cp = tmp_path / "c.json"
    cp.write_text(json.dumps(c), encoding="utf-8")
    assert tr.resolve("human-arbiter", "claude", env={}, table=str(GOLD / "table.json"), catalog=str(cp))["code"] == "tier_reserved_empty"


def test_effort_scale_labels_validated_like_node(tmp_path):
    bad = {"1": "low", "2": "Medium!", "3": "high", "4": None, "5": None}
    t = _table_with(tmp_path, lambda t: t.update(effort_scale={"claude": bad}))
    got = tr.resolve("implementer", "claude", env={}, table=t, catalog=str(GOLD / "catalog.json"))
    assert got["code"] == "effort_invalid"


def test_legacy_t_key_table_is_unknown_tier_like_node(tmp_path):
    def legacy(t):
        t["tiers"] = {"T1": t["tiers"]["4"], "T2": t["tiers"]["3"], "T3": t["tiers"]["2"]}
    t = _table_with(tmp_path, legacy)
    cat = str(GOLD / "catalog.json")
    assert tr.resolve("implementer", "claude", "2", env={}, table=t, catalog=cat)["code"] == "unknown_tier"
    assert tr.resolve("implementer", "claude", env={}, table=t, catalog=cat)["code"] == "unknown_tier"


@pytest.mark.parametrize("mutate", [
    lambda d: d["inputs"].__setitem__(0, {"kind": "tiers", "path": 5, "present": True, "sha256": "x"}),
    lambda d: d["inputs"].__setitem__(0, "not-a-dict"),
    lambda d: d["inputs"].__setitem__(0, {"kind": 7, "path": None}),
])
def test_malformed_snapshot_inputs_are_unreadable_not_a_crash(tmp_path, mutate):
    snap, _ = make_snapshot(tmp_path)
    d = json.loads(snap.read_text(encoding="utf-8"))
    mutate(d)
    snap.write_text(json.dumps(d), encoding="utf-8")
    assert tr.resolve("implementer", "claude", env={"AGENT_AGILE_TIER_SNAPSHOT": str(snap)})["code"] == "snapshot_unreadable"


@pytest.mark.parametrize("errors", ["boom", [None], [], [5]])
def test_malformed_snapshot_errors_do_not_crash(tmp_path, errors):
    snap, _ = make_snapshot(tmp_path)
    d = json.loads(snap.read_text(encoding="utf-8"))
    d.update(status="error", errors=errors)
    snap.write_text(json.dumps(d), encoding="utf-8")
    assert tr.resolve("implementer", "claude", env={"AGENT_AGILE_TIER_SNAPSHOT": str(snap)})["code"] == "snapshot_error"


def test_unicode_digits_are_not_tiers():
    """Chữ số Unicode (Ả Rập-Ấn, số mũ) không được coi là tier — khớp Node (\\d ASCII)."""
    import re
    assert not re.fullmatch(r"[0-9]+", "\u0663")
    assert not re.fullmatch(r"[0-9]+", "\u00b2")


def test_effective_tier_from_table_and_pin_rule():
    kw = dict(env={}, table=str(GOLD / "table.json"), catalog=str(GOLD / "catalog.json"))
    assert tr.resolve("qa", "claude", **kw)["tier"] == 1  # roles.qa.tier = 1 wins over the catalog default 2
    assert tr.resolve("business-reviewer", "claude", **kw)["code"] == "catalog_table_mismatch"
    assert tr.resolve("implementer", "claude", "03", **kw)["code"] == "role_tier_mismatch"
    assert tr.resolve("implementer", "claude", "03", effort=4, **kw)["tier"] == 3
    assert tr.resolve("implementer", "claude", "03", model="fake-pinned", **kw)["model"] == "fake-pinned"
    assert tr.resolve("implementer", "claude", "02", **kw)["tier"] == 2  # same as effective: no pin needed


def test_inheriting_role_follows_the_parent_cell_of_the_table(tmp_path):
    kw = dict(env={}, table=str(GOLD / "table.json"), catalog=str(GOLD / "catalog.json"))
    child = tr.resolve("reviewer-child", "claude", **kw)
    assert (child["tier"], child["model"], child["inherited_from"]) == (4, "fake-claude-t4", "reviewer-base")
    assert tr.resolve("reviewer-base", "codex", **kw)["tier"] == 4
    # the child's own cell wins over the parent's; no cell anywhere falls back to the catalog default
    own = _table_with(tmp_path, lambda t: t["roles"].update({"reviewer-child": {"tier": "3"}}))
    assert tr.resolve("reviewer-child", "claude", env={}, table=own, catalog=kw["catalog"])["tier"] == 3
    none = _table_with(tmp_path, lambda t: t["roles"].pop("reviewer-base"))
    assert tr.resolve("reviewer-child", "claude", env={}, table=none, catalog=kw["catalog"])["tier"] == 3
    # real catalog: raising tech-reviewer to 4 raises every role that inherits it
    cat = tr.load_catalog(REPO / "tiers" / "role-catalog.json")
    defaults = json.loads((REPO / "tiers" / "tiers.defaults.json").read_text(encoding="utf-8"))
    defaults["roles"] = {"tech-reviewer": {"tier": "4"}}
    heirs = [r for r, v in cat["roles"].items() if v.get("inherits") == "tech-reviewer"]
    assert len(heirs) == 17
    for r in heirs:
        assert tr.resolve_role_turn(r, "claude", catalog=cat, table=defaults)["tier"] == 4, r
