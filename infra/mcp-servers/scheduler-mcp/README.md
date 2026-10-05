# scheduler-mcp

> Reference MCP server for production scheduling — exposes work-order state, machine load and capacity to AI agents.

Inspired by the architecture in 圖二 of the original manufacturing.md design (the `manufacturing-main` orchestrator pattern).

A real MCP server: JSON-RPC 2.0 over stdio (one JSON message per line), implemented with the **Python standard library only** (**Python 3.10+**, no `pip install` needed). Data is read from `mock-data/*.json`; the server refuses to start if those files are missing or malformed.

---

## Server name and tool names

The server is called **`manufacturing-scheduler`** everywhere: the `serverInfo.name` it reports, the name you give `claude mcp add`, and the prefix of every tool in Claude Code (`mcp__manufacturing-scheduler__<tool>`). The directory is still `scheduler-mcp/`. If you register it under another name, the agent/command allow-lists in `core/` (`production-planner`, `sales-coordinator`, `/order-status`) will not match and the tools will be unavailable to them.

## Tools (all read-only)

| Tool                    | Arguments                                                                                                         | 用途                                                                          |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `list_work_orders`      | `status?`, `so_id?`, `customer?` (strings), `limit?` (integer 1-200, default 50), `offset?` (integer >= 0)        | 依狀態 / 訂單號 / 客戶過濾工單 → `{work_orders: [...], has_more, ...}`        |
| `get_work_order_status` | `wo_id` (string, required)                                                                                        | 單張工單目前狀態與進度                                                        |
| `get_machine_load`      | `machine` (string, required), `days_ahead?` (integer 1-90, default 7)                                             | 機台負載；工時依 `days_ahead` 由 7 日 mock 數字線性換算                       |
| `find_bottlenecks`      | `threshold?` (number 0-1, default 0.85), `limit?`, `offset?` (same rules as above)                                | `load_pct >= threshold`（含等於）的瓶頸機台，負載高的在前 → `{bottlenecks: [...], has_more, ...}` |
| `get_capacity_summary`  | none                                                                                                              | 整廠產能總覽（機台數、平均負載、瓶頸數、`as_of`）                             |

`load_pct` is a ratio from 0 to 1 (0.85 = 85%). A machine is a bottleneck when `load_pct >= threshold`, i.e. the comparison is inclusive; `get_capacity_summary` counts bottlenecks at the default 0.85.

### List limits (`list_work_orders`, `find_bottlenecks`)

- `limit` defaults to **50** and may be at most **200**. Every list response carries `returned`, `total_matched`, `limit`, `offset` and **`has_more`**.
- `has_more: true` means more rows exist: call again with `offset` = previous `offset` + `returned`. Do not draw conclusions from a first page that has `has_more: true`.
- A `limit` above 200 is rejected with JSON-RPC error **`-32602`** (`invalid params: argument 'limit' must be between 1 and 200`), not silently clamped. Other bad `limit`/`offset` values (0, negative, wrong type) come back as an `isError` tool result.

### Errors

- Arguments are validated against each tool's `inputSchema` (types `string`, `integer`, `number`, `boolean`, `array`, `object`, `null`; unknown arguments are rejected). Bad arguments, "not found" and data errors come back as a tool result with `isError: true` and a short message. Raw exception text is never returned.
- `-32602` is used for an unknown tool name and for `limit` above the maximum; `-32601` unknown method; `-32700` / `-32600` unparsable / invalid message.
- `-32603 internal error: <ExceptionClass>` means a bug in the server itself (for example a schema using a type the validator does not know). It is never reported as "unknown tool".

Write tools in the original design (`schedule_work_order`, `update_progress`, `flag_exception`, `close_work_order`) are **not exposed in v1**.

---

## Register in Claude Code

Use the **absolute** path to `server.py`. A relative path only works while Claude Code is started from the repo root; from any other folder the server fails to start (`CONNECTION_CLOSED`).

```bash
claude mcp add manufacturing-scheduler -- python3 /opt/manufacturing-skill/infra/mcp-servers/scheduler-mcp/server.py
```

Replace `/opt/manufacturing-skill` with where you cloned the repo. Options such as `-s` and `-e` go before the name; everything after `--` is the server command. Then run `/mcp` inside Claude Code (or `claude mcp list`) to confirm `manufacturing-scheduler` is connected. Check `claude mcp add --help` if your version differs.

### Scope: who sees the server

`claude mcp add` registers the server in the **local** scope unless you pass `-s` / `--scope`.

| Scope             | Flag         | Stored in                                          | Visible to                                         | Use when                                         |
| ----------------- | ------------ | -------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------ |
| `local` (default) | `-s local`   | `~/.claude.json`, under the current folder's entry | only you, **only in the folder you ran it from**   | trying it out; open Claude Code elsewhere and it is gone |
| `project`         | `-s project` | `.mcp.json` in the project root (commit it)        | everyone who opens that project; each member must approve it once | a team shares one setup (keep the path absolute or use an env var) |
| `user`            | `-s user`    | `~/.claude.json`, global                           | only you, in every folder                          | your own workstation, all projects               |

Example for a team: `claude mcp add -s project manufacturing-scheduler -- python3 /opt/manufacturing-skill/infra/mcp-servers/scheduler-mcp/server.py`. Installing the plugin does not register this server for you.

---

## Manual smoke test

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"find_bottlenecks","arguments":{"threshold":0.9}}}' \
  | python3 infra/mcp-servers/scheduler-mcp/server.py
```

Expected: two response lines (`id` 1 and 2); the notification gets none. Swap the last line for `"method":"tools/list"` to see every tool and its schema. Automated version: `python3 -m unittest discover -s tests/mcp -p 'test_*.py'` (or `python3 tests/mcp/test_scheduler_mcp.py`).

---

## 對 agent 的用法

Agents 透過 MCP 取得即時生產狀態，例如 production-planner 排程時：

1. `get_machine_load {"machine": "CNC#3", "days_ahead": 7}` → 看回傳的 `load_pct`（0-1）
2. 若 `load_pct >= 0.85`（含 85%），呼叫 `find_bottlenecks {"threshold": 0.85}`
3. 提建議：外包 / 改機台 / 加班

查工單：給訂單號用 `list_work_orders {"so_id": "SO-2026-0421"}`，給工單號用 `get_work_order_status {"wo_id": "..."}`；若回應 `has_more` 為 true，用 `offset` 續查。

---

## 接正式生產環境

1. 把 `DataSource` 換成 MES / ERP 實作（保持 tool 名稱與回傳欄位；list 工具要在資料來源端套用 `limit`，不要整批撈回再切）
2. 補實 write tools，並加 auth（每個 tool 要求對應 agent 角色：`schedule_work_order` → production-planner、`update_progress` → operator、`flag_exception` → any agent、`close_work_order` → quality-inspector）
3. 先在開發環境驗證，再上 production

### 重用在別的 server

JSON-RPC 管線在 `server.py` 的 `McpServer`：給它自己的 `serverInfo` 與工具表即可，不必複製：

```python
from server import McpServer
McpServer({"name": "my-erp-reader", "version": "0.1.0"}, MY_TOOLS).serve(my_data_source)
```

`MY_TOOLS` 的格式同 `TOOLS`（`fn`、`description`、`inputSchema`）。目前不拆共用套件。
