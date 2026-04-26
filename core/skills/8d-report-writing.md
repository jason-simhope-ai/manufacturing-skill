---
name: 8d-report-writing
displayName: 8D 報告撰寫
description: Eight-Disciplines problem solving — D1-D8 SOP, common pitfalls, customer-deliverable template
when_to_use: User invokes /8d, customer complaint received, NCR escalated, on-error hook triggered for severe defect
---

# 8D 報告撰寫 Skill

由 **quality-inspector** 主導；`/8d` command 觸發此 skill。

> **8D**（Eight Disciplines）由 **Ford 在 1980s** 提出，是製造業客訴 / 重大不良處理的世界共通方法。
> 多數汽車業客戶（IATF 16949 體系）強制要求 8D 格式。
> 部分新版加 D9（將學習轉移到其他產品線）— 此 skill 涵蓋 D1-D8 主流版。

---

## 八個步驟（細節）

### D1. Team — 團隊組成

**規模**：3-7 人，跨部門。**少於 3 人**容易盲點，**多於 7 人**會議效率低。

**必要角色**：

- Leader（通常品管課長或工程師）
- 製程相關（生管 + 操作員）
- 設計 / 工程
- 客戶接口（業助）

**選用角色**：

- 採購（材料相關不良）
- 設備（機台異常）
- 模具 / 治具（射出 / CNC 變更需求）

### D2. Problem Description — 問題描述

用 **5W2H** 量化。**不要用「客戶說我們不良」這種空話**。

| 維度          | 該寫的內容                                   |
| ------------- | -------------------------------------------- |
| WHO           | 誰發現？我們 OQC、客戶 IQC、終端使用者？     |
| WHAT          | 具體不良 — 量化（規範 vs 實測）、不良型態    |
| WHEN          | 發現時間、製造日期、影響批次                 |
| WHERE         | 哪台機、哪個工序、哪批料                     |
| WHY (initial) | 第一線判斷 — 之後 D4 會深入                  |
| HOW           | 如何被發現的（量測 / 目視 / 客戶端使用）     |
| HOW MANY      | **量化**：影響件數、客戶端庫存、金額損失估算 |

### D3. Containment — 暫時對策（防止繼續流出）

「**先止血**」階段。**3 個位置**都要管：

1. **客戶端庫存**：請客戶停用 + 隔離 + 100% 檢
2. **在途貨**：通知物流 + 收回或標識
3. **我廠在製品 / 成品庫存**：100% 全檢，分良品 vs 不良
4. **我廠生產線**：暫停或加嚴抽檢，等 D5 對策上線

**完成 D3 的標誌**：「不會再有相同不良流出去」。

### D4. Root Cause — 根因分析

最常被做爛的一段。**直接根因**（why this defect happened）+ **系統根因**（why our process didn't catch it / prevent it）**兩個都要找**。

**5 Why 範例**：

```
不良：孔距 50.08（規範 50±0.05）
Why 1：CNC#3 的 D4 銑刀磨耗
Why 2：第 80 件後刀具進入磨耗加速區
Why 3：操作員未換刀
Why 4：SOP 未明定強制換刀件數，依賴目視判斷
Why 5：當初 SOP 是試切時定的，沒回頭驗證量產時的真實壽命
```

**直接根因**：刀具磨耗。
**系統根因**：SOP 沒強制換刀，量產驗證沒做。

> ❌ 在 Why 5 寫「操作員疏忽」就停 — **不是根因**。
> 問「為什麼 SOP 沒擋住操作員疏忽？」 → 才是系統思考。

**工具**：

- 5 Why（簡單問題）
- Fishbone / Ishikawa（複雜，6M：Man / Machine / Material / Method / Measurement / Mother nature）
- FTA Fault Tree Analysis（高安全件 / 多原因交互）

### D5. Permanent Action — 永久對策

對應 D4 的兩個根因：

| 根因類型             | 對策類型                                  |
| -------------------- | ----------------------------------------- |
| 直接根因（刀具磨耗） | 操作改變 — 換刀策略 / 切削參數 / 量測加嚴 |
| 系統根因（SOP 不夠） | **結構改變** — SOP 強制 / 防呆 / 機制變更 |

**對策層級（由弱到強）**：

1. 教育訓練（最弱）— 人會忘
2. 警告標示 — 人會無視
3. 程序 / SOP — 人會跳工序
4. **設備能力提升**（更精度）
5. **防呆設計**（Poka-Yoke）— 物理上不能犯錯
6. **取消來源**（不再做這件事）— 最強

> 永久對策**至少要到第 3 層**。第 5/6 層最理想。

### D6. Verification — 對策實施 + 驗證

實施 ≠ 有效。要有**數據**：

- 製程數據（SPC 對策前 vs 後）
- 抽檢結果（連續 N 件 / N 批 OK）
- Cpk / Ppk 變化
- 客訴件數變化（追蹤 1-3 個月）

**完成 D6 的標誌**：「我們有證據說對策真的解決了問題」。

### D7. Prevent Recurrence — 預防再發

**橫向展開**：類似情境會不會在其他工序 / 其他產品再發生？

更新：

- ☑ PFMEA — 重新評 S/O/D，特別是 D（detection）分數
- ☑ Control Plan — 新增控制點
- ☑ SOP — 加強制要求
- ☑ 培訓教材 — 帶入 lessons learned
- ☑ 防呆裝置 — 物理機制
- ☑ 量具 / 機台 / 治具規範 — 升級需求

**完成 D7 的標誌**：「同類根因不會在其他地方重演」。

### D8. Closure — 結案 + 團隊感謝

- ☑ 客戶 sign-off（書面）
- ☑ Lessons learned 入庫（內部知識管理）
- ☑ 團隊感謝會議（不只是 leader 的功勞）

---

## 8D 報告 template（送客戶版）

```markdown
# 8D Report — [編號]

| Item              | Detail                      |
| ----------------- | --------------------------- |
| Issue ID          | NCR-... or 客戶單號         |
| Customer          | [客戶名]                    |
| Part              | [件號] / [品名]             |
| Quantity Affected | [件數]                      |
| Date Reported     | [日期]                      |
| Report Date       | [日期]                      |
| Status            | Open / In Progress / Closed |

## D1. Team

[列名單 + 角色]

## D2. Problem Description

[5W2H + 量化]
[附現象照片 / 量測數據]

## D3. Containment Actions

[時間] [動作] [責任人] [完成日]

## D4. Root Cause

**Direct Root Cause**: [...]
**Systemic Root Cause**: [...]
**Analysis Method**: 5 Why / Fishbone / FTA
[附分析過程]

## D5. Permanent Corrective Action

[對應 D4 兩個根因，列具體措施 + 對策層級]

## D6. Verification

[數據 / SPC / Cpk / 抽檢結果]
[附圖表]

## D7. Prevent Recurrence

[PFMEA 更新 / Control Plan 更新 / SOP 更新 / 橫向展開]

## D8. Closure

Customer Sign-off: [姓名] [日期]
Lessons Learned File: [內部路徑]
Team Recognition: [日期]

---

Submitted: [姓名] [日期]
Approved: [姓名] [日期]
```

---

## Anti-patterns（最常見的廢 8D）

| 病灶                       | 具體現象                                       |
| -------------------------- | ---------------------------------------------- |
| **D2 不量化**              | 「客戶反應有不良」— 沒影響件數、沒金額、沒範圍 |
| **D3 只管自己廠**          | 客戶端在途、客戶端庫存沒控制 — 不良繼續流出    |
| **D4 停在第一層**          | 「操作員疏忽」「製程波動」這種空話當根因       |
| **D5 寫教育訓練**          | 「強化教育訓練」「加強巡檢」— 不是對策，是輔助 |
| **D5 跟 D4 對不上**        | 根因是 A，對策卻是 B — 對策不會有效            |
| **D6 無數據**              | 「對策已實施」就完事，沒證據對策有效           |
| **D7 不更新 PFMEA**        | 同類問題下次還會出                             |
| **D8 忘 sign-off**         | 客戶不簽認 = 8D 不算結案                       |
| **整份用模板填空，沒內容** | AI 幫忙時要警告 — 8D 是要解決問題不是寫報告    |

---

## Checklist（送客戶前自檢）

- [ ] D2 5W2H 完整、有量化、有圖
- [ ] D3 三個位置（客戶端 / 在途 / 我廠）都管到
- [ ] D4 根因有 5 Why 過程，分直接 + 系統
- [ ] D5 對策層級至少第 3 層
- [ ] D6 有 SPC / 數據 / 圖表
- [ ] D7 PFMEA / SOP / Control Plan 至少 3 個更新
- [ ] D8 客戶 sign-off 欄已留白給客戶簽

---

## 連結

- Command：[`/8d`](../commands/8d.md)
- Hook：[`on-error`](../hooks/on-error.md)（嚴重不良自動 trigger 8D 開啟）
- Know-how：[`fmea-pfmea`](../know-how/fmea-pfmea.md)（D7 要更新的對象）
- Agent：[`quality-inspector`](../agents/quality-inspector.md)（主導）
