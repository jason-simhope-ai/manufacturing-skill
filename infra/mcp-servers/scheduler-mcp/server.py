#!/usr/bin/env python3
"""manufacturing-scheduler - read-only MCP server for production scheduling (mock data).

Speaks MCP over stdio: JSON-RPC 2.0, one JSON message per line, using only the
Python standard library. Requires Python 3.10 or newer (checked at start-up).

Methods: initialize, notifications/initialized, ping, tools/list, tools/call.
Data comes from mock-data/*.json; replace DataSource for a real MES/ERP.
Write tools (schedule_work_order, ...) are intentionally not exposed in v1.

Reuse: the JSON-RPC plumbing lives in McpServer; a sibling server only needs its
own SERVER_INFO-style dict, TOOLS table and data source, e.g.
    McpServer({"name": "x", "version": "0"}, MY_TOOLS).serve(my_ds)
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    sys.exit("manufacturing-scheduler requires Python 3.10+, found " + sys.version.split()[0])

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVER_NAME = "manufacturing-scheduler"  # Claude Code tool prefix: mcp__manufacturing-scheduler__
SERVER_VERSION = "0.3.0"
SERVER_INFO = {"name": SERVER_NAME, "version": SERVER_VERSION}
PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]  # newest first
DATA_DIR = Path(__file__).resolve().parent / "mock-data"
DATA_FILES = ("work_orders", "machine_loads")
BOTTLENECK_DEFAULT = 0.85  # a machine is a bottleneck when load_pct >= threshold (inclusive)
LIST_LIMIT_DEFAULT = 50    # rows returned when a list tool gets no `limit`
LIST_LIMIT_MAX = 200       # larger limits are rejected with JSON-RPC -32602


class ToolError(Exception):
    """A safe, short message that may be shown to the model."""


class UnknownTool(Exception):
    """tools/call named a tool this server does not have (JSON-RPC -32602)."""


class InvalidParams(Exception):
    """Arguments rejected at protocol level (JSON-RPC -32602)."""


class DataSource:
    """Reads mock-data/<name>.json. Missing or malformed files are errors."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.dir = data_dir

    def load(self, name: str) -> list[dict]:
        path = self.dir / f"{name}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"cannot load {path}: {exc}") from exc
        if not isinstance(data, list):
            raise RuntimeError(f"{path} must contain a JSON list")
        return data

    def check(self) -> None:
        for name in DATA_FILES:
            self.load(name)


# ─── Tools ───────────────────────────────────────────────────────────

def paginate(rows: list, a: dict) -> tuple[list, dict]:
    """Apply limit/offset (the schema already bounded both); return (page, paging info)."""
    limit, offset = a.get("limit", LIST_LIMIT_DEFAULT), a.get("offset", 0)
    page = rows[offset:offset + limit]
    return page, {"returned": len(page), "total_matched": len(rows), "limit": limit,
                  "offset": offset, "has_more": offset + len(page) < len(rows)}


def list_work_orders(ds: DataSource, a: dict) -> Any:
    wos = ds.load("work_orders")
    for key in ("status", "so_id", "customer"):
        if key in a:
            wos = [w for w in wos if w.get(key) == a[key]]
    page, info = paginate(wos, a)
    return {"work_orders": page, **info}


def get_work_order_status(ds: DataSource, a: dict) -> Any:
    for wo in ds.load("work_orders"):
        if wo.get("id") == a["wo_id"]:
            return wo
    raise ToolError(f"work order not found: {a['wo_id']}")


def get_machine_load(ds: DataSource, a: dict) -> Any:
    days = a.get("days_ahead", 7)
    for m in ds.load("machine_loads"):
        if m.get("machine") == a["machine"]:
            # Mock data only holds 7-day figures; scale hours linearly to the
            # requested window. load_pct is a ratio so it does not change.
            scale = days / 7
            return {
                "machine": m["machine"],
                "type": m.get("type"),
                "days_ahead": days,
                "available_hours": round(m["available_hours_7d"] * scale, 1),
                "scheduled_hours": round(m["scheduled_hours_7d"] * scale, 1),
                "load_pct": m["load_pct"],
                "status": m.get("status"),
                "next_available": m.get("next_available"),
                "basis": "linear scaling of 7-day mock figures",
            }
    raise ToolError(f"machine not found: {a['machine']}")


def find_bottlenecks(ds: DataSource, a: dict) -> Any:
    t = a.get("threshold", BOTTLENECK_DEFAULT)
    hot = sorted((m for m in ds.load("machine_loads") if m["load_pct"] >= t),
                 key=lambda m: m["load_pct"], reverse=True)  # worst first
    page, info = paginate(hot, a)
    return {"threshold": t, "bottlenecks": page, **info}


def get_capacity_summary(ds: DataSource, a: dict) -> Any:
    loads = ds.load("machine_loads")
    avg = sum(m["load_pct"] for m in loads) / len(loads) if loads else 0
    return {
        "total_machines": len(loads),
        "avg_load_pct": round(avg, 3),
        "bottleneck_count": sum(1 for m in loads if m["load_pct"] >= BOTTLENECK_DEFAULT),
        "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _schema(props: dict, required: tuple = ()) -> dict:
    s: dict = {"type": "object", "properties": props, "additionalProperties": False}
    if required:
        s["required"] = list(required)
    return s


# Shared paging arguments of every list-style tool. `limit` above the maximum is
# a protocol-level error (-32602) rather than a tool result (x-protocol-error).
PAGING = {
    "limit": {"type": "integer", "minimum": 1, "maximum": LIST_LIMIT_MAX,
              "default": LIST_LIMIT_DEFAULT, "x-protocol-error": True,
              "description": f"Max rows to return (default {LIST_LIMIT_DEFAULT}, "
                             f"max {LIST_LIMIT_MAX}; larger values are rejected)."},
    "offset": {"type": "integer", "minimum": 0, "default": 0,
               "description": "Rows to skip; use with has_more to read the next page."},
}

TOOLS: dict[str, dict] = {
    "list_work_orders": {
        "fn": list_work_orders,
        "description": "List work orders, optionally filtered by status "
                       "(e.g. scheduled, in_production, waiting, blocked), sales "
                       "order (so_id) or customer. Paged: returns at most `limit` "
                       f"rows (default {LIST_LIMIT_DEFAULT}, max {LIST_LIMIT_MAX}) plus "
                       "has_more; pass offset to read the next page.",
        "inputSchema": _schema({
            "status": {"type": "string", "minLength": 1},
            "so_id": {"type": "string", "minLength": 1},
            "customer": {"type": "string", "minLength": 1},
            **PAGING}),
    },
    "get_work_order_status": {
        "fn": get_work_order_status,
        "description": "Get the detail of a single work order by ID.",
        "inputSchema": _schema({"wo_id": {"type": "string", "minLength": 1}}, ("wo_id",)),
    },
    "get_machine_load": {
        "fn": get_machine_load,
        "description": "Get the load forecast of one machine for the next N days. "
                       "load_pct is a ratio from 0 to 1 (0.85 = 85%).",
        "inputSchema": _schema({
            "machine": {"type": "string", "minLength": 1},
            "days_ahead": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7},
        }, ("machine",)),
    },
    "find_bottlenecks": {
        "fn": find_bottlenecks,
        "description": "List machines whose load_pct is at or above a threshold "
                       f"(0-1, inclusive: load_pct >= threshold; default {BOTTLENECK_DEFAULT}), "
                       "highest load first. Paged like list_work_orders "
                       f"(default limit {LIST_LIMIT_DEFAULT}, max {LIST_LIMIT_MAX}, has_more).",
        "inputSchema": _schema({
            "threshold": {"type": "number", "minimum": 0, "maximum": 1,
                          "default": BOTTLENECK_DEFAULT},
            **PAGING}),
    },
    "get_capacity_summary": {
        "fn": get_capacity_summary,
        "description": "Plant-wide capacity summary (machine count, average load_pct, "
                       f"bottleneck_count at load_pct >= {BOTTLENECK_DEFAULT}).",
        "inputSchema": _schema({}),
    },
}


# ─── Input validation (the subset of JSON Schema used above) ─────────

class _Invalid(Exception):
    def __init__(self, message: str, protocol: bool = False):
        super().__init__(message)
        self.protocol = protocol  # True: report as JSON-RPC -32602, not a tool result


def _type_ok(kind: str, value: Any) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) \
            and math.isfinite(value)
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, dict)
    if kind == "null":
        return value is None
    # A schema using a type we cannot check is a bug in this server, not bad input.
    raise ValueError(f"unsupported schema type: {kind!r}")


def _check(value: Any, spec: dict, label: str, protocol: bool = False) -> None:
    kind = spec["type"]
    if not _type_ok(kind, value):
        raise _Invalid(f"argument '{label}' must be of type {kind}")
    protocol = protocol or bool(spec.get("x-protocol-error"))
    if kind == "string" and len(value) < spec.get("minLength", 0):
        raise _Invalid(f"argument '{label}' must not be empty")
    if kind in ("integer", "number"):
        lo, hi = spec.get("minimum"), spec.get("maximum")
        if (lo is not None and value < lo) or (hi is not None and value > hi):
            bounds = (f"between {lo} and {hi}" if lo is not None and hi is not None
                      else f"at least {lo}" if lo is not None else f"at most {hi}")
            # x-protocol-error only escalates a value above the maximum
            raise _Invalid(f"argument '{label}' must be {bounds}",
                           protocol and hi is not None and value > hi)
    if kind == "array":
        if len(value) < spec.get("minItems", 0):
            raise _Invalid(f"argument '{label}' must have at least {spec['minItems']} items")
        if "maxItems" in spec and len(value) > spec["maxItems"]:
            raise _Invalid(f"argument '{label}' must have at most {spec['maxItems']} items")
        if "items" in spec:
            for i, item in enumerate(value):
                _check(item, spec["items"], f"{label}[{i}]")
    if kind == "object" and "properties" in spec:
        _check_object(value, spec, label)


def _check_object(value: dict, schema: dict, label: str | None) -> None:
    where = f" in '{label}'" if label else ""
    props = schema["properties"]
    for key in schema.get("required", []):
        if key not in value:
            raise _Invalid(f"missing required argument: {key}{where}")
    for key, item in value.items():
        if key not in props:
            if schema.get("additionalProperties", True) is False:
                raise _Invalid(f"unknown argument: {key}{where}")
            continue
        _check(item, props[key], f"{label}.{key}" if label else key)


def check_args(args: Any, schema: dict) -> None:
    """Raise _Invalid when args do not satisfy the schema (top level: an object)."""
    if not isinstance(args, dict):
        raise _Invalid("arguments must be an object")
    _check_object(args, schema, None)


def validate(args: Any, schema: dict) -> str | None:
    """Return a short error message, or None when args satisfy the schema.

    Supports string, integer, number, boolean, array (items, minItems, maxItems),
    object (properties, required, additionalProperties) and null. A schema that
    uses any other type raises ValueError: that is a server bug and surfaces as
    JSON-RPC -32603, never as a bad-argument or unknown-tool answer.
    """
    try:
        check_args(args, schema)
    except _Invalid as exc:
        return str(exc)
    return None


# ─── JSON-RPC / MCP plumbing ─────────────────────────────────────────

def ok(rid: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def err(rid: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def tool_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


class McpServer:
    """JSON-RPC 2.0 / MCP stdio plumbing, independent of any particular tool set.

    `tools` maps name -> {"fn": f(ds, args), "description": str, "inputSchema": dict}.
    """

    def __init__(self, info: dict, tools: dict[str, dict],
                 protocol_versions: list[str] | None = None):
        self.info = info
        self.tools = tools
        self.protocol_versions = protocol_versions or PROTOCOL_VERSIONS

    def call_tool(self, ds: Any, params: Any) -> dict:
        name = params.get("name") if isinstance(params, dict) else None
        if not isinstance(name, str) or name not in self.tools:
            raise UnknownTool(name)
        tool = self.tools[name]
        args = params.get("arguments")
        args = {} if args is None else args
        try:
            check_args(args, tool["inputSchema"])
        except _Invalid as exc:
            if exc.protocol:
                raise InvalidParams(str(exc)) from None
            return tool_result(f"invalid arguments: {exc}", True)
        try:
            result = tool["fn"](ds, args)
        except ToolError as exc:
            return tool_result(str(exc), True)
        except Exception as exc:  # never leak raw exception text to the client
            print(f"{self.info['name']}: {name} failed: {exc!r}", file=sys.stderr)
            return tool_result("internal error: data source unavailable or malformed", True)
        return tool_result(json.dumps(result, ensure_ascii=False, indent=2))

    def handle(self, msg: Any, ds: Any) -> dict | None:
        """Return a response dict, or None for notifications."""
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" \
                or not isinstance(msg.get("method"), str):
            return err(msg.get("id") if isinstance(msg, dict) else None, -32600, "invalid request")
        method, rid, params = msg["method"], msg.get("id"), msg.get("params")
        if "id" not in msg:  # notification: never answered
            return None
        try:
            if method == "initialize":
                asked = params.get("protocolVersion") if isinstance(params, dict) else None
                version = asked if asked in self.protocol_versions else self.protocol_versions[0]
                return ok(rid, {"protocolVersion": version, "capabilities": {"tools": {}},
                                "serverInfo": self.info})
            if method == "ping":
                return ok(rid, {})
            if method == "tools/list":
                return ok(rid, {"tools": [
                    {"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
                    for n, t in self.tools.items()]})
            if method == "tools/call":
                return ok(rid, self.call_tool(ds, params))
            return err(rid, -32601, f"method not found: {method}")
        except UnknownTool as exc:
            return err(rid, -32602, f"unknown tool: {exc}")
        except InvalidParams as exc:
            return err(rid, -32602, f"invalid params: {exc}")
        except Exception as exc:  # a bug in this server, e.g. an unsupported schema type
            print(f"{self.info['name']}: {method} crashed: {exc!r}", file=sys.stderr)
            return err(rid, -32603, f"internal error: {type(exc).__name__}")

    def serve(self, ds: Any, stdin: Any = None, stdout: Any = None) -> int:
        """Answer one JSON message per line until stdin closes."""
        stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
        for line in stdin:
            if not line.strip():
                continue
            try:
                reply = self.handle(json.loads(line), ds)
            except ValueError:
                reply = err(None, -32700, "parse error")
            if reply is not None:
                stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                stdout.flush()
        return 0


def build_server() -> McpServer:
    """Factory for this server's tool set."""
    return McpServer(SERVER_INFO, TOOLS)


def handle(msg: Any, ds: DataSource) -> dict | None:
    return build_server().handle(msg, ds)


def main() -> int:
    ds = DataSource()
    try:
        ds.check()
    except RuntimeError as exc:
        print(f"{SERVER_NAME}: {exc}", file=sys.stderr)
        return 1
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    return build_server().serve(ds)


if __name__ == "__main__":
    sys.exit(main())
