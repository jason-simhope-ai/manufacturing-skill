# INVENTORY

> One-page entry-point map. 從這裡找到 repo 任何東西。
>
> 規模：v0.1.5 + Unreleased（v0.2.0-alpha 數位分身團隊，實驗性）· MIT
> 最後更新：2026-10-05

---

## 30 秒：依身份找入口

| 你是誰                        | 從這裡讀                                                                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 第一次看到、完全不懂          | [docs/quickstart-for-beginners.zh-TW.md](docs/quickstart-for-beginners.zh-TW.md)                                                              |
| 想 5 分鐘看懂這玩意           | [docs/explainers/04-懶人包-5分鐘上手.html](docs/explainers/04-懶人包-5分鐘上手.html)                                                          |
| 機械業老闆 / 二代             | [docs/explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)                                                                          |
| 企業 IT 部門                  | [docs/explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html) → [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md) |
| 業助 / 廠長 / 品管            | [docs/explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html)                                                          |
| AI 導入顧問                   | [docs/adoption-guide.md](docs/adoption-guide.md)                                                                                              |
| 要導入分身團隊（agent / 人）  | [TEAM.md](TEAM.md)（agent）· [team/README.zh-TW.md](team/README.zh-TW.md)（人，10 分鐘）                                                      |
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
TEAM.md                   ← 數位分身團隊 agent 啟動檔（v0.2.0-alpha，見 Team tier）
LICENSE                   ← MIT
INVENTORY.md              ← 這份
```

### `core/` — 普世製造業（任何工廠都用得到）

#### `core/commands/` — 7 個 slash commands

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

| 檔                                                               | 用途                                                                                                                                                             |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [install.sh](adapters/claude-code/install.sh)                    | 互動式 / CLI 安裝（POSIX bash 3.2+ 相容）。v0.1.4 起加 `--resolve` flag 預覽 extends 合併輸出。v0.1.5 起接 `<p1>,<p2>,...` 多 profile 與 `--list-conflicts` flag |
| [\_resolve_extends.py](adapters/claude-code/_resolve_extends.py) | v0.1.4+ profile inheritance resolver（被 install.sh 叫用；有 `extends:` 的 profile 檔交給它合併）                                                                |
| [\_multiprofile.py](adapters/claude-code/_multiprofile.py)       | v0.1.5+ multi-profile helper：`scan` 衝突偵測 + `scan-all` CI 批掃 + `aggregate` 產 `active-profiles.json`                                                       |
| [plugin-mapping.md](adapters/claude-code/plugin-mapping.md)      | source → `~/.claude/plugins/` 映射說明（v0.1.5 加多 profile 章節）                                                                                               |

### `tests/extends/` — Inheritance resolver 測試 fixtures

13 個 golden-file case，每個釘住 resolver 的某個行為或失敗模式。用 `py tests/extends/run.py` 跑完整套，CI Step 10c 也會跑。

### `tests/multiprofile/` — Multi-profile helper 單元測試

`test_multiprofile.py` — 8 個測試 in-process 驗證 `scan_set` / `scan_pair` / `aggregate_profiles` 的行為（含合成衝突 / 三 profile 部分衝突 / list 欄位 union dedupe）。CI Step 13 會跑。

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

### Team tier — 數位分身團隊（v0.2.0-alpha，實驗性）

第 7 層 TEAM 與第三階 `team/`。設計見 [spec](docs/superpowers/specs/2026-10-05-digital-twin-team-design.md)。

**入口與資料（`TEAM.md`、`team/`）**

| 檔 | 用途 |
| -- | ---- |
| [TEAM.md](TEAM.md) | agent 啟動檔（≤ 6,000 B）：六條規則、啟動演算法、漸進揭露地圖 |
| [team/README.zh-TW.md](team/README.zh-TW.md) | 人讀的 10 分鐘說明 |
| [team/roster.example.yaml](team/roster.example.yaml) | 範例 roster（synthetic：7 個通用部門、7 個職位、3 個頻道） |
| [team/twins/](team/twins/) | `_template.md` + 3 個範例分身：[production-manager](team/twins/production-manager.md) · [qa-manager](team/twins/qa-manager.md) · [engineering-manager](team/twins/engineering-manager.md) |
| [team/policies/core-rules.md](team/policies/core-rules.md) · [restricted.md](team/policies/restricted.md) | 所有分身共用 preamble · T3 政策 |
| [team/gate/need-a-twin.md](team/gate/need-a-twin.md) | 「需要分身嗎？」閘門問卷與季複審清單 |
| [team/local/README.md](team/local/README.md) | 本機專屬設定說明（`team/local/*` 與 `team/.build/` 皆 gitignored） |
| [core/commands/team.md](core/commands/team.md) | `/team status \| ask \| check \| gate \| demo`（預覽用，不經 gateway） |

**工具（`team/tools/`）**

| 檔 | 用途 |
| -- | ---- |
| [teamctl.py](team/tools/teamctl.py) | `check`（驗證）、`roster`（檢視）、`audit-verify`（驗稽核雜湊鏈） |
| [build.py](team/tools/build.py) | 編譯 `team/.build/`（`roster.json`、分身 prompt、`ref/`；輸出可重現） |
| [deid.py](team/tools/deid.py) | 來源端去識別（CSV：NFKC／空白折疊後客戶名 → `CUST-xx`、整詞比對、刪欄；殘留掃描含 email、電話、姓名＋職稱、聯絡人欄，命中即 exit 1，除非 `--allow-residual`） |
| [_teamlib.py](team/tools/_teamlib.py) | 手寫驗證器與錯誤碼表（`E0xx` / `W0xx`） |
| [lint-allow.txt](team/tools/lint-allow.txt) · [pre-commit-names.sample](team/tools/pre-commit-names.sample) | 名稱 lint 豁免清單 · 本機 pre-commit 名單 hook 範本 |

**Chat gateway（[infra/chat-gateway/](infra/chat-gateway/)；Python 3.11，核心只用 stdlib）**

| 路徑 | 用途 |
| ---- | ---- |
| [README.md](infra/chat-gateway/README.md) · [demo.py](infra/chat-gateway/demo.py) | 說明 · 2 分鐘離線 demo（8 個情境 + 稽核驗證） |
| `chat_gateway/core.py` | 載入與驗證 roster（T3 → exit 3；`act*`、雜湊不符等 → exit 78）、路由、有效 autonomy、限流、`Gateway` |
| `chat_gateway/sanitize.py` · `formatter.py` · `prompt.py` | 正規化（NFKC＋去除格式字元）／`<<UNTRUSTED>>` 信封／tripwire／DLP（含本機 denylist）／輸出過濾 · 回覆版型 · 12,000 B prompt 預算與 token 估算 |
| `chat_gateway/approvals.py` · `audit.py` · `patterns.py` · `config.py` | 核准簿（結構化點擊、argsHash、TTL 30 分、一次性；alpha 無可執行動作）· HMAC 金鑰雜湊鏈稽核＋簽章 checkpoint · secret／名稱／PII／DLP 樣式唯一來源（`_teamlib` 直接載入）· 環境變數設定 |
| `chat_gateway/adapters/` | `base.py`（凍結介面）、`mock.py`（CI 完整測試） |
| `chat_gateway_ext/` | 跨進程／網路邊界的整合，不受核心「禁用 subprocess/網路」限制，只以名稱延遲載入：`slack.py`、`discord.py`（共用 `_saas.py`；**未在 CI 對真實平台測試，需要憑證**）、`claude_code.py` |
| `chat_gateway/drivers/` | `base.py`（凍結介面）、`mock.py`（完整測試）、`chat_gateway_ext/claude_code.py`（獨立套件，不受核心「禁用 subprocess/網路」限制；固定受限旗標集，只以假 `claude` 測試；需要服務帳號憑證） |
| `fixtures/` | 範例 roster 快照、`demo.jsonl` 劇本、`mock_driver.json` |

**測試**

| 套件 | 內容 | 怎麼跑（CI Step） |
| ---- | ---- | ----------------- |
| [tests/team/](tests/team/) | `fixtures.yaml` 110 個 lint case + 18 個 deid case（`run.py` 逐一在暫存迷你 repo 執行 `teamctl` / `deid`）；`test_team.py` 42 個 unittest（驗證器、build 決定性、effective autonomy、CLI exit code） | `python3 tests/team/run.py`（Step 19）· `python3 -m unittest tests/team/test_team.py` |
| [tests/gateway/](tests/gateway/) | `test_gateway.py` 98 個 unittest（路由、autonomy、核准、限流、taint 與衰退、DLP、稽核竄改偵測、prompt 預算、核心與 `chat_gateway_ext` 靜態安全檢查、CLI、demo golden）；`test_adapters.py` 35 個 unittest（Slack／Discord 事件對應、T1 上限，假 transport）；`test_claude_code_driver.py` 39 個 unittest（假 `claude` 驗 argv、環境、cwd、promptSha、`self_check`）；`golden/demo.txt` | `python3 -m unittest discover -s tests/gateway -p 'test_*.py'` · `python3 infra/chat-gateway/demo.py --check tests/gateway/golden/demo.txt`（Steps 20–21） |

---

### `docs/` — 文件層

| 檔                                                                                                                            | 對象 / 用途                                                     |
| ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [quickstart-for-beginners.zh-TW.md](docs/quickstart-for-beginners.zh-TW.md)                                                   | 完全沒裝過 CLI 工具的工廠人員：6 步驟導引                       |
| [architecture.md](docs/architecture.md)                                                                                       | 開發者：七層架構詳解（含 Layer 7 TEAM）                         |
| [adoption-guide.md](docs/adoption-guide.md)                                                                                   | 顧問：6 週導入 playbook + ROI 計算                              |
| [profile-development.md](docs/profile-development.md)                                                                         | 開發者：怎麼長新 vertical profile                               |
| [ROADMAP.md](docs/ROADMAP.md)                                                                                                 | 全：v0.1 → v2.0 路線                                            |
| [index.html](docs/index.html)                                                                                                 | GitHub Pages 著陸頁（單頁行銷）                                 |
| [explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)                                                               | 老闆：5 分鐘看懂                                                |
| [explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html)                                                   | IT：infra / security / ops 視角                                 |
| [explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html)                                               | 業助 / 廠長 / 品管：每日指令快查                                |
| [explainers/04-懶人包-5分鐘上手.html](docs/explainers/04-懶人包-5分鐘上手.html)                                               | 不想看字：6 步驟視覺操作流                                      |
| [explainers/screenshots/](docs/explainers/screenshots/)                                                                       | 上面 4 張的 PNG 版本（給 LinkedIn / 簡報用）                    |
| [quickstart-screenshots/](docs/quickstart-screenshots/)                                                                       | 6 步驟安裝實機截圖 + mockup（含 CAPTURE-GUIDE.md 紀錄產出方式） |
| [demo/quote-demo.gif](docs/demo/quote-demo.gif) · [demo/quote-demo-en.gif](docs/demo/quote-demo-en.gif)                       | `/quote` 19 秒實錄 GIF（雙語版）                                |
| [demo/slides/](docs/demo/slides/)                                                                                             | 6-capability 介紹簡報（HTML + retina PNG）                      |
| [superpowers/specs/2026-04-26-manufacturing-skill-design.md](docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md) | 設計史：v0.1 spec 完整版                                        |

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

| 路徑                                     | 內容                                                                                                                    |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `~/.claude/plugins/manufacturing-skill/` | 安裝後的 plugin 目錄（install.sh 的 target）                                                                            |
| `~/.claude/CLAUDE.md`                    | Global 個人 conventions（包括 commit signature）                                                                        |
| `.claude/` (本 repo)                     | Claude Code 本機 session state，整個 gitignored                                                                         |
| GitHub Releases                          | v0.1.3 起開始 tag（見 CHANGELOG.md）                                                                                    |
| GitHub Actions CI                        | [.github/workflows/ci.yml](.github/workflows/ci.yml)（v0.1.1 起；JSON / plugin schema / frontmatter / install.sh 驗證） |

---

## Repo metrics（v0.1.3）

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
Quickstart for beginners: 1 doc + 7 step images (3 real screenshots + 3 mockups
                              + 1 hero) + CAPTURE-GUIDE.md
Demo                    : /quote 19s GIFs (繁中/EN) + 2 styled HTML + 6-capability slide
Landing page            : docs/index.html (GitHub Pages from /docs)
Docs                    : 5 (architecture / adoption-guide / profile-dev / ROADMAP
                              / quickstart-for-beginners)
Infra                   : 2 MCP servers + 1 on-prem guide
Examples                : 4 files
.github/                : CI workflow + 4 issue templates (incl. config.yml router)
                              + PR template
Tracked files           : 139
```

---

_更新本檔的時機：每次新增 / 移除 / 重命名 entry point 後。`_templates/` 之類的內部結構變動不用 reflect。_
