---
name: fixture-design-patterns
displayName: 夾治具設計常見 pattern
description: Common fixture design patterns for CNC machining — vise + soft jaw, modular base, vacuum, magnetic, custom poka-yoke
when_to_use: fixture-designer evaluates a part requiring custom fixturing, or quote needs fixture cost estimate
---

# 夾治具設計常見 Pattern

由 **fixture-designer** 主導。

---

## Pattern 1：標準虎鉗 + 軟爪（70% 零件用得上）

- 適用：方形 / 長方體件，量小到中
- 軟爪客製成工件外形，1 hr 內可完成
- 優：成本低、換型快
- 缺：薄件夾不穩、異形件不適用

---

## Pattern 2：Modular Base + 可換定位塊

- 適用：同系列件、客戶常下單
- 一個底座 + 多個定位塊（每個對應一種件）
- 優：換型 < 5 min、易擴充
- 缺：底座成本高、需良好倉儲管理定位塊

---

## Pattern 3：真空吸盤

- 適用：薄件、大平面、無法夾邊
- 優：不傷工件、不變形
- 缺：需真空泵浦、薄件中間切穿會漏氣

---

## Pattern 4：磁性吸盤

- 適用：鐵件、平件
- 永磁式：手動 ON/OFF；電磁式：開機才有力
- 優：定位快、不需夾持力推
- 缺：只能鐵件、磁殘留可能影響

---

## Pattern 5：3-2-1 客製夾具

完全客製，遵循 3-2-1 原則：

```
3 個定位點限制 3 個自由度（主基準面）
2 個定位點限制 2 個自由度（次基準面）
1 個定位點限制 1 個自由度（末基準面）
總共限制 6 個自由度，工件不會晃
```

- 適用：異形件、量大、精度要求高
- 優：定位最準
- 缺：設計工時高、製作成本高

---

## Pattern 6：旋轉 / 翻轉夾具

- 適用：6 面加工、車銑複合
- 手動：人工翻面，成本低
- 自動（4 軸 / 5 軸）：機台旋轉，速度快但機台貴
- 優：一次裝夾多面（減積累誤差）
- 缺：設計複雜

---

## 選擇決策樹

```
量 < 50 件？
  ├─ 是 → 標準夾具（Pattern 1）+ 軟爪
  └─ 否 → 量 > 500 件？
            ├─ 是 → 客製夾具（Pattern 5 或 6）
            └─ 否 → Modular（Pattern 2）

特殊：
  - 薄 / 大平面 → Pattern 3 真空
  - 鐵件平件 → Pattern 4 磁性
  - 異形 + 量大 → Pattern 5 客製
  - 6 面加工 → Pattern 6 翻轉
```

---

## 防呆原則

無論哪種 pattern，都應包含：

- **裝錯就裝不上去**：偏心、缺角、不對稱定位銷
- **方向唯一**：定位面只有一種正確方向
- **可視化**：標註正確方向的箭頭、顏色

---

## ROI 計算

```
攤提 = 夾具設計 + 製作成本
攤提 < 5% × 預估訂單金額 → 值得做
攤提 5~10% → 邊緣，看客戶長期合作關係
攤提 > 10% → 不做、用標準夾具 + 多花裝夾時間
```
