# Architecture — manufacturing-plugin 六層架構詳解

> 給開發者、SI、認真要 fork 的人看的內部架構文件。
> 老闆 / IT / 終端使用者請看 `docs/explainers/` 內的圖卡。

---

## TL;DR

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — USE         /quote /order-status /bom-check ...  │
├─────────────────────────────────────────────────────────────┤
│  Layer 2 — FLOW        報價→接單→排程→生產→檢驗→出貨        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3 — ROLE        5 core agents + profile agents       │
├─────────────────────────────────────────────────────────────┤
│  Layer 4 — INFRA       MCP servers, on-prem LLM, files      │
├─────────────────────────────────────────────────────────────┤
│  Layer 5 — REF         ISO 9001, IATF, Lean, OEE, SPC ...   │
├─────────────────────────────────────────────────────────────┤
│  Layer 6 — HOOK        pre-quote, post-order, on-error ...  │
└─────────────────────────────────────────────────────────────┘
        │                                              │
        ▼ (core 層) ─────────────────── ▼ (profile 層 — overlay)
   普世製造業共通                    垂直領域加碼
   存放：core/                      存放：profiles/<vertical>/
```

---

## Layer 1 — USE 入口層

**內容**：使用者每天會打的 slash command。

**位置**：`core/commands/*.md` + `profiles/<vertical>/commands/*.md`（profile 可加碼）

**設計原則**：

- 名字短、直覺、口語化（`/quote` 而非 `/initiate-quote-process`）
- 每個 command 對應 1~N 個 agent + 1 個 skill
- frontmatter 含 `allowed-tools`, `argument-hint`，符合 Claude Code 規範

**v1 內建**：

- `/quote` — 報價
- `/order-status` — 訂單狀態
- `/bom-check` — BOM 健檢
- `/inspect` — 檢驗（IQC/IPQC/FQC/OQC）
- `/install-profile` — 切換 profile
- `/manufacturing` — plugin meta 資訊

---

## Layer 2 — FLOW 流程層

**內容**：製造業的 6 段普世流程。

**位置**：`core/skills/01-報價.md` ~ `06-出貨.md`

```
報價 → 接單 → 排程 → 生產 → 檢驗 → 出貨
 1     2      3      4      5      6
```

**為什麼是 6 段（不是 5 也不是 7）**：

- 來自 SIMHOPE 實務 + ISO 9001 / IATF 16949 體系
- 「檢驗」獨立是因為 IQC/IPQC/FQC/OQC 是 4 個不同階段、不同 agent 行為
- 「研發 / 打樣」**沒放 core**（不是所有工廠都有），改放 CNC profile 的 know-how

**每段 skill 結構**：

- Process（步驟）
- Checklist
- Anti-patterns
- 連結到上下游 skill / agent / hook

---

## Layer 3 — ROLE 角色層

**內容**：agent persona — AI 在不同情境下扮演的「人」。

**位置**：`core/agents/` + `profiles/<vertical>/agents/`

**Core 5 隻**（普世）：

- `quote-specialist` — 報價師
- `sales-coordinator` — 業助
- `production-planner` — 生管
- `quality-inspector` — 品管
- `inventory-manager` — 倉管

**CNC profile 加 4 隻**：

- `cnc-programmer`
- `tool-life-engineer`
- `fixture-designer`
- `prototype-coordinator`

**Agent 之間如何協作**：

- `quote-specialist` 看到 CNC 件 → dispatch `cnc-programmer` 諮詢
- `sales-coordinator` 接到 PO → 觸發 `post-order` hook 通知 `production-planner` + `inventory-manager`
- `quality-inspector` 發現 NG → 升級 `on-error` hook → 多人協作 8D

---

## Layer 4 — INFRA 基礎設施層

**內容**：plugin 與外部世界的接口。

**位置**：`infra/`

**v1 包含**：

- `mcp-servers/scheduler-mcp/` — 生產排程 MCP（含 mock data，可立即跑）
- `mcp-servers/erp-connector/` — ERP 連接 template（contract.py 定義介面，實作交給用戶）
- `on-prem/gb10-setup.md` — 地端 LLM 安裝指南

**設計原則**：

- 所有外部依賴透過 MCP 標準化
- 預設可離線（沒接 ERP 也能用 mock data 試 demo）
- 安全優先（service account、audit log、internal-only）

---

## Layer 5 — REF 參考層

**內容**：製造業 know-how 知識庫，agent 隨時引用。

**位置**：`core/know-how/` + `profiles/<vertical>/know-how/`

**Core 4 份**：

- `iso-9001.md` — 品質管理體系
- `lean-5s.md` — 精實 + 現場
- `oee.md` — 設備總效率
- `mrp-basics.md` — 物料需求規劃

**CNC profile 加 4 份**：

- `iatf-16949.md` — 汽車品質體系
- `刀具壽命管理.md`
- `切削參數查表.md`
- `開發工廠-vs-量產.md`

**為什麼用 markdown 而不是知識圖譜**：

- 純文字易維護、易 review、易 diff
- 跨平台（任何 LLM 都讀得懂）
- 可印出來給人看
- 版控友善

---

## Layer 6 — HOOK 生命週期層

**內容**：在特定流程節點自動觸發的動作。

**位置**：`core/hooks/` + `profiles/<vertical>/hooks/`

**Core 4 個**：

- `pre-quote.md` — 報價前圖紙完整度檢查
- `post-order.md` — 接單後通知 + 排程觸發
- `pre-ship.md` — 出貨前最後檢查
- `on-error.md` — 異常統一升級

**CNC profile 加 1 個**：

- `pre-cnc-program-checkin.md` — G-code 進版控前安全檢查

**設計原則**：

- Hook 是「閘門」（可阻擋）或「通知」（純廣播）
- 失敗要明確（讓人類知道為什麼擋）
- 可繞過要記錄（誰、為什麼）

---

## Core + Profile Overlay 規則

### 啟用單一 profile

```
/install-profile cnc-machining
```

### Override 規則

1. **同名檔案 = override**：profile 內 `agents/quote-specialist.md` 取代 core 同名檔
2. **新名檔案 = 加碼**：profile 內 `agents/cnc-programmer.md` 在 core 沒有 → 純加
3. **不允許跨 profile 繼承**（避免菱形繼承）
4. **profile.json 宣告 `extends-core: false` = 完全取代**（少用）

### 為什麼這樣設計

- 多數 vertical 共用 80% 流程（核心 6 段都跑）
- 差異在 20%（材料、機台、客戶要求、合規體系）
- DRY：核心改一次全 profile 受惠
- 簡單：只有 override / 加碼兩種規則，沒有複雜繼承

---

## 不在這個架構內的東西（Non-architecture）

明確排除以避免混淆：

| 不在內                 | 為什麼                              |
| ---------------------- | ----------------------------------- |
| MES / ERP 取代         | plugin 是「接上」現有系統，不取代   |
| 即時生產監控 dashboard | 那是 BI tool / Grafana 的工作       |
| 工人手機 app           | 不是 plugin 範疇                    |
| 訓練自家 LLM           | 用既有的 LLM（Claude / Ollama）即可 |
| RPA                    | RPA 是另一種工具，可整合但不重疊    |
| PLM / CAD 整合         | 透過 MCP 接，不重新做               |

---

## 與其他類似專案的差異

| 專案                      | 差異                                                                  |
| ------------------------- | --------------------------------------------------------------------- |
| `addyosmani/agent-skills` | 那是給 AI coding agent 的工程系統；我們是給製造業的 domain agent 系統 |
| `superpowers` plugin      | 那是純技能集；我們有 6 層 + 兩階 overlay                              |
| `OpenManufacturing`       | （概念）— 我們具體 + 可 install + 含 profile                          |
| 廠商客製 SI 案            | 那是一次性閉源；我們是開源 framework + 客製 profile                   |

---

## 後續演進

見 `docs/ROADMAP.md`。
