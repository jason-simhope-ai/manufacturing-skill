# profiles/machinery-eto/（機械設備製造 — ETO 接單設計 · alpha）

> 狀態：**🧪 alpha** — 已有內容，但**尚未經在職設備廠專案工程師、報價工程師或機械安全工程師驗證**。
> 徵求做特殊機、自動化設備、工具機 / 成型機類設備的報價、專案、安規、售後人員協助 review。

> ⛔ **重要 — 報價是工程估算，安全簽核是人的事。**
> 本 profile 產出的報價都是**工程估算草稿**，不是對客戶的承諾；正式價格與交期由權責主管核准。
> CE 標示、符合性聲明、風險評估、台灣安全資訊申報與任何安全簽核，都由**人類工程師 / 製造商權責人員**負責。**本 profile 任何內容都不是安全評估，也不是法規意見**；法規與標準細節一律標「需驗證」，數字一律是「範例」。

---

## 適合誰

- **接單設計（ETO）的設備廠**：特殊機、自動化設備 / 工作站、組裝與檢測設備、工具機 / 成型機 / 沖壓類設備的製造商與改造商
- 報價是**選配與規格**導向（不是逐件報價），專案以**工程專案**方式跑：規格 → 設計審查 → 長交期採購 → 組裝 → FAT / SAT → 安裝試車 → 售後
- 常服務**高安規要求的客戶**（客戶有自己的技術規範、驗收與文件要求）
- 範例公司一律稱「台灣機械設備製造商」

**不適合**：純零件加工廠（用 `cnc-machining` 或 core 就好）、目錄品 / 標準機量產且沒有客製設計的工廠。

## v0.1 alpha 有什麼

| 類型     | 項目                                                                                   | 做什麼                                                                       |
| -------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Agent    | [`eto-quote-engineer`](agents/eto-quote-engineer.md)                                   | 選配規格 → 成本結構 → 整機報價草稿；永遠列出假設與未定規格                  |
| Agent    | [`project-engineer`](agents/project-engineer.md)                                       | 規格凍結、設計審查、長交期採購、FAT / SAT 檢核準備；不替代 PM 的承諾        |
| Agent    | [`commissioning-service-coordinator`](agents/commissioning-service-coordinator.md)     | 安裝試車與售後：驗收紀錄、備品清單、問題分級升級；不承諾交期與到場時間      |
| Skill    | [`eto-quote-breakdown`](skills/eto-quote-breakdown.md)                                 | 配置選項表、工時與外購件估算、風險加成、假設清單、有效期與匯率條款（範例） |
| Skill    | [`spec-freeze-and-design-review`](skills/spec-freeze-and-design-review.md)             | 規格凍結清單、DR1 / DR2 / DR3 checklist、凍結後變更的重報價觸發條件         |
| Skill    | [`fat-sat-acceptance`](skills/fat-sat-acceptance.md)                                   | FAT / SAT 檢核表、遺留問題分級、驗收紀錄格式、保固起算條款範例             |
| Know-how | [`eto-vs-mts-quoting`](know-how/eto-vs-mts-quoting.md)                                 | MTS / MTO / CTO / ETO 差異、常見漏報項 Top 10、預算 vs 正式報價             |
| Know-how | [`machinery-safety-ce-basics`](know-how/machinery-safety-ce-basics.md)                 | ISO 12100 風險評估流程、安全功能、CE 技術文件、台灣申報要點（需驗證）      |
| Know-how | [`project-handover-and-after-sales`](know-how/project-handover-and-after-sales.md)     | 交機文件包、備品與耗材、售後 SLA 範例、問題升級矩陣                         |
| Hook     | [`pre-quote`](hooks/pre-quote.md)                                                      | 取代 core `pre-quote`：加上 ETO 閘門（規格未凍結不得正式報價、未定選配標 `[需澄清]`），**core 零件檢查原封保留** |

## 和 core 報價師怎麼分工

```
客戶詢價
  └─ pre-quote（本 profile 版）分流
       ├─ 零件 / 備品零件 / 有圖紙的加工件 → core quote-specialist（逐件報價，行為與 core 相同）
       └─ 整機 / 產線 / 自動化工作站 / 改造 → eto-quote-engineer
                └─ 整機內的自製件清單 → 交 core quote-specialist 算單件 → 彙整回整機成本
```

- 本 profile **不覆寫** core `quote-specialist`，只新增整機報價工程師；兩者透過 `pre-quote` hook 分流。
- 和 `cnc-machining` 可同時安裝（`bash adapters/claude-code/install.sh machinery-eto,cnc-machining`）：零件仍可交 `cnc-programmer` 評估可行性。
- 本 profile 是目前唯一覆寫 `pre-quote` 的 profile；若日後其他 profile 也覆寫，同時安裝會被 install.sh 的衝突掃描擋下。

## 三類內容說明

| 類別 | 本 profile 的做法                                                                                                           |
| ---- | --------------------------------------------------------------------------------------------------------------------------- |
| 強化 | 把 core 已有的報價與變更流程「加深」到整機層級：**報價假設清單**、**設計審查 checklist**、重報價觸發條件                   |
| 創造 | core 沒有的 ETO 專屬工作：**FAT / SAT 檢核**、驗收紀錄格式、保固起算、交機文件包與售後升級矩陣                              |
| 外包類 | 外包加工、外包組裝、委外檢測等管理**不在此 profile**（零件外包成本仍由 core 報價流程處理）                               |

## 它做什麼 / 不做什麼

| ✅ 會做                                          | ❌ 不會做                                             |
| ------------------------------------------------ | ----------------------------------------------------- |
| 攤開整機成本結構、列出假設與未定規格             | 出「正式報價」給未凍結的規格、承諾價格或交期          |
| 起草規格凍結表、DR 議程與待辦、變更影響摘要      | 核准規格變更、代簽凍結表 / DR / FAT / SAT 紀錄        |
| 起草 FAT / SAT 檢核表與驗收紀錄格式              | 判定安全功能合格、做風險評估結論                      |
| 列出安規「需要確認的問題」                       | 判定適用法規、宣告符合 CE 或台灣安全標準             |
| 整理售後問題、建議分級與升級對象                 | 承諾到場時間、解釋保固範圍、建議繞過安全功能          |

---

## 給不懂技術的同事：怎麼用

安裝需要 terminal，**可請 IT 或顧問協助**（`bash adapters/claude-code/install.sh machinery-eto`）。裝好後：

1. **先去識別化**：客戶名稱、客戶規範原文、機密圖面先拿掉或改代號。
2. **客戶來詢價**：貼上需求規格，說「幫我做整機報價的配置選項表和澄清問題清單」。
3. **接單後**：說「對照報價假設，幫我列規格凍結確認表」。
4. **FAT 前**：說「依凍結規格幫我起草 FAT 檢核表」。
5. **售後來電**：貼上客戶描述，說「整理成售後問題紀錄，建議等級與升級對象，回覆草稿不要寫時間承諾」。
6. **別做**：不要把 AI 的報價直接寄給客戶；不要把 AI 的話當安全判定或驗收依據。

---

## 還缺什麼（歡迎 contribute — 見 [profile.json](profile.json) 的 `wantedContributions`）

- `machine-safety-engineer` agent、`ce-technical-file-assembler` skill（只起草不簽核）
- 專案成本追蹤、長交期採購、備品報價 skills
- 遠端服務與資安邊界、機電軟介面審查 know-how
- 台灣機械設備器具安全標準 / 安全資訊申報逐條對照
- **在職設備廠專案 / 報價 / 安規工程師的驗證**（PR co-sign）

## 如何貢獻

修正內容：直接改 `agents/` / `skills/` / `know-how/` / `hooks/`，PR 說明「哪裡錯、正確是什麼、依據（標準 / 法規名稱與版次）」。要推進到 beta / complete，先開 [Profile contribution issue](../../.github/ISSUE_TEMPLATE/profile-contribution.yml) 對齊範圍。

**請勿在 PR 或 issue 中放入真實客戶規範、報價單或機密圖面** — 範例一律使用合成資料。

商業合作請聯絡 [Jason Lin](mailto:jasonlin@simhope.com.tw)。
