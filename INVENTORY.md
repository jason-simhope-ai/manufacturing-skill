# INVENTORY

> One-page entry-point map. 從這裡找到 repo 任何東西。
>
> 規模：91 檔案 · 5 commits · v0.1.0 · MIT
> 最後更新：2026-04-26

---

## 30 秒：依身份找入口

| 你是誰                        | 從這裡讀                                                                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 想 5 分鐘看懂這玩意           | [docs/explainers/04-懶人包-5分鐘上手.html](docs/explainers/04-懶人包-5分鐘上手.html)                                                          |
| 機械業老闆 / 二代             | [docs/explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)                                                                          |
| 企業 IT 部門                  | [docs/explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html) → [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md) |
| 業助 / 廠長 / 品管            | [docs/explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html)                                                          |
| AI 導入顧問                   | [docs/adoption-guide.md](docs/adoption-guide.md)                                                                                              |
| 想 fork 開新 vertical         | [docs/profile-development.md](docs/profile-development.md)                                                                                    |
| 開發者讀架構                  | [docs/architecture.md](docs/architecture.md)                                                                                                  |
| 看設計脈絡 / decision history | [docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md](docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md)            |
| 看未來路線                    | [docs/ROADMAP.md](docs/ROADMAP.md)                                                                                                            |

---

## 30 秒：依任務找檔

| 我想...             | 改 / 看這個                                                                                                             |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 安裝 plugin         | [adapters/claude-code/install.sh](adapters/claude-code/install.sh)                                                      |
| 看 plugin 元資訊    | [plugin.json](plugin.json)                                                                                              |
| 切換 / 啟用 profile | [core/commands/install-profile.md](core/commands/install-profile.md) + `bash install.sh <name>`                         |
| 第一次用引導        | [core/commands/init.md](core/commands/init.md)                                                                          |
| 加新指令            | 新增 `core/commands/<name>.md`（看 frontmatter convention）                                                             |
| 加新 agent          | 新增 `core/agents/<name>.md`（核心）或 `profiles/<X>/agents/`（領域）                                                   |
| 修報價邏輯          | [core/skills/01-報價.md](core/skills/01-報價.md) + [core/agents/quote-specialist.md](core/agents/quote-specialist.md)   |
| 修排程邏輯          | [core/skills/03-排程.md](core/skills/03-排程.md) + [core/skills/capacity-planning.md](core/skills/capacity-planning.md) |
| 修檢驗邏輯          | [core/skills/05-檢驗.md](core/skills/05-檢驗.md) + [core/skills/spc-basics.md](core/skills/spc-basics.md)               |
| 接 ERP              | 看 [infra/mcp-servers/erp-connector/contract.py](infra/mcp-servers/erp-connector/contract.py) 介面                      |
| 接生產排程          | 用 [infra/mcp-servers/scheduler-mcp/server.py](infra/mcp-servers/scheduler-mcp/server.py) 當參考                        |
| 看 demo 輸出長怎樣  | [examples/sample-quote-output.md](examples/sample-quote-output.md)                                                      |

---

## 完整檔案地圖

### 頂層 (5)

```
manufacturing.md          ← 靈魂入口文件，先讀
README.md                 ← 英文介紹
README.zh-TW.md           ← 繁中介紹
plugin.json               ← Claude Code plugin manifest
LICENSE                   ← MIT
INVENTORY.md              ← 這份
```

### `core/` — 普世製造業（任何工廠都用得到）

#### `core/commands/` — 7 個 slash commands

| 指令                                                     | 用途                        |
| -------------------------------------------------------- | --------------------------- |
| [`/quote`](core/commands/quote.md)                       | 啟動報價（圖紙 / 描述都可） |
| [`/order-status`](core/commands/order-status.md)         | 查訂單目前在哪段流程        |
| [`/bom-check`](core/commands/bom-check.md)               | BOM 健檢 + 缺料預警         |
| [`/inspect`](core/commands/inspect.md)                   | IQC / IPQC / FQC / OQC 檢驗 |
| [`/install-profile`](core/commands/install-profile.md)   | 切換 vertical profile       |
| [`/manufacturing`](core/commands/manufacturing.md)       | 看 plugin 狀態              |
| [`/manufacturing init`](core/commands/init.md)           | 第一次用的 4 問題引導       |
| [`/morning-briefing`](core/commands/morning-briefing.md) | 廠長每日 8 AM 早會懶人包    |
| [`/8d`](core/commands/8d.md)                             | 啟動 8D 客訴 / 重大不良處理 |

#### `core/agents/` — 6 隻 universal persona

| Agent                                                                     | 角色               |
| ------------------------------------------------------------------------- | ------------------ |
| [`quote-specialist`](core/agents/quote-specialist.md)                     | 報價師             |
| [`sales-coordinator`](core/agents/sales-coordinator.md)                   | 業助               |
| [`production-planner`](core/agents/production-planner.md)                 | 生管               |
| [`quality-inspector`](core/agents/quality-inspector.md)                   | 品管               |
| [`inventory-manager`](core/agents/inventory-manager.md)                   | 倉管               |
| [`engineering-change-manager`](core/agents/engineering-change-manager.md) | 工程變更經理 (ECM) |

#### `core/skills/` — 11 個 skill（6 段流程 + 5 通用）

| Skill                                                                   | 內容                                          |
| ----------------------------------------------------------------------- | --------------------------------------------- |
| [01-報價](core/skills/01-報價.md)                                       | RFQ → 結構化報價 6 步驟                       |
| [02-接單](core/skills/02-接單.md)                                       | PO → SO → WO 對帳                             |
| [03-排程](core/skills/03-排程.md)                                       | 派工 + 瓶頸識別                               |
| [04-生產](core/skills/04-生產.md)                                       | 開工 + IPQC + 異常升級                        |
| [05-檢驗](core/skills/05-檢驗.md)                                       | 4 階段檢驗 + NCR / 8D                         |
| [06-出貨](core/skills/06-出貨.md)                                       | 包裝 + 文件 + 通知                            |
| [bom-management](core/skills/bom-management.md)                         | EBOM↔MBOM、cost rollup                        |
| [capacity-planning](core/skills/capacity-planning.md)                   | 產能評估 + 瓶頸前瞻                           |
| [spc-basics](core/skills/spc-basics.md)                                 | 管制圖 + Cpk + 失控規則                       |
| [8d-report-writing](core/skills/8d-report-writing.md)                   | 8D 八步驟 + customer-deliverable template     |
| [engineering-change-process](core/skills/engineering-change-process.md) | ECN/ECO 5 步驟 SOP + 13-item impact checklist |

#### `core/know-how/` — 7 份普世知識

| 檔                                        | 內容                                            |
| ----------------------------------------- | ----------------------------------------------- |
| [iso-9001](core/know-how/iso-9001.md)     | 品質管理體系 7 原則 + PDCA                      |
| [lean-5s](core/know-how/lean-5s.md)       | 5S + 7 大浪費 + JIT                             |
| [oee](core/know-how/oee.md)               | 設備總效率公式 + 改善方向                       |
| [mrp-basics](core/know-how/mrp-basics.md) | MRP / Lead time / ABC 分類                      |
| [gd-and-t](core/know-how/gd-and-t.md)     | GD&T 14 符號 + datum 3-2-1 + MMC/LMC/RFS        |
| [fmea-pfmea](core/know-how/fmea-pfmea.md) | AIAG-VDA 7 步法 + S/O/D + AP table              |
| [incoterms](core/know-how/incoterms.md)   | INCOTERMS 2020 11 條款 + risk vs cost           |
| [eco-ecn](core/know-how/eco-ecn.md)       | ECN/ECO 制度 + ISO 9001 §8.5.6 + Class I/II/III |

#### `core/hooks/` — 4 個生命週期 hook

| Hook                                   | 觸發時機              |
| -------------------------------------- | --------------------- |
| [pre-quote](core/hooks/pre-quote.md)   | 報價前圖紙完整度檢查  |
| [post-order](core/hooks/post-order.md) | 接單後通知生管 + 採購 |
| [pre-ship](core/hooks/pre-ship.md)     | 出貨前最後檢查        |
| [on-error](core/hooks/on-error.md)     | 異常分類升級          |

---

### `profiles/` — 垂直領域

#### `profiles/cnc-machining/` — ★ v1 唯一完整 profile

| 類別         | 內容                                                                                                                                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manifest     | [profile.json](profiles/cnc-machining/profile.json) + [manufacturing.md](profiles/cnc-machining/manufacturing.md)                                                                                                                                                                                       |
| Agents (4)   | [cnc-programmer](profiles/cnc-machining/agents/cnc-programmer.md) · [tool-life-engineer](profiles/cnc-machining/agents/tool-life-engineer.md) · [fixture-designer](profiles/cnc-machining/agents/fixture-designer.md) · [prototype-coordinator](profiles/cnc-machining/agents/prototype-coordinator.md) |
| Skills (3)   | [g-code-review](profiles/cnc-machining/skills/g-code-review.md) · [cutting-parameter-calc](profiles/cnc-machining/skills/cutting-parameter-calc.md) · [fixture-design-patterns](profiles/cnc-machining/skills/fixture-design-patterns.md)                                                               |
| Know-how (4) | [iatf-16949](profiles/cnc-machining/know-how/iatf-16949.md) · [刀具壽命管理](profiles/cnc-machining/know-how/刀具壽命管理.md) · [切削參數查表](profiles/cnc-machining/know-how/切削參數查表.md) · [開發工廠-vs-量產](profiles/cnc-machining/know-how/開發工廠-vs-量產.md)                               |
| Hooks (1)    | [pre-cnc-program-checkin](profiles/cnc-machining/hooks/pre-cnc-program-checkin.md)                                                                                                                                                                                                                      |

#### `profiles/injection-molding/` — 🧪 v0.1.1 alpha profile

| 類別         | 內容                                                                                                                                                                    |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manifest     | [profile.json](profiles/injection-molding/profile.json) · [README.md](profiles/injection-molding/README.md)                                                             |
| Agents (1)   | [mold-designer](profiles/injection-molding/agents/mold-designer.md)                                                                                                     |
| Skills (1)   | [shot-weight-calc](profiles/injection-molding/skills/shot-weight-calc.md)                                                                                               |
| Know-how (2) | [common-defects](profiles/injection-molding/know-how/common-defects.md) · [polymer-material-database](profiles/injection-molding/know-how/polymer-material-database.md) |

> **Alpha 警告**：內容基於公開資料，未經實際射出廠工程師驗證。歡迎射出廠師傅 PR 修正。

#### Stub profiles（3 個 — 歡迎 contribute）

| Profile                                      | manifest                                                                                                | 預留範本                                                                             |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [pcb-assembly](profiles/pcb-assembly/)       | [profile.json](profiles/pcb-assembly/profile.json) · [README.md](profiles/pcb-assembly/README.md)       | [\_templates/agent-starter.md](profiles/pcb-assembly/_templates/agent-starter.md)    |
| [food-processing](profiles/food-processing/) | [profile.json](profiles/food-processing/profile.json) · [README.md](profiles/food-processing/README.md) | [\_templates/agent-starter.md](profiles/food-processing/_templates/agent-starter.md) |
| [pharma](profiles/pharma/)                   | [profile.json](profiles/pharma/profile.json) · [README.md](profiles/pharma/README.md)                   | [\_templates/agent-starter.md](profiles/pharma/_templates/agent-starter.md)          |

> **重要**：`_templates/` 不會被 install.sh 複製進使用者的 plugin 安裝目錄，避免 placeholder 變成假 agent。

---

### `adapters/claude-code/` — Claude Code 安裝層

| 檔                                                          | 用途                                      |
| ----------------------------------------------------------- | ----------------------------------------- |
| [install.sh](adapters/claude-code/install.sh)               | 互動式 / CLI 安裝（POSIX bash 3.2+ 相容） |
| [plugin-mapping.md](adapters/claude-code/plugin-mapping.md) | source → `~/.claude/plugins/` 映射說明    |

---

### `infra/` — 跟外部系統的接口

| 路徑                                                                                                                                                                                                   | 內容                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| [mcp-servers/scheduler-mcp/](infra/mcp-servers/scheduler-mcp/)                                                                                                                                         | 範例 MCP server，含 mock data 可立即跑     |
| `mcp-servers/scheduler-mcp/`[server.py](infra/mcp-servers/scheduler-mcp/server.py) · [README.md](infra/mcp-servers/scheduler-mcp/README.md) · [mock-data/](infra/mcp-servers/scheduler-mcp/mock-data/) |                                            |
| [mcp-servers/erp-connector/](infra/mcp-servers/erp-connector/)                                                                                                                                         | ERP 整合介面契約（template，實作交給用戶） |
| `mcp-servers/erp-connector/`[contract.py](infra/mcp-servers/erp-connector/contract.py) · [README.md](infra/mcp-servers/erp-connector/README.md)                                                        |                                            |
| [on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md)                                                                                                                                                   | NVIDIA GB10 + Ollama 地端 LLM 安裝指南     |

---

### `docs/` — 文件層

| 檔                                                                                                                            | 對象 / 用途                                  |
| ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [architecture.md](docs/architecture.md)                                                                                       | 開發者：六層架構詳解                         |
| [adoption-guide.md](docs/adoption-guide.md)                                                                                   | 顧問：6 週導入 playbook + ROI 計算           |
| [profile-development.md](docs/profile-development.md)                                                                         | 開發者：怎麼長新 vertical profile            |
| [ROADMAP.md](docs/ROADMAP.md)                                                                                                 | 全：v0.1 → v2.0 路線                         |
| [explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)                                                               | 老闆：5 分鐘看懂                             |
| [explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html)                                                   | IT：infra / security / ops 視角              |
| [explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html)                                               | 業助 / 廠長 / 品管：每日指令快查             |
| [explainers/04-懶人包-5分鐘上手.html](docs/explainers/04-懶人包-5分鐘上手.html)                                               | 不想看字：6 步驟視覺操作流                   |
| [explainers/screenshots/](docs/explainers/screenshots/)                                                                       | 上面 4 張的 PNG 版本（給 LinkedIn / 簡報用） |
| [superpowers/specs/2026-04-26-manufacturing-skill-design.md](docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md) | 設計史：v0.1 spec 完整版                     |

---

### `examples/` — 合成 demo 資料（不可放真實客戶資料）

| 檔                                                                | 用途                           |
| ----------------------------------------------------------------- | ------------------------------ |
| [README.md](examples/README.md)                                   | 為什麼是合成資料 + 怎麼跑 demo |
| [sample-drawing/bracket.md](examples/sample-drawing/bracket.md)   | 模擬 CNC 件圖紙 metadata       |
| [sample-bom/bracket-bom.csv](examples/sample-bom/bracket-bom.csv) | 對應的 BOM                     |
| [sample-quote-output.md](examples/sample-quote-output.md)         | `/quote` 預期輸出範例          |

---

## 慣例速查

| 想知道                                             | 看                                                                                                                                   |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Frontmatter 格式（agent / skill / command）        | 任一檔開頭 + [docs/profile-development.md](docs/profile-development.md)                                                              |
| Override 規則（profile 怎麼疊在 core 上）          | [adapters/claude-code/plugin-mapping.md](adapters/claude-code/plugin-mapping.md)                                                     |
| 命名規範                                           | [docs/profile-development.md#profile-命名規範](docs/profile-development.md)                                                          |
| 語言策略（README 雙語、explainer 繁中、code 英文） | [docs/superpowers/specs/...md#9-file--commit--language-conventions](docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md) |
| Co-Authored-By 規則                                | `~/.claude/CLAUDE.md`（global，不在 repo）                                                                                           |

---

## 隱藏 / 不在 repo 但相關

| 路徑                                     | 內容                                             |
| ---------------------------------------- | ------------------------------------------------ |
| `~/.claude/plugins/manufacturing-skill/` | 安裝後的 plugin 目錄（install.sh 的 target）     |
| `~/.claude/CLAUDE.md`                    | Global 個人 conventions（包括 commit signature） |
| `.claude/` (本 repo)                     | Claude Code 本機 session state，整個 gitignored  |
| GitHub Releases                          | 還沒做（v0.2 計畫）                              |
| GitHub Actions CI                        | 還沒做（v0.2 計畫）                              |

---

## Repo metrics（v0.1.2）

```
頂層檔                  : 9 (README × 2, LICENSE, plugin.json, manufacturing.md,
                              INVENTORY, CONTRIBUTING, CHANGELOG, SECURITY)
core/  agents           : 6
core/  commands         : 9
core/  skills           : 11
core/  know-how         : 8
core/  hooks            : 4
CNC profile (complete)  : 4 agents + 3 skills + 4 know-how + 1 hook + 1 manifest
Injection profile (alpha): 1 agent + 1 skill + 2 know-how + 1 manifest
Stub profiles           : 3 (PCB / food / pharma — manifest + README + _templates)
Explainers (HTML)       : 4 + 4 PNG snapshots
Demo                    : 2 styled HTML (繁中/EN) + 1 mock animation + 2 PNG
Landing page            : docs/index.html (GitHub Pages from /docs)
Docs                    : 4 (architecture / adoption-guide / profile-dev / ROADMAP)
Infra                   : 2 MCP servers + 1 on-prem guide
Examples                : 4 files
.github/                : CI workflow + 3 issue templates + PR template
```

---

_更新本檔的時機：每次新增 / 移除 / 重命名 entry point 後。`_templates/` 之類的內部結構變動不用 reflect。_
