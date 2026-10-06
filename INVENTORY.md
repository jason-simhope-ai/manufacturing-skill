# INVENTORY

> One-page entry-point map. 從這裡找到 repo 任何東西。
>
> 規模：v0.1.5 + Unreleased（v0.2.0-alpha 數位分身團隊，實驗性）· MIT
> 最後更新：2026-10-06
>
> 只列本分支 tree 內實際存在的檔案（以 `git ls-files` 為準）；其他分支或未合併 PR 新增的檔案，合併後再補進來。

---

## 30 秒：依身份找入口

| 你是誰                        | 從這裡讀                                                                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 第一次看到、完全不懂          | [docs/quickstart-for-beginners.zh-TW.md](docs/quickstart-for-beginners.zh-TW.md)                                                              |
| 想 5 分鐘看懂這玩意           | [docs/explainers/04-懶人包-5分鐘上手.html](docs/explainers/04-懶人包-5分鐘上手.html)                                                          |
| 機械業老闆 / 二代             | [docs/explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)                                                                          |
| 想一眼看懂分身團隊            | [docs/explainers/05-分身團隊-一張圖看懂.html](docs/explainers/05-分身團隊-一張圖看懂.html) → 點擊式示範 [docs/demo/team-demo.html](docs/demo/team-demo.html)          |
| 要簽字導入分身的董事長        | [docs/owner-one-page.zh-TW.md](docs/owner-one-page.zh-TW.md)（簽什麼、花多少、怎麼停、第 4 週怎麼判）                                       |
| 法務、客戶稽核員              | [docs/owner-auditor-sheet.zh-TW.md](docs/owner-auditor-sheet.zh-TW.md)（稽核員三行與擋不到的情況，先經法務確認）                            |
| 企業 IT 部門                  | [docs/explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html) → [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md) |
| 業助 / 廠長 / 品管            | [docs/explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html)                                                          |
| AI 導入顧問                   | [docs/adoption-guide.md](docs/adoption-guide.md) → [docs/consulting/](docs/consulting/README.md)（工作坊、問卷、SOW、pilot 一頁紙、交付清單）     |
| 要導入分身團隊（agent / 人）  | [TEAM.md](TEAM.md)（agent）· [team/README.zh-TW.md](team/README.zh-TW.md)（人，10 分鐘）                                                      |
| 想 fork 開新 vertical         | [docs/profile-development.md](docs/profile-development.md)                                                                                    |
| Coding agent / 貢獻者         | [CLAUDE.md](CLAUDE.md)（repo 地圖、語言慣例、CI 規則）                                                                                        |
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
| 接 ERP              | 看 [infra/mcp-servers/erp-connector/contract.py](infra/mcp-servers/erp-connector/contract.py) 介面（參考實作：[mock_connector.py](infra/mcp-servers/erp-connector/mock_connector.py)） |
| 接生產排程          | 用 [infra/mcp-servers/scheduler-mcp/server.py](infra/mcp-servers/scheduler-mcp/server.py) 當參考                        |
| 填公司事實與資料分級 | [examples/company-facts.template.md](examples/company-facts.template.md) + [docs/data-classification.md](docs/data-classification.md) |
| 設定工作站權限      | [docs/permissions-template.md](docs/permissions-template.md)                                                            |
| 給其他 AI 工具用    | [adapters/generic/export.py](adapters/generic/export.py)（純 markdown 匯出，experimental）                             |
| 看 demo 輸出長怎樣  | [examples/sample-quote-output.md](examples/sample-quote-output.md)                                                      |

---

## 完整檔案地圖

### 頂層 (13)

```
manufacturing.md          ← 靈魂入口文件，先讀
README.md                 ← 英文介紹
README.zh-TW.md           ← 繁中介紹
plugin.json               ← Claude Code plugin manifest
TEAM.md                   ← 數位分身團隊 agent 啟動檔（v0.2.0-alpha，見 Team tier）
LICENSE                   ← MIT
INVENTORY.md              ← 這份
CHANGELOG.md              ← 版本紀錄（Keep a Changelog；[Unreleased] 在最上面）
CONTRIBUTING.md           ← 貢獻指南
SECURITY.md               ← 回報漏洞 + 資安範圍（含 team tier）
.gitignore                ← 含 team/local/*、team/.build/
CLAUDE.md                 ← 給 coding agent 的貢獻指南（repo 地圖、慣例、CI 規則）
.gitattributes            ← 強制 LF（install.sh / *.py 在 CRLF checkout 下會壞）
```

### `core/` — 普世製造業（任何工廠都用得到）

#### `core/commands/` — 11 個 slash commands

| 指令                                                     | 用途                                                             |
| -------------------------------------------------------- | ---------------------------------------------------------------- |
| [`/quote`](core/commands/quote.md)                       | 啟動報價（圖紙 / 描述都可）                                      |
| [`/order-status`](core/commands/order-status.md)         | 查訂單目前在哪段流程                                             |
| [`/bom-check`](core/commands/bom-check.md)               | BOM 健檢 + 缺料預警                                              |
| [`/inspect`](core/commands/inspect.md)                   | IQC / IPQC / FQC / OQC 檢驗                                      |
| [`/install-profile`](core/commands/install-profile.md)   | 切換 vertical profile（v0.1.5+ 支援 `<p1>,<p2>,...` 多 profile） |
| [`/add-profile`](core/commands/add-profile.md)           | v0.1.5+ — 在現有 active set 加一個 profile（add 語意）           |
| [`/manufacturing`](core/commands/manufacturing.md)       | 看 plugin 狀態                                                   |
| [`/manufacturing init`](core/commands/init.md)           | 第一次用的 4 問題引導                                            |
| [`/morning-briefing`](core/commands/morning-briefing.md) | 廠長每日 8 AM 早會懶人包                                         |
| [`/8d`](core/commands/8d.md)                             | 啟動 8D 客訴 / 重大不良處理                                      |
| [`/team`](core/commands/team.md)                         | 數位分身團隊（v0.2.0-alpha）：status / ask / add / check / gate / demo |

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

#### `core/know-how/` — 9 份普世知識

| 檔                                        | 內容                                            |
| ----------------------------------------- | ----------------------------------------------- |
| [iso-9001](core/know-how/iso-9001.md)     | 品質管理體系 7 原則 + PDCA                      |
| [iatf-16949](core/know-how/iatf-16949.md) | IATF 16949 + PPAP 18 要素 / 5 級 + 各製程差異   |
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
| Know-how (3) | [刀具壽命管理](profiles/cnc-machining/know-how/刀具壽命管理.md) · [切削參數查表](profiles/cnc-machining/know-how/切削參數查表.md) · [開發工廠-vs-量產](profiles/cnc-machining/know-how/開發工廠-vs-量產.md)                               |
| Hooks (1)    | [pre-cnc-program-checkin](profiles/cnc-machining/hooks/pre-cnc-program-checkin.md)                                                                                                                                                                                                                      |

#### `profiles/injection-molding/` — 🧪 v0.1.1 alpha profile

| 類別         | 內容                                                                                                                                                                    |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manifest     | [profile.json](profiles/injection-molding/profile.json) · [README.md](profiles/injection-molding/README.md)                                                             |
| Agents (1)   | [mold-designer](profiles/injection-molding/agents/mold-designer.md)                                                                                                     |
| Skills (1)   | [shot-weight-calc](profiles/injection-molding/skills/shot-weight-calc.md)                                                                                               |
| Know-how (2) | [common-defects](profiles/injection-molding/know-how/common-defects.md) · [polymer-material-database](profiles/injection-molding/know-how/polymer-material-database.md) |

> **Alpha 警告**：內容基於公開資料，未經實際射出廠工程師驗證。歡迎射出廠師傅 PR 修正。

#### `profiles/food-processing/` — 🧪 v0.1 alpha profile

| 類別         | 內容                                                                                                                                                                                  |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manifest     | [profile.json](profiles/food-processing/profile.json) · [README.md](profiles/food-processing/README.md)                                                                               |
| Agents (2)   | [haccp-coordinator](profiles/food-processing/agents/haccp-coordinator.md) · [traceability-officer](profiles/food-processing/agents/traceability-officer.md)                           |
| Skills (2)   | [haccp-plan-review](profiles/food-processing/skills/haccp-plan-review.md) · [batch-traceability-recall-drill](profiles/food-processing/skills/batch-traceability-recall-drill.md)     |
| Know-how (2) | [haccp-iso22000-basics](profiles/food-processing/know-how/haccp-iso22000-basics.md) · [food-defects-and-ccp-examples](profiles/food-processing/know-how/food-defects-and-ccp-examples.md) |
| Hooks (1)    | [pre-ship](profiles/food-processing/hooks/pre-ship.md)（取代 core `pre-ship`，加食品批次放行要件）                                                                                  |

> **Alpha 警告**：內容基於 Codex / ISO 22000 公開資料，未經食品廠 HACCP 小組驗證；管制界限皆為範例，法規細節標「需驗證」。不可取代 HACCP 管制小組或法規顧問，AI 不簽核 CCP 偏差、不決定回收。

#### `profiles/pcb-assembly/` — 🧪 v0.1.0 alpha profile

| 類別         | 內容                                                                                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Manifest     | [profile.json](profiles/pcb-assembly/profile.json) · [README.md](profiles/pcb-assembly/README.md)                                                            |
| Agents (2)   | [smt-process-engineer](profiles/pcb-assembly/agents/smt-process-engineer.md) · [ems-quality-analyst](profiles/pcb-assembly/agents/ems-quality-analyst.md)     |
| Skills (2)   | [smt-dfm-review](profiles/pcb-assembly/skills/smt-dfm-review.md) · [aoi-defect-pareto](profiles/pcb-assembly/skills/aoi-defect-pareto.md)                     |
| Know-how (2) | [ipc-a-610-basics](profiles/pcb-assembly/know-how/ipc-a-610-basics.md) · [smt-common-defects](profiles/pcb-assembly/know-how/smt-common-defects.md)           |
| 預留範本     | [\_templates/agent-starter.md](profiles/pcb-assembly/_templates/agent-starter.md)                                                                            |

> **Alpha 警告**：內容基於公開 IPC 標準摘要與業界通識，未經 EMS 工程師驗證；數字標「範例 / 需驗證」。尚無 MES 連線 — AOI/SPI/ICT/FCT 分析需先匯出 CSV。

#### `profiles/pharma/` — 🧪 v0.1.0 alpha profile

| 類別         | 內容                                                                                                                                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Manifest     | [profile.json](profiles/pharma/profile.json) · [README.md](profiles/pharma/README.md)                                                                                                                          |
| Agents (2)   | [deviation-capa-coordinator](profiles/pharma/agents/deviation-capa-coordinator.md) · [batch-record-reviewer](profiles/pharma/agents/batch-record-reviewer.md)                                                   |
| Skills (2)   | [deviation-investigation-5whys-fishbone](profiles/pharma/skills/deviation-investigation-5whys-fishbone.md) · [batch-record-completeness-review](profiles/pharma/skills/batch-record-completeness-review.md)     |
| Know-how (2) | [gmp-gxp-basics](profiles/pharma/know-how/gmp-gxp-basics.md) · [validation-and-change-control](profiles/pharma/know-how/validation-and-change-control.md)                                                       |
| Hooks (1)    | [pre-batch-release](profiles/pharma/hooks/pre-batch-release.md)（新增，不覆寫 core `pre-ship`；QA 放行前文件齊備檢查）                                                                                         |
| 預留範本     | [\_templates/agent-starter.md](profiles/pharma/_templates/agent-starter.md)                                                                                                                                    |

> **Alpha 警告**：內容基於 PIC/S GMP、ICH Q7/Q9/Q10、資料完整性指引公開摘要，未經 GMP QA / 確效人員驗證；數字標「範例 / 需驗證」。AI 輸出永遠不是 GMP 紀錄 — 不結案偏差、不核准 CAPA、不放行批次；不取代 QA / QP、法規事務或經確效的系統。

#### `profiles/machinery-eto/` — 🧪 v0.1.0 alpha profile

| 類別         | 內容                                                                                                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Manifest     | [profile.json](profiles/machinery-eto/profile.json) · [README.md](profiles/machinery-eto/README.md)                                                                                                                                        |
| Agents (3)   | [eto-quote-engineer](profiles/machinery-eto/agents/eto-quote-engineer.md) · [project-engineer](profiles/machinery-eto/agents/project-engineer.md) · [commissioning-service-coordinator](profiles/machinery-eto/agents/commissioning-service-coordinator.md) |
| Skills (3)   | [eto-quote-breakdown](profiles/machinery-eto/skills/eto-quote-breakdown.md) · [spec-freeze-and-design-review](profiles/machinery-eto/skills/spec-freeze-and-design-review.md) · [fat-sat-acceptance](profiles/machinery-eto/skills/fat-sat-acceptance.md) |
| Know-how (3) | [eto-vs-mts-quoting](profiles/machinery-eto/know-how/eto-vs-mts-quoting.md) · [machinery-safety-ce-basics](profiles/machinery-eto/know-how/machinery-safety-ce-basics.md) · [project-handover-and-after-sales](profiles/machinery-eto/know-how/project-handover-and-after-sales.md) |
| Hooks (1)    | [pre-quote](profiles/machinery-eto/hooks/pre-quote.md)（取代 core `pre-quote`：加 ETO 閘門 — 規格未凍結不得正式報價、未定選配標 `[需澄清]`；core 零件檢查原封保留）                                                                    |

> **Alpha 警告**：內容基於公開機械安全標準摘要（ISO 12100、IEC 60204-1）與設備廠一般實務，未經設備廠專案 / 報價 / 安規工程師驗證；數字標「範例」，CE（2006/42/EC、2023/1230）與台灣安全資訊申報細節標「需驗證」。報價是工程估算；AI 不承諾交期、不簽驗收、不做安全評估或 CE 判定。零件級報價仍由 core `quote-specialist` 處理。

> **重要**：`_templates/` 不會被 install.sh 複製進使用者的 plugin 安裝目錄，避免 placeholder 變成假 agent。

---

### `adapters/claude-code/` — Claude Code 安裝層

| 檔                                                               | 用途                                                                                                                                                             |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [install.sh](adapters/claude-code/install.sh)                    | 互動式 / CLI 安裝（POSIX bash 3.2+ 相容）。v0.1.4 起加 `--resolve` flag 預覽 extends 合併輸出。v0.1.5 起接 `<p1>,<p2>,...` 多 profile 與 `--list-conflicts` flag |
| [\_resolve_extends.py](adapters/claude-code/_resolve_extends.py) | v0.1.4+ profile inheritance resolver（被 install.sh 叫用；有 `extends:` 的 profile 檔交給它合併）                                                                |
| [\_multiprofile.py](adapters/claude-code/_multiprofile.py)       | v0.1.5+ multi-profile helper：`scan` 衝突偵測 + `scan-all` CI 批掃 + `aggregate` 產 `active-profiles.json`                                                       |
| [plugin-mapping.md](adapters/claude-code/plugin-mapping.md)      | source → `~/.claude/plugins/` 映射說明（v0.1.5 加多 profile 章節）                                                                                               |

### `adapters/generic/` — 純 markdown 匯出（experimental, v0.3 preview）

| 檔 | 用途 |
| -- | ---- |
| [export.py](adapters/generic/export.py) | 把 core + profile（`extends:` 已解析、多 profile 衝突檢查同 install.sh）匯出成純 markdown：`files` 資料夾 + `MANIFEST.json` 或單一 `bundle` 檔 |
| [README.md](adapters/generic/README.md) | 用法：Cursor、Gemini CLI / Codex、地端 Ollama / Open WebUI、列印成 SOP |

### `tests/extends/` — Inheritance resolver 測試 fixtures

24 個 golden-file case，每個釘住 resolver 的某個行為或失敗模式。用 `py tests/extends/run.py` 跑完整套，CI Step 10c 也會跑。

### `tests/multiprofile/` — Multi-profile helper 單元測試

`test_multiprofile.py` — 16 個測試 in-process 驗證 `scan_set` / `scan_pair` / `aggregate_profiles` 的行為（含合成衝突 / 三 profile 部分衝突 / list 欄位 union dedupe）。CI Step 13 會跑。

### `tests/generic/` — Generic adapter 測試

`test_export.py` — 12 個 stdlib unittest（匯出內容與 install.sh 一致、`extends:` 解析、衝突拒絕、bundle / files 兩種格式）。CI「Generic adapter — export tests」會跑。

### `tests/mcp/` — MCP server 測試

`test_erp_contract.py` — 78 個 unittest（`CallContext`、角色遮罩、寫入核准 token、`max_rows`／`fields`，含可重用的 `ConformanceSuite` 跑 `MockErpConnector`）；`test_scheduler_mcp.py` — 30 個 unittest（`manufacturing-scheduler` stdio JSON-RPC：`initialize`、`tools/list`、`tools/call`、輸入驗證、惡意輸入）。CI「erp-connector — contract tests」「scheduler-mcp — stdio protocol tests」會跑。

---

### `infra/` — 跟外部系統的接口

| 路徑                                                                                                                                                                                                   | 內容                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| [mcp-servers/scheduler-mcp/](infra/mcp-servers/scheduler-mcp/)                                                                                                                                         | 範例 MCP server，含 mock data 可立即跑     |
| `mcp-servers/scheduler-mcp/`[server.py](infra/mcp-servers/scheduler-mcp/server.py) · [README.md](infra/mcp-servers/scheduler-mcp/README.md) · [mock-data/](infra/mcp-servers/scheduler-mcp/mock-data/) |                                            |
| [mcp-servers/erp-connector/](infra/mcp-servers/erp-connector/)                                                                                                                                         | ERP 整合介面契約（template，實作交給用戶） |
| `mcp-servers/erp-connector/`[contract.py](infra/mcp-servers/erp-connector/contract.py) · [README.md](infra/mcp-servers/erp-connector/README.md) · [mock_connector.py](infra/mcp-servers/erp-connector/mock_connector.py) · [mock-data/erp_mock.json](infra/mcp-servers/erp-connector/mock-data/erp_mock.json) |                                            |
| [on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md)                                                                                                                                                   | NVIDIA GB10 + Ollama 地端 LLM 安裝指南     |
| [chat-gateway/](infra/chat-gateway/)                                                                                                                                                                   | 數位分身聊天 gateway（見下方 Team tier）；`install.sh` 不安裝 `infra/` |

---

### Team tier — 數位分身團隊（v0.2.0-alpha，實驗性）

第 7 層 TEAM 與第三階 `team/`。設計見 [spec](docs/superpowers/specs/2026-10-05-digital-twin-team-design.md)。

**入口與資料（`TEAM.md`、`team/`）**

| 檔 | 用途 |
| -- | ---- |
| [TEAM.md](TEAM.md) | agent 啟動檔（≤ 6,000 B）：六條規則、啟動演算法、漸進揭露地圖 |
| [team/README.zh-TW.md](team/README.zh-TW.md) | 人讀的說明：前 60 行看懂分身（誰做什麼、安全三句話、三分類、三步開始），其餘依讀者分段（給主管；給 IT 與導入者、給貢獻者收在展開區塊） |
| [team/for-frontline.zh-TW.md](team/for-frontline.zh-TW.md) | 給業務助理、檢驗員等前線同仁的一頁說明（5 分鐘）：分身是誰的、我可以做什麼、答錯誰負責、會不會考核我、可以拒絕嗎、怎麼反映 |
| [team/roster.example.yaml](team/roster.example.yaml) | 範例 roster（synthetic：7 個通用部門、7 個職位、3 個頻道） |
| [team/twins/](team/twins/) | `_template.md` + 3 個範例分身：[production-manager](team/twins/production-manager.md) · [qa-manager](team/twins/qa-manager.md) · [engineering-manager](team/twins/engineering-manager.md) |
| [team/policies/core-rules.md](team/policies/core-rules.md) · [restricted.md](team/policies/restricted.md) | 所有分身共用 preamble · T3 政策 |
| [team/gate/need-a-twin.md](team/gate/need-a-twin.md) | 「需要分身嗎？」閘門問卷與季複審清單 |
| [team/local/README.md](team/local/README.md) · `team/local/.gitkeep` | 本機專屬設定說明（`team/local/*` 與 `team/.build/` 皆 gitignored） |
| [core/commands/team.md](core/commands/team.md) | `/team status \| ask \| add \| check \| gate \| demo`（預覽用，不經 gateway；先找 `$ROOT` 再用 `$ROOT/…` 路徑） |

**工具（`team/tools/`）**

| 檔 | 用途 |
| -- | ---- |
| [teamctl.py](team/tools/teamctl.py) | `check`（驗證）、`roster`（檢視）、`audit-verify`（驗稽核雜湊鏈） |
| [build.py](team/tools/build.py) | 編譯 `team/.build/`（`roster.json`、分身 prompt、`ref/`；輸出可重現） |
| [deid.py](team/tools/deid.py) | 來源端去識別（CSV：NFKC／空白折疊後客戶名 → `CUST-xx`、整詞比對、刪欄；殘留掃描含 email、電話、姓名＋職稱、聯絡人欄，命中即 exit 1，除非 `--allow-residual`） |
| [teamlib/](team/tools/teamlib/) · [_teamlib.py](team/tools/_teamlib.py) | 手寫驗證器與錯誤碼表（`E0xx` / `W0xx`）：`schema.py`（常數、`CODES`、欄位規格、樣式橋接）· `io.py`（YAML／JSON／日期）· `compile.py`（組裝與 build）· `validate.py`（驗證器）；`_teamlib.py` 是相容 shim |
| [lint-allow.txt](team/tools/lint-allow.txt) · [pre-commit-names.sample](team/tools/pre-commit-names.sample) | 名稱 lint 豁免清單 · 本機 pre-commit 名單 hook 範本（Python regex，與 gateway 同語法） |
| [denylist.starter.txt](team/tools/denylist.starter.txt) | 建議起始 denylist：通用中英同義詞、保密約定、金額寫法；`T3:` 開頭的行命中視為 T3 |

**Chat gateway（[infra/chat-gateway/](infra/chat-gateway/)；Python 3.11，核心只用 stdlib）**

| 路徑 | 用途 |
| ---- | ---- |
| [README.md](infra/chat-gateway/README.md) · [demo.py](infra/chat-gateway/demo.py) · `requirements-optional.txt` | 說明 · 2 分鐘離線 demo（8 個情境 + 稽核驗證；`--plain` 前線版）· 選用相依（Slack／Discord SDK） |
| [DEPLOY.md](infra/chat-gateway/DEPLOY.md) · [RUNBOOK.md](infra/chat-gateway/RUNBOOK.md) | Pilot 部署檢核表（主機、帳號、systemd、出口、祕密、廠商檢查表、首日驗收）· 停機與外洩處置（凍結、撤銷、輪替、封存） |
| `chat_gateway/__main__.py` | CLI：`run`、`post`、`self-check`、`audit-verify`、`freeze`／`unfreeze`（`state-reset` 在 `team/tools/teamctl.py`） |
| `chat_gateway/core.py` | 載入與驗證 roster（T3 → exit 3；`act*`、雜湊不符等 → exit 78）、路由、有效 autonomy、限流、`Gateway` |
| `chat_gateway/sanitize.py` · `formatter.py` · `prompt.py` | 正規化（NFKC＋去除格式字元）／`<<UNTRUSTED>>` 信封／tripwire／DLP（含本機 denylist）／輸出過濾 · 回覆版型 · 12,000 B prompt 預算與 token 估算 |
| `chat_gateway/approvals.py` · `audit.py` · `patterns.py` · `config.py` · `spend.py` | 核准簿（結構化點擊、argsHash、TTL 30 分、一次性；alpha 無可執行動作）· HMAC 金鑰雜湊鏈稽核＋簽章 checkpoint＋主機外錨點（`--heads-out`／`--anchor`）· secret／名稱／PII／DLP 樣式唯一來源（`teamlib/schema.py` 直接載入）· 環境變數設定 · claude-code driver 的每日預算上限（持久化） |
| `chat_gateway/datascan.py` | `MFG_TEAM_DATA_T1` 資料夾內容掃描（DLP＋denylist，只重讀變動檔，5,000 檔上限） |
| `chat_gateway/spend.py` | 每分身每日費用累計（`$MFG_TEAM_STATE_DIR/daily-spend.json`，0600、UTC 日期、檔案鎖，重啟不歸零） |
| `audit-weekly.sh` | 每週稽核 systemd timer 用的腳本（`audit-verify --anchor` → `--heads-out` → 推到主機外） |
| `chat_gateway/adapters/` | `base.py`（凍結介面）、`mock.py`（CI 完整測試） |
| `chat_gateway_ext/` | 跨進程／網路邊界的整合，不受核心「禁用 subprocess/網路」限制，只以名稱延遲載入：`slack.py`、`discord.py`（共用 `_saas.py`；**未在 CI 對真實平台測試，需要憑證**）、`claude_code.py`、`twin_result.schema.json` |
| `chat_gateway/drivers/` | `base.py`（凍結介面）、`mock.py`（完整測試）、`chat_gateway_ext/claude_code.py`（獨立套件，不受核心「禁用 subprocess/網路」限制；固定受限旗標集，只以假 `claude` 測試；需要服務帳號憑證） |
| `fixtures/` | 範例 roster 快照（`roster/`）、`demo.jsonl` 劇本、`mock_driver.json` |

**測試**

| 套件 | 內容 | 怎麼跑（CI Step） |
| ---- | ---- | ----------------- |
| [tests/team/](tests/team/) | `fixtures.yaml` 135 個 lint case + 18 個 deid case（`run.py` 逐一在暫存迷你 repo 執行 `teamctl` / `deid`）；`test_team.py` 58 個 unittest（驗證器、build 決定性、effective autonomy、CLI exit code、agent 檔的 `$ROOT` 路徑） | `python3 tests/team/run.py`（Step 19）· `python3 tests/team/test_team.py` |
| [tests/gateway/](tests/gateway/) | `test_gateway.py` 142 個 unittest（路由、autonomy、核准、限流、taint 與衰退、DLP、稽核竄改偵測、prompt 預算、每日費用上限與 `daily-spend.json`、核心與 `chat_gateway_ext` 靜態安全檢查、CLI、demo golden）；`test_adapters.py` 50 個 unittest（Slack／Discord 事件對應、T1 上限、Slack scope 檢查與 README 一致性，假 transport）；`test_claude_code_driver.py` 90 個 unittest（假 `claude` 驗 argv、環境、cwd、promptSha、`self_check`、資料夾掃描、家目錄隱藏目錄）；`test_frontline.py` 20 個 unittest（前線回合：參考非指示、不同意／親手做、無分身日、learner mode、`demo --plain`）；`test_pilot.py` 40 個 unittest（starter denylist 與 7 句實測、kill switch（含凍結先於預算檢查、凍結中丟棄的回覆仍計費）、稽核錨點、symlink state dir、錯誤訊息）；`fixtures/`；`golden/demo.txt` | `python3 -m unittest discover -s tests/gateway -p 'test_*.py'` · `python3 infra/chat-gateway/demo.py --check tests/gateway/golden/demo.txt`（Steps 20–21） |

---

### `docs/` — 文件層

| 檔                                                                                                                            | 對象 / 用途                                                     |
| ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [quickstart-for-beginners.zh-TW.md](docs/quickstart-for-beginners.zh-TW.md)                                                   | 完全沒裝過 CLI 工具的工廠人員：6 步驟導引                       |
| [architecture.md](docs/architecture.md)                                                                                       | 開發者：七層架構詳解（含 Layer 7 TEAM）                         |
| [adoption-guide.md](docs/adoption-guide.md)                                                                                   | 顧問：6 週導入 playbook + ROI 計算；分身 4 週 pilot、原則與核准範本 |
| [owner-one-page.zh-TW.md](docs/owner-one-page.zh-TW.md)                                                                       | 董事長：簽三件事前的一頁（費用、最壞情況、停機、第 4 週決策表） |
| [data-classification.md](docs/data-classification.md) | 導入負責人 / IT：T0–T3 資料分級與 AI 工具使用規則 |
| [permissions-template.md](docs/permissions-template.md) | IT：Claude Code `permissions` 最小權限範本（allow / ask / deny） |
| [consulting/](docs/consulting/README.md) | 顧問交付包（6 份範本）：90 分鐘探索工作坊、IT 資料流問卷、SOW、pilot 一頁紙、交付物清單 |
| [audit-operations.md](docs/audit-operations.md) | IT／稽核：分身 gateway 稽核週作業、簽收單、金鑰輪替與遺失、ISO 27001 對應 |
| [owner-auditor-sheet.zh-TW.md](docs/owner-auditor-sheet.zh-TW.md)                                                             | 法務：給客戶稽核員的三行與擋不到的情況（另印一張）              |
| [profile-development.md](docs/profile-development.md)                                                                         | 開發者：怎麼長新 vertical profile                               |
| [ROADMAP.md](docs/ROADMAP.md)                                                                                                 | 全：v0.1 → v2.0 路線                                            |
| [index.html](docs/index.html)                                                                                                 | GitHub Pages 著陸頁（單頁行銷）                                 |
| [explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)                                                               | 老闆：5 分鐘看懂                                                |
| [explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html)                                                   | IT：infra / security / ops 視角                                 |
| [explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html)                                               | 業助 / 廠長 / 品管：每日指令快查                                |
| [explainers/04-懶人包-5分鐘上手.html](docs/explainers/04-懶人包-5分鐘上手.html)                                               | 不想看字：6 步驟視覺操作流                                      |
| [explainers/05-分身團隊-一張圖看懂.html](docs/explainers/05-分身團隊-一張圖看懂.html)                                         | 老闆 / 主管 / 現場同仁：分身是什麼、誰做什麼、安全三句話、怎麼開始 |
| [explainers/screenshots/](docs/explainers/screenshots/)                                                                       | 上面 5 張的 PNG 版本（給 LinkedIn / 簡報用）                    |
| [quickstart-screenshots/](docs/quickstart-screenshots/)                                                                       | 6 步驟安裝實機截圖 + mockup（含 CAPTURE-GUIDE.md 紀錄產出方式） |
| [demo/quote-demo.gif](docs/demo/quote-demo.gif) · [demo/quote-demo-en.gif](docs/demo/quote-demo-en.gif)                       | `/quote` 19 秒實錄 GIF（雙語版）                                |
| [demo/quote-demo.html](docs/demo/quote-demo.html) · [quote-real.html](docs/demo/quote-real.html)（含 `-en` 版）· [real-claude-response.md](docs/demo/real-claude-response.md) · [screenshots/](docs/demo/screenshots/) | GIF 的 HTML 原稿、真實 Claude 回覆紀錄與截圖 |
| [demo/team-demo.html](docs/demo/team-demo.html) · [team-demo.md](docs/demo/team-demo.md) · [screenshots/team-demo.png](docs/demo/screenshots/team-demo.png) | 分身團隊點擊式示範（4 段：排程貼文、@ 提問、「我先說」、「我不同意」；回覆預錄自離線 demo，不是即時模型）與文字版 |
| [demo/slides/](docs/demo/slides/)                                                                                             | 6-capability 介紹簡報（HTML + retina PNG）                      |
| [superpowers/specs/2026-04-26-manufacturing-skill-design.md](docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md) | 設計史：v0.1 spec 完整版                                        |
| [superpowers/specs/](docs/superpowers/specs/)                                                                                 | 其餘 5 份設計 spec：v0.1.1、v0.1.2、profile 繼承、多 profile、數位分身團隊 |

---

### `examples/` — 合成 demo 資料（不可放真實客戶資料）

| 檔                                                                | 用途                           |
| ----------------------------------------------------------------- | ------------------------------ |
| [README.md](examples/README.md)                                   | 為什麼是合成資料 + 怎麼跑 demo |
| [sample-drawing/bracket.md](examples/sample-drawing/bracket.md)   | 模擬 CNC 件圖紙 metadata       |
| [sample-bom/bracket-bom.csv](examples/sample-bom/bracket-bom.csv) | 對應的 BOM                     |
| [sample-quote-output.md](examples/sample-quote-output.md)         | `/quote` 預期輸出範例          |
| [company-facts.template.md](examples/company-facts.template.md)   | 公司事實檔填寫範本（費率、毛利、交期、核准權限；填好的檔不進 repo） |

---

### `scripts/` — 維護腳本

| 檔 | 用途 |
| -- | ---- |
| [regen_explainers.py](scripts/regen_explainers.py) | 重生 `docs/explainers/*.html` 的 `AUTO-START`／`AUTO-END` 區塊（計數、版本、分身數）；`--check` 供 CI Step 11 |
| [regen_screenshots.py](scripts/regen_screenshots.py) | 從 HTML 重拍已提交的 PNG（explainer 01–05、簡報、新手 mockup、分身點擊示範）；Node Playwright + 預裝 Chromium；`--check` 列出比 HTML 舊的 PNG |

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

| 路徑                                     | 內容                                                                                                                    |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `~/.claude/plugins/manufacturing-skill/` | 安裝後的 plugin 目錄（install.sh 的 target）                                                                            |
| `~/.claude/CLAUDE.md`                    | Global 個人 conventions（包括 commit signature）                                                                        |
| `.claude/` (本 repo)                     | Claude Code 本機 session state，整個 gitignored                                                                         |
| GitHub Releases                          | v0.1.3 起開始 tag（見 CHANGELOG.md）                                                                                    |
| GitHub Actions CI                        | [.github/workflows/ci.yml](.github/workflows/ci.yml)（v0.1.1 起；JSON / plugin schema / frontmatter / install.sh 驗證；Step 18–22 為 team tier 與 chat gateway） |

---

## Repo metrics（本分支，`git ls-files`）

```
頂層檔                  : 13 (README × 2, LICENSE, plugin.json, manufacturing.md, TEAM.md,
                              CLAUDE.md, INVENTORY, CONTRIBUTING, CHANGELOG, SECURITY,
                              .gitignore, .gitattributes)
core/  agents           : 6
core/  commands         : 11 (含 /team)
core/  skills           : 11
core/  know-how         : 9
core/  hooks            : 4
CNC profile (complete)  : 4 agents + 3 skills + 3 know-how + 1 hook + 1 manifest
Injection profile (alpha): 1 agent + 1 skill + 2 know-how + 1 manifest
Food profile (alpha)    : 2 agents + 2 skills + 2 know-how + 1 hook + 1 manifest
PCB profile (alpha)     : 2 agents + 2 skills + 2 know-how + 1 manifest
Pharma profile (alpha)  : 2 agents + 2 skills + 2 know-how + 1 hook + 1 manifest
Machinery ETO (alpha)   : 3 agents + 3 skills + 3 know-how + 1 hook + 1 manifest
Stub profiles           : 0
Adapters                : claude-code (install.sh + 2 Python helpers + plugin-mapping.md)
                              + generic (export.py + README; experimental, v0.3 preview)
Team tier               : TEAM.md + team/ 24 files (README, for-frontline, gate, policies × 2,
                              roster.example, 3 example twins + _template, tools 12, local 2)
Infra                   : 2 MCP servers (scheduler-mcp 5 files; erp-connector 4 incl.
                              mock_connector + mock data) + 1 on-prem guide
                              + chat-gateway (36 files)
Explainers (HTML)       : 5 + 5 PNG snapshots
Quickstart for beginners: 1 doc + 7 step images (3 real screenshots + 3 mockups
                              + 1 hero) + 4 mockup HTML + CAPTURE-GUIDE.md
Demo                    : /quote 19s GIFs (繁中/EN) + 4 HTML + 2 PNG + real-claude-response.md
                              + twin-team click-through (HTML + transcript + PNG)
                              + 6-capability slide (HTML + PNG)
Landing page            : docs/index.html (GitHub Pages from /docs)
Docs                    : 10 (architecture / adoption-guide / profile-dev / ROADMAP
                              / quickstart-for-beginners / owner-one-page
                              / owner-auditor-sheet / data-classification
                              / permissions-template / audit-operations)
                              + consulting kit 6 + 6 design specs
Scripts                 : 2 (regen_explainers.py, regen_screenshots.py)
Tests                   : 92 files — extends 24 cases, multiprofile 16, team 135 + 18 fixture
                              cases + 58 unittest, gateway 342 unittest + demo golden,
                              generic 12, mcp 78 (erp contract) + 30 (scheduler stdio)
Examples                : 5 files
.github/                : CI workflow + 4 issue templates (incl. config.yml router)
                              + PR template
Tracked files           : 356
```

---

_更新本檔的時機：每次新增 / 移除 / 重命名 entry point 後。`_templates/` 之類的內部結構變動不用 reflect。_
