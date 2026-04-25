---
name: capacity-planning
displayName: 產能規劃
description: Capacity load analysis, bottleneck identification, scenario modeling for new orders
when_to_use: New order arrives requiring delivery commitment, weekly capacity review, or production-planner queries 'can we take this on?'
---

# 產能規劃 Skill

由 **production-planner** 主導。

---

## 核心公式

```
可用產能 = (機台數 × 班別工時 × 工作天) × OEE
有效產能 = 可用產能 × (1 - 緩衝率%)
新單可承接性 = 有效產能 - 已承諾產能 ≥ 新單需求工時？
```

---

## Process（5 步）

### 1. 盤點當前產能

對每個工作中心（work center）：

- 機台數 × 每日可運轉時數 × 未來 N 週工作天 = 名義產能（小時）
- 乘以 OEE（看 `core/know-how/oee.md`）= 實際產能
- 扣掉預定保養、員工請假預估 = 可用產能

### 2. 盤點已承諾產能

從 `scheduler-mcp` 取所有已排定工單的工時加總。

### 3. 計算剩餘空間

```
剩餘空間 = 可用產能 - 已承諾 - 緩衝（15-20%）
```

### 4. 評估新單影響

新單需要工時 X 小時：

- X ≤ 剩餘空間 → 可承接，給承諾交期
- X > 剩餘空間 → 三種選項：
  - (a) 延後排程，給較晚的交期
  - (b) 加班 / 三班補產能
  - (c) 部分外包

### 5. 瓶頸前瞻

往未來 4 週看：

- 哪幾週、哪些 work center 會達瓶頸
- 提前 2 週做瓶頸對策（外包配額、新增人力、新增班別）

---

## 範例

```
本週 CNC#3 產能評估：
  名義產能：2 班 × 8h × 5 天 = 80h
  OEE：72%
  實際產能：80 × 0.72 = 57.6h
  扣保養 4h、人力缺 8h = 45.6h
  已承諾：38h
  剩餘空間：45.6 - 38 - 0.18 × 45.6 (緩衝) ≈ 0h

🔴 本週 CNC#3 已滿載，新單 → 看 CNC#5 或外包
```

---

## Checklist

- [ ] OEE 數據是最近 30 天（不要用陳年數據）
- [ ] 緩衝至少 15%
- [ ] 預定保養 / 請假已扣
- [ ] 瓶頸對策有 2 週前置時間

---

## Anti-patterns

- ❌ 用名義產能承接（沒打 OEE 折）→ over-promise
- ❌ 緩衝為 0 → 第一個意外就崩
- ❌ 只看當週、不看未來 4 週 → 瓶頸沒前瞻
