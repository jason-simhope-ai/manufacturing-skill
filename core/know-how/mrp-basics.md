---
title: MRP 物料需求規劃基礎
tags: [mrp, erp, planning, materials]
last-reviewed: 2026-04-26
source: APICS / ASCM CPIM body of knowledge
---

# MRP 物料需求規劃基礎

把銷售訂單 / 預測 → 展開成所有零件的採購與生產時程。

---

## MRP 三大 input

```
1. MPS (Master Production Schedule) — 主生產排程
   = 訂單 + 預測 + 目標庫存 - 現有庫存

2. BOM — 物料結構表（誰是誰的子件、用量）

3. 庫存資料 — 現庫、在途、已分配
```

→ MRP 系統展開後 output：

```
1. 計畫採購單（Planned Purchase Order）
2. 計畫生產單（Planned Manufacturing Order）
3. 變更建議（Reschedule, Cancel）
```

---

## 核心邏輯（簡化版）

對 BOM 樹從上往下展開：

```
For each item (top-down):
  毛需求 = 上層需求 × 用量 × (1 + 損耗%)
  淨需求 = 毛需求 - 庫存 - 在途 + 已分配

  if 淨需求 > 0:
    if 自製:
      開計畫生產單 (考慮 lead time 與批量)
    else:
      開計畫採購單 (考慮 lead time 與 EOQ)
```

---

## Lead Time 倒推

```
客戶交期 2026-05-30
↓
出貨備齊 2026-05-28
↓
完工 2026-05-25
↓
最後製程開工 2026-05-20
↓
原料齊 2026-05-15
↓
採購最晚下單 2026-05-08（Lead time 7 天）
```

任何一步算晚了，整鏈塌。

---

## 安全庫存與 ROP

```
ROP (Re-Order Point) = 平均日用量 × Lead Time + 安全庫存
```

達到 ROP 就要下單，不要等到歸零。

---

## ABC 分類

對所有料按金額排序：

| 類  | 佔金額 | 佔項數 | 管理方式                           |
| --- | ------ | ------ | ---------------------------------- |
| A   | 80%    | 20%    | 嚴管：頻繁盤、緊密追 ROP、優化 EOQ |
| B   | 15%    | 30%    | 中管：季盤、定期檢視               |
| C   | 5%     | 50%    | 寬管：年盤、簡化採購（大批一次買） |

---

## 對 agent 的影響

- **inventory-manager** 用 MRP 規則做缺料預警
- **production-planner** 排程要對應 MPS
- **quote-specialist** 估交期要倒推 lead time
- ABC 分類影響採購頻率與盤點頻率

---

## 常見誤解

- ❌ 庫存越少越好 → 缺料風險被忽略
- ❌ MRP 是 ERP 自動的不用管 → 主資料（lead time、用量、損耗率）錯了 MRP 就錯
- ❌ 預測就是業務拍腦袋 → 預測要有方法（指數平滑、季節因子）
