---
name: spc-basics
displayName: SPC 統計製程管制基礎
description: Statistical process control — control charts (Xbar-R, p, c), capability indices (Cp, Cpk), out-of-control rules
when_to_use: IPQC sampling triggers SPC analysis, quality-inspector reviews process stability, or new process needs capability study
---

# SPC 統計製程管制基礎

由 **quality-inspector** 主導，IPQC 階段使用。

---

## 為什麼要 SPC

- 不良品**事後**檢驗，已經晚了
- SPC 用統計提早發現製程偏移，**事中**就介入
- 是 ISO 9001 / IATF 16949 的硬要求

---

## 4 種常用管制圖

| 圖          | 用途                   | 資料類型               |
| ----------- | ---------------------- | ---------------------- |
| **Xbar-R**  | 連續變數平均 + 全距    | 量測值（如直徑）       |
| **Xbar-S**  | 樣本大時用標準差替代 R | 量測值，n>10           |
| **p chart** | 不良率                 | 屬性資料（OK/NG）      |
| **c chart** | 缺點數                 | 計數資料（每件缺點數） |

---

## 管制界限

預設取 **±3σ**：

```
UCL = X̄ + A2 × R̄  （上管制界限）
LCL = X̄ - A2 × R̄  （下管制界限）
CL  = X̄          （中心線）
```

A2 是樣本大小對應係數（n=5 → A2=0.577，查表）。

---

## 失控規則（Western Electric Rules）

任一條件出現即視為製程失控，需立刻介入：

1. 1 點超出 ±3σ
2. 連續 2/3 點在 ±2σ 之外（同側）
3. 連續 4/5 點在 ±1σ 之外（同側）
4. 連續 8 點在中心線同側
5. 連續 6 點漸增 / 漸減（趨勢）
6. 連續 14 點交替上下（震盪）

---

## 製程能力指數

```
Cp  = (USL - LSL) / (6σ)        — 看製程展開夠不夠窄
Cpk = min(USL - X̄, X̄ - LSL) / (3σ)  — 看是否偏中心
```

| Cpk       | 評價                        |
| --------- | --------------------------- |
| ≥ 1.67    | 卓越（IATF 16949 量產需求） |
| 1.33~1.67 | 良好                        |
| 1.00~1.33 | 勉強合格                    |
| < 1.00    | 不合格，需改善              |

---

## Process（5 步）

1. 決定要管制的關鍵特性（Critical to Quality, CTQ）
2. 取**初始 25 組樣本**，計算 X̄、R̄、UCL/LCL
3. 之後每組樣本（依抽樣頻率）標到管制圖上
4. 檢查 6 條失控規則
5. 失控 → 立刻找根因（5 Why）+ 對策

---

## Anti-patterns

- ❌ 用規格界限當管制界限 → 完全沒有提早預警功能
- ❌ 失控不處理、繼續打點 → SPC 變裝飾
- ❌ Cp 高但 Cpk 低（製程偏移）卻不調 → 客戶檢驗會挑出來
- ❌ 只看 Xbar 不看 R → 平均值 OK 但變異很大也是問題
