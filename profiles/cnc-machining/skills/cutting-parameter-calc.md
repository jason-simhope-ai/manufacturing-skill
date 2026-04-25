---
name: cutting-parameter-calc
displayName: 切削參數計算
description: Calculate cutting speed (vc), feed per tooth (fz), depth of cut (ap, ae) for CNC operations
when_to_use: cnc-programmer needs parameters for new tool/material combo, or quote needs accurate cycle time estimate
---

# 切削參數計算 Skill

由 **cnc-programmer** 主導。

---

## 4 個關鍵參數

| 參數     | 符號 | 單位     | 意義                             |
| -------- | ---- | -------- | -------------------------------- |
| 切削速度 | vc   | m/min    | 刀刃線速度（材料切削表面的速度） |
| 每齒進給 | fz   | mm/tooth | 每個刀齒切下的厚度               |
| 軸向切深 | ap   | mm       | Z 方向切深                       |
| 徑向切深 | ae   | mm       | XY 方向切寬                      |

---

## 從 vc 算 RPM

```
RPM = (vc × 1000) / (π × D)
D：刀具直徑 (mm)
vc：切削速度 (m/min)
```

範例：D8 平銑刀切 SUS304，vc 取 80 m/min

```
RPM = (80 × 1000) / (3.14159 × 8) = 3,183 RPM
```

---

## 從 fz 算進給率

```
F = fz × Z × RPM
F：進給率 (mm/min)
fz：每齒進給 (mm)
Z：刀刃數
```

範例：上面 D8 平銑 4 刃，fz=0.05 mm

```
F = 0.05 × 4 × 3183 = 637 mm/min
```

---

## 推薦參數查表（精華版）

| 材料           | 刀具       | vc (m/min) | fz (mm)   | ap    | ae    |
| -------------- | ---------- | ---------- | --------- | ----- | ----- |
| 鋁合金 6061    | 鎢鋼平銑   | 200~400    | 0.05~0.15 | 0.5×D | 0.5×D |
| 軟鋼 S45C      | 鎢鋼平銑   | 100~150    | 0.05~0.10 | 0.3×D | 0.3×D |
| 不鏽鋼 SUS304  | TiAlN 塗層 | 60~100     | 0.03~0.08 | 0.2×D | 0.2×D |
| 不鏽鋼 SUS304  | 高速鋼 HSS | 15~25      | 0.02~0.05 | 0.2×D | 0.2×D |
| 鈦合金 Ti6Al4V | TiAlN 塗層 | 30~60      | 0.02~0.05 | 0.1×D | 0.1×D |
| Inconel 718    | TiAlN 塗層 | 15~30      | 0.02~0.04 | 0.1×D | 0.1×D |

完整版見 `know-how/切削參數查表.md`。

---

## 機台剛性修正

| 機台等級                      | vc / fz 修正 |
| ----------------------------- | ------------ |
| 高剛性（5 軸 / 大型加工中心） | 上限         |
| 一般 3 軸加工中心             | 中位         |
| 老舊 / 輕型機                 | 下限的 70%   |

---

## Cycle time 估算

```
單孔 / 單槽 cycle time = (移動長度 / F) + setup × 適當係數
單件 cycle time = Σ 所有工序 cycle time + 換刀時間
```

回報給 quote-specialist 用於報價工時。

---

## Anti-patterns

- ❌ 拿鋁合金的參數切不鏽鋼 → 燒刀
- ❌ 不分機台剛性套同一參數 → 老機振動爆
- ❌ ap = D（滿銑）排屑不良 → 卡刀
- ❌ 不留試切微調空間 → 第一次就上量產參數很危險
