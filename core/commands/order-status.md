---
name: order-status
description: 查詢訂單目前狀態 — 從接單、排程、生產、檢驗到出貨各階段
allowed-tools: [Read, Grep, Glob, Bash, mcp__manufacturing-scheduler__list_work_orders, mcp__manufacturing-scheduler__get_work_order_status, mcp__manufacturing-scheduler__get_machine_load]
argument-hint: "[訂單號 或 客戶名稱 或 工單號]"
---

# /order-status — 訂單狀態查詢

呼叫 **sales-coordinator** agent（`core/agents/sales-coordinator.md`）查詢訂單目前所在階段。

## 流程

1. 解析使用者給的識別資訊（訂單號 / PO / 客戶名 / 工單號）
2. 透過 `infra/mcp-servers/erp-connector` 查 ERP 訂單 master
3. 透過 MCP server `manufacturing-scheduler`（`infra/mcp-servers/scheduler-mcp`）查生產排程：
   - 給訂單號 → `list_work_orders`（`so_id`）；給客戶名 → `list_work_orders`（`customer`）；給工單號 → `get_work_order_status`（`wo_id`）
   - `list_work_orders` 預設回 50 筆、上限 200；`has_more` 為 true 時用 `offset` 續查
   - 工單落在負載高的機台時，用 `get_machine_load` 看該機 `load_pct`（0–1，≥ 0.85 視為瓶頸）作為延遲風險依據
4. 整合 6 段流程的所在位置：報價 → 接單 → 排程 → 生產 → 檢驗 → 出貨
5. 如果有延遲風險，主動標示並建議下一步

## 使用範例

```
/order-status SO-2026-0421
/order-status 客戶A
/order-status 工單W2026042100123
```

## 期待輸出

```
訂單 SO-2026-0421（客戶A · 不鏽鋼支架 × 100）
目前階段：[4. 生產中] 進度 60% (60/100 件)
預計檢驗：2026-04-28
預計出貨：2026-04-30
⚠️ 風險：刀具壽命將於 80 件達上限，已通知刀具部
```

詳細邏輯：`core/skills/02-接單.md`、`core/skills/03-排程.md`、`core/skills/04-生產.md`
