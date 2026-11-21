"""tier_setup.py: create the standalone table once, never over a user table, never beside OpcOS. Temp dirs only."""

from __future__ import annotations

import json

from conftest import FIXTURES, run_script
import tier_setup as ts

DEFAULTS = FIXTURES / "tier-golden" / "table.json"


def test_creates_when_absent(tmp_path):
    dest = tmp_path / "new" / "agent-agile-team" / "tiers.json"
    res = ts.setup(DEFAULTS, dest, env={})
    assert res["action"] == "created" and dest.read_bytes() == DEFAULTS.read_bytes()
    assert not list(dest.parent.glob("*.tmp"))


def test_dry_run_writes_nothing(tmp_path):
    dest = tmp_path / "x" / "tiers.json"
    assert ts.setup(DEFAULTS, dest, dry_run=True, env={})["action"] == "would_create"
    assert not dest.parent.exists()


def test_never_overwrites_user_table(tmp_path):
    dest = tmp_path / "tiers.json"
    dest.write_text('{"mine": true}', encoding="utf-8")
    assert ts.setup(DEFAULTS, dest, env={})["action"] == "skipped_exists"
    assert json.loads(dest.read_text(encoding="utf-8")) == {"mine": True}


def test_skipped_beside_opcos_snapshot(tmp_path):
    dest = tmp_path / "tiers.json"
    res = ts.setup(DEFAULTS, dest, env={"AGENT_AGILE_TIER_SNAPSHOT": str(tmp_path / "s.json")})
    assert res["action"] == "skipped_opcos" and not dest.exists()


def test_defaults_missing_or_invalid(tmp_path):
    dest = tmp_path / "tiers.json"
    assert ts.setup(tmp_path / "none.json", dest, env={})["code"] == "defaults_missing"
    bad = tmp_path / "bad.json"
    bad.write_text("[1]", encoding="utf-8")
    assert ts.setup(bad, dest, env={})["code"] == "defaults_invalid"
    assert not dest.exists()


def test_default_destination_from_env(tmp_path):
    res = ts.setup(DEFAULTS, env={"LOCALAPPDATA": str(tmp_path)}, dry_run=True)
    assert res["dest"] == str(tmp_path / "agent-agile-team" / "tiers.json")


def test_cli_json(tmp_path):
    dest = tmp_path / "t.json"
    env = {"AGENT_AGILE_TIER_SNAPSHOT": ""}
    r = run_script("tier_setup.py", "--defaults", str(DEFAULTS), "--dest", str(dest), "--json", env=env)
    assert r.returncode == 0 and json.loads(r.stdout)["action"] == "created" and dest.is_file()
    r = run_script("tier_setup.py", "--defaults", str(tmp_path / "no.json"), "--dest", str(tmp_path / "u.json"), "--json", env=env)
    assert r.returncode == 2


def test_table_appearing_during_write_is_never_replaced(tmp_path, monkeypatch):
    dest = tmp_path / "tiers.json"
    real_link = ts.os.link

    def racing_link(src, dst, *a, **k):
        dest.write_text('{"user": 1}', encoding="utf-8")  # the user's table lands after the exists() check
        return real_link(src, dst, *a, **k)

    monkeypatch.setattr(ts.os, "link", racing_link)
    res = ts.setup(DEFAULTS, dest, env={})
    assert res["action"] == "skipped_exists"
    assert json.loads(dest.read_text(encoding="utf-8")) == {"user": 1}
    assert not list(tmp_path.glob("*.tmp"))


def test_no_hard_link_support_falls_back_to_exclusive_create(tmp_path, monkeypatch):
    dest = tmp_path / "tiers.json"

    def no_link(*a, **k):
        raise OSError("hard links unsupported")

    monkeypatch.setattr(ts.os, "link", no_link)
    assert ts.setup(DEFAULTS, dest, env={})["action"] == "created"
    assert dest.read_bytes() == DEFAULTS.read_bytes() and not list(tmp_path.glob("*.tmp"))
