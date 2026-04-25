---
name: bom-management
displayName: BOM 管理
description: BOM parse, completeness check, version control, where-used analysis, cost rollup
when_to_use: User invokes /bom-check, BOM revision occurs, or needs cost/inventory rollup
---

# BOM 管理 Skill

由 **inventory-manager** 主導。

---

## 兩種 BOM 結構

| 類型                          | 用途                     | 工具     |
| ----------------------------- | ------------------------ | -------- |
| **EBOM**（Engineering BOM）   | 設計階段，工程師畫的     | PLM 系統 |
| **MBOM**（Manufacturing BOM） | 生產階段，加上製程相關料 | ERP 系統 |

EBOM → MBOM 的轉換通常加：

- 製程消耗品（油、氣、塗料）
- 包材
- 治具消耗
- 損耗備量

---

## Process（4 步）

### 1. 解析 BOM 檔

支援格式：xlsx / csv / pdf / 直接從 ERP 取

每行必含欄位：

- Level（層級，如 0/1/2 表示 BOM 樹深度）
- 料號
- 品名
- 規格 / 描述
- 單位
- 用量
- 損耗率（%）
- 供應商（外購件）
- Lead time

### 2. 完整性檢查

| 檢查項                         | 處理                                  |
| ------------------------------ | ------------------------------------- |
| 缺料號                         | 標 `❌ 未建檔` → 通知工程開料號       |
| 規格不明（如「特殊塗層」）     | 標 `❌ 規格不明` → 通知工程或業助澄清 |
| 用量為 0 或負數                | 標 `❌ 異常用量` → 提報               |
| 單位不一致（同料用 PCS 和 KG） | 標 `⚠️ 單位混用` → 標準化             |
| 替代料（substitute）未列       | 提示工程是否補充                      |

### 3. 庫存對照

對 ERP 查每料：

- 即時庫存
- 在途
- 安全庫存
- 近 6 個月用量

計算缺口：

```
本單需求 = Σ (用量 × (1 + 損耗率))
缺口 = max(0, 本單需求 - 庫存 - 在途)
```

### 4. 採購建議

對缺口項：

- 計算 EOQ（經濟訂購量）
- 對照 ABC 分類決定採購頻率
- 考慮 lead time → 算「最晚下單日」
- 排優先級（缺得越多、lead time 越長越優先）

---

## Cost Rollup

從 BOM 樹葉節點算上來：

```
Level N 節點成本 = Σ (Level N+1 子件成本 × 用量)
                 + 該節點的加工成本
```

最後得到完整工件的材料成本（不含加工）。

---

## Checklist

- [ ] 所有層級的料都有料號
- [ ] 所有料都建檔在 ERP
- [ ] 用量 + 損耗率 都填了
- [ ] 缺料項都列出採購建議
- [ ] Cost rollup 結果可追溯

---

## Anti-patterns

- ❌ 用 EBOM 直接做生產採購 → 漏採製程消耗品
- ❌ 損耗率沒設 → 缺料時找不到原因
- ❌ 替代料沒列 → 缺主料時無法應變
- ❌ BOM 改版不做差異分析 → 舊單仍用新 BOM，亂套
