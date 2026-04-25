---
name: inspect
description: 啟動檢驗流程 — IQC / IPQC / FQC / OQC 任一階段
allowed-tools: [Read, Grep, Glob, Bash]
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

## 使用範例

```
/inspect IQC PO-2026-0421
/inspect IPQC W2026042100123
/inspect FQC W2026042100123
/inspect OQC SO-2026-0421
```

詳細邏輯：`core/skills/05-檢驗.md`
