---
name: deviation-investigation-5whys-fishbone
displayName: 偏差調查（5 Whys + 魚骨圖）
description: Structure a GMP deviation investigation — fishbone (6M) brainstorm, evidence plan per hypothesis, 5 Whys down to a system-level cause, impact-assessment prompts, CAPA draft with predefined effectiveness checks (AI-DRAFT only, never closes a deviation or approves a CAPA)
when_to_use: deviation-capa-coordinator investigates a deviation, a deviation recurs, a CAPA effectiveness check is due, pre-inspection review of open investigations
status: alpha
---

# 偏差調查（5 Whys + 魚骨圖）Skill

> ⚠️ **Alpha**：架構依 ICH Q9(R1) 品質風險管理、ICH Q10 CAPA 系統與業界常見調查方法整理。**產出全部是 `AI-DRAFT — 非 GMP 紀錄`**；正式調查報告由調查人員在受控系統中撰寫，分類、根因結論、產品處置與 CAPA 核准由 QA 簽核。

由 **deviation-capa-coordinator** 主導。

---

## Process

### Step 0. 先確認三件事

1. 立即措施做了嗎？（隔離受影響物料 / 批次、暫停設備、標示「待判定」）— 沒做先提醒，**由現場與 QA 決定**
2. 這是不是同時是 **OOS / OOT / 投訴 / 資料完整性事件**？是的話還要走對應程序（見 [`gmp-gxp-basics`](../know-how/gmp-gxp-basics.md)）
3. 調查期限：依貴公司程序書（常見做法是設定天數並允許有理由的展延 — 天數需驗證）

### Step 1. 問題描述（Is / Is-not）

| 面向   | 是（Is）                 | 不是（Is not）                 |
| ------ | ------------------------ | ------------------------------ |
| 什麼   | 哪個產品、哪個參數       | 類似但沒發生的產品 / 參數      |
| 哪裡   | 哪條線、哪台設備、哪一步 | 同類設備有沒有發生             |
| 何時   | 首次發現、持續期間、班別 | 之前的批次為何沒發生           |
| 多少   | 影響數量、偏離幅度       | —                              |

「Is not」常常是破案關鍵：同樣的 SOP，為什麼 A 線發生、B 線沒有？

### Step 2. 魚骨圖（6M）展開

```
人（Man）        機（Machine）     料（Material）
  訓練/資格        確效/校正狀態     供應商/批次
  輪班/疲勞        保養/異常紀錄     規格/取樣
       \               |               /
        ────────────── 偏差 ──────────────
       /               |               \
  法（Method）     測（Measurement）  環（Environment）
  SOP/MBR 清楚嗎    儀器/方法確效      溫濕度/壓差/潔淨度
  表單設計          資料完整性         換線/清潔
```

每一根骨頭至少問一次；**列出來的都只是「可能原因」**。

### Step 3. 證據計畫（每個可能原因一列）

| 可能原因               | 支持 / 排除需要的證據                       | 誰去拿 | 結果               |
| ---------------------- | ------------------------------------------- | ------ | ------------------ |
| 混合機轉速偏低         | 設備 log、校正紀錄、同期其他批次參數        | 工務   | 待確認             |
| 操作員未依新版 SOP     | 訓練紀錄、SOP 版次生效日、現場訪談          | 主管   | 待確認             |
| 原料粒徑變異           | 供應商 CoA、進料檢驗、同原料批的其他批次    | QC     | 待確認             |

**沒有證據就不能升級為根因**；被排除的原因也要留下排除理由（稽核會問）。

### Step 4. 5 Whys 追到系統層

```
Why 1  為何含量偏低？        → 混合時間少了 5 分鐘
Why 2  為何少了 5 分鐘？      → 操作員依舊版 SOP 的時間
Why 3  為何用舊版？          → 現場夾板內仍放著舊版影本
Why 4  為何舊版還在現場？      → 文件發行程序沒有「回收舊版」的確認步驟
Why 5  為何沒有該步驟？        → 文件管理程序未規定現場文件回收與核對
→ 可能根因（需調查小組確認）：文件管理系統缺陷，不是單純人為疏失
```

> 範例為合成情境。停在 Why 2 的結論會是「人為疏失 → 再訓練」— 下個月換另一個人同樣會發生。

### Step 5. 影響評估提問（給調查小組，不下結論）

- 同設備 / 同原料批 / 同操作人員 / 同期間的**其他批次**是否受影響？含**已放行、已出貨**批次
- 對品質屬性（含量、不純物、無菌性、溶離、功能 / 性能）的潛在影響？需要額外檢驗或穩定性試驗嗎？
- 設備、製程、清潔、電腦化系統的**確效狀態**是否仍成立？（見 [`validation-and-change-control`](../know-how/validation-and-change-control.md)）
- 是否與**註冊 / 許可內容**不一致？→ 轉法規事務（RA）
- 是否涉及資料完整性？→ 依資料完整性程序擴大審查範圍
- 風險評估工具：可用 core [`fmea-pfmea`](../../../core/know-how/fmea-pfmea.md) 的嚴重度 × 發生度 × 偵測度思路，分數門檻由 QA 定

### Step 6. CAPA 草稿與有效性確認

| #  | 類型 | 行動                                       | 負責（職稱） | 期限 | 需變更管制？ | 有效性判定標準（事先定義）          |
| -- | ---- | ------------------------------------------ | ------------ | ---- | ------------ | ----------------------------------- |
| C1 | 矯正 | 全廠現場文件盤點，回收舊版                 | 文管         | 範例 | 否           | 盤點紀錄 100% 完成                  |
| P1 | 預防 | 文件管理程序增加「發行時回收舊版並簽認」   | QA           | 範例 | **是**       | 後續 N 次稽核抽查無舊版（N 由 QA 定） |

- 有效性確認要在 **CAPA 實施後一段時間**再做，不是實施當天
- 判定為「無效」→ 重新開調查，不是延長期限了事
- 輸出最後一行固定：`本草稿不構成偏差結案或 CAPA 核准。QA 審核：＿＿＿＿ 日期：＿＿＿＿`

---

## Anti-patterns

- ❌ 根因 = 「人為疏失」，CAPA = 「再教育訓練」，而且沒有任何證據或系統層分析
- ❌ 先有結論再找證據；只列支持的證據，不列排除的
- ❌ 影響評估只看本批，不看前後批與已放行批
- ❌ 每次偏差都開新 CAPA，從不檢查是不是重複發生
- ❌ CAPA 有效性 = 「已完成」；沒有事先定義的判定標準
- ❌ 調查拖到超過期限且沒有展延理由

---

## 待補完（contribution welcome）

- 人因工程（Human Error）分類與面談技巧範本
- 偏差分類矩陣範例（嚴重度 × 範圍）
- 實驗室 OOS Phase I / II 調查專用版（見 profile.json `wantedContributions`）
