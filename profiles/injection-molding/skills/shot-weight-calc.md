---
name: shot-weight-calc
displayName: 射出量計算
description: Calculate required shot weight from part design, validate against machine barrel capacity
when_to_use: mold-designer estimates production feasibility, quote-specialist needs cycle time / machine selection input, troubleshooting short-shot or overpacking
status: alpha
---

# 射出量計算 Skill

> ⚠️ **Alpha**：公式為業界共通，但安全係數 / 實際機台 datasheet 須以你工廠的實際設備為準。

由 **mold-designer** 主導，**quote-specialist** 與 **molding-process-engineer**（v0.2 預計新增）會引用。

---

## 核心公式

```
Shot weight (g) = Part weight × Cavities × (1 + Runner ratio) × Safety factor
```

| 變數          | 取值       | 來源                             |
| ------------- | ---------- | -------------------------------- |
| Part weight   | 件重（克） | CAD 體積 × 材料密度              |
| Cavities      | 模穴數     | 模具設計決定                     |
| Runner ratio  | 流道佔比   | 冷流道 0.10~0.30；熱澆道幾乎為 0 |
| Safety factor | 1.05~1.10  | 製程波動補償                     |

---

## 機台選擇準則

```
選機台射出量 ≥ Shot weight / 0.80
```

理由：射出機通常**不要用超過 80% 的料筒容量**。原因：

- > 80%：每模都把料筒清空，料停留時間極短 → 高溫敏感料（POM / PA）來不及完全熔融
- < 20%：料停留太久 → 退化（PVC 黑點、ABS 黃化）

**最佳工作區：機台容量的 30%~80%**。

---

## 計算範例

### 範例 1：ABS 外殼 4 穴熱澆道

```
件重：35 g（從 CAD 算）
材料：ABS（密度 1.05 g/cm³）
模穴：4
流道：熱澆道（runner ratio ≈ 0）
安全：1.05

Shot weight = 35 × 4 × (1 + 0) × 1.05 = 147 g
建議機台射出量：147 / 0.80 = 184 g 以上
→ 選 250 g 機（145 g 工作量 ≈ 58% 容量，OK）
→ 不選 150 g 機（98% 容量爆，風險高）
```

### 範例 2：PP 杯蓋 16 穴冷流道

```
件重：3.5 g
材料：PP（密度 0.91 g/cm³）
模穴：16
流道：冷流道（runner ratio ≈ 0.20）
安全：1.10

Shot weight = 3.5 × 16 × (1 + 0.20) × 1.10 = 73.9 g
建議機台射出量：73.9 / 0.80 = 92.4 g 以上
→ 選 125 g 機（59% 容量）
```

### 範例 3：PA66+GF30 結構件

```
件重：120 g
材料：PA66+GF30（密度 1.36 g/cm³）
模穴：1
流道：冷流道（runner ratio ≈ 0.15）
安全：1.10
（玻纖補強料 → 流動性差，安全係數調高）

Shot weight = 120 × 1 × (1 + 0.15) × 1.10 = 152 g
建議機台射出量：152 / 0.80 = 190 g 以上
→ 選 250 g 機，但需確認鎖模力（PA66+GF 投影面積 × 600~800 kg/cm²）
```

---

## 鎖模力快速驗算（額外）

許多時候射出量算出來 OK，但機台**鎖模力不夠**也不能用：

```
鎖模力 (ton) ≥ 投影面積 (cm²) × 模穴內壓 (kg/cm²) / 1000

模穴內壓參考：
  PE / PP / PS         300~500 kg/cm²
  ABS / PC             400~700
  PA / POM             500~800
  PA66 + GF30 / PEEK   700~1200
```

範例：上述 PA66+GF30 結構件投影面積 80 cm²

```
80 × 800 / 1000 = 64 ton → 選 ≥ 80 ton 鎖模機
```

---

## Process（agent 怎麼跑這個 skill）

1. 讀件 CAD 體積（或從 STEP / STL 估）
2. 查 [`polymer-material-database.md`](../know-how/polymer-material-database.md) 取材料密度
3. 算件重
4. 套上面公式得 shot weight
5. 用 / 0.80 算建議機台射出量
6. 用投影面積 × 模穴內壓算鎖模力
7. 回報「建議 ≥ X g 射出量、≥ Y ton 鎖模力的機台」

---

## Anti-patterns

- ❌ 用 100% 機台容量塞滿 — 會出料退化、cycle 不穩
- ❌ 忘記算流道（特別是大型件 / 多穴）
- ❌ 玻纖補強料用普通安全係數 — 流動性差很多，要 1.10~1.15
- ❌ 只看射出量不算鎖模力 — 大投影面積件會撐開模具

---

## 待補完（contribution welcome）

- Cycle time 估算（包含冷卻時間公式 — 需要新 skill `cooling-time-calc`）
- 多種料 / 多色機（multi-shot / overmolding）的射出量計算
- 真實工廠的機台清單與費率對照表
