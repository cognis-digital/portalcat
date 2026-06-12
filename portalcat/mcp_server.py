"""portalcat MCP server — stdio JSON-RPC 2.0. Standard library only.

    {"command": "python", "args": ["-m", "portalcat", "mcp"]}
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from portalcat import TOOL_NAME, TOOL_VERSION
from portalcat.core import (
    PortalError,
    impact_of,
    load_catalog,
    summarize,
    validate_catalog,
)

PROTOCOL_VERSION = "2024-11-05"

_TOOLS = [
    {
        "name": "summary",
        "description": "Summarize a software catalog: entity counts by kind, by "
                       "owner, and dangling references.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"], "additionalProperties": False,
        },
    },
    {
        "name": "validate",
        "description": "Validate catalog entities and their ownership/dependency "
                       "references; reports dangling refs and missing owners.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"], "additionalProperties": False,
        },
    },
    {
        "name": "impact",
        "description": "List everything that transitively depends on an entity.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "ref": {"type": "string"}},
            "required": ["path", "ref"], "additionalProperties": False,
        },
    },
]


def _result(req_id, result): return {"jsonrpc": "2.0", "id": req_id, "result": result}
def _error(req_id, code, msg): return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}}


def _call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    path = args.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("`path` (string) is required")
    entities = load_catalog(path)
    if name == "summary":
        return {"content": [{"type": "text", "text": json.dumps(summarize(entities), indent=2)}],
                "isError": False}
    if name == "validate":
        res = validate_catalog(entities)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}],
                "isError": not res["ok"]}
    if name == "impact":
        ref = args.get("ref")
        if not isinstance(ref, str):
            raise ValueError("`ref` (string) is required")
        deps = impact_of(entities, ref)
        return {"content": [{"type": "text",
                             "text": json.dumps({"ref": ref, "dependents": deps}, indent=2)}],
                "isError": False}
    raise ValueError(f"unknown tool: {name}")


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}
    is_notification = "id" not in req
    if method == "initialize":
        res = _result(req_id, {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {"tools": {"listChanged": False}},
                               "serverInfo": {"name": TOOL_NAME, "version": TOOL_VERSION}})
        return None if is_notification else res
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return None if is_notification else _result(req_id, {})
    if method == "tools/list":
        return _result(req_id, {"tools": _TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            return _result(req_id, _call_tool(name, args))
        except (ValueError, OSError, PortalError) as exc:
            return _error(req_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover
            return _error(req_id, -32603, f"internal error: {exc}")
    if is_notification:
        return None
    return _error(req_id, -32601, f"method not found: {method}")


def run_mcp_server(stdin=None, stdout=None) -> None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            stdout.flush()
            continue
        response = handle_request(req)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
