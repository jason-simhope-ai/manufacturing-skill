---
name: engineering-change-process
displayName: 工程變更流程
description: ECN/ECO 5-step process — request, impact analysis, approval, implementation, verification & closure
when_to_use: Customer requests design change, internal engineering proposes change, supplier discontinues material, defect requires permanent fix that affects design or BOM
---

# 工程變更流程 Skill

由 **engineering-change-manager** 主導；任何「設計 / BOM / SOP / 製程要動」的時候走這流程。

> 對應 **ISO 9001 §8.5.6**（變更管控）與 **IATF 16949 §8.5.6.1**（變更管控的特殊要求）。

---

## 5 步驟概覽

```
Step 1: ECR — 變更請求收件 + 編號 + 分類
   ↓
Step 2: Impact Analysis — 全方位影響評估
   ↓
Step 3: CCB Approval — Change Control Board 簽核
   ↓ approved
Step 4: Implementation — 圖紙 / BOM / SOP / PFMEA / 工具同步更新
   ↓
Step 5: Verification & Closure — 首件 + PPAP（如需）+ 結案歸檔
```

任何一步失敗 → 回到 Step 2 重評。

---

## Step 1: ECR (Engineering Change Request)

### 觸發條件

| 來源     | 範例                                         |
| -------- | -------------------------------------------- |
| 客戶     | 「公差收緊」「材料指定改變」「外觀色號調整」 |
| 內部 R&D | 「新版設計優化」「降本方案」                 |
| 內部品管 | 8D 永久對策需要設計改動                      |
| 供應商   | 「原料停產，要找替代」                       |
| 法規     | RoHS / REACH 新增禁用物質 → 材料替換         |
| 製造     | 「現有工藝做不出，要客戶放寬公差」           |

### 必填欄位

```
ECR-2026-NNN
請求日期：YYYY-MM-DD
請求人：[姓名 + 部門 / 客戶]
變更對象：[件號 / 圖紙 / 製程 / 文件編號]
變更內容：[簡述 — Before vs After]
變更理由：[為什麼要改]
急迫性：[緊急 / 一般 / 可規劃]
建議分類：Class I / II / III（見下表）
```

### 分類

| Class   | 定義                                      | 範例                                                   |
| ------- | ----------------------------------------- | ------------------------------------------------------ |
| **I**   | 影響 form / fit / function；安全 / 法規件 | 結構件強度規格改、醫材生物相容性料變更、汽車件接口改變 |
| **II**  | 規格收緊 / 製程改善 / 等價材料替換        | 公差收緊、表面粗糙度提升、ABS 換 ABS+                  |
| **III** | 文件層級 — 不影響件本身                   | 圖紙 typo、註記補充、metadata 修正                     |

> 不確定時 → **升級**（Class III → II，Class II → I）。

---

## Step 2: Impact Analysis

由 **engineering-change-manager** 主導，dispatch 並聯：

### 13-item checklist（強制跑完）

| #   | 評估項                                                | 由誰負責                              |
| --- | ----------------------------------------------------- | ------------------------------------- |
| 1   | 圖紙 rev 變動                                         | 工程                                  |
| 2   | BOM 增/減/改料                                        | 工程 + inventory-manager              |
| 3   | 既有工單在製品處理（continue 舊 or 切換新）           | production-planner                    |
| 4   | 既有庫存舊規格件處置（用完 / 報廢 / 特採 / 折扣銷售） | inventory-manager + sales-coordinator |
| 5   | SOP 更新清單                                          | 工程 + 各製程主管                     |
| 6   | PFMEA 重評                                            | quality-inspector                     |
| 7   | Control Plan 變動                                     | quality-inspector                     |
| 8   | 夾具影響（沿用 / 改造 / 新製）                        | 製程 + fixture-designer               |
| 9   | 刀具 / 模具 / 治具影響                                | 製程 + 對應 profile agent             |
| 10  | 量具影響（新尺寸有合適量具？校驗 OK？）               | quality-inspector                     |
| 11  | 客戶 PPAP / FAI 重提需求                              | sales-coordinator + quality-inspector |
| 12  | 供應商通知 / 退料 / 新供應商資格                      | inventory-manager / 採購              |
| 13  | 成本變動 → 是否重新報價                               | quote-specialist                      |

### 成本影響估算

```
變更成本 =
   舊庫存處置損失（折扣 / 報廢）
 + 新工具 / 量具採購
 + 工程 / 工時
 + PPAP 文件 / 樣品工時
 + 客戶可能要求的補償
 + 短期生產效率損失（首批新規格學習曲線）
```

對 Class I 變更，**成本估算須超過 NT$50,000 或佔該專案 5%** 都該明列上 CCB。

---

## Step 3: CCB Approval (Change Control Board)

### CCB 組成

固定成員：

- 工程主管
- 品管主管
- 生管主管
- 業務主管（如客戶相關）
- engineering-change-manager（召集 + 紀錄）

選用成員（依案件）：

- 客戶代表（重大 Class I）
- 採購（材料變更）
- 設備 / IT（系統變更）

### 決議三選一

- **Approved** — 進 Step 4
- **Approved with conditions** — 進 Step 4，但加 X 個前提
- **Rejected** — 結案，給請求人理由
- **Hold** — 缺資訊，回 Step 2 補

### 紀錄

CCB 會議紀錄必含：

- 出席名單
- 決議內容
- 簽核（每位成員簽名 / 數位簽章）
- 下一步 owner + 截止日

---

## Step 4: Implementation

### 同步更新清單（Class I 必跑）

每個受影響的文件都要改 + 重發 + 通知對應人：

```
☐ 圖紙 rev N → rev N+1（PLM 系統 / 圖庫）
☐ BOM rev 變動（ERP）
☐ SOP 更新（QMS 文件管理系統）
☐ PFMEA / Control Plan 重發
☐ 工具 / 治具 / 模具 / 量具 to position
☐ 操作員培訓 + 簽到
☐ 操作員手冊更新
☐ 客戶通知書面送出（含預定 effective date）
☐ 供應商 / 採購單更新
```

### 切換時點

兩種模式：

| 模式                | 適用          | 操作                                                            |
| ------------------- | ------------- | --------------------------------------------------------------- |
| **Hard cutover**    | 安全 / 法規件 | 指定日期凌晨 0:00，舊規格停做、新規格上線；舊庫存報廢或特殊客戶 |
| **Soft transition** | 一般          | 新單按新規格、在製品做完舊規格、舊庫存賣完轉新                  |

每張工單在 ERP 內標明用 ECN-XXXX 規格，**追溯永遠對得上**。

---

## Step 5: Verification & Closure

### 驗證

- 首件按新規格量測 + 檢驗 → OK
- 連續 N 件（建議 30 件以上）SPC 數據穩定
- 客戶 PPAP（如需）通過
- 客戶端首批驗收 sign-off

### 結案歸檔

```
☑ 全套變更文件入庫（ECR + impact analysis + CCB minutes + implementation
   evidence + verification data）
☑ ERP 內 effective date 鎖定
☑ ECR 編號 → 升 ECN → 升 ECO（已生效）
☑ Lessons learned 入庫（如過程有教訓）
☑ 對請求人正式通知變更已完成
```

---

## Anti-patterns

- ❌ **Verbal change** — 「客戶口頭說要改」就改，沒 ECR 沒紀錄 → 量產出問題沒人擔責
- ❌ **Skip impact analysis** — 工程簽簽就上線 → 量具沒準備 / 庫存沒處置 / 客戶沒通知
- ❌ **No PPAP re-submit on Class I** — 客戶稽核必抓
- ❌ **Class III 當成 Class I 跑** — 流程效率低、團隊覺得 ECM 在找麻煩
- ❌ **Class I 當成 Class III 跑** — 風險爆
- ❌ **新版規格上線後沒驗證就 close** — 量產不穩定才發現
- ❌ **不歸檔** — 客戶稽核或 10 年後召回時找不到當時為什麼這樣改

---

## 連結

- Agent：[`engineering-change-manager`](../agents/engineering-change-manager.md)
- Know-how：[`eco-ecn`](../know-how/eco-ecn.md)、[`fmea-pfmea`](../know-how/fmea-pfmea.md)、[`iso-9001`](../know-how/iso-9001.md)
- 相關 hook：（v0.2 計畫加 `pre-eco-implementation` hook）
