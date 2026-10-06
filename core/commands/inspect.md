---
name: inspect
description: 啟動檢驗流程 — IQC / IPQC / FQC / OQC 任一階段
allowed-tools: [Read, Grep, Glob]
argument-hint: "[檢驗階段] [工單號 或 進料單號]"
---

# /inspect — 檢驗

呼叫 **quality-inspector** agent（`core/agents/quality-inspector.md`）執行對應檢驗階段。

## 支援的檢驗階段

| 階段   | 全名                       | 時機       |
| ------ | -------------------------- | ---------- |
| `IQC`  | Incoming Quality Control   | 進料時     |
| `IPQC` | In-Process Quality Control | 製程中抽檢 |
| `FQC`  | Final Quality Control      | 完工後     |
| `OQC`  | Outgoing Quality Control   | 出貨前     |

## 流程

1. 載入對應階段的檢驗 checklist（從 `core/skills/05-檢驗.md` 取得）
2. 如果工件來自特定 vertical，疊加 profile 的檢驗規範（如 CNC 的 IATF 16949）
3. 引導使用者填寫關鍵尺寸 / 外觀 / 性能項目
4. 觸發 `pre-ship` hook 如果通過 OQC

## 分類與分工

| 項目 | 內容 |
| ---- | ---- |
| 今天誰做什麼（today） | 檢驗員自己量測、填紀錄、查 AQL 表定樣本數、對照規範與 SPC 規則，判定合格與否，並寫不良的根因與處置。 |
| 導入後人仍親手做（humanStillDoes） | **親手量測並填值；先寫下你的判定與根因假說，再看 AI 的對照**（AQL 對應列、規範值、SPC 規則、歷史相似不良）；簽名確認檢驗紀錄。 |
| 分類 | **強化既有優勢**：AI 帶出對照資料、算式與檢查清單，量測與判定仍是你的。由 AI 直接寫「判定」或「根因」，是**外包既有工作**，**預設不啟用**。 |

輸出是「參考」，不是判定。簽這份檢驗紀錄的人才是負責人，要放行或攔下都由你決定。

## 使用範例

```
/inspect IQC PO-2026-0421
/inspect IPQC W2026042100123
/inspect FQC W2026042100123
/inspect OQC SO-2026-0421
```

詳細邏輯：`core/skills/05-檢驗.md`
