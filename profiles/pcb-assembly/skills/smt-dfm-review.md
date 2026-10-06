---
name: smt-dfm-review
displayName: SMT DFM 檢討
description: DFM checklist for a new PCBA — land patterns, stencil apertures, component spacing, MSL parts, panelization — producing a risk list with options for the customer
when_to_use: New product introduction (NPI), customer sends Gerber / BOM / centroid for quotation or first build, recurring defect traced back to design, smt-process-engineer prepares DFM feedback
status: alpha
---

# SMT DFM 檢討 Skill

> ⚠️ **Alpha**：checklist 項目為業界通識；所有標「範例 / 需驗證」的數值只是討論起點，必須以你們的設備能力、PCB 廠製程能力、客戶規範與 IPC 標準原文（如 IPC-7351 焊墊、IPC-7525 鋼板設計指引）為準。

由 **smt-process-engineer** 主導，**ems-quality-analyst**（可測性、檢驗可視性）與 core **quote-specialist**（報價風險）會引用。

---

## 輸入

| 資料                        | 用途                                 | 缺了怎麼辦                         |
| --------------------------- | ------------------------------------ | ---------------------------------- |
| Gerber（含錫膏層、防焊層）  | 焊墊、開孔、防焊間隔                 | 無法做 → 只能做 BOM 層級檢討       |
| BOM（含製造商料號）         | 封裝、MSL、替代料                    | 標記為「無法評估 MSL」             |
| 座標檔（centroid / XY）     | 貼片角度、極性、元件間距             | 請客戶補；不可自行猜角度           |
| 組裝圖 / 特殊要求           | 極性標示、禁區、塗覆、壓接           | 列入「需客戶確認」                 |
| 客戶允收要求                | IPC-A-610 Class、空洞率、清潔度      | 列入「需客戶確認」，不要假設 Class |

---

## Checklist（6 大類）

### 1. 焊墊（land pattern）

| 檢查                                   | 風險                         | 常見建議                                                  |
| -------------------------------------- | ---------------------------- | --------------------------------------------------------- |
| 焊墊尺寸與封裝不符                     | 墓碑、偏移、少錫             | 對照 IPC-7351 或元件 datasheet 建議焊墊                   |
| 兩端焊墊熱容量不對稱（一端接大銅面）   | 墓碑（小元件）               | 加熱阻隔（thermal relief）或縮小銅面連接                  |
| 細間距焊墊之間沒有防焊橋（solder dam） | 橋接                         | 確認 PCB 廠最小防焊橋寬度（範例：約 0.075~0.1 mm，需驗證） |
| 焊墊上有導通孔（via-in-pad）未塞孔     | 吸錫、空洞、少錫             | 要求樹脂塞孔＋蓋銅（filled & capped）或移出焊墊           |
| BGA 焊墊 SMD/NSMD 定義不清             | 焊點可靠度、枕頭效應         | 與客戶確認；依元件 datasheet                              |

### 2. 鋼板開孔（stencil aperture）

| 檢查                                    | 風險                     | 常見建議                                                               |
| --------------------------------------- | ------------------------ | ---------------------------------------------------------------------- |
| 面積比（area ratio）偏低                | 脫模不良 → 少錫          | 經驗值面積比 ≥ 約 0.66、寬厚比 ≥ 約 1.5（IPC-7525 指引，需驗證）       |
| 同一片板有 0201/01005 與大型元件        | 單一厚度顧不到兩邊       | 階梯鋼板（step stencil）或折衷厚度；列為 trade-off 給客戶              |
| QFN / 功率元件中央散熱焊盤整片開孔      | 空洞、元件浮高、橋接     | 分格開孔（windowpane），覆蓋率範例約 50~70%（需驗證）                  |
| 細間距 IC 開孔 1:1                      | 橋接                     | 開孔寬度內縮（範例：約 5~10%，需驗證）                                 |
| 通孔元件走 paste-in-hole（PIH）         | 填錫不足                 | 計算孔體積與錫膏量；必要時 overprint                                   |

### 3. 元件間距與方向

- **返修空間**：BGA / 大型 IC 周邊要留返修噴嘴與治具空間（距離依返修設備，範例約 2~3 mm，需驗證）
- **AOI 可視性**：高元件（電解電容、連接器、屏蔽框）旁的小元件是否被陰影遮住
- **方向一致**：同類極性元件盡量同方向，降低作業與 AOI 程式錯誤
- **波焊面（若有 THT 走波焊）**：SMD 長軸方向與陰影效應、是否需要治具遮蔽
- **雙面回焊**：重元件放第一面或確認第二次回焊時不會掉件

### 4. 濕敏元件（MSL）

- 從 BOM 列出 MSL ≥ 2a 的元件、封裝與標籤 floor life
- 標記「可能需要烘烤」的元件與其包材耐溫（捲帶/托盤不一定耐烘）
- 提醒生管：MSL 會影響開封時機與換線順序（core production-planner 不會自動考慮）
- 細節見 [`ems-quality-analyst`](../agents/ems-quality-analyst.md) 的 MSL 段

### 5. 拼板（panelization）與 MARK 點

| 檢查                       | 常見建議（範例，需驗證）                                         |
| -------------------------- | ---------------------------------------------------------------- |
| 工藝邊（rails）            | 依軌道寬度與夾持需求，常見約 3~5 mm 以上                         |
| 全域 MARK 點               | 每片拼板至少 2~3 個，不對稱放置；細間距元件旁加局部 MARK         |
| V-cut vs 郵票孔            | 元件（特別是 MLCC）離 V-cut 太近會在分板時裂；保持安全距離       |
| 板厚 / 板彎                | 薄板與大拼板需要支撐；板彎翹規格依 IPC-6012 與客戶要求（需驗證） |
| 定位孔                     | 確認與 ICT/FCT 治具一致                                          |

### 6. 可測性（給 ICT / FCT）

- 每個網路是否有測試點？測試點直徑/間距是否符合你們治具能力
- 測試點是否被元件、標籤或塗覆擋住
- 未覆蓋的網路列清單 → 說明「這部分只能靠 AOI / X-ray / FCT」

---

## 輸出格式

```
DFM 回饋 — <機種> <版本>
資料完整度：Gerber ✅ / BOM ✅ / 座標檔 ❌（缺，角度無法確認）

🔴 高風險（不改會有量產不良）
  1. <位置/料號> — <問題> → <會造成的不良> → 選項 A / B / C
🟡 中風險（可量產但要管控）
🟢 建議（改了更好）
❓ 需客戶確認
  - IPC-A-610 Class / 空洞允收 / 是否允許改版
```

**原則**：每項都給選項與 trade-off；不替客戶決定；不承諾「改了就零不良」。

---

## 相關資源

- Agent：[`smt-process-engineer`](../agents/smt-process-engineer.md)
- Know-how：[`smt-common-defects`](../know-how/smt-common-defects.md)（每個 DFM 問題對應的不良型態）
- Core：[`fmea-pfmea`](../../../core/know-how/fmea-pfmea.md)（把高風險項寫進 PFMEA）、[`engineering-change-process`](../../../core/skills/engineering-change-process.md)（客戶改版走 ECN）
