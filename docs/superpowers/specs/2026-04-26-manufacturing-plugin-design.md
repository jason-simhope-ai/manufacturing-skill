# manufacturing-plugin v1 Design Spec

- **Date**: 2026-04-26
- **Author**: Jason Lin (SIMHOPE Generative AI Specialist)
- **Repo**: https://github.com/jason-simhope-ai/manufacturing-skill (will rename to `manufacturing-plugin`)
- **License**: MIT
- **Status**: Approved for v1 implementation

---

## 1. Vision

`manufacturing-plugin` 是一個**製造業 AI 導入起手包**，以 Claude Code plugin 形式發行，採用「core + profile overlay」架構，讓任何製造業企業 fork 後 30 分鐘內能在自己的環境（雲端 or 地端 GB10/Ollama）跑起一套對應自己 vertical 的 AI 助理，並附帶讓**老闆 / IT / 操作者**三種人都看得懂的 explainer 圖卡。

**Tagline**: *"The AI starter kit for manufacturers — fork it, profile it, ship it."*

**Positioning**:
- vs `addyosmani/agent-skills`：那個是「AI coding agent 工程系統」；本專案是「製造業 domain agent 系統」，引用六層設計但內容垂直化
- vs `CLAUDE.md`：CLAUDE.md 是單檔 context，本專案是 plugin（commands + agents + skills + hooks + profiles）
- vs ERP/MES：不取代它們，而是接上它們（透過 MCP server 讀 ERP/MES 資料給 agent 用）

**Created at SIMHOPE** (a Taiwan precision machining manufacturer), open-sourced for the broader machinery industry. Maintained by Jason Lin.

---

## 2. Audiences

| 受眾 | 看什麼 | 期待結果 |
|---|---|---|
| **機械業二代協進會會員（老闆）** | 架構總覽 explainer + README.zh-TW.md | 5 分鐘理解能解決什麼、值不值得導 |
| **企業 IT 部門** | IT 部門系統說明 explainer + adapters/ + infra/on-prem/ | 知道架構、安裝步驟、資安疑慮 |
| **業助 / 廠長 / 品管（最終使用者）** | 使用者 cheatsheet explainer | 每天會用到的指令一張紙搞定 |
| **AI 導入顧問（包括 Jason 自己對外）** | docs/adoption-guide.md | 拿這個 playbook 直接去客戶端導入 |
| **想長新 vertical 的開發者** | docs/profile-development.md | 照著做能 fork 出新 profile |

---

## 3. Architecture: Core + Profile Overlay (六層 × 兩階)

### 3.1 六層（致敬 addyosmani，垂直化到製造業）

| # | 層 | 製造業詮釋 | 對應內容 |
|---|---|---|---|
| 1 | **USE 入口層** | 製造業每天會打的指令 | `/quote`, `/order-status`, `/bom-check`, `/cnc-review`, `/inspect`, `/install-profile` |
| 2 | **FLOW 流程層** | 報價 → 接單 → 排程 → 生產 → 檢驗 → 出貨 | 6 段流程 skill，每段一份 markdown |
| 3 | **ROLE 角色層** | 5 大 universal agent persona | quote-specialist / sales-coordinator / production-planner / quality-inspector / inventory-manager |
| 4 | **INFRA 基礎設施層** | 製造業數位化 surface | MCP 連 ERP/MES、檔案規範、地端 LLM (Ollama on GB10)、選配 Telegram bot |
| 5 | **REF 參考層** | 製造業 know-how 與標準 | ISO 9001 / IATF 16949 / GD&T / Lean / 5S / OEE / SPC / MRP / BOM |
| 6 | **LIFECYCLE Hook 層** | 製造業流程 hook | pre-quote / post-order / pre-ship / on-error |

### 3.2 兩階：core + profile overlay

- **`core/`** 提供層 1, 2, 3（5 角色）, 5（普世 know-how）, 6（普世 hook）
- **`profiles/<vertical>/`** 疊加層 1（多幾個指令）, 3（多幾隻 agent）, 5（垂直 know-how）, 6（垂直 hook），可 override core agent
- **`infra/`** 是跨層底座（不屬於 core 也不屬於 profile）
- **`adapters/claude-code/`** 把 platform-neutral 內容映射成 `.claude/{commands,agents,skills,hooks}/`

### 3.3 Override 規則

- Profile 同名檔案 **覆蓋** core 同名檔案（filename-based override）
- Profile 可在 `profile.json` 宣告 `extends-core: true|false`（預設 true）
- Override 時 profile agent prompt 開頭可寫 `<!-- extends: core/agents/quote-specialist.md -->` 表示繼承並擴充
- 不允許跨 profile 繼承（避免菱形問題）

---

## 4. Repo Structure

```
manufacturing-plugin/
├── README.md                       # 英文（國際開發者）
├── README.zh-TW.md                 # 繁中（台灣老闆 / 二代）
├── LICENSE                         # MIT
├── plugin.json                     # Claude Code plugin manifest
├── manufacturing.md                # 框架靈魂入口文件 — 一份統整全圖的 anchor doc
│
├── docs/
│   ├── explainers/                 # 100% 繁中, A3 print-friendly
│   │   ├── 01-架構總覽.html
│   │   ├── 02-IT部門系統說明.html
│   │   └── 03-使用者cheatsheet.html
│   ├── architecture.md             # 六層架構詳解（給開發者）
│   ├── adoption-guide.md           # 給 Jason / SI 顧問的 playbook
│   ├── profile-development.md      # 第三方怎麼長新 profile
│   └── ROADMAP.md                  # v2 自建 CLI runtime 計畫
│
├── core/
│   ├── commands/                   # /quote, /order-status, /bom-check, /inspect …
│   ├── agents/                     # 5 隻 universal persona
│   │   ├── quote-specialist.md
│   │   ├── sales-coordinator.md
│   │   ├── production-planner.md
│   │   ├── quality-inspector.md
│   │   └── inventory-manager.md
│   ├── skills/                     # 6 段流程 + 通用 skill
│   │   ├── 01-報價.md
│   │   ├── 02-接單.md
│   │   ├── 03-排程.md
│   │   ├── 04-生產.md
│   │   ├── 05-檢驗.md
│   │   ├── 06-出貨.md
│   │   ├── bom-management.md
│   │   ├── capacity-planning.md
│   │   └── spc-basics.md
│   ├── know-how/                   # 普世 know-how（繁中）
│   │   ├── iso-9001.md
│   │   ├── lean-5s.md
│   │   ├── oee.md
│   │   └── mrp-basics.md
│   └── hooks/                      # pre-quote / post-order / pre-ship / on-error
│
├── profiles/
│   ├── cnc-machining/              # ★ v1 唯一完整 profile
│   │   ├── profile.json
│   │   ├── manufacturing.md        # profile 級 overrides 說明
│   │   ├── agents/
│   │   │   ├── cnc-programmer.md
│   │   │   ├── tool-life-engineer.md
│   │   │   ├── fixture-designer.md
│   │   │   └── prototype-coordinator.md
│   │   ├── skills/
│   │   │   ├── g-code-review.md
│   │   │   ├── cutting-parameter-calc.md
│   │   │   └── fixture-design-patterns.md
│   │   ├── know-how/
│   │   │   ├── iatf-16949.md
│   │   │   ├── 刀具壽命管理.md
│   │   │   ├── 切削參數查表.md
│   │   │   └── 開發工廠-vs-量產.md
│   │   └── hooks/
│   ├── pcb-assembly/               # stub: profile.json + README only
│   ├── injection-molding/          # stub
│   ├── food-processing/            # stub
│   └── pharma/                     # stub
│
├── adapters/
│   └── claude-code/
│       ├── install.sh              # 一鍵安裝
│       └── plugin-mapping.md       # 怎麼把 platform-neutral 映射到 .claude/
│
├── infra/
│   ├── mcp-servers/
│   │   ├── scheduler-mcp/          # 範例 MCP server（仿圖二）
│   │   └── erp-connector/          # ERP connector template (stub)
│   └── on-prem/
│       └── gb10-setup.md           # Ollama on GB10 地端安裝（繁中）
│
└── examples/                       # 合成 demo 資料（不用真實 SIMHOPE 客戶資料）
    ├── sample-drawing/
    ├── sample-bom/
    └── sample-quote-output.md
```

---

## 5. File Conventions

### 5.1 Agent prompt format

```markdown
---
name: quote-specialist
description: 製造業報價師 — 從圖紙、BOM、客戶詢價內容產出結構化報價
model: sonnet
tools: [Read, Grep, Glob, Bash]
---

# 報價師 / Quote Specialist

你是一位有 15 年機械加工報價經驗的資深報價師...

## 你的任務
...

## 你會用的資源
- ISO 9001 / IATF 16949 文件規範
- core/skills/01-報價.md 流程 skill
- ...

## Output 格式
...
```

### 5.2 Skill format

呼應 superpowers convention：

```markdown
---
name: 01-報價
description: Use when user invokes /quote or asks about pricing — covers RFQ analysis, cost breakdown, lead-time estimation
when_to_use: User invokes /quote, mentions 報價/詢價/RFQ, or attaches a drawing for quoting
---

# 報價 Skill

## Process
1. ...
2. ...

## Checklist
- [ ] 圖紙完整度檢查
- [ ] BOM 拆解
- [ ] 工時估算
- [ ] 材料成本
- [ ] 加工成本
- [ ] 利潤率
- [ ] 報價單輸出
```

### 5.3 Know-how format

純 markdown 繁中，frontmatter optional：

```markdown
---
title: ISO 9001 品質管理體系基礎
tags: [quality, iso, standards]
last-reviewed: 2026-04-26
source: ISO 9001:2015
---

# ISO 9001 品質管理體系基礎

## 適用情境
...

## 核心原則（7 大）
...
```

### 5.4 Profile manifest (`profile.json`)

```json
{
  "name": "cnc-machining",
  "displayName": "CNC 精密加工",
  "version": "0.1.0",
  "extends-core": true,
  "agents": ["cnc-programmer", "tool-life-engineer", "fixture-designer", "prototype-coordinator"],
  "skills": ["g-code-review", "cutting-parameter-calc", "fixture-design-patterns"],
  "knowHow": ["iatf-16949", "刀具壽命管理", "切削參數查表", "開發工廠-vs-量產"],
  "supports": ["job-shop", "low-volume-mass"],
  "tags": ["metal", "subtractive", "precision"]
}
```

### 5.5 Plugin manifest (`plugin.json`)

```json
{
  "name": "manufacturing-plugin",
  "displayName": "Manufacturing Plugin",
  "version": "0.1.0",
  "description": "AI starter kit for manufacturers — fork it, profile it, ship it.",
  "author": "Jason Lin (SIMHOPE)",
  "license": "MIT",
  "claudeCodeVersion": ">=1.0.0",
  "profiles": ["cnc-machining", "pcb-assembly", "injection-molding", "food-processing", "pharma"],
  "defaultProfile": "cnc-machining"
}
```

---

## 6. Explainer Cards (3 張殺手鐧)

呼應 siyulio-workspace 的版面語言，**100% 繁中、A3 print-friendly、靜態 HTML 自帶 inline CSS**（無外部依賴，可離線打開）。

### 6.1 `01-架構總覽.html` — 給老闆 / 二代

**版面 inspired by** siyulio-workspace 第一張：
- 標題：`manufacturing-plugin 架構總覽 — 製造業 AI 導入起手包`
- 副標：`GitHub: jason-simhope-ai/manufacturing-plugin · 由 Jason 個人實踐 · v0.1`
- 6 個橫向 section：
  1. 使用者入口層（USE）— 列出 v1 所有 slash command
  2. 流程引擎層（FLOW）— 6 段流程
  3. 角色專家層（ROLE）— 5 隻 core agent + CNC profile 4 隻
  4. 基礎設施層（INFRA）— MCP / 地端 LLM / 檔案規範
  5. 參考資源層（REF）— 標準與 know-how 清單
  6. 生命週期層（HOOK）— hook 點
- 右側 sidebar：
  - 當前規模：`5` core agents、`9` core skills、`4` core know-how、`1` 完整 profile、`4` stub profile
  - 支援 Agent CLI：Claude Code（v1）、其他（roadmap）
- 下方核心價值橫向卡片：「為什麼這樣架構」5-6 個賣點
- 最下方名詞解釋：用比喻說清楚（AI 不熟的老闆友善）：
  - Claude Code ≈ 工廠裡會聽你話的萬能新人
  - Plugin ≈ 給這位新人的「製造業職前訓練包」
  - Core ≈ 所有製造業共通的基本功
  - Profile ≈ 你這個產業的專業知識
  - MCP ≈ 讓新人能讀懂 ERP/MES 的翻譯機

### 6.2 `02-IT部門系統說明.html` — 給 IT

**版面 inspired by** siyulio-workspace 第三張：
- 標題：`manufacturing-plugin — 給 IT 部門看的系統說明`
- 副標：`Infra · Security · Ops Perspective`
- meta line：`Compute: GB10 / Ollama local · LLM: 本地或 Anthropic · Source: GitHub MIT · CI/CD: GitHub Actions`
- 6 個 section：
  1. 網路入口（EDGE）
  2. 應用層（APP）— Claude Code plugin 機制
  3. 資料層（DATA）— 圖紙 / BOM / NC 程式怎麼放、敏感資料 .gitignore
  4. 運算排程（COMPUTE）— 地端 GB10 / Ollama 模型選擇
  5. CI/CD 部署（DEPLOY）— GitHub → Claude Code plugin install
  6. 安全合規（SECURITY）— 圖紙不外流、IATF 16949 客戶稽核、SSO
- 右側 sidebar：OPS 指標、技術棧、IT 常見疑問 FAQ
- 下方「選擇這些技術的理由 · IT 角度」橫向卡片
- 最下方名詞對照（給 IT 用熟悉術語）：
  - Agent ≈ 工廠 RPA（但更聰明）
  - MCP ≈ ESB 企業服務匯流排
  - Plugin ≈ VS Code Extension
  - Local LLM ≈ 自建 ERP server（資料不出公司）
  - Profile ≈ 應用模板（Template）

### 6.3 `03-使用者cheatsheet.html` — 給業助 / 廠長 / 品管

**版面 inspired by** siyulio-workspace 第二張：
- 標題：`manufacturing-plugin Cheatsheet — 業助 / 廠長 / 品管 自用快查表`
- 副標：`印出來掛牆 · 每天 5 分鐘掌握`
- 6 個 section：
  1. 報價（DAILY QUOTE）
  2. 訂單管理（ORDER）
  3. 生產追蹤（PRODUCTION）
  4. 品質檢驗（QC）
  5. 庫存盤點（INVENTORY）
  6. 常見除錯（DEBUG）
- 右側 sidebar：快速片段、常用 URL、固定排程
- 下方「工作節奏 · 每日 / 每週 / 每月」
- 最下方「指令快查 · 按字母」

---

## 7. Demo Flow (v1 Definition of Done #4)

匿名合成 demo data 演示「fresh install → 報價」全鏈路：

1. 使用者在 Claude Code 打：`/quote @examples/sample-drawing/bracket.png`
2. **quote-specialist** agent 接手：
   - 呼叫 `core/skills/01-報價.md` 流程
   - 觸發 `pre-quote` hook 檢查圖紙完整度
3. quote-specialist 偵測到是 CNC 加工件，dispatch 給 CNC profile 的 **cnc-programmer**
4. cnc-programmer 用 `profiles/cnc-machining/skills/cutting-parameter-calc.md` 算切削參數
5. 回傳給 quote-specialist 整合報價單
6. 輸出：`examples/sample-quote-output.md` 格式的結構化報價

**期待時間**：3 分鐘內。

---

## 8. v1 Ship List (Definition of Done)

### Tier 1 — 必 ship

- [x] Repo 骨架（README × 2、LICENSE、plugin.json、manufacturing.md）
- [x] Core 完整：6 段流程 skill、5 agent、4 know-how
- [x] CNC profile 完整：4 agent、3 skill、4 know-how、profile.json
- [x] 4 stub profile（PCB / injection / food / pharma）
- [x] adapters/claude-code/install.sh
- [x] infra：scheduler-mcp 範例、ERP connector template、gb10-setup.md
- [x] docs：architecture / adoption-guide / profile-development / ROADMAP
- [x] **3 份 explainer 圖卡**（HTML, 繁中, A3 print）
- [x] examples 合成 demo data

### Non-goals

- ❌ 自建 CLI runtime（v2）
- ❌ PCB / injection / food / pharma profile 完整內容（社群 / 客戶 contribute）
- ❌ Cursor / Gemini / Codex adapter（v1 stable 後 port）
- ❌ 真接 SAP / Oracle / 鼎新 ERP（顧問導入時客製）
- ❌ 雲端部署指南（v1 focus on-prem）
- ❌ Auth / RBAC（用 Claude Code 自帶）
- ❌ zh-CN / 日文（v1 繁中 + 英文）
- ❌ Mobile / 語音 / 即時 dashboard
- ❌ 報價演算法的精確公式（每家公司不同，給 framework 不給數字）

### Acceptance criteria

1. **30 秒安裝**：fresh `git clone` → `bash adapters/claude-code/install.sh` → Claude Code 認得 plugin
2. **60 秒首次體驗**：裝完打 `/quote` 拿到合理 mock 輸出
3. **10 分鐘理解**：陌生人讀完 `README.zh-TW.md` + 架構總覽 explainer 能講出價值
4. **3 分鐘 CNC demo**：圖紙 → 報價含切削參數
5. **可擴展性證明**：射出成型二代讀完 `profile-development.md` 能 fork
6. **Print-ready**：3 份 explainer 印 A3 看得清楚
7. **CI 通過**：基本 markdown lint + plugin.json schema 驗證（v1 可用 GitHub Actions 簡單 lint）

---

## 9. File / commit / language conventions

- **README.md**：英文（國際開發者協作）
- **README.zh-TW.md**：繁中（台灣老闆 / 二代）
- **explainer 圖卡**：100% 繁中
- **agent prompt**：繁中（直接對應台灣製造業情境）
- **know-how**：繁中
- **skill 流程說明**：繁中（內容） + 英文（frontmatter）
- **程式碼註解、commit message、PR title**：英文（國際開發者 friendly）
- **Conventional Commits**：`feat: / fix: / docs: / chore: / refactor:`
- **Co-Authored-By**：`Jason simhope ai agent <jasonlin@simhope.com.tw>`

---

## 10. Roadmap (post-v1)

| 版本 | 內容 | 預期 |
|---|---|---|
| v0.1 | 此 spec 描述的 v1 | 2026-04 |
| v0.2 | PCB / injection / food / pharma 其中一個 profile 補完 | 視 contributor |
| v0.3 | Cursor / Gemini CLI adapter | 等 v1 stable |
| v1.0 | 第一個機械業二代協進會企業真實導入 case study | 視合作機會 |
| v2.0 | 自建 CLI runtime（圖二架構，Telegram bot 整合，地端 orchestrator） | 視市場需求 |

---

## 11. Risks & Open Questions

| Risk | Mitigation |
|---|---|
| 圖紙資料合規（可能含客戶機密） | examples/ 一律用合成 dummy；adoption-guide 中強調 .gitignore |
| 老闆看不懂 explainer | 名詞解釋區用比喻（不用術語）；A3 印出來方便傳閱 |
| CNC profile 寫得太 SIMHOPE-specific 別家不能用 | profile-development.md 教如何 fork-customize；不假設特定 ERP |
| Stub profile 永遠是 stub 變廢墟 | ROADMAP 明確標註 v0.2 補一個；不能補就保持 stub 但標 "community wanted" |
| Claude Code plugin 規範變動 | adapters/ 抽象層存在的目的就是吸收這個變動 |

---

*本 spec 為 v1 實作啟動文件。實作完成後此 spec 不再更新；後續變更走 ADR 路線。*
