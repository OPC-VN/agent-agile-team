#!/usr/bin/env python3
"""Create the standalone tier table of this machine (ADR-008 #2).

Usage:
    python scripts/tier_setup.py [--defaults FILE] [--dest FILE] [--dry-run] [--json]

Copies the defaults file (default: tiers/tiers.defaults.json of this plugin) to the user table
(default: AGENT_AGILE_TIERS, else %LOCALAPPDATA%\\agent-agile-team\\tiers.json) ONLY when
  * AGENT_AGILE_TIER_SNAPSHOT is not set (an OpcOS install keeps its own table and snapshot), and
  * the user table does not exist yet (a table the user edited is never overwritten).
--dry-run reports the action and writes nothing. The table appears atomically (temp file, then hard link, which cannot replace an existing file).
Actions: created | would_create | skipped_opcos | skipped_exists | error (defaults missing/invalid).
Exit codes: 0 done or skipped on purpose, 2 error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Mapping

from tier_resolve import PLUGIN_ROOT, standalone_table_path

DEFAULTS = PLUGIN_ROOT / "tiers" / "tiers.defaults.json"


def setup(
    defaults: str | os.PathLike | None = None,
    dest: str | os.PathLike | None = None,
    dry_run: bool = False,
    env: Mapping[str, str] | None = None,
) -> dict:
    env = os.environ if env is None else env
    src = Path(defaults) if defaults else DEFAULTS
    target = Path(dest) if dest else standalone_table_path(env)
    base = {"defaults": str(src), "dest": str(target), "dry_run": dry_run}
    if env.get("AGENT_AGILE_TIER_SNAPSHOT"):
        return {**base, "action": "skipped_opcos", "reason": "AGENT_AGILE_TIER_SNAPSHOT is set: OpcOS owns the table and snapshot."}
    if target.exists():
        return {**base, "action": "skipped_exists", "reason": "the user table already exists and is never overwritten."}
    try:
        data = src.read_bytes()
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, dict) or not isinstance(parsed.get("tiers"), dict):
            raise ValueError("defaults file is not a tier table (tiers{} missing)")
    except FileNotFoundError:
        return {**base, "action": "error", "code": "defaults_missing", "reason": f"defaults file not found: {src}"}
    except (OSError, ValueError) as e:
        return {**base, "action": "error", "code": "defaults_invalid", "reason": str(e)}
    if dry_run:
        return {**base, "action": "would_create"}
    tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            os.link(tmp, target)  # fails with FileExistsError if a table appeared meanwhile: never overwrites
        except FileExistsError:
            return {**base, "action": "skipped_exists", "reason": "the user table appeared meanwhile and is never overwritten."}
        except OSError:  # no hard links on this volume: exclusive create instead
            with open(target, "xb") as fh:
                fh.write(data)
    except FileExistsError:
        return {**base, "action": "skipped_exists", "reason": "the user table appeared meanwhile and is never overwritten."}
    except OSError as e:
        return {**base, "action": "error", "code": "write_failed", "reason": str(e)}
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    return {**base, "action": "created"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Create the standalone tier table from the defaults file.")
    p.add_argument("--defaults")
    p.add_argument("--dest")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    res = setup(a.defaults, a.dest, a.dry_run)
    if a.json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        tail = res.get("reason", "")
        print(f"{res['action']}: {res['dest']}" + (f" ({tail})" if tail else ""))
    return 2 if res["action"] == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
