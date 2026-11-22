"""role-catalog.json and tiers.defaults.json: shape, the nine core roles vs the machine table, the 14 role cards."""

from __future__ import annotations

import json
import re

import pytest

from conftest import REPO
import tier_resolve as tr

TIERS = REPO / "tiers"
CATALOG = json.loads((TIERS / "role-catalog.json").read_text(encoding="utf-8"))
DEFAULTS = json.loads((TIERS / "tiers.defaults.json").read_text(encoding="utf-8"))
REC_TABLE = REPO.parent.parent / "system" / "workshop" / "records" / "agent-agile-team" / "tiers.json"
GROUPS = {"executor", "verifier", "advisor", "generalist"}
CORE = ("researcher", "qa", "implementer", "analyst", "architect", "tech-reviewer", "business-reviewer", "gate-delegate", "advisor")


def test_catalog_shape_and_contract():
    assert (CATALOG["schema"], CATALOG["resolver_contract"], CATALOG["tier_scale"]) == (1, tr.RESOLVER_CONTRACT, 2)
    assert CATALOG["human_only"] == [5] and CATALOG["alias_scope"] == "records_only"
    assert CATALOG["legacy_alias"] == {"T1": 4, "T2": 3, "T3": 2}
    assert tr.load_catalog(TIERS / "role-catalog.json") == CATALOG


def test_every_role_is_well_formed_and_inheritance_is_one_level():
    for name, r in CATALOG["roles"].items():
        assert r["group"] in GROUPS, name
        if "inherits" in r:
            assert CATALOG["roles"][r["inherits"]].get("inherits") is None, name
            assert tr.catalog_role(CATALOG, name)["tier_default"] is not None
        else:
            lo, hi = r["tier_range"]
            assert lo <= r["tier_default"] <= hi and 1 <= lo <= hi <= 4, name


def test_core_roles_inherit_nothing_and_specialists_follow_tech_reviewer():
    for name in CORE:
        assert "inherits" not in CATALOG["roles"][name]
    for name in ("dual-review", "backend-specialist", "data-specialist", "frontend-specialist", "security-specialist", "python-reviewer"):
        assert tr.catalog_role(CATALOG, name)["tier_default"] == 3 and CATALOG["roles"][name]["inherits"] == "tech-reviewer"


@pytest.mark.skipif(not REC_TABLE.is_file(), reason="Chưa chạy: machine tier table not present")
def test_core_roles_match_the_machine_table():
    table = json.loads(REC_TABLE.read_text(encoding="utf-8"))
    for name in CORE:
        assert str(CATALOG["roles"][name]["tier_default"]) == table["roles"][name]["tier"], name
        assert CATALOG["roles"][name]["group"] == table["roles"][name]["group"], name


def test_catalog_covers_the_14_role_cards_and_the_13_agents():
    cards = [c for c in sorted((REPO / "roles").rglob("*.md")) if c.name != "README.md"]
    assert len(cards) == 14
    for card in cards:
        head = card.read_text(encoding="utf-8").split("---")[1]
        name = re.search(r"^name:\s*(\S+)", head, re.M).group(1)
        group = re.search(r"^group:\s*(\S+)", head, re.M).group(1)
        assert name in CATALOG["roles"], f"{card.name}: {name} missing from the catalog"
        assert CATALOG["roles"][name]["group"] == group, name
    agents = list((REPO / "agents").glob("*.md"))
    assert len(agents) == 16
    for agent in agents:
        assert agent.stem in CATALOG["roles"], agent.name
    # CO16: every core role is either an agent file or reachable through the [AAT role=...] tag (a catalog role).
    stems = {a.stem for a in agents}
    for name in CORE:
        assert name in stems or name in CATALOG["roles"], name


def test_decision_role_agents_are_read_only_and_carry_no_model():
    for name in ("business-reviewer", "gate-delegate", "advisor"):
        text = (REPO / "agents" / f"{name}.md").read_text(encoding="utf-8")
        head = text.split("---")[1]
        assert re.search(rf"^name:\s*{name}$", head, re.M)
        assert not re.search(r"^model\s*:", head, re.M), name
        tools = re.search(r"^tools:\s*(.+)$", head, re.M).group(1)
        assert "Write" not in tools and "Edit" not in tools, name
        assert re.search(r"^description: Sprint role \(agile ON only\)", head, re.M), name
        assert not re.search(r"\bT[123]\b", text), name


def test_defaults_table_resolves_every_catalog_role_per_vendor():
    for name in CATALOG["roles"]:
        for vendor in tr.VENDORS:
            res = tr.resolve_role_turn(name, vendor, catalog=CATALOG, table=DEFAULTS)
            assert res["model"] and res["effort"] in (1, 2, 3), (name, vendor, res)
    assert DEFAULTS["tiers"]["5"]["models"] == {} and DEFAULTS["known"] == {} and DEFAULTS["as_of"] == "2026-11-22"
    assert DEFAULTS["tiers"]["4"]["models"]["claude"] == "claude-fable-5-2"


def test_defaults_hold_no_paths_or_secrets():
    text = json.dumps(DEFAULTS)
    assert not re.search(r"[A-Za-z]:\\|/Users/|\.secret|sk-|token", text, re.I)
