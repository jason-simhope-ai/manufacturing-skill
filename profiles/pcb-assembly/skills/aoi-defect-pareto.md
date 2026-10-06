---
name: aoi-defect-pareto
displayName: AOI/SPI/ICT 缺陷柏拉圖
description: Turn AOI / SPI / ICT / FCT exports into per-station FPY, DPMO, a defect Pareto drilled down to location and part number, and an owner-assigned action list
when_to_use: Weekly quality review, yield drop on a line, new product ramp-up, customer asks for defect data, ems-quality-analyst or smt-process-engineer needs evidence before changing a process
status: alpha
---

# AOI / SPI / ICT 缺陷柏拉圖 Skill

> ⚠️ **Alpha — 沒有 MES 即時連線**。這個 skill 只處理使用者**從 MES 或設備匯出**的 CSV / Excel。不同廠牌設備的欄位與缺陷代碼差異很大，第一次使用一定要先做欄位對照。未來的 `mes-connector` 會比照 [`erp-connector/contract.py`](../../../infra/mcp-servers/erp-connector/contract.py) 定義唯讀介面（見 profile.json `wantedContributions`）。

由 **ems-quality-analyst** 主導，**smt-process-engineer** 用結果決定製程對策。

---

## 0. 匯出前（給 IT / MES 管理者）

- 用**唯讀帳號**匯出，不要給 AI 直接寫入 MES 的權限
- 移除或代碼化：客戶名稱、成品序號、作業員姓名（保留班別即可）
- 範圍：建議至少 1~2 週，或一個完整工單
- 檔名包含站別與期間，例如 `aoi_line2_2026W40.csv`

---

## 1. 最少需要的欄位

| 欄位            | 說明                                      | 必要 |
| --------------- | ----------------------------------------- | ---- |
| `board_id`      | 板號 / 拼板內子板號                       | ✅   |
| `station`       | SPI / AOI-pre / AOI-post / ICT / FCT      | ✅   |
| `result`        | PASS / FAIL（該板該站第一次結果）         | ✅   |
| `defect_code`   | 設備原始缺陷代碼                          | ✅   |
| `refdes`        | 位置（U7、C12…）                          | ✅   |
| `review_result` | 複判結果：TRUE（真不良）/ FALSE（誤判）   | AOI ✅ |
| `part_no`       | 料號                                      | 建議 |
| `line` / `shift`| 線別 / 班別                               | 建議 |
| `timestamp`     | 時間                                      | 建議 |

**沒有 `review_result` 的 AOI 資料不能直接做柏拉圖** — 會把誤判當不良。先請現場補複判紀錄，或只分析 ICT/FCT。

---

## 2. 統一缺陷代碼

不同設備對同一種不良用不同代碼。先建一張對照表（存成 CSV，下次沿用）：

| 原始代碼（範例） | 統一分類       |
| ---------------- | -------------- |
| `BRIDGE`, `SHORT`, `SB` | 短路/橋接 |
| `INSUFF`, `LOW_VOL`     | 少錫     |
| `TOMB`, `LIFT`          | 墓碑/翹起 |
| `SHIFT`, `OFFSET`       | 偏移     |
| `MISSING`               | 缺件     |
| `POLARITY`, `REVERSE`   | 極性錯誤 |

分類名稱對齊 [`smt-common-defects`](../know-how/smt-common-defects.md)，才能直接接到對策。

---

## 3. 指標定義（先講清楚再算）

```
分站 FPY  = 該站第一次就 PASS 的板數 / 該站測試板數
RTY       = FPY_SPI × FPY_AOI × FPY_ICT × FPY_FCT
AOI 誤判率 = 複判為 FALSE 的報警數 / AOI 總報警數
DPMO      = 真不良數 / (板數 × 每板 opportunity 數) × 1,000,000
```

- **Opportunity 怎麼算一定要寫出來**（每個焊點？每個元件？）。不同定義的 DPMO 不能互相比較
- 重測後才 PASS 的板，不算進 FPY 的分子

---

## 4. 柏拉圖步驟

1. 篩選：只留**真不良**（AOI 用 `review_result = TRUE`；ICT/FCT 用 FAIL）
2. 依統一分類計數，由大到小排序，算累計百分比
3. 找出累計約 80% 的前幾類（不是硬切 80%，看斷點）
4. 對前 1~3 類**往下鑽**：refdes → part_no → line / shift → 時間趨勢
5. 一個 refdes 佔該類 30% 以上，通常是設計或鋼板問題；平均分散在很多位置，通常是製程或材料問題（經驗法則，需驗證）

### 範例程式（只用 Python 標準函式庫）

```python
import csv
from collections import Counter

rows = list(csv.DictReader(open("aoi_line2_2026W40.csv", encoding="utf-8")))
code_map = {r["raw"]: r["unified"] for r in csv.DictReader(open("defect_code_map.csv", encoding="utf-8"))}

true_defects = [r for r in rows if r.get("review_result", "").upper() == "TRUE"]
by_type = Counter(code_map.get(r["defect_code"], "未分類") for r in true_defects)

total = sum(by_type.values())
cum = 0
for kind, n in by_type.most_common():
    cum += n
    print(f"{kind:10s} {n:5d} {n/total:6.1%} 累計 {cum/total:6.1%}")

top = by_type.most_common(1)[0][0]
by_ref = Counter(r["refdes"] for r in true_defects if code_map.get(r["defect_code"]) == top)
print("前 5 位置：", by_ref.most_common(5))
```

「未分類」比例超過約 5%（範例）時，先補對照表再下結論。

---

## 5. 行動清單格式

| # | 問題（具體到位置/料號） | 推定根因 | 對策 | 負責 | 期限 | 驗證方式 |
|---|---|---|---|---|---|---|
| 1 | U7 pin 12-13 短路 96 筆 | 鋼板開孔過大（推定） | 開孔內縮 + SPI 上限收緊 | 製程 | 10/12 | SPI 體積 Cpk、連續 3 天 AOI 數據 |

規則：

- 每個對策都要有**驗證方式**，不然下週無法判斷有效
- 涉及回焊 profile、AOI 門檻、測試程式的變更 → 標記「**需人工簽核**」，不在此 skill 內決定
- 涉及偏差 / 特採 → 轉 core [`quality-inspector`](../../../core/agents/quality-inspector.md) 流程，不在此 skill 內核准

---

## 6. 搭配 core

- SPI 體積、高度是連續資料 → 用 [`spc-basics`](../../../core/skills/spc-basics.md) 算 Cpk 與管制圖
- 重複發生的不良 → [`8d-report-writing`](../../../core/skills/8d-report-writing.md)
- 設備停機與速度損失 → [`oee`](../../../core/know-how/oee.md)（FPY 只是 OEE 品質率的一部分）
