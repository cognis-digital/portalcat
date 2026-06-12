"""Command-line interface for portalcat."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from portalcat import TOOL_NAME, TOOL_VERSION
from portalcat.core import (
    PortalError,
    impact_of,
    load_catalog,
    scaffold,
    summarize,
    validate_catalog,
    who_owns,
)

_SEV = {"error": "ERR ", "warning": "WARN"}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Software catalog & scaffolder — index entities, graph "
                    "ownership/dependencies, and scaffold new components.")
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("summary", help="Summarize a catalog (kinds, owners, dangling).")
    s.add_argument("path")
    s.add_argument("--format", choices=("table", "json"), default="table")

    v = sub.add_parser("validate", help="Validate entities and references.")
    v.add_argument("path")
    v.add_argument("--format", choices=("table", "json"), default="table")

    o = sub.add_parser("owner", help="Show who owns an entity.")
    o.add_argument("path")
    o.add_argument("ref")

    i = sub.add_parser("impact", help="What (transitively) depends on an entity.")
    i.add_argument("path")
    i.add_argument("ref")

    sc = sub.add_parser("scaffold", help="Render a template tree into a new component.")
    sc.add_argument("template")
    sc.add_argument("dest")
    sc.add_argument("--set", action="append", default=[], metavar="K=V")

    sub.add_parser("mcp", help="Run as an MCP server (stdio JSON-RPC).")
    return p


def _run_summary(a) -> int:
    try:
        info = summarize(load_catalog(a.path))
    except (OSError, PortalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.format == "json":
        print(json.dumps(info, indent=2))
    else:
        print(f"portalcat — {info['entity_count']} entity(ies)")
        print("=" * 56)
        print("  by kind : " + ", ".join(f"{k}={v}" for k, v in sorted(info["by_kind"].items())))
        print("  by owner: " + ", ".join(f"{k}={v}" for k, v in sorted(info["by_owner"].items())))
        if info["dangling"]:
            print(f"  DANGLING ({info['dangling_count']}):")
            for d in info["dangling"]:
                print(f"    {d['from']} --{d['via']}--> {d['to']} (missing)")
    return 0


def _run_validate(a) -> int:
    try:
        res = validate_catalog(load_catalog(a.path))
    except (OSError, PortalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.format == "json":
        print(json.dumps(res, indent=2))
    else:
        print("portalcat validate")
        print("=" * 56)
        for f in res["findings"]:
            print(f"[{_SEV.get(f['severity'], f['severity'])}] {f['ref']}: {f['message']}")
        print("RESULT: " + ("PASS" if res["ok"] else f"FAIL ({res['error_count']} error(s))"))
    return 0 if res["ok"] else 1


def _run_owner(a) -> int:
    try:
        owner = who_owns(load_catalog(a.path), a.ref)
    except (OSError, PortalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if owner is None:
        print(f"{a.ref}: no owner (or entity not found)")
        return 1
    print(f"{a.ref}: {owner}")
    return 0


def _run_impact(a) -> int:
    try:
        deps = impact_of(load_catalog(a.path), a.ref)
    except (OSError, PortalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"portalcat impact — {len(deps)} entity(ies) depend on {a.ref}")
    for d in deps:
        print(f"  {d}")
    return 0


def _run_scaffold(a) -> int:
    values = {}
    for item in a.set:
        if "=" not in item:
            print(f"error: --set expects K=V, got {item!r}", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        values[k] = v
    try:
        written = scaffold(a.template, a.dest, values)
    except (OSError, PortalError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"portalcat scaffold — wrote {len(written)} file(s) to {a.dest}")
    for w in written:
        print(f"  {w}")
    return 0


def _run_mcp() -> int:
    from portalcat.mcp_server import run_mcp_server
    run_mcp_server()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "summary":
        return _run_summary(args)
    if args.command == "validate":
        return _run_validate(args)
    if args.command == "owner":
        return _run_owner(args)
    if args.command == "impact":
        return _run_impact(args)
    if args.command == "scaffold":
        return _run_scaffold(args)
    if args.command == "mcp":
        return _run_mcp()
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
