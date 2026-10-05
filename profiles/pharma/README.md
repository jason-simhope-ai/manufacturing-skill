# profiles/pharma/（製藥 / 醫材 GMP · alpha）

> 狀態：**🧪 alpha** — 已有內容，但**尚未經在職 GMP QA、確效或法規人員驗證**。
> 徵求有藥廠 / 醫材廠 QA、偏差調查、批次紀錄審查、確效實務經驗的人協助 review。

> ⛔ **重要 — AI 輸出永遠不是 GMP 紀錄。**
> 本 profile 任何內容都**不能取代** QA / QP（或依法規授權的品質單位放行人員）的放行決定、法規事務（RA）的判斷，或經過確效的電腦化系統。AI 不結案偏差、不核准 CAPA、不判定 OOS 無效、不放行批次。所有輸出標示 `AI-DRAFT — 非 GMP 紀錄`，只能當草稿參考，必須由權責人員在受控系統中重新產出、審核、簽署。
> 本 plugin 本身**未經電腦化系統確效（CSV）**。在 GxP 範圍內使用前，請由貴公司 QA 依預期用途評估；建議先用在非 GxP 的草稿、教育訓練與文件整理。

---

## 適合誰

- 原料藥（API）、製劑、醫療器材工廠的 **QA、QC、生產主管、偏差調查員、接班人**
- 想用 AI 幫忙**想清楚、寫清楚**偏差調查，或在正式審查前**先抓批次紀錄漏洞**的人
- 正在準備 PIC/S GMP 查核、ISO 13485 稽核，想做自我檢查的團隊

## v0.1 alpha 有什麼

| 類型     | 項目                                                                                       | 做什麼                                                                     |
| -------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Agent    | [`deviation-capa-coordinator`](agents/deviation-capa-coordinator.md)                       | 偏差事實整理、分類建議、根因調查架構、影響評估提問、CAPA / 有效性確認草稿 |
| Agent    | [`batch-record-reviewer`](agents/batch-record-reviewer.md)                                 | 批次紀錄完整性預檢：漏填、漏簽、計算、時序、ALCOA+ 訊號、偏差引用         |
| Skill    | [`deviation-investigation-5whys-fishbone`](skills/deviation-investigation-5whys-fishbone.md) | Is / Is-not、魚骨圖 6M、證據計畫、5 Whys、影響評估、CAPA 有效性確認       |
| Skill    | [`batch-record-completeness-review`](skills/batch-record-completeness-review.md)           | 審查員 checklist、ALCOA+ 資料完整性檢查、常見發現 Top 10                  |
| Know-how | [`gmp-gxp-basics`](know-how/gmp-gxp-basics.md)                                             | GMP 支柱、文件層級、GDP、偏差 vs OOS vs OOT、ALCOA+、查核常見缺失          |
| Know-how | [`validation-and-change-control`](know-how/validation-and-change-control.md)               | DQ/IQ/OQ/PQ、製程確效、CSV、變更管制流程、再確效觸發條件                  |
| Hook     | [`pre-batch-release`](hooks/pre-batch-release.md)                                          | 放行前文件齊備檢查：批次紀錄已審、CoA、偏差 / OOS 已結、變更已核准       |

## 它做什麼 / 不做什麼

| ✅ 會做                                    | ❌ 不會做                                  |
| ------------------------------------------ | ------------------------------------------ |
| 整理偏差事實、起草調查架構與 CAPA 草稿     | 結案偏差、核准 CAPA、判定 CAPA 有效        |
| 在正式審查前挑出批次紀錄的漏填漏簽         | 放行批次、寫「審查通過」                   |
| 用白話解釋 GMP / ALCOA+ / 確效概念、出考題 | 判定 OOS 無效、決定法規變更類別或通報      |
| 列出影響評估與變更管制要問的問題           | 產出、修改或取代任何 GMP 紀錄              |

---

## 給不懂技術的接班人：怎麼搭配 LINE 用

安裝需要用到 terminal，**可以請 IT 或顧問幫你裝**（`bash adapters/claude-code/install.sh pharma`）。裝好後日常用法：

1. **先去識別化再貼**：把偏差描述或批次紀錄頁面貼給 Claude 前，拿掉病患資料、客戶名稱、未公開配方與製程參數；批號可用代碼。
2. **偏差來了**：貼上事情經過，說「幫我整理成偏差事實摘要，並用魚骨圖列可能原因與要查的證據」。
3. **送 QA 審查前**：貼上批次紀錄的頁面文字，說「幫我做完整性預檢，只列發現，不要下結論」。
4. **AI 回覆 → 貼回 LINE**：請它「整理成 5 行以內、可以貼到 LINE 群組的摘要，開頭標 AI-DRAFT」，再轉給 QA 主管討論。
5. **別做**：不要把 AI 回覆直接貼進批次紀錄、偏差系統或任何正式表單；**不要把 AI 的話當放行或結案依據**。

> 不想裝？也可以把 `know-how/` 兩份文件內容複製到 claude.ai 的專案知識裡，用同樣的問法 — 效果較陽春，但同樣適用上面的界線。

---

## 還缺什麼（歡迎 contribute — 見 [profile.json](profile.json) 的 `wantedContributions`）

- `qa-release-support` agent（放行文件包彙整，只彙整不放行）
- `oos-oot-investigation`、`cleaning-validation`、`process-validation`、`apr-pqr` skills
- AI 工具本身的 CSV 指引、Annex 1 無菌、ISO 13485 / 台灣醫材 QMS 深入 know-how
- 台灣 PIC/S GMP 查核常見缺失逐條對照
- 可直接複製貼上的 LINE / claude.ai 提示詞包
- **在職 GMP QA / 確效人員的驗證**（PR co-sign）

## 如何貢獻

修正既有內容：直接改 `agents/` / `skills/` / `know-how/` / `hooks/`，並在 PR 說明「哪裡錯、正確是什麼、依據（法規 / 指引名稱與版次）」。要推進到 beta / complete，先開 [Profile contribution issue](../../.github/ISSUE_TEMPLATE/profile-contribution.yml) 對齊範圍。

**請勿在 PR 或 issue 中放入任何真實批次紀錄、偏差報告或公司機密** — 範例一律使用合成資料。

由於合規敏感性，商業合作（依貴廠程序書客製、私下協作）請聯絡 [Jason Lin](mailto:jasonlin@simhope.com.tw)。
