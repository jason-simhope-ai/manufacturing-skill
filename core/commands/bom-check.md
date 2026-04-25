---
name: bom-check
description: 解析 BOM 並檢查完整性、單位一致性、庫存可用性、缺料風險
allowed-tools: [Read, Grep, Glob, Bash]
argument-hint: "[BOM 檔路徑：xlsx/csv/pdf]"
---

# /bom-check — BOM 檢查

呼叫 **inventory-manager** agent（`core/agents/inventory-manager.md`）做 BOM 健檢。

## 流程

1. 解析 BOM 檔（支援 xlsx / csv / pdf）
2. 檢查欄位完整性：料號、品名、規格、用量、單位、供應商、Lead time
3. 對照標準件庫（如有）找出非標準件需要外購
4. 透過 ERP MCP 查目前庫存與在途
5. 計算缺料數、預估缺料日期、建議下單時間

## 使用範例

```
/bom-check @工單W2026042100123/BOM.xlsx
/bom-check @客戶B-專案/BOM-rev3.csv
```

## 期待輸出

```
BOM 檢查結果（共 47 項）
✅ 41 項庫存充足
⚠️ 4 項缺料，建議今日下單：
  - SUS304-φ20×1000 缺 30 支（Lead time 7 天）
  - M6×20 內六角螺絲 缺 200 顆（Lead time 3 天）
  ...
❌ 2 項規格不明確，需澄清：
  - 「特殊塗層」未指定規範
  - 「鍍層厚度」未指定範圍
```

詳細流程：`core/skills/bom-management.md`
