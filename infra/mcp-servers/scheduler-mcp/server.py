"""
scheduler-mcp — Reference MCP server for manufacturing production scheduling.

v1 STUB: returns mock data only. Replace MockDataSource with real ERP/MES integration.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

MOCK_DATA_DIR = Path(__file__).parent / "mock-data"


class MockDataSource:
    """Stub data source — reads from JSON files in mock-data/."""

    def __init__(self, data_dir: Path = MOCK_DATA_DIR):
        self.data_dir = data_dir

    def _load(self, name: str) -> Any:
        path = self.data_dir / f"{name}.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def list_work_orders(self, status: str | None = None) -> list[dict]:
        wos = self._load("work_orders")
        if status:
            wos = [w for w in wos if w["status"] == status]
        return wos

    def get_work_order(self, wo_id: str) -> dict | None:
        for wo in self._load("work_orders"):
            if wo["id"] == wo_id:
                return wo
        return None

    def get_machine_load(self, machine: str, days_ahead: int = 7) -> dict:
        loads = self._load("machine_loads")
        match = next((m for m in loads if m["machine"] == machine), None)
        if not match:
            return {"machine": machine, "error": "machine not found"}
        return match

    def find_bottlenecks(self, threshold: float = 0.85) -> list[dict]:
        return [m for m in self._load("machine_loads") if m["load_pct"] >= threshold]

    def get_capacity_summary(self) -> dict:
        loads = self._load("machine_loads")
        if not loads:
            return {"total_machines": 0, "avg_load_pct": 0, "bottleneck_count": 0}
        avg = sum(m["load_pct"] for m in loads) / len(loads)
        return {
            "total_machines": len(loads),
            "avg_load_pct": round(avg, 3),
            "bottleneck_count": sum(1 for m in loads if m["load_pct"] >= 0.85),
            "as_of": datetime.utcnow().isoformat() + "Z",
        }


# ─── MCP protocol shim (minimal) ─────────────────────────────────────
# This is a stub. Production should use the official `mcp` Python SDK:
#   pip install mcp
# and use the proper Server class.

TOOLS = {
    "list_work_orders": {
        "description": "List work orders, optionally filtered by status",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string"}},
        },
    },
    "get_work_order_status": {
        "description": "Get detail of a single work order by ID",
        "inputSchema": {
            "type": "object",
            "properties": {"wo_id": {"type": "string"}},
            "required": ["wo_id"],
        },
    },
    "get_machine_load": {
        "description": "Get load forecast for a specific machine",
        "inputSchema": {
            "type": "object",
            "properties": {
                "machine": {"type": "string"},
                "days_ahead": {"type": "integer", "default": 7},
            },
            "required": ["machine"],
        },
    },
    "find_bottlenecks": {
        "description": "Identify machines with load >= threshold (default 0.85)",
        "inputSchema": {
            "type": "object",
            "properties": {"threshold": {"type": "number", "default": 0.85}},
        },
    },
    "get_capacity_summary": {
        "description": "Plant-wide capacity summary",
        "inputSchema": {"type": "object", "properties": {}},
    },
}

WRITE_TOOLS = {
    "schedule_work_order",
    "update_progress",
    "flag_exception",
    "close_work_order",
}


def handle_call(tool: str, args: dict, ds: MockDataSource) -> dict:
    if tool in WRITE_TOOLS:
        return {"error": "501 Not Implemented in v1 stub", "tool": tool}

    if tool == "list_work_orders":
        return {"work_orders": ds.list_work_orders(args.get("status"))}
    if tool == "get_work_order_status":
        wo = ds.get_work_order(args["wo_id"])
        return wo or {"error": "not found"}
    if tool == "get_machine_load":
        return ds.get_machine_load(args["machine"], args.get("days_ahead", 7))
    if tool == "find_bottlenecks":
        return {"bottlenecks": ds.find_bottlenecks(args.get("threshold", 0.85))}
    if tool == "get_capacity_summary":
        return ds.get_capacity_summary()

    return {"error": f"unknown tool: {tool}"}


def main():
    """
    Minimal stdio loop for demo.
    Production MUST use official mcp SDK for proper protocol handling.
    """
    ds = MockDataSource()
    print("scheduler-mcp v0.1 stub — listening on stdin (line-delimited JSON)", file=sys.stderr)
    print(f"available tools: {', '.join(TOOLS.keys())}", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            tool = req.get("tool")
            args = req.get("args", {})
            result = handle_call(tool, args, ds)
            print(json.dumps(result, ensure_ascii=False))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
