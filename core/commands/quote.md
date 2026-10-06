---
name: quote
description: 啟動報價流程 — 從 RFQ / 圖紙 / 客戶口頭詢價產生結構化報價單
allowed-tools: [Read, Grep, Glob]
argument-hint: "[圖紙路徑或 RFQ 檔案] [選用：客戶名稱]"
---

# /quote — 報價

請依照以下流程處理使用者的報價請求：

1. **召喚 quote-specialist agent**（`core/agents/quote-specialist.md`）
2. 載入報價 skill：`core/skills/01-報價.md`
3. 觸發 `pre-quote` hook（`core/hooks/pre-quote.md`）— 圖紙完整度檢查
4. 如果偵測到是特定 vertical 的件（CNC / 射出 / PCB ...），dispatch 給對應 profile 的專精 agent 協作
5. 產出格式參照 `examples/sample-quote-output.md`

## 分類與分工

| 項目 | 內容 |
| ---- | ---- |
| 今天誰做什麼（today） | 報價人員或業助自己看圖紙、查材料單價與機台費率、估工時、組報價單，並決定利潤率與報價金額；漏看的條件常到客戶回問才發現。 |
| 導入後人仍親手做（humanStillDoes） | **先寫下你自己的估價與利潤判斷，再看 AI 的成本拆解對照**；逐項回應 `[需澄清]` 與假設；決定最後報價金額並簽核送出。 |
| 分類 | **強化既有優勢**：AI 提供成本拆解對照、圖紙漏項與工程矛盾清單，你的估價與決定仍由你做。若有人想讓 AI 直接組出整份報價單與金額供照送，那是**外包既有工作**，**預設不啟用**，需主管同意並逐項核對。 |

輸出是「參考」，不是報價。簽這張報價單的人才是負責人，AI 說過什麼不能當作理由。

## 使用範例

```
/quote @examples/sample-drawing/bracket.md
/quote @customer-rfq/客戶A-2026Q2.pdf 客戶A
/quote 「我們需要一批不鏽鋼304的支架，數量100個，公差±0.05mm」
```

## 期待輸出

結構化報價單，包含：

- 工件規格摘要
- 材料成本
- 加工成本（工時 × 機台費率）
- 工藝路線
- 利潤率與報價金額（參考值，供你與自己先寫下的估算對照）
- 預估交期
- 假設與備註（不確定的地方標明）

詳細流程：`core/skills/01-報價.md`
