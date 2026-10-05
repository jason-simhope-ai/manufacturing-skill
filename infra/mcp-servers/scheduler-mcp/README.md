# scheduler-mcp

> Reference MCP server for production scheduling — exposes work-order state, machine load and capacity to AI agents.

Inspired by the architecture in 圖二 of the original manufacturing.md design (the `manufacturing-main` orchestrator pattern).

A real MCP server: JSON-RPC 2.0 over stdio (one JSON message per line), implemented with the **Python standard library only** (**Python 3.10+**, no `pip install` needed). Data is read from `mock-data/*.json`; the server refuses to start if those files are missing or malformed.

---

## Tools (all read-only)

| Tool                    | Arguments                                                                 | 用途                                                        |
| ----------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `list_work_orders`      | `status?` (string)                                                        | 列出所有 / 依狀態過濾的工單 → `{work_orders: [...]}`        |
| `get_work_order_status` | `wo_id` (string, required)                                                | 單張工單目前狀態與進度                                      |
| `get_machine_load`      | `machine` (string, required), `days_ahead?` (integer 1-90, default 7)     | 機台負載；工時依 `days_ahead` 由 7 日 mock 數字線性換算     |
| `find_bottlenecks`      | `threshold?` (number 0-1, default 0.85)                                   | `load_pct >= threshold` 的瓶頸機台 → `{bottlenecks: [...]}` |
| `get_capacity_summary`  | none                                                                      | 整廠產能總覽（機台數、平均負載、瓶頸數、`as_of`）           |

Arguments are validated against each tool's `inputSchema` (unknown arguments are rejected). Bad arguments, "not found" and data errors come back as a tool result with `isError: true` and a short message; an unknown tool name is a JSON-RPC error (`-32602`). Raw exception text is never returned.

Write tools in the original design (`schedule_work_order`, `update_progress`, `flag_exception`, `close_work_order`) are **not exposed in v1**.

---

## Register in Claude Code

From the repo root (the exact command and flags are defined by the Claude Code docs and may differ by version; check `claude mcp add --help`):

```bash
claude mcp add scheduler -- python3 infra/mcp-servers/scheduler-mcp/server.py
```

Use an absolute path to `server.py` if Claude Code is not started from the repo root. Then run `/mcp` inside Claude Code to confirm `scheduler` is connected.

---

## Manual smoke test

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"find_bottlenecks","arguments":{"threshold":0.9}}}' \
  | python3 infra/mcp-servers/scheduler-mcp/server.py
```

Expected: two response lines (`id` 1 and 2); the notification gets none. Swap the last line for `"method":"tools/list"` to see every tool and its schema. Automated version: `python3 tests/mcp/test_scheduler_mcp.py`.

---

## 對 agent 的用法

Agents 透過 MCP 取得即時生產狀態，例如 production-planner 排程時：

1. `get_machine_load {"machine": "CNC#3", "days_ahead": 7}` → 看回傳的 `load_pct`（0-1）
2. 若 `load_pct > 0.85`，呼叫 `find_bottlenecks {"threshold": 0.85}`
3. 提建議：外包 / 改機台 / 加班

---

## 接正式生產環境

1. 把 `DataSource` 換成 MES / ERP 實作（保持 tool 名稱與回傳欄位）
2. 補實 write tools，並加 auth（每個 tool 要求對應 agent 角色：`schedule_work_order` → production-planner、`update_progress` → operator、`flag_exception` → any agent、`close_work_order` → quality-inspector）
3. 先在開發環境驗證，再上 production
