---
title: FMEA / PFMEA 失效模式分析
tags: [fmea, pfmea, dfmea, risk, aiag-vda]
last-reviewed: 2026-04-26
source: AIAG-VDA FMEA Handbook 1st Edition (2019, the harmonized US+EU method)
---

# FMEA / PFMEA 失效模式分析

> 此文件用 **AIAG-VDA 統一方法（2019 起）** — 取代了舊版 AIAG-only（北美）與 VDA-only（德國）兩種分歧版本。
> IATF 16949 / ISO 9001 客戶通常會接受這個版本。

## 一句話定義

**FMEA**（Failure Mode and Effects Analysis）= 在問題發生前，系統性找出「可能怎麼壞」 + 「壞了會有多嚴重」 + 「現在有什麼防線」，然後把高風險項加防線。

兩種主要類型：

| 類型                     | 看什麼           | 何時做                          |
| ------------------------ | ---------------- | ------------------------------- |
| **DFMEA** (Design FMEA)  | 產品設計可能失效 | 開案 → 設計階段（在凍結圖紙前） |
| **PFMEA** (Process FMEA) | 製造過程可能失效 | 試產前 → 製程開發階段           |

> 還有 **MFMEA**（Machine）、**SFMEA**（System / Software）、**LFMEA**（Logistics）— 概念一樣，scope 不同。

---

## AIAG-VDA 7 步法（2019 起）

```
1. Planning & Preparation
2. Structure Analysis
3. Function Analysis
4. Failure Analysis
5. Risk Analysis           ← 計算 AP（Action Priority）
6. Optimization
7. Results Documentation
```

舊 AIAG 版只有 5 步、用 RPN（Risk Priority Number）；新 AIAG-VDA 7 步、用 AP — 改善 RPN 的「相同分數但不同風險」問題。

---

## Risk Analysis — 三個維度評分

每個 **failure mode → effect** 組合，給 1-10 分：

### S — Severity（嚴重度）

失效對下游/客戶/終端使用者的後果：

| 分  | 描述                      |
| --- | ------------------------- |
| 10  | 危及生命、無預警          |
| 9   | 危及生命、有預警          |
| 8   | 主要功能失效 → 召回       |
| 7   | 主要功能降級              |
| 6   | 次要功能失效              |
| 5   | 次要功能降級              |
| 4   | 外觀缺陷 — 客戶很介意     |
| 3   | 外觀缺陷 — 客戶會介意     |
| 2   | 外觀缺陷 — 客戶不一定發現 |
| 1   | 無感                      |

### O — Occurrence（發生度）

該失效原因發生的頻率：

| 分  | 頻率（PPM 估算）      |
| --- | --------------------- |
| 10  | > 100,000 ppm（10%+） |
| 9   | 50,000~100,000        |
| 8   | 20,000~50,000         |
| 7   | 10,000~20,000         |
| 6   | 5,000~10,000          |
| 5   | 2,000~5,000           |
| 4   | 500~2,000             |
| 3   | 100~500               |
| 2   | 10~100                |
| 1   | < 10 ppm              |

### D — Detection（偵測度）

現有控制能在問題流到下游前抓住的能力：

| 分  | 描述                                   |
| --- | -------------------------------------- |
| 10  | 沒有控制能抓                           |
| 9-8 | 出貨後客戶才會抓到                     |
| 7-6 | 出貨前 OQC 抽檢可能抓到（但不靠 100%） |
| 5-4 | FQC 全檢能抓到                         |
| 3-2 | 製程中 SPC + 自動量測能即時抓          |
| 1   | 防呆設計 — 物理上做不出不良            |

### AP — Action Priority

```
S, O, D → AP table → 高 / 中 / 低
```

AIAG-VDA 不再用 RPN = S × O × D 的單一數字。改用查表 — S=10 自動高 AP（即使 O 與 D 都低），因為「會出人命的事即使少發生也不能放」。

---

## PFMEA template（簡化）

| Process Step | Function         | Failure Mode | Effect   | S   | Cause        | O   | Current Control    | D   | AP  | Action                     |
| ------------ | ---------------- | ------------ | -------- | --- | ------------ | --- | ------------------ | --- | --- | -------------------------- |
| OP20 銑外形  | 把毛胚銑成 50×30 | 尺寸超差     | 客戶退貨 | 8   | 刀具磨耗     | 5   | 每 50 件 SPC 抽檢  | 4   | M   | 加首件 + 80 件強制換刀     |
| OP30 鑽孔    | 鑽 4 個 φ6 通孔  | 漏鑽         | 件報廢   | 7   | 操作員跳工序 | 3   | 工單上 OP 確認簽名 | 6   | M   | 加防呆夾具確認鑽完才能取下 |
| OP40 陽極    | 表面處理         | 厚度不均     | 不耐蝕   | 6   | 槽液濃度漂   | 4   | 每月校             | 7   | H   | 加每日 pH 量測 + 警報      |

---

## 對 agent 的影響

- **`quality-inspector`**：開新工單時要做 PFMEA，特別是 IATF / 醫材客戶；看到客訴時要更新 PFMEA（D 分數可能要降，因為「現有控制」被證實不夠）
- **`production-planner`**：高 S 分數的工序要排能力強的人 + 機台；高 AP 工序要更密的 IPQC 抽樣
- **`engineering-change-manager`**（v0.1.2 新增）：任何設計 / 製程變更要 trigger DFMEA / PFMEA 重新檢視 — 變更可能引入新失效模式
- **`quote-specialist`**：高 AP 的件報價要加防線成本（更密的 SPC、額外 inspection、防呆裝置）

---

## 常見誤解

- ❌ **「FMEA 是 IATF 客戶才要做的紙上作業」** → FMEA 是用來**找風險、放防線**的工具，沒有客戶要也該做關鍵件
- ❌ **「RPN 800 就是高風險」** → 舊 AIAG 的 RPN = S×O×D 設計就有問題（S=10 O=10 D=8 是 800；S=8 O=10 D=10 也是 800，但前者風險更高）。AIAG-VDA 的 AP 表解決這個
- ❌ **「FMEA 寫完就放著」** → 任何客訴 / NCR / 製程變更後都要回去更新；不更新的 FMEA 是廢紙
- ❌ **「PFMEA 是品管的事」** → PFMEA 是跨部門團隊（設計、製程、品管、生管、採購）的事，由品管召集

---

## 工具

- AIAG-VDA FMEA Handbook（必備，付費）
- 軟體：APIS IQ-FMEA、Plato Scio、PTC Windchill FMEA
- 簡單做：Excel 模板（vault 內可開一個 `templates/pfmea.xlsx` — v0.2 加）
