# profiles/cnc-machining/manufacturing.md

> CNC 精密加工 profile 的 overlay 說明 — 在 core 之上加什麼、改什麼。

啟用此 profile：

```
/install-profile cnc-machining
```

---

## 這個 profile 解決什麼

讓 manufacturing-skill 從「通用製造業」升級為「**懂 CNC 切削加工**」：

- 知道 G-code 與切削參數
- 知道 IATF 16949（汽車業客戶必備）
- 知道刀具壽命怎麼管
- 知道夾治具設計原則
- 知道開發工廠（job shop）vs 量產的不同流程

---

## 加在 core 上面的東西

### 多 4 隻 agent

| Agent                   | 角色           | 主要任務                                            |
| ----------------------- | -------------- | --------------------------------------------------- |
| `cnc-programmer`        | CNC 程式工程師 | 寫 G-code、選刀、選夾治具、估工時                   |
| `tool-life-engineer`    | 刀具壽命工程師 | 管刀具庫、預測磨耗、安排換刀                        |
| `fixture-designer`      | 夾治具設計師   | 設計加工夾具、定位基準、防呆                        |
| `prototype-coordinator` | 試樣協調員     | 開發件的特殊流程：首樣 → DFM 檢討 → 試切 → 客戶確認 |

### 多 3 個 skill

| Skill                     | 用途                                                    |
| ------------------------- | ------------------------------------------------------- |
| `g-code-review`           | 檢查 G-code：安全、效率、刀具壽命影響                   |
| `cutting-parameter-calc`  | 算切削參數：vc / fz / ap / ae，依材料 + 刀具 + 機台剛性 |
| `fixture-design-patterns` | 設計夾具的常見 pattern                                  |

### 多 4 份 know-how

| Know-how           | 內容                                       |
| ------------------ | ------------------------------------------ |
| `iatf-16949`       | 汽車業品質體系，含 PPAP / FAI / Run @ Rate |
| `刀具壽命管理`     | 各類刀具的典型壽命、換刀策略               |
| `切削參數查表`     | 常見材料 × 常見刀具的推薦參數              |
| `開發工廠-vs-量產` | 兩種生產模式的差異、什麼時候該怎麼做       |

### 多 1 個 hook

- `pre-cnc-program-checkin` — G-code 進版控前自動跑安全檢查（碰撞、過切、轉速超限）

---

## 修改的 core 行為（overrides）

v0.1 暫無 override，CNC profile 只「加」不「改」。

未來如果加 `overrides:` 範例：

```json
"overrides": {
  "agents": ["quote-specialist"],   // 用 CNC 專屬報價邏輯取代 core 預設
  "skills": ["05-檢驗"],            // 用 IATF 16949 嚴格版檢驗取代
  "knowHow": []
}
```

被 override 的 core 檔案會變成備份（`core/agents/quote-specialist.md.bak`），啟用時優先用 profile 版。

---

## SIMHOPE 場景對應

此 profile 是基於 SIMHOPE 真實 job shop 場景開發：

- 接客戶開發件：dispatch `prototype-coordinator`
- 客戶要求 PPAP：用 `iatf-16949` know-how
- 急件想知道刀夠不夠：問 `tool-life-engineer`
- 報價時的工時估算：用 `cutting-parameter-calc`

---

## 下一步

- 看完 [profiles/cnc-machining/agents/cnc-programmer.md](agents/cnc-programmer.md) 了解主要角色
- 看 [docs/explainers/03-使用者cheatsheet.html](../../docs/explainers/03-使用者cheatsheet.html) CNC 區塊
- 跑 `/quote @../../examples/sample-drawing/bracket.md` 體驗完整 demo
