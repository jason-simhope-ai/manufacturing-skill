#!/usr/bin/env python3
"""scheduler-mcp - read-only MCP server for production scheduling (mock data).

Speaks MCP over stdio: JSON-RPC 2.0, one JSON message per line, using only the
Python standard library. Requires Python 3.10 or newer (checked at start-up).

Methods: initialize, notifications/initialized, ping, tools/list, tools/call.
Data comes from mock-data/*.json; replace DataSource for a real MES/ERP.
Write tools (schedule_work_order, ...) are intentionally not exposed in v1.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    sys.exit("scheduler-mcp requires Python 3.10+, found " + sys.version.split()[0])

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVER_INFO = {"name": "scheduler-mcp", "version": "0.2.0"}
PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]  # newest first
DATA_DIR = Path(__file__).resolve().parent / "mock-data"
DATA_FILES = ("work_orders", "machine_loads")
BOTTLENECK_DEFAULT = 0.85


class ToolError(Exception):
    """A safe, short message that may be shown to the model."""


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

def list_work_orders(ds: DataSource, a: dict) -> Any:
    wos = ds.load("work_orders")
    if "status" in a:
        wos = [w for w in wos if w.get("status") == a["status"]]
    return {"work_orders": wos}


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
    return {"threshold": t,
            "bottlenecks": [m for m in ds.load("machine_loads") if m["load_pct"] >= t]}


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


TOOLS: dict[str, dict] = {
    "list_work_orders": {
        "fn": list_work_orders,
        "description": "List work orders, optionally filtered by status "
                       "(e.g. scheduled, in_production, waiting, blocked).",
        "inputSchema": _schema({"status": {"type": "string", "minLength": 1}}),
    },
    "get_work_order_status": {
        "fn": get_work_order_status,
        "description": "Get the detail of a single work order by ID.",
        "inputSchema": _schema({"wo_id": {"type": "string", "minLength": 1}}, ("wo_id",)),
    },
    "get_machine_load": {
        "fn": get_machine_load,
        "description": "Get the load forecast of one machine for the next N days.",
        "inputSchema": _schema({
            "machine": {"type": "string", "minLength": 1},
            "days_ahead": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7},
        }, ("machine",)),
    },
    "find_bottlenecks": {
        "fn": find_bottlenecks,
        "description": "List machines whose load_pct is at or above a threshold (0-1).",
        "inputSchema": _schema({"threshold": {
            "type": "number", "minimum": 0, "maximum": 1, "default": BOTTLENECK_DEFAULT}}),
    },
    "get_capacity_summary": {
        "fn": get_capacity_summary,
        "description": "Plant-wide capacity summary.",
        "inputSchema": _schema({}),
    },
}


# ─── Input validation (the subset of JSON Schema used above) ─────────

def validate(args: Any, schema: dict) -> str | None:
    """Return a short error message, or None when args satisfy the schema."""
    if not isinstance(args, dict):
        return "arguments must be an object"
    props = schema["properties"]
    for key in schema.get("required", []):
        if key not in args:
            return f"missing required argument: {key}"
    for key, value in args.items():
        if key not in props:
            return f"unknown argument: {key}"
        spec = props[key]
        kind = spec["type"]
        is_num = isinstance(value, (int, float)) and not isinstance(value, bool)
        ok = {"string": isinstance(value, str),
              "integer": isinstance(value, int) and not isinstance(value, bool),
              "number": is_num}[kind]
        if not ok:
            return f"argument '{key}' must be of type {kind}"
        if kind == "string" and len(value) < spec.get("minLength", 0):
            return f"argument '{key}' must not be empty"
        if kind != "string" and not (spec.get("minimum", value) <= value <= spec.get("maximum", value)):
            return f"argument '{key}' must be between {spec['minimum']} and {spec['maximum']}"
    return None


# ─── JSON-RPC / MCP plumbing ─────────────────────────────────────────

def ok(rid: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def err(rid: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def tool_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def call_tool(ds: DataSource, params: Any) -> dict:
    name = params.get("name") if isinstance(params, dict) else None
    if name not in TOOLS:
        raise KeyError(name)
    args = params.get("arguments")
    args = {} if args is None else args
    problem = validate(args, TOOLS[name]["inputSchema"])
    if problem:
        return tool_result(f"invalid arguments: {problem}", True)
    try:
        result = TOOLS[name]["fn"](ds, args)
    except ToolError as exc:
        return tool_result(str(exc), True)
    except Exception as exc:  # never leak raw exception text to the client
        print(f"scheduler-mcp: {name} failed: {exc!r}", file=sys.stderr)
        return tool_result("internal error: data source unavailable or malformed", True)
    return tool_result(json.dumps(result, ensure_ascii=False, indent=2))


def handle(msg: Any, ds: DataSource) -> dict | None:
    """Return a response dict, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return err(msg.get("id") if isinstance(msg, dict) else None, -32600, "invalid request")
    method, rid, params = msg["method"], msg.get("id"), msg.get("params")
    if "id" not in msg:  # notification: never answered
        return None
    if method == "initialize":
        asked = params.get("protocolVersion") if isinstance(params, dict) else None
        version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return ok(rid, {"protocolVersion": version, "capabilities": {"tools": {}},
                        "serverInfo": SERVER_INFO})
    if method == "ping":
        return ok(rid, {})
    if method == "tools/list":
        return ok(rid, {"tools": [
            {"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
            for n, t in TOOLS.items()]})
    if method == "tools/call":
        try:
            return ok(rid, call_tool(ds, params))
        except KeyError:
            return err(rid, -32602, "unknown tool")
    return err(rid, -32601, f"method not found: {method}")


def main() -> int:
    ds = DataSource()
    try:
        ds.check()
    except RuntimeError as exc:
        print(f"scheduler-mcp: {exc}", file=sys.stderr)
        return 1
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line), ds)
        except ValueError:
            reply = err(None, -32700, "parse error")
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
