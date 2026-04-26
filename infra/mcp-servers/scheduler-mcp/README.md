# scheduler-mcp

> Reference MCP server for production scheduling — exposes capacity, work-order state, machine load to AI agents.

Inspired by the architecture in 圖二 of the original manufacturing.md design (the `manufacturing-main` orchestrator pattern).

---

## What this MCP server provides

Read tools (查詢):

| Tool                    | 用途                        |
| ----------------------- | --------------------------- |
| `list_work_orders`      | 列出所有 / 過濾條件下的工單 |
| `get_work_order_status` | 單張工單目前狀態與進度      |
| `get_machine_load`      | 機台目前負載（未來 N 天）   |
| `get_capacity_summary`  | 整廠 / 部門產能總覽         |
| `find_bottlenecks`      | 識別瓶頸機台                |

Write tools (異動):

| Tool                  | 用途                  | 權限                    |
| --------------------- | --------------------- | ----------------------- |
| `schedule_work_order` | 排定工單到機台 + 時段 | production-planner only |
| `update_progress`     | 回報加工進度          | operator                |
| `flag_exception`      | 標記異常              | any agent               |
| `close_work_order`    | 完工關單              | quality-inspector       |

---

## v1 stub 範圍

`server.py` 只實作 read tools 的 stub 回應（mock data 從 `mock-data/` 讀），write tools 回 501 Not Implemented。

正式接生產環境時：

1. 把 `data_source` 從 `MockDataSource` 換成 `MesDataSource` / `ErpDataSource`
2. 補實 write tools
3. 加 auth（每個 tool 要求對應 agent 角色）
4. CSV：先在開發環境驗證，再上 production

---

## 啟動

```bash
cd infra/mcp-servers/scheduler-mcp
pip install -r requirements.txt
python server.py
# 預設 listen on stdio (Claude Code MCP 標準)
```

加到 Claude Code MCP 設定（`~/.claude/settings.json`）：

```json
{
  "mcpServers": {
    "manufacturing-scheduler": {
      "command": "python",
      "args": [
        "/path/to/manufacturing-skill/infra/mcp-servers/scheduler-mcp/server.py"
      ]
    }
  }
}
```

---

## 對 agent 的用法

agents 透過 MCP 取得即時生產狀態：

```python
# 範例：production-planner 排程時
load = mcp.call("get_machine_load", {"machine": "CNC#3", "days_ahead": 7})
if load["pct"] > 0.85:
    bottleneck = mcp.call("find_bottlenecks", {"window_days": 7})
    # 提建議：外包 / 改機台 / 加班
```

詳見 `server.py` 與 `tools/*.py`。
