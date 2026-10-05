# profiles/food-processing/（食品加工 · alpha）

> 狀態：**🧪 alpha** — 已有內容，但**尚未經在職食品廠 HACCP 小組成員驗證**。
> 徵求有 HACCP / ISO 22000 實務經驗的食品廠品保、食品技師協助 review。

> ⛔ **重要**：本 profile 任何內容都**不能取代**合格的 HACCP 管制小組、食品技師 / 專責人員或法規顧問。AI 不判定 CCP 偏差能否放行、不決定回收、不代為通報主管機關 — **一律由人簽核**。文中管制界限都是「範例」，標「需驗證」的法規細節請以衛福部食藥署現行公告為準。

---

## 適合誰

- 食品加工廠的**接班人、品保、生管**，想用 AI 幫忙整理 HACCP 文件、檢查紀錄、跑追溯演練
- 已有（或正在建立）HACCP / ISO 22000 / FSSC 22000 / TQF 制度的工廠
- 烘焙、飲料、冷凍、即食餐、醬料、零食、乳品、肉品水產等批次生產型工廠

## v0.1 alpha 有什麼

| 類型     | 項目                                                                           | 做什麼                                                             |
| -------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Agent    | [`haccp-coordinator`](agents/haccp-coordinator.md)                             | 危害分析、CCP 判定、監控紀錄檢查、偏差報告草稿、稽核準備           |
| Agent    | [`traceability-officer`](agents/traceability-officer.md)                       | 一步向前 / 一步向後追溯、客訴批號查詢、回收演練                    |
| Skill    | [`haccp-plan-review`](skills/haccp-plan-review.md)                             | 12 步驟 / 7 原則 checklist、CCP 判定樹                             |
| Skill    | [`batch-traceability-recall-drill`](skills/batch-traceability-recall-drill.md) | 回收模擬：計時、質量平衡、斷點、改善事項                           |
| Know-how | [`haccp-iso22000-basics`](know-how/haccp-iso22000-basics.md)                   | 7 原則、PRP / GHP、CCP vs OPRP、紀錄、稽核常見缺失                 |
| Know-how | [`food-defects-and-ccp-examples`](know-how/food-defects-and-ccp-examples.md)   | 殺菌 / 冷藏 / 金屬檢測 / 過敏原 / 異物的 CCP 範例                  |
| Hook     | [`pre-ship`](hooks/pre-ship.md)（取代 core 版）                                | 出貨前加查 CCP 紀錄簽核、CoA、批號 / 有效日期、過敏原標示、溫度紀錄 |

## 它做什麼 / 不做什麼

| ✅ 會做                            | ❌ 不會做                    |
| ---------------------------------- | ---------------------------- |
| 檢查紀錄有沒有漏填、超標、漏簽     | 簽核 CCP 偏差、放行產品      |
| 起草偏差報告、8D、教育訓練題目     | 決定要不要回收、通報主管機關 |
| 用白話解釋 HACCP / ISO 22000 概念   | 當作法規最終解釋             |
| 算追溯影響範圍與質量平衡           | 自己設定你工廠的管制界限     |

---

## 給不懂技術的接班人：怎麼搭配 LINE 用

安裝需要用到 terminal，**可以請 IT 或顧問幫你裝**（`bash adapters/claude-code/install.sh food-processing`）。裝好後日常用法：

1. **紀錄拍照 → 問 AI**：把殺菌紀錄、冷藏庫溫度表的照片或 LINE 群組裡的文字貼給 Claude，說「幫我檢查這張 CCP 紀錄有沒有漏簽或超標」。
2. **AI 回覆 → 貼回 LINE**：請它「整理成 5 行以內、可以貼到 LINE 群組的摘要」，再轉給品保主管。
3. **客訴來了**：貼上客訴內容與包裝上的批號，說「幫我做追溯草稿」。
4. **每季一次**：說「幫我出一題回收演練」，照著跑、計時、留紀錄。
5. **別貼**：客戶個資、供應商合約價格；**別把 AI 回覆直接當放行依據**。

> 不想裝？也可以把 `know-how/` 兩份文件內容複製到 claude.ai 的專案知識裡，用同樣的問法 — 效果較陽春，但同樣適用上面的界線。

---

## 還缺什麼（歡迎 contribute — 見 [profile.json](profile.json) 的 `wantedContributions`）

- `food-qa-inspector` agent（微生物檢驗、感官評估、留樣）
- `allergen-management`、`shelf-life-prediction`、`cleaning-validation`（CIP/SIP）skills
- GHP 逐條對照、FSSC 22000 額外要求、Halal / Kosher、出口美國 FSMA know-how
- 可直接複製貼上的 LINE / claude.ai 提示詞包
- **在職食品廠 HACCP 小組成員的驗證**（PR co-sign）

## 如何貢獻

修正既有內容：直接改 `agents/` / `skills/` / `know-how/` / `hooks/`，並在 PR 說明「哪裡錯、正確是什麼、依據」。要推進到 beta / complete，先開 [Profile contribution issue](../../.github/ISSUE_TEMPLATE/profile-contribution.yml) 對齊範圍。

商業合作（依貴廠產品與 HACCP 計畫客製）：[Jason Lin](mailto:jasonlin@simhope.com.tw)。
