---
name: batch-record-completeness-review
displayName: 批次紀錄完整性審查
description: Pre-review checklist for executed batch records (BMR / BPR / API batch record / device DHR) — completeness, signatures, calculations, chronology, ALCOA+ data-integrity signals, deviation cross-references, common findings (AI-DRAFT only, never releases a batch)
when_to_use: batch-record-reviewer pre-checks a batch record before QA review, training new reviewers, self-inspection of GDP / data-integrity practice, preparing for a GMP inspection
status: alpha
---

# 批次紀錄完整性審查 Skill

> ⚠️ **Alpha**：checklist 依 PIC/S GMP 文件管理章節、ICH Q7 第 6 章、PIC/S PI 041 / MHRA / FDA 資料完整性指引的公開架構整理（各文件現行版次需驗證）。**這是正式審查前的預檢工具 — 產出為 `AI-DRAFT — 非 GMP 紀錄`，不構成審查結論，也不是放行。**

由 **batch-record-reviewer** 主導。

---

## 審查員在看什麼（4 層）

| 層次       | 問題                                     | AI 能幫的程度                  |
| ---------- | ---------------------------------------- | ------------------------------ |
| 1 完整性   | 每一格都填了嗎？每個簽名都在嗎？         | ✅ 高 — 這是本 skill 的主力    |
| 2 一致性   | 數字、批號、時間前後對得上嗎？           | ✅ 中高 — 需要完整頁面         |
| 3 符合性   | 數值在 MBR / 規格範圍內嗎？              | ⚠️ 只能比對使用者提供的範圍   |
| 4 判斷     | 偏離可接受嗎？批次可放行嗎？             | ❌ 永遠是 QA / QP             |

---

## A. 完整性 checklist

- [ ] 每頁有產品名、批號、頁碼（第 x 頁 / 共 y 頁），沒有缺頁
- [ ] MBR 版次 = 執行當時的有效版次
- [ ] 所有欄位已填；不適用欄位依程序劃 N/A 並簽名日期（不是留白）
- [ ] 關鍵步驟有**執行者 + 覆核者**兩個簽名，且**不是同一人**
- [ ] 簽名者在簽名清冊上、且當時具備該步驟的訓練資格（需對照訓練紀錄）
- [ ] 列印報表（秤量條、設備列印、層析圖摘要）已附上、簽名、與紀錄數值一致
- [ ] 清潔 / 換線紀錄與前批產品、清潔狀態標籤一致
- [ ] 中間品 / 製程中管制（IPC）結果都有填，且引用檢驗紀錄編號

## B. 一致性與計算

- [ ] 原料 / 包材批號：領料單 = 秤量紀錄 = 標籤
- [ ] 設備編號在紀錄中前後一致，校正 / 確效狀態在有效期內
- [ ] **時序合理**：步驟時間不倒流、不重疊到不可能；簽名日期不早於執行日期
- [ ] 計算重算一次：理論量、產率、物料平衡（容許範圍以 MBR 為準）
- [ ] 單位、有效位數、四捨五入規則一致
- [ ] 包裝：印字批號 / 效期、標籤發放數 = 使用數 + 銷毀數 + 退回數（標籤對帳）

## C. ALCOA+ 資料完整性訊號

| 原則                 | 在批次紀錄上看什麼                                         |
| -------------------- | ---------------------------------------------------------- |
| Attributable 可歸屬  | 每筆資料能對應到一個人與時間；無共用帳號、無代簽           |
| Legible 清晰         | 字跡可讀；更正為單線劃除、原值仍可見、附理由簽名日期       |
| Contemporaneous 同步 | 無預填（未來時間已填好）、無整頁同一筆跡同一墨色的事後補記 |
| Original 原始        | 原始數據（列印條、電子原始檔）存在且被引用，不是只有謄寫值 |
| Accurate 正確        | 數值與原始數據一致；計算正確                               |
| Complete 完整        | 含重測、重複注射、失敗結果；沒有被「挑掉」的數據           |
| Consistent 一致      | 時間戳記順序、格式一致                                     |
| Enduring 持久        | 用不可擦除筆、受控表單；無便利貼、無鉛筆                   |
| Available 可取得     | 審查與稽核時可調閱（含電子資料與 audit trail）             |

**特別警訊**（標 🔴 並請 QA 看）：數值長期完全相同或過於整齊；同一時間點一人出現在兩處；修正液 / 覆寫；「重測」「重新取樣」未見 OOS 或偏差編號；電子系統結果與紙本謄寫值不符。

## D. 偏差與變更引用

- [ ] 紀錄中每個偏離都有偏差編號；偏差狀態（調查中 / 已結案）已知
- [ ] 本批涉及的變更管制單（新原料供應商、設備變更、SOP 改版）已核准且在生效期間
- [ ] 若有偏差尚未結案 → 列為「放行前需 QA 決定」，交 [`deviation-capa-coordinator`](../agents/deviation-capa-coordinator.md) 整理狀態

---

## 常見發現（Top 10，自我檢查用）

1. 覆核欄空白，或執行者自己覆核自己
2. 更正沒有簽名、日期或理由
3. 不適用欄位留白而非 N/A
4. 列印報表沒附、沒簽、或與謄寫值不一致
5. 時間序不合理（覆核早於執行、跨班時間重疊）
6. 物料平衡 / 產率計算錯誤或超出範圍未見偏差
7. 用了已過期版次的 MBR 或表單
8. 設備校正過期仍被使用
9. 「重測」「重新取樣」沒有對應的 OOS / 偏差調查
10. 標籤對帳數字對不起來

---

## Output

依 [`batch-record-reviewer`](../agents/batch-record-reviewer.md) 的預檢報告格式：🔴 / 🟡 / ⚪ 分級、頁碼與步驟定位、未審查範圍、固定結尾「需 QA 審查與決定。AI 不判定批次可否放行。」

---

## Anti-patterns

- ❌ 只看最後一頁的結果，不看過程
- ❌ 把「AI 預檢 0 項」當作「紀錄沒問題」— 只代表在提供的頁面中未見
- ❌ 審查時順手補填或建議「補簽一下就好」
- ❌ 電子批次紀錄只看報表，不看 audit trail（是否需看由程序書規定）

---

## 待補完（contribution welcome）

- 醫材 DHR 專用欄位（UDI、序號、設備參數）checklist
- 電子批次紀錄（EBR）的 audit trail 審查重點
- 依劑型（無菌、口服固體、原料藥）的加查項目
