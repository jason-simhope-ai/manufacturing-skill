---
name: order-status
description: 查詢訂單目前狀態 — 從接單、排程、生產、檢驗到出貨各階段
allowed-tools: [Read, Grep, Glob, Bash, mcp__manufacturing-scheduler__list_work_orders, mcp__manufacturing-scheduler__get_work_order_status, mcp__manufacturing-scheduler__get_machine_load]
argument-hint: "[訂單號 或 客戶名稱 或 工單號]"
---

# /order-status — 訂單狀態查詢

> **注意：沒有 MCP 連線時，輸出是模擬資料。**
> 若 `erp-connector` / `manufacturing-scheduler` 沒有接上真實系統，本指令只會使用
> `infra/mcp-servers/scheduler-mcp/mock-data/` 內的 mock data。此時回覆**必須**在開頭與每個數字區塊標示
> 「模擬資料」，不得當作真實訂單 / 機台狀態呈現，也不得改用 `git log` 或其他推測方式補齊狀態。
> 沒有任何資料來源時，直接回答「無法取得資料」。

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
6. 若資料來自 mock data（無 MCP 連線），在輸出標示「模擬資料」

## 分類與分工

| 項目 | 內容 |
| ---- | ---- |
| 今天誰做什麼（today） | 業助自己打電話問生管、倉庫，或在 ERP 多層選單裡翻訂單，再整理成各階段進度，並決定怎麼回客戶。 |
| 導入後人仍親手做（humanStillDoes） | **先寫下你打算怎麼回客戶（交期與措辭），再看 AI 的狀態整理對照**；承諾交期前先跟生管確認；親自回覆客戶。 |
| 分類 | **強化既有優勢**：AI 跨系統彙整各階段所在位置與延遲風險，你仍是答覆客戶的人。AI 代寫整則回覆給客戶照貼，是**外包既有工作**，**預設不啟用**；預設只給「可引用的事實要點」，回覆由你寫。 |

輸出是「參考」，不是對客戶的承諾。簽發、寄出這則狀態回覆的人才是負責人。

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
