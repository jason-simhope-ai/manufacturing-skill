# manufacturing.md — The Soul of This Plugin

> **這份文件是整個 plugin 的入口靈魂文件。**
> 不論你是 Claude Code、Cursor、開發者、AI 導入顧問、或機械業老闆，從這裡開始讀。

---

## TL;DR

**這是一個製造業 AI 導入起手包。**

Fork 整個 repo → 安裝 → 30 分鐘內，你的 Claude Code 就會：

1. 知道製造業 6 段流程（報價→接單→排程→生產→檢驗→出貨）怎麼跑
2. 召喚 5 隻 universal agent persona（報價師/業助/生管/品管/倉管）
3. 載入你選的 vertical profile（v1 完整支援 CNC 精密加工）
4. 接上你的 ERP/MES/PLM（透過 MCP server）
5. 在地端 GPU（GB10 / Ollama）或雲端 LLM 跑起來

---

## 為什麼有這份文件

製造業導入 AI 通常死在三件事：

| 痛點              | 傳統作法                                | 本 plugin 提供                                               |
| ----------------- | --------------------------------------- | ------------------------------------------------------------ |
| AI 不懂製造業術語 | 自己訓 LLM、自己寫 prompt（卡在沒人會） | 5 隻內建 agent + 4 份 know-how，AI 開箱就懂 ISO / Lean / OEE |
| 各家流程都不一樣  | 找 SI 客製，超貴超慢                    | core + profile overlay 架構，企業 fork 後改 profile 即可     |
| IT 部門擋資安     | 雲端 SaaS 過不了客戶稽核                | 預設地端 GB10/Ollama，圖紙不出公司                           |

---

## 三個身份的快速入門

### 👔 我是老闆 / 機械業二代

→ 讀 [README.zh-TW.md](README.zh-TW.md) → 看 [docs/explainers/01-架構總覽.html](docs/explainers/01-架構總覽.html)

5 分鐘理解這能解決什麼。

### 💻 我是企業 IT 部門

→ 讀 [docs/explainers/02-IT部門系統說明.html](docs/explainers/02-IT部門系統說明.html) → 跟 [adapters/claude-code/install.sh](adapters/claude-code/install.sh) → 看 [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md)

知道架構、安裝步驟、資安疑慮怎麼處理。

### 🛠️ 我是業助 / 廠長 / 品管（每天會用的人）

→ 印一份 [docs/explainers/03-使用者cheatsheet.html](docs/explainers/03-使用者cheatsheet.html) 掛牆上。

每天打 `/quote`、`/order-status`、`/inspect` 就好。

---

## 架構一頁總覽（六層）

| 層                | 內容                                                      | 在哪                                      |
| ----------------- | --------------------------------------------------------- | ----------------------------------------- |
| 1. USE 入口       | slash commands `/quote /order-status /bom-check /inspect` | `core/commands/`                          |
| 2. FLOW 流程      | 6 段 skill：報價→接單→排程→生產→檢驗→出貨                 | `core/skills/01-06.md`                    |
| 3. ROLE 角色      | 5 大 persona + profile 加碼                               | `core/agents/` + `profiles/*/agents/`     |
| 4. INFRA 基礎設施 | MCP server / 地端 LLM / 檔案規範                          | `infra/`                                  |
| 5. REF 知識庫     | ISO / IATF / Lean / OEE / SPC                             | `core/know-how/` + `profiles/*/know-how/` |
| 6. HOOK 生命週期  | pre-quote / post-order / pre-ship / on-error              | `core/hooks/` + `profiles/*/hooks/`       |

兩階：**core**（普世製造業）+ **profile**（垂直領域）。

---

## v1 完整 profile：CNC 精密加工

`profiles/cnc-machining/` 是 v1 唯一完整 profile，多疊加：

- 4 隻 agent：cnc-programmer / tool-life-engineer / fixture-designer / prototype-coordinator
- 3 個 skill：g-code-review / cutting-parameter-calc / fixture-design-patterns
- 4 份 know-how：IATF 16949 / 刀具壽命 / 切削參數 / 開發工廠 vs 量產

其他 vertical（PCB / 射出 / 食品 / 製藥）v1 是 stub，歡迎 [contribute](docs/profile-development.md)。

---

## 30 秒安裝

```bash
git clone https://github.com/jason-simhope-ai/manufacturing-skill.git manufacturing-skill
cd manufacturing-skill
bash adapters/claude-code/install.sh
```

裝完打 `/quote` 就有反應。詳見 [README.md](README.md)。

---

## 我要客製給我自己的工廠

讀 [docs/profile-development.md](docs/profile-development.md)。

簡單流程：

1. `cp -r profiles/cnc-machining profiles/<你的vertical>`
2. 改 `profile.json`
3. 改裡面的 agent / skill / know-how
4. PR 回來分享給社群（可選）

---

## 我是 AI 導入顧問，要拿這個去客戶端

讀 [docs/adoption-guide.md](docs/adoption-guide.md)。

裡面有 Jason 自己用過的導入順序、踩雷清單、客製化指引。

---

## License

MIT — fork 走、商用、不用回饋（但回饋了會很開心）。

---

_Created at SIMHOPE (a Taiwan precision machining manufacturer), open-sourced for the broader machinery industry. Maintained by [Jason Lin](mailto:jasonlin@simhope.com.tw), SIMHOPE Generative AI Specialist._
