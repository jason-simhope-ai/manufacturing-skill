---
name: spec-freeze-and-design-review
displayName: 規格凍結與設計審查
description: Engineer-to-order specification freeze checklist (functional, performance, utilities, safety market, interfaces, acceptance criteria, documentation), staged design-review checklists (DR1 concept / DR2 detailed / DR3 release), and the triggers that force a re-quote after a post-freeze change
when_to_use: project-engineer freezes the specification after order, prepares or records a design review, evaluates a customer change request after freeze, or checks whether a change should go back to eto-quote-engineer
status: alpha
---

# 規格凍結與設計審查 Skill

> ⚠️ **Alpha**：依 ISO 9001 §8.3（設計與開發）與設備廠專案一般實務整理，**未經在職設備專案工程師驗證**。門檻數字皆為「範例」。安全相關審查項目只確認「有做、有人負責、有紀錄」，**不是安全評估**。

由 **project-engineer** 主導；變更流程沿用 core [`engineering-change-process`](../../../core/skills/engineering-change-process.md)。

---

## 流程概覽

```
接單（報價假設清單交接）
  ↓
規格凍結（本 skill A 段）— 客戶 + 我方 PM 簽署
  ↓
DR1 概念 / 佈置審查 → DR2 詳細設計審查 → DR3 出圖 / BOM 釋出前審查（B 段）
  ↓                         ↑
凍結後變更 → ECR（core）→ 重報價判斷（C 段）
  ↓
長交期件下單 → 組裝 → FAT（見 fat-sat-acceptance）
```

---

## A. 規格凍結清單

逐項確認「客戶書面確認」與「與報價假設是否一致」兩欄。

| 類別         | 項目                                                                     | 客戶書面確認 | 與報價假設一致？ |
| ------------ | ------------------------------------------------------------------------ | ------------ | ---------------- |
| 功能         | 製程內容、工件範圍（尺寸 / 重量 / 材質）、換線方式、選配項全部定案       | ☐            | ☐                |
| 性能         | 節拍 / 產能、精度、良率等驗收指標**及其量測方法**                        | ☐            | ☐                |
| 公用設施     | 電壓 / 頻率 / 接地型式、氣壓與流量、冷卻水、排氣 / 集塵                  | ☐            | ☐                |
| 安全與法規   | 目標市場、客戶要求的安全規範、適用法規清單（需安規工程師確認）           | ☐            | ☐                |
| 控制與介面   | 控制器 / 指定品牌、通訊介面、與上下游設備的訊號交握、資料上拋需求       | ☐            | ☐                |
| 佈置         | 占地、高度、維修空間、搬入路徑、拆機分箱限制                             | ☐            | ☐                |
| 驗收         | FAT / SAT 項目、驗收工件提供方式、遺留問題處理原則                       | ☐            | ☐                |
| 文件與訓練   | 文件語言、文件清單、訓練天數與地點                                       | ☐            | ☐                |
| 商務連動     | 交貨條件（INCOTERMS + 地點）、保固起算、付款里程碑                       | ☐            | ☐                |

**凍結條件**：所有列已確認；不一致的列已判斷是否觸發重報價（C 段）；凍結表由客戶與我方 PM 簽署（AI 不代簽）。

> 未能凍結的項目（例：客戶產品仍在開發）→ 明列為「凍結例外」，寫明最晚確認日與對交期 / 成本的影響。

---

## B. 設計審查 checklist

每次 DR 輸出：出席者、審查範圍（圖號 / 版次）、發現、待辦（負責人 + 期限）、結論（通過 / 有條件通過 / 不通過 — 由主審人決定）。

### DR1 概念 / 佈置審查

- [ ] 規格凍結表的每一項都有對應的設計方案
- [ ] 佈置圖：占地、維修空間、操作者位置、物流動線
- [ ] **風險評估已啟動**（依 ISO 12100 流程，見 [`machinery-safety-ce-basics`](../know-how/machinery-safety-ce-basics.md)），有負責人
- [ ] 主要安全防護概念（固定護罩、聯鎖門、感應式防護等）已提出
- [ ] 長交期件清單與建議下單時點
- [ ] 運輸方案：最大分箱尺寸 / 重量 vs 貨櫃或車輛限制
- [ ] 沿用 / 修改 / 全新模組比例與報價假設比較

### DR2 詳細設計審查

- [ ] 強度 / 剛性 / 壽命計算有紀錄（關鍵結構與傳動件）
- [ ] 電控圖：電源、接地、保護元件、急停與安全迴路（依 IEC 60204-1 原則 — 設計判定由電控工程師負責）
- [ ] 安全功能清單與要求的性能等級（如適用 ISO 13849-1 PL）— 由安規 / 設計工程師填寫
- [ ] 可維修性：保養點可及性、易損件更換時間、上鎖掛牌（LOTO）點
- [ ] 介面：與客戶上下游設備的訊號表、機械介面圖
- [ ] 可組裝性與可測試性；FAT 測試方法可行
- [ ] 風險評估已更新至詳細設計

### DR3 出圖 / BOM 釋出前審查

- [ ] 圖面、BOM 版次一致（EBOM → MBOM 見 core [`bom-management`](../../../core/skills/bom-management.md)）
- [ ] 前兩次 DR 待辦全部關閉或有核准的例外
- [ ] FAT / SAT 檢核表草稿已送客戶（見 [`fat-sat-acceptance`](fat-sat-acceptance.md)）
- [ ] 手冊與技術文件的撰寫分工與時程
- [ ] 安規文件（風險評估、標準清單）狀態 — 由安規工程師確認

---

## C. 凍結後變更 → 重報價觸發條件

凍結後任何變更先開 ECR（core 流程），再依下表判斷是否回 [`eto-quote-engineer`](../agents/eto-quote-engineer.md) 重報價。**任一條成立 → 觸發重報價評估**（是否向客戶收費由 PM / 主管決定）。

| #   | 觸發條件（門檻為範例）                                              |
| --- | ------------------------------------------------------------------- |
| 1   | 新增 / 刪除選配項，或改變選配內容                                   |
| 2   | 性能驗收指標變更（節拍、精度、工件範圍）                            |
| 3   | 目標市場或安全規範變更（新增法規、客戶安全規範改版）                |
| 4   | 控制器 / 指定品牌變更，或介面規格變更                               |
| 5   | 公用設施或現場條件與凍結表不同                                      |
| 6   | 變更影響已下單或已加工的長交期件 / 自製件                            |
| 7   | 預估設計工時增加 > 40 小時，或成本影響 > 合約金額 2%（範例）        |
| 8   | 交期要求提前                                                        |
| 9   | 驗收工件、驗收方法或文件語言變更                                    |
| 10  | 匯率 / 原物料超過合約條款門檻                                      |

輸出「變更影響摘要」：範圍 / 成本 / 交期 / 安全（風險評估是否需更新）/ 文件 / 已下單件 — 交 PM 決策。

---

## Anti-patterns

- ❌ 「先畫再說，規格邊做邊定」— 沒有凍結表就沒有變更的基準
- ❌ DR 只有會議、沒有待辦與關閉紀錄
- ❌ 風險評估等到出貨前才補 — 安全措施應在設計階段決定
- ❌ 客戶口頭追加 → 直接改圖，沒有 ECR、沒有重報價評估
- ❌ 長交期件在規格凍結前下單卻沒有標示風險與核准

## 連結

- Agent：[`project-engineer`](../agents/project-engineer.md)
- 前一步：[`eto-quote-breakdown`](eto-quote-breakdown.md)
- 下一步：[`fat-sat-acceptance`](fat-sat-acceptance.md)
- Core：[`engineering-change-process`](../../../core/skills/engineering-change-process.md)、[`eco-ecn`](../../../core/know-how/eco-ecn.md)、[`capacity-planning`](../../../core/skills/capacity-planning.md)
