---
name: quote
description: 啟動報價流程 — 從 RFQ / 圖紙 / 客戶口頭詢價產生結構化報價單
allowed-tools: [Read, Grep, Glob, Bash]
argument-hint: "[圖紙路徑或 RFQ 檔案] [選用：客戶名稱]"
---

# /quote — 報價

請依照以下流程處理使用者的報價請求：

1. **召喚 quote-specialist agent**（`core/agents/quote-specialist.md`）
2. 載入報價 skill：`core/skills/01-報價.md`
3. 觸發 `pre-quote` hook（`core/hooks/pre-quote.md`）— 圖紙完整度檢查
4. 如果偵測到是特定 vertical 的件（CNC / 射出 / PCB ...），dispatch 給對應 profile 的專精 agent 協作
5. 產出格式參照 `examples/sample-quote-output.md`

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
- 利潤率與報價金額
- 預估交期
- 假設與備註（不確定的地方標明）

詳細流程：`core/skills/01-報價.md`
