#!/usr/bin/env python3
"""Tier resolver of agent-agile-team (ADR-008 #1-#3, #7, #12): role + vendor -> model + effort.

Usage:
    python scripts/tier_resolve.py --role R --vendor V [--tier N] [--effort N] [--json]
    python scripts/tier_resolve.py status [--json]
    (both accept --snapshot F, --table F, --catalog F to override the environment)

Two modes, one contract:
  * opcos       AGENT_AGILE_TIER_SNAPSHOT is set. The snapshot written by the Node resolver
                (system/bridges/lib/tier-snapshot.mjs) is READ, never recomputed. A set variable whose file is
                missing, unreadable or stale is an error (snapshot_missing / snapshot_unreadable / snapshot_stale),
                never a silent fall back to standalone.
  * standalone  The variable is absent. The resolver reads the user table (AGENT_AGILE_TIERS, else
                %LOCALAPPDATA%\\agent-agile-team\\tiers.json) and the role catalog (AGENT_AGILE_ROLE_CATALOG, else
                tiers/role-catalog.json of this plugin; missing -> catalog_missing). It resolves model and effort
                per role only: no skill overlay, no table writes.

Error order for one role turn (shared with Node; tests/fixtures/tier-golden/README.md):
    unknown_role -> legacy_alias_forbidden_in_role_turn -> unknown_tier -> tier_reserved_human_only
    -> role_tier_mismatch, then the table errors (model_tier_unavailable, effort_*).

Exit codes: 0 ok, 2 error. Output carries model ids, codes and paths only; never secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_SCHEMA = 1
RESOLVER_CONTRACT = 1
VENDORS = ("claude", "codex", "antigravity")
ERROR_ORDER = (
    "unknown_role",
    "legacy_alias_forbidden_in_role_turn",
    "unknown_tier",
    "tier_reserved_human_only",
    "role_tier_mismatch",
)
_FULL_SCALE = {1: "low", 2: "medium", 3: "high", 4: "xhigh", 5: "max"}
DEFAULT_EFFORT_SCALE = {
    "claude": _FULL_SCALE,
    "codex": _FULL_SCALE,
    "antigravity": {1: "low", 2: "medium", 3: "high", 4: None, 5: None},
}
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class TierError(Exception):
    """A resolution failure with a stable machine code."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


# ── Paths and mode detection ──────────────────────────────────────────────────

def standalone_table_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get("AGENT_AGILE_TIERS"):
        return Path(env["AGENT_AGILE_TIERS"])
    local = env.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / ".local" / "state"
    return base / "agent-agile-team" / "tiers.json"


def catalog_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get("AGENT_AGILE_ROLE_CATALOG"):
        return Path(env["AGENT_AGILE_ROLE_CATALOG"])
    return PLUGIN_ROOT / "tiers" / "role-catalog.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _input_entry(kind: str, path: str | None) -> dict:
    if not path or not Path(path).is_file():
        return {"kind": kind, "path": path, "present": False, "sha256": None}
    return {"kind": kind, "path": path, "present": True, "sha256": _sha(Path(path).read_bytes())}


def _hash_inputs(inputs: list[dict]) -> str:
    # Byte-for-byte the Node hashInputs: `${kind}\0${sha|absent}\n` per input, joined, sha256.
    text = "".join(f"{i['kind']}\0{i['sha256'] if i['present'] else 'absent'}\n" for i in inputs)
    return _sha(text.encode("utf-8"))


def read_snapshot(path: str | os.PathLike) -> dict:
    """Mirror of Node readSnapshot: {status: ok|stale|error, code?, snapshot?}."""
    try:
        snap = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "error", "code": "snapshot_missing"}
    except (OSError, ValueError):
        return {"status": "error", "code": "snapshot_unreadable"}
    if (
        not isinstance(snap, dict)
        or snap.get("schema") != SNAPSHOT_SCHEMA
        or not isinstance(snap.get("inputs"), list)
        or not all(
            isinstance(i, dict) and isinstance(i.get("kind"), str) and (i.get("path") is None or isinstance(i.get("path"), str))
            for i in snap["inputs"]
        )
        or not isinstance(snap.get("input_hash"), str)
    ):
        return {"status": "error", "code": "snapshot_unreadable"}
    try:
        now = _hash_inputs([_input_entry(i["kind"], i.get("path")) for i in snap["inputs"]])
    except (OSError, ValueError):
        return {"status": "error", "code": "snapshot_unreadable"}
    if now != snap["input_hash"]:
        return {"status": "stale", "code": "snapshot_stale", "snapshot": snap}
    if snap.get("status") == "error":
        errors = snap.get("errors")
        first = errors[0] if isinstance(errors, list) and errors else None
        code = first.get("code") if isinstance(first, dict) else None
        return {"status": "error", "code": code if isinstance(code, str) else "snapshot_error", "snapshot": snap}
    return {"status": "ok", "snapshot": snap}


def detect_mode(env: Mapping[str, str] | None = None, snapshot: str | None = None) -> dict:
    """{mode, source, snapshot?}. Raises TierError for a set-but-unusable snapshot (ADR-008 #3)."""
    env = os.environ if env is None else env
    var = snapshot or env.get("AGENT_AGILE_TIER_SNAPSHOT")
    if var:
        r = read_snapshot(var)
        if r["status"] != "ok":
            raise TierError(r["code"], f"AGENT_AGILE_TIER_SNAPSHOT points at {var}: {r['code']}")
        return {"mode": "opcos", "source": var, "snapshot": r["snapshot"]}
    return {"mode": "standalone", "source": str(standalone_table_path(env))}


# ── Catalog and table ─────────────────────────────────────────────────────────

def load_catalog(path: str | os.PathLike | None) -> dict:
    if not path or not Path(path).is_file():
        raise TierError("catalog_missing", f"role catalog not found: {path}")
    try:
        c = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise TierError("catalog_invalid", f"role catalog unreadable: {e}")
    if not isinstance(c, dict) or c.get("schema") != 1 or not isinstance(c.get("roles"), dict):
        raise TierError("catalog_invalid", "role catalog wrong shape (schema 1, roles{}).")
    if c.get("resolver_contract") != RESOLVER_CONTRACT:
        raise TierError("catalog_invalid", f"role catalog resolver_contract {c.get('resolver_contract')} != {RESOLVER_CONTRACT}.")
    return c


def catalog_role(catalog: dict, role: str) -> dict | None:
    roles = catalog["roles"]
    e = roles.get(role)
    if not isinstance(e, dict):
        return None
    if not e.get("inherits"):
        return {**e, "inherited_from": None}
    parent = roles.get(e["inherits"])
    if not isinstance(parent, dict) or parent.get("inherits"):
        raise TierError("catalog_invalid", f"role {role} inherits {e['inherits']} invalid.")
    out = {**parent, **e}
    out["tier_default"] = e.get("tier_default", parent.get("tier_default"))
    out["tier_range"] = e.get("tier_range", parent.get("tier_range"))
    out["inherited_from"] = e["inherits"]
    return out


def load_table(path: str | os.PathLike) -> dict:
    if not Path(path).is_file():
        raise TierError("tiers_file_missing", f"tier table not found: {path}")
    try:
        t = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise TierError("model_tier_unavailable", f"tier table unreadable: {e}")
    if not isinstance(t, dict) or not isinstance(t.get("tiers"), dict) or t.get("schema") not in (1, 2, 3):
        raise TierError("model_tier_unavailable", "tier table wrong shape (schema 1-3, tiers{}).")
    return t


def _is_level(n: Any) -> bool:
    return isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 5


def _effort_cell(v: Any, vendor: str) -> int | None:
    if _is_level(v):
        return v
    if isinstance(v, dict) and _is_level(v.get(vendor)):
        return v[vendor]
    return None


def _effort_scale(table: dict) -> tuple[dict, dict]:
    scale = {h: dict(DEFAULT_EFFORT_SCALE[h]) for h in VENDORS}
    fallback: dict[str, str] = {}
    if table.get("schema", 1) < 2:
        return scale, fallback
    es = table.get("effort_scale")
    if es is not None:
        if not isinstance(es, dict):
            raise TierError("effort_invalid", "effort_scale must be an object.")
        for h, block in es.items():
            if h not in VENDORS or not isinstance(block, dict) or sorted(block) != ["1", "2", "3", "4", "5"]:
                raise TierError("effort_invalid", f"effort_scale.{h} invalid.")
            if any(v is not None and not (isinstance(v, str) and re.fullmatch(r"[a-z]{2,12}", v)) for v in block.values()):
                raise TierError("effort_invalid", f"effort_scale.{h} labels must be native strings or null.")
            scale[h] = {int(k): v for k, v in block.items()}
    fb = table.get("fallback")
    if fb is not None:
        if not isinstance(fb, dict) or any(h not in VENDORS or v != "clamp_to_max" for h, v in fb.items()):
            raise TierError("effort_invalid", "fallback must be {vendor: clamp_to_max}.")
        fallback = dict(fb)
    return scale, fallback


# ── Resolver (standalone) ─────────────────────────────────────────────────────

def resolve_role_turn(
    role: str,
    vendor: str,
    tier: Any = None,
    effort: int | None = None,
    model: str | None = None,
    *,
    catalog: dict,
    table: dict,
) -> dict:
    """One role turn: catalog rules in ERROR_ORDER, then the table. Raises TierError."""
    entry = catalog_role(catalog, role)
    if entry is None:
        raise TierError("unknown_role", f"role {role!r} is not in the role catalog.")
    if isinstance(tier, float) and tier.is_integer():
        tier = int(tier)  # JSON 4.0 is the number 4, as in JavaScript
    given = tier is not None and str(tier).strip() != ""
    raw = re.sub(r"^tier\s*(?=[0-9]+$)", "", str(tier).strip(), flags=re.I) if given else None
    if given and re.fullmatch(r"T\d+", raw, flags=re.I):
        raise TierError("legacy_alias_forbidden_in_role_turn", f'alias {raw} is forbidden in a role turn; write "tier N" (1-5).')
    tiers = table["tiers"]
    if given:
        # Node: Number(raw) when all digits, then the table key is String(n): "04" is tier 4.
        if not re.fullmatch(r"[0-9]+", raw) or str(int(raw)) not in tiers:
            raise TierError("unknown_tier", f"tier {raw} is not in the tier table.")
        n = int(raw)
    else:
        n = entry.get("tier_default")
        if not isinstance(n, int):
            raise TierError("unknown_tier", f"role {role} has no default tier.")
    if n in (catalog.get("human_only") or []):
        raise TierError("tier_reserved_human_only", f"tier {n} is for the human decider; not assignable to a role.")
    rng = entry.get("tier_range")
    if isinstance(rng, list) and len(rng) == 2 and not rng[0] <= n <= rng[1]:
        raise TierError("role_tier_mismatch", f"role {role} tier range {rng[0]}-{rng[1]}, not {n}.")
    if vendor not in VENDORS:
        raise TierError("model_tier_unavailable", f"vendor {vendor!r} unknown; valid: {', '.join(VENDORS)}.")
    key = str(n)
    tdef = tiers.get(key)
    if not isinstance(tdef, dict):
        raise TierError("unknown_tier", f"tier {n} is not in the tier table.")
    roles = table.get("roles") if table.get("schema", 1) >= 2 and isinstance(table.get("roles"), dict) else {}
    rdef = roles.get(role) if isinstance(roles.get(role), dict) else None
    if rdef is not None and str(rdef.get("tier")) != key:
        raise TierError("role_tier_mismatch", f"table roles.{role}.tier = {rdef.get('tier')}, not tier {n}.")

    # Model: pin -> role -> tier. No default, no downgrade, no vendor swap.
    m_src = None
    chosen = None
    if model is not None:
        if not isinstance(model, str) or not _MODEL_ID_RE.match(model):
            raise TierError("model_unknown", "pin.model has a bad shape.")
        chosen, m_src = model, "pin"
    else:
        rm = ((rdef or {}).get("models") or {}).get(vendor)
        tm = (tdef.get("models") or {}).get(vendor)
        if isinstance(rm, str) and rm:
            chosen, m_src = rm, "role"
        elif isinstance(tm, str) and tm:
            chosen, m_src = tm, "tier"
    if not chosen:
        models = tdef.get("models")
        if key == "5" and (tdef.get("purpose") == "reserved-human-only" or (isinstance(models, dict) and not models)):
            raise TierError("tier_reserved_empty", f"tier {n} has no model on purpose (human decider).")
        raise TierError("model_tier_unavailable", f"table has no model for {vendor} at pin, role or tier {n}.")

    # Effort: pin -> role -> tier -> unset. Clamp by the table fallback.
    level = None
    e_src = "unset"
    if effort is not None:
        if not _is_level(effort):
            raise TierError("effort_invalid", "effort_level must be an integer 1-5.")
        level, e_src = effort, "pin"
    elif _effort_cell((rdef or {}).get("effort"), vendor) is not None:
        level, e_src = _effort_cell(rdef["effort"], vendor), "role"
    elif table.get("schema", 1) >= 2 and _effort_cell(tdef.get("effort"), vendor) is not None:
        level, e_src = _effort_cell(tdef["effort"], vendor), "tier"
    native = None
    if level is not None:
        scale, fallback = _effort_scale(table)
        native = scale[vendor].get(level)
        if native is None:
            lower = next((lv for lv in (5, 4, 3, 2, 1) if lv < level and scale[vendor].get(lv)), None)
            if fallback.get(vendor) != "clamp_to_max" or lower is None:
                raise TierError("effort_unsupported", f"level {level} has no native label for {vendor} and no fallback.")
            level, native, e_src = lower, scale[vendor][lower], "clamped_by_table"
    return {
        "status": "ok",
        "tier": n,
        "model": chosen,
        "effort": level,
        "effort_native": native,
        "sources": {"model": m_src, "effort": e_src},
        "inherited_from": entry["inherited_from"],
    }


# ── Resolver (opcos: read the snapshot, no own resolution) ───────────────────

def resolve_from_snapshot(snapshot: dict, role: str, vendor: str, tier: Any = None, effort: int | None = None, model: str | None = None) -> dict:
    """Look up a role turn in a snapshot. It holds the default tier per role only."""
    roles = snapshot.get("roles") or {}
    entry = roles.get(role)
    if not isinstance(entry, dict):
        raise TierError("unknown_role", f"role {role!r} is not in the snapshot.")
    if isinstance(tier, float) and tier.is_integer():
        tier = int(tier)
    given = tier is not None and str(tier).strip() != ""
    if given:
        raw = re.sub(r"^tier\s*(?=[0-9]+$)", "", str(tier).strip(), flags=re.I)
        if re.fullmatch(r"T\d+", raw, flags=re.I):
            raise TierError("legacy_alias_forbidden_in_role_turn", f'alias {raw} is forbidden in a role turn; write "tier N" (1-5).')
        same = (str(int(raw)) if re.fullmatch(r"[0-9]+", raw) else raw) == str(entry.get("tier"))
        if not same:
            raise TierError("snapshot_override_unsupported", f"snapshot holds the default tier {entry.get('tier')} only, not {raw}.")
    if effort is not None or model is not None:
        raise TierError("snapshot_override_unsupported", "a snapshot cannot honour --effort or --model; the pin is refused, not ignored.")
    cell = entry.get(vendor)
    if not isinstance(cell, dict):
        raise TierError("model_tier_unavailable", f"snapshot has no entry for {role}/{vendor}.")
    if cell.get("status") != "ok":
        raise TierError(cell.get("code") or "model_tier_unavailable", f"snapshot marks {role}/{vendor} as unresolved.")
    return {
        "status": "ok",
        "tier": entry.get("tier"),
        "model": cell.get("model"),
        "effort": cell.get("effort_level"),
        "effort_native": cell.get("effort_native"),
        "sources": cell.get("sources"),
        "inherited_from": entry.get("inherits"),
    }


# ── Public entry ──────────────────────────────────────────────────────────────

def resolve(
    role: str,
    vendor: str,
    tier: Any = None,
    effort: int | None = None,
    model: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    snapshot: str | None = None,
    table: str | None = None,
    catalog: str | None = None,
) -> dict:
    """Detect the mode, resolve one role turn, return {status, mode, ...} or {status:'error', code, message}."""
    env = os.environ if env is None else env
    try:
        mode = detect_mode(env, snapshot)
        if mode["mode"] == "opcos":
            out = resolve_from_snapshot(mode["snapshot"], role, vendor, tier, effort, model)
        else:
            t_path = Path(table) if table else standalone_table_path(env)
            c_path = Path(catalog) if catalog else catalog_path(env)
            out = resolve_role_turn(role, vendor, tier, effort, model, catalog=load_catalog(c_path), table=load_table(t_path))
        return {**out, "mode": mode["mode"], "source": mode["source"], "resolver": f"tier_resolve.py/{mode['mode']}"}
    except TierError as e:
        return {"status": "error", "code": e.code, "message": e.message}


def status(env: Mapping[str, str] | None = None, snapshot: str | None = None, table: str | None = None, catalog: str | None = None) -> dict:
    env = os.environ if env is None else env
    try:
        mode = detect_mode(env, snapshot)
    except TierError as e:
        return {"status": "error", "code": e.code, "message": e.message, "snapshot": snapshot or env.get("AGENT_AGILE_TIER_SNAPSHOT")}
    if mode["mode"] == "opcos":
        snap = mode["snapshot"]
        return {"status": "ok", "mode": "opcos", "source": mode["source"], "revision": snap.get("revision"),
                "roles": len(snap.get("roles") or {})}
    t_path = Path(table) if table else standalone_table_path(env)
    c_path = Path(catalog) if catalog else catalog_path(env)
    return {"status": "ok", "mode": "standalone", "source": str(t_path), "table_present": t_path.is_file(),
            "catalog": str(c_path), "catalog_present": c_path.is_file()}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="Tier resolver (role + vendor -> model + effort).")
    p.add_argument("command", nargs="?", choices=["status"], help="`status` prints the mode and its source")
    p.add_argument("--role")
    p.add_argument("--vendor", choices=VENDORS)
    p.add_argument("--tier")
    p.add_argument("--effort", type=int)
    p.add_argument("--model")
    p.add_argument("--snapshot")
    p.add_argument("--table")
    p.add_argument("--catalog")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    if a.command == "status":
        res = status(snapshot=a.snapshot, table=a.table, catalog=a.catalog)
    else:
        if not a.role or not a.vendor:
            p.error("--role and --vendor are required (or use `status`)")
        res = resolve(a.role, a.vendor, a.tier, a.effort, a.model, snapshot=a.snapshot, table=a.table, catalog=a.catalog)
    if a.json:
        print(json.dumps(res, ensure_ascii=False))
    elif res["status"] == "ok":
        print(" ".join(f"{k}={v}" for k, v in res.items() if k not in ("status", "sources", "snapshot") and v is not None))
    else:
        print(f"error {res['code']}: {res.get('message', '')}", file=sys.stderr)
    return 0 if res["status"] == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
