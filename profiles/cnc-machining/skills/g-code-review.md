---
name: g-code-review
displayName: G-code 安全審查
description: Review CNC G-code for safety (collision risk), efficiency, tool life impact, missing safety commands
when_to_use: cnc-programmer exports new G-code, before checking into version control, before first dry-run on machine
---

# G-code 安全審查 Skill

由 **cnc-programmer** 主導。所有從 CAM 軟體 export 的 G-code 都要過這一關才能上機。

---

## Process（4 階段檢查）

### 1. 基本指令完整性

必含的開頭 / 結尾指令：

```
%
O0001 (program number)
G21 (mm)
G90 (absolute)
G17 (XY plane)
G54 (work offset)
G43 H?? (tool length offset)
M03 S???? (spindle on, with RPM)
... 加工指令 ...
M05 (spindle off)
G91 G28 Z0 (return Z to home)
G91 G28 X0 Y0 (return XY to home)
M30 (program end)
%
```

**任一缺漏 → 標警告**。

### 2. 安全檢查

| 風險     | 檢查                                                 |
| -------- | ---------------------------------------------------- |
| 碰撞     | Z 安全高度 ≥ 工件最高點 + 5mm，每段 G00 移動有先抬刀 |
| 過切     | 刀徑補正（G41/G42）使用正確、進退刀路徑合理          |
| 轉速超限 | S 值 ≤ 機台主軸最高 RPM、≤ 刀具廠商建議              |
| 進給超限 | F 值 ≤ 切削參數查表 × 安全係數                       |
| 換刀位置 | M06 換刀前 Z 抬到安全高、X/Y 在換刀點                |
| 冷卻液   | M08（開）/ M09（關）對應切削動作                     |

### 3. 效率檢查

| 浪費         | 檢查                                |
| ------------ | ----------------------------------- |
| 空跑時間長   | G00 路徑可優化？刀具順序可重排？    |
| 換刀次數過多 | 同刀工序可合併？                    |
| 切削參數保守 | 與經驗值差 > 30% → 詢問是否可加快   |
| 重複定位     | 同一個位置反覆定位 → 一次完成多動作 |

### 4. 刀具壽命影響檢查

對照 `know-how/刀具壽命管理.md`：

- 切削速度是否在最佳區間？
- 進給率是否導致過大切削力？
- 切深 + 切寬 是否超過刀具承受？
- 是否有滿銑（full slot cut）導致排屑不良？

→ 預估這支程式對刀壽影響、回報給 `tool-life-engineer`

---

## Output 範例

```
G-code Review Report
程式：O0123-bracket-rev2.nc

✅ 基本指令完整
✅ 安全檢查通過
⚠️ 效率：第 234 行 G00 X100 Y100 Z-10 — 建議先抬 Z 再 XY 移動
⚠️ 刀壽：D8 平銑刀切深 4mm + 切寬 6mm（滿銑），建議改 ae=4mm
❌ 第 567 行 S=15000，超過刀具廠商建議（max 12000） → 必改

判定：需修正後重審
```

---

## 通過標準

- 0 ❌（必改項）
- ⚠️ 警告項：cnc-programmer 自行判斷是否修
- ✅ 通過後觸發 `pre-cnc-program-checkin` hook 進版控
