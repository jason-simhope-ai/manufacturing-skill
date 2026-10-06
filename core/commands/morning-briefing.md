---
name: morning-briefing
description: 廠長每日早會懶人包 — 一個指令出未完工單、瓶頸、延誤風險、昨日 NCR、今日重點
allowed-tools: [Read, Grep, Glob, Bash, mcp__manufacturing-scheduler__list_work_orders, mcp__manufacturing-scheduler__get_machine_load, mcp__manufacturing-scheduler__find_bottlenecks, mcp__manufacturing-scheduler__get_capacity_summary]
argument-hint: "[選用：日期 YYYY-MM-DD，預設今日]"
---

# /morning-briefing — 廠長 / 生管 / 業務每日早會懶人包

每天早上 8 點打這個。AI 自動爬 ERP / manufacturing-scheduler / 昨日 inspection log，整理成 5 分鐘看完的早會稿。

> **注意：沒有 MCP 連線時，輸出是模擬資料。**
> 若 `erp-connector` / `manufacturing-scheduler` 沒有接上真實系統，本指令只會使用
> `infra/mcp-servers/scheduler-mcp/mock-data/` 內的 mock data。此時回覆**必須**在開頭與每個數字區塊標示
> 「模擬資料」，不得當作真實訂單 / 機台狀態呈現，也不得改用 `git log` 或其他推測方式補齊狀態。
> 沒有任何資料來源時，直接回答「無法取得資料」。

## 使用範例

```
/morning-briefing
/morning-briefing 2026-04-26
/morning-briefing yesterday        # 補昨日的早會（請假回來用）
```

## 流程

1. 透過 MCP server `manufacturing-scheduler`（`infra/mcp-servers/scheduler-mcp`）取所有未完工單 + 機台負載（皆為唯讀）：
   - 未完工單 → `list_work_orders`（預設回 50 筆、上限 200；`has_more` 為 true 時用 `offset` 續查）
   - 機台負載 → `get_machine_load`；瓶頸 → `find_bottlenecks`（`load_pct >= threshold`）；整體產能 → `get_capacity_summary`
2. 讀 `infra/mcp-servers/erp-connector/` — 取今日預計出貨清單 + 昨日新進 PO
3. 讀 `logs/inspections/` （如有）— 統計昨日 IPQC / FQC / OQC 結果與 NCR
4. 讀 `logs/exceptions/` — 昨日異常事件
5. **dispatch** 給多個 agent 並聯整合：
   - `production-planner` 算瓶頸與延誤風險
   - `quality-inspector` 整理昨日不良統計
   - `sales-coordinator` 列出今日承諾交期單
   - `inventory-manager` 列出今日缺料風險
6. 統一輸出格式（見下）

## 期待輸出格式

```
═══════════════════════════════════════════════════
  早會簡報 · 2026-04-26（週一）· 上午 8:00
═══════════════════════════════════════════════════

📊 昨日結算
  完工：12 張工單（98 件）
  進度：✅ 全達標
  不良：FQC 2 件 NG（W-...123 SUS304 支架，孔距超差）
  異常：1 次（CNC#3 14:20 主軸警報，已重啟 OK）

🎯 今日重點
  出貨：3 張單（客戶 A × 100、客戶 B × 50、客戶 C × 200）
  完工目標：8 張工單
  排程開工：5 張新單

⚠️ 風險警示
  [瓶頸] CNC#3 本週負載 95% — W-...125 急單建議改 CNC#5
  [缺料] SUS304-φ20 缺 30 支，今日不下單將影響下週 W-...130 開工
  [延誤] W-...118 預估完工 4/28 → 客戶承諾 4/27，須加班或溝通

📋 待裁示
  - 客戶 D 詢價（鈦合金件，量 5）— 是否接？毛利低
  - 客戶 A 客訴件 8D 進度 → D5 永久對策待裁示

🔧 設備
  CNC#3 例行保養：本週四下午 → production-planner 已預排
  量具校驗：CMM ABC-001 下月到期，採購單已開
```

---

## 沒接 ERP / MCP 時的降級行為

如果 `manufacturing-scheduler` 沒回應，AI 會：

1. 改用 `infra/mcp-servers/scheduler-mcp/mock-data/` 的 mock data，並在簡報最上方標明「模擬資料：未連線 ERP / MES，以下數字僅供示範，不可用於早會決策」
2. mock data 也不可用時，回答「無法取得資料」，**不要**用 `git log`、commit 紀錄或檔案修改時間推測工單 / 機台狀態
3. 提示「請執行 `/manufacturing doctor` 檢查 MCP 連線」

---

## 客製化

每家工廠的早會風格不同。有公司想要：

- 含產量數字（pcs、產值）
- 含品質指標（不良率 PPM、Cpk）
- 含客戶滿意度（客訴件數、退貨率）
- 含人員（出勤、加班時數）

可以複製此檔到 `profiles/<your-vertical>/commands/morning-briefing.md` 改寫，install 時會 override core 預設。

---

## Anti-patterns

- ❌ 把這個當「今日代辦清單」 — 它是**情勢簡報**，待辦清單是 production-planner 的事
- ❌ 早會花 30 分鐘看這個 — 設計上 5 分鐘讀完，30 分鐘讓人開會討論「裁示」項
- ❌ 不打開直接相信 AI 的判讀 — 有風險警示要去現場確認
