---
name: order-status
description: 查詢訂單目前狀態 — 從接單、排程、生產、檢驗到出貨各階段
allowed-tools: [Read, Grep, Glob, Bash]
argument-hint: "[訂單號 或 客戶名稱 或 工單號]"
---

# /order-status — 訂單狀態查詢

呼叫 **sales-coordinator** agent（`core/agents/sales-coordinator.md`）查詢訂單目前所在階段。

## 流程

1. 解析使用者給的識別資訊（訂單號 / PO / 客戶名 / 工單號）
2. 透過 `infra/mcp-servers/erp-connector` 查 ERP 訂單 master
3. 透過 `infra/mcp-servers/scheduler-mcp` 查生產排程
4. 整合 6 段流程的所在位置：報價 → 接單 → 排程 → 生產 → 檢驗 → 出貨
5. 如果有延遲風險，主動標示並建議下一步

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
