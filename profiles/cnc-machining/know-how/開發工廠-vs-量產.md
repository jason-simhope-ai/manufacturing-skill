---
title: 開發工廠（Job Shop）vs 量產（Mass Production）
tags: [job-shop, mass-production, business-model, simhope]
last-reviewed: 2026-04-26
source: SIMHOPE 實務經驗
---

# 開發工廠（Job Shop）vs 量產（Mass Production）

機械加工業最大的兩種商業模式。同樣是 CNC，做法、報價邏輯、人才需求完全不同。

---

## 比較表

| 面向 | 開發工廠 / Job Shop | 量產 / Mass Production |
|---|---|---|
| 訂單特性 | 每張不同件、量小（< 100 件常見） | 同件大量（千件 ~ 萬件） |
| 客戶 | 研發單位、原型、特殊應用 | OEM 整廠採購、Tier 1/2 |
| 報價 | 一張一報，工時 + 材料 + 風險加成大 | 分量級階梯，初期攤夾治具 + 工程費 |
| 利潤率 | 30~50%（高風險高報酬） | 10~20%（規模 + 效率） |
| 機台 | 多功能、彈性高（5 軸、車銑複合） | 專機、產線化（大量同型 3 軸） |
| 夾治具 | 標準為主 + 軟爪 | 客製為主、攤提分散 |
| 人員 | 多技能師傅、可獨立完成 | 分工明確、單站專精 |
| 品管 | 首件 + 全檢為主 | SPC + 抽檢、Cpk ≥ 1.67 |
| 文件 | 簡 → 中（內部用） | 完整 PPAP / FAI / Run @ Rate |
| 交期 | 短週期、緊湊（客戶等首件決定下一步） | 長週期、可預測 |
| 風險 | 試切失敗、估錯工時 | 量產初期 ramp-up 慢、長期客戶流失 |

---

## SIMHOPE 屬於哪一種？

**主開發工廠 + 部分小量量產**。

對應到 plugin agent 配置：

- ✅ 啟用 `prototype-coordinator`（開發件協調）
- ✅ 報價時 `quote-specialist` 多算 prototype 工時 + 風險加成
- ✅ 排程時保留 buffer 給試切失敗重做
- ⚠️ IATF 16949 PPAP 的 Cpk ≥ 1.67 在開發階段難達到（樣本不足），轉量產才嚴

---

## 兩種模式的數位化重點不同

### 開發工廠（job shop）的 AI 重點

- **報價快**：客戶問價 → 4 hr 內回覆（不是 4 天）
- **DFM 自動**：工程師看圖 30 分鐘做的 DFM 檢討，AI 先做完
- **工時估準**：基於 `cutting-parameter-calc` + 歷史工單
- **試切回饋學習**：每次試切結果回寫經驗庫，下次估更準

### 量產的 AI 重點

- **OEE 監控**：每分鐘抓設備狀態，不良率、停機原因即時統計
- **預測保養**：刀具壽命、機台震動 → 預測故障
- **SPC 即時**：每件量測值即時打點、即時失控警報
- **追溯極致**：哪台機、哪把刀、哪個操作員、做了哪批 → 客戶客訴秒查

---

## 兩種模式不該混用 prompt

CNC profile 內的 agent 預設偏 **job shop 思維**（因 SIMHOPE 場景）。

如果你是純量產廠，建議：
1. fork 此 profile → `profiles/cnc-mass-production/`
2. 移除 `prototype-coordinator` agent
3. 把 `quote-specialist` 的 prompt 改成「分量級階梯報價」邏輯
4. 把 `quality-inspector` 改成 SPC + Cpk 為主而非 100% 檢驗

詳見 `docs/profile-development.md`。

---

## 給 agent 的判斷規則

收到新 RFQ 時，依以下判斷：

```
量 < 50 件 + 圖紙 rev 0 (新件) → 開發件，dispatch prototype-coordinator
量 50~500 件 + 客戶熟、件熟 → 小量量產，走標準 6 段流程
量 > 500 件 + 客戶要求 PPAP → 量產，全套 IATF 16949 文件
```
