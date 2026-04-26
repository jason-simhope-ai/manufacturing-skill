---
title: ECN / ECO / ECR — 工程變更管控制度基礎
tags: [eco, ecn, ecr, change-control, iso-9001, plm]
last-reviewed: 2026-04-26
source: ISO 9001:2015 §8.5.6 + IATF 16949 §8.5.6.1 + industry PLM practice
---

# ECN / ECO / ECR — 工程變更管控制度基礎

## 為什麼存在這套制度

製造業的真實場景：

> 4/15 客戶說孔徑改 ⌀6 → ⌀6.2。<br>
> 4/16 工程改了圖紙 rev。<br>
> 4/17 CNC 還在用舊程式做 ⌀6（沒人通知 production）。<br>
> 4/20 量產 200 件 ⌀6 → 客戶端 IQC 退貨 → NT$80,000 損失。

ECM（Engineering Change Management）就是讓上面**不再發生**的制度。

ISO 9001 §8.5.6 規定：

> 「組織應審查並控制與生產或服務提供有關的變更，以便在符合規範要求的範圍內進行。」

實質要求：**任何變更都要有 paper trail、有審核、有受影響項全展、有實施 + 驗證 + 結案**。

---

## 三個關鍵縮寫

| 縮寫    | 全名                       | 階段                                    |
| ------- | -------------------------- | --------------------------------------- |
| **ECR** | Engineering Change Request | 「我想改」 — 請求階段                   |
| **ECN** | Engineering Change Notice  | 「我們批准了你改」 — 已核准、通知執行   |
| **ECO** | Engineering Change Order   | 「改完了，從這天起生效」 — 已實施、生效 |

許多公司只用 ECN + ECO 兩個（沒 ECR），或只用 ECO 一個，**重點是公司內部一致**。本文用三階段。

> ECR / ECN / ECO 編號可以是同一個：`ECR-2026-001` → approved 升 `ECN-2026-001` → implemented 升 `ECO-2026-001`，編號不變只改前綴。
> 或一律用 ECO，但內部分 status：requested / approved / implemented。

---

## 三個分類等級

| Class                 | 定義                                      | 流程                          | 客戶通知                       |
| --------------------- | ----------------------------------------- | ----------------------------- | ------------------------------ |
| **Class I**（重大）   | 影響 form / fit / function；安全 / 法規件 | 完整 5 步驟 + CCB + PPAP 重提 | 必通知 + 取得書面 acceptance   |
| **Class II**（一般）  | 規格收緊 / 製程改善 / 等價材料替換        | 完整 5 步驟 + 內部 CCB        | 通知 + 14 天無異議視為接受     |
| **Class III**（次要） | 文件層級 — 不影響件本身                   | 工程簡簽                      | 不需通知（除非客戶合約有規定） |

### 判斷 Class 的快速規則

問三題：

1. **件出去後客戶端會用得不一樣嗎**？（裝配 / 性能 / 安全）→ Yes = Class I
2. **規格 / 製程改變但功能不變**？→ Class II
3. **只是改字、改格式、補充註記**？→ Class III

---

## CCB (Change Control Board) 結構

```
            CCB Chair（通常工程主管或 ECM）
                  │
        ┌─────────┼─────────┐
        │         │         │
   品管主管    生管主管   業務主管
        │         │         │
   品管工程   生管工程   業務助理
   （操作層）  （操作層）  （操作層）

附加（依案件招集）：
   客戶代表       採購主管       設備 / IT
```

CCB 開會頻率：

- **緊急 ECR** — 24 小時內召集（電子簽核也行）
- **常規 ECR** — 每週 1-2 次例會

---

## ISO 9001 §8.5.6 要求對應

| ISO 條款               | 我們的對應                               |
| ---------------------- | ---------------------------------------- |
| 「審查變更」           | Step 2 Impact Analysis + Step 3 CCB      |
| 「保留變更紀錄」       | ECR + Impact Report + CCB Minutes 全歸檔 |
| 「鑑別執行變更的人員」 | CCB 名單 + 簽核紀錄                      |
| 「鑑別必要的措施」     | Step 4 Implementation 同步更新清單       |
| 「審查變更後果」       | Step 5 Verification + 客戶反饋追蹤       |

---

## IATF 16949 §8.5.6.1 額外要求（汽車業）

汽車業比一般 ISO 9001 嚴：

- **任何 Class I 變更必須客戶書面 approve before 實施**
- **PPAP 重提是預設行為** — 客戶要明示「不需重提」才可省
- **變更追溯到單件 / 批次** — 「這件是 ECN-XXX 後做的」要對得上
- **製程變更（生產地點 / 設備 / 第二來源）算 Class I**

---

## 文件層級（哪些文件會被變更牽動）

ECM 的價值就是看到「改一個圖紙會牽動 N 份文件」：

```
            圖紙 rev
              │
    ┌─────────┼─────────┬──────────┬──────────┐
    │         │         │          │          │
  BOM      SOP      PFMEA      Control     Work
                              Plan        Instruction
    │         │         │          │          │
    │         │         │          │          │
  採購單   操作員   不良對策    抽樣      組裝指示
  + 物料   培訓     重評       規範
  庫存                         + 量具
  處置
```

**變更後沒有同步更新的文件 = 未來 NCR / 客訴的種子**。

---

## 常見誤解

- ❌ **「ECN 是寫給品管看的」** — ECN 是**全公司**動作通知，每個受影響部門都要動
- ❌ **「Class III 不用紀錄」** — Class III 也要 paper trail，否則「這個 typo 是誰改的」沒人知道
- ❌ **「客戶說要改就改，反正是他們要求」** — 客戶要求也要走 ECR，否則客戶事後否認 / 要求不給錢時你沒證據
- ❌ **「變更影響很小，跳過 PFMEA 重評」** — 即使影響小，PFMEA 不更新就是隱形債務累積
- ❌ **「實施後沒人 verify 也沒事」** — 量產後出問題才發現實施有漏，已造成更大損失
- ❌ **「ECO 編號隨便給」** — 編號要有格式（year-sequence）、要連號（不可跳號）、要全公司唯一

---

## 工具

- **PLM 系統**（PTC Windchill / Siemens Teamcenter / Aras Innovator / 鼎新 PLM）— 大公司用
- **ERP 內變更模組**（SAP / Oracle / D365）— 中型廠用
- **GitHub / GitLab + markdown**（小團隊用，IT 強的工廠）— 開源製造業 starter
- **Excel + 共享資料夾**（最小可行，但難 audit）— 不建議但常見

---

## 對 manufacturing-skill 用戶的建議

如果你的工廠：

| 規模            | 建議                                              |
| --------------- | ------------------------------------------------- |
| 月 < 100 件變更 | Excel + git + 嚴格命名規範 + ECM 角色由品管課長兼 |
| 月 100-500 件   | ERP / PLM 變更模組 + 專職 ECM                     |
| 月 > 500 件     | 完整 PLM 系統 + 變更管理小組                      |

manufacturing-skill 的 [`engineering-change-manager`](../agents/engineering-change-manager.md) agent 設計上**不假設特定 PLM 工具** — 走的是流程通則，可以接你現有的任何系統。

---

## 連結

- Agent：[`engineering-change-manager`](../agents/engineering-change-manager.md)
- Skill：[`engineering-change-process`](../skills/engineering-change-process.md) — 5 步驟詳細 SOP
- 相關 know-how：[`fmea-pfmea`](fmea-pfmea.md)（Step 2 + Step 4 都要更新）、[`iso-9001`](iso-9001.md)（§8.5.6 要求）
