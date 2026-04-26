# manufacturing-skill

> 製造業 AI 導入起手包 — fork 它、profile 它、ship 它。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)](https://claude.com/claude-code)
[![English](https://img.shields.io/badge/lang-English-blue)](README.md)

一個 Claude Code plugin，讓任何製造業企業在 30 分鐘內建好對應自己 vertical 的 AI 助理 — 跑在自己的 GPU 上、不外流圖紙。

---

## 這是什麼

`manufacturing-skill` 是一個 **Claude Code plugin**，採用「**core + profile overlay**」架構。

- **Core 層** — 所有製造業共通的基本功：6 段流程（報價→接單→排程→生產→檢驗→出貨）、5 隻 agent persona（報價師、業助、生管、品管、倉管）、普世 know-how（ISO 9001、Lean、OEE、MRP）。
- **Profile 層** — 各垂直領域加碼。v1 完整支援 **CNC 精密加工**（4 隻專精 agent、3 個 skill、4 份 know-how 涵蓋 IATF 16949、刀具壽命、切削參數、開發工廠 vs 量產）。其他 vertical（PCB / 射出 / 食品 / 製藥）以 stub 形式存在，歡迎社群或客戶 contribute。
- **Infra 層** — MCP server template 接 ERP/MES、地端 LLM 安裝指南（Ollama on NVIDIA GB10）。
- **Adapter 層** — Claude Code adapter（v1）。Cursor / Gemini / Codex adapter 排在 v1 之後。

---

## 為什麼有這個 plugin

製造業導入 AI 通常死在三件事：

| 痛點              | 傳統作法                                | 本 plugin 提供                                               |
| ----------------- | --------------------------------------- | ------------------------------------------------------------ |
| AI 不懂製造業術語 | 自己訓 LLM、自己寫 prompt（卡在沒人會） | 5 隻內建 agent + 4 份 know-how，AI 開箱就懂 ISO / Lean / OEE |
| 各家流程都不一樣  | 找 SI 客製，超貴超慢                    | core + profile overlay，企業 fork 後改 profile 即可          |
| IT 部門擋資安     | 雲端 SaaS 過不了客戶稽核                | 預設地端 GB10/Ollama，圖紙不出公司                           |

---

## 30 秒安裝

```bash
# 1. Clone
git clone https://github.com/jason-simhope-ai/manufacturing-skill.git
cd manufacturing-skill

# 2. 裝進 Claude Code（互動選 profile）
bash adapters/claude-code/install.sh
# 會出現選單，列出 5 個 vertical profile + "core-only 純試框架" 選項

# 3. 試試看（在 Claude Code 內）
/manufacturing init     # ← 第一次用打這個，AI 會引導 4 個問題
```

或者直接 skip 引導：
```bash
/quote @examples/sample-drawing/bracket.md   # CNC profile demo
/quote 「我做不鏽鋼五金件，幫我寫一份報價流程」  # 純文字描述也可以
```

---

### 我不是 CNC 廠也能用嗎？

**可以**，三種選法：

1. **Try without a profile（最快）** — 跑 `bash install.sh --core-only`，跳過所有 vertical profile，只裝 5 隻通用 agent（報價師 / 業助 / 生管 / 品管 / 倉管）。可以直接用通用問答試「AI 懂不懂我的工廠」。
2. **Stub 加碼客製** — 若你是 PCB / 射出 / 食品 / 製藥，那個 profile 是 stub 但有 starter template，照著填內容就能用
3. **Fork CNC profile 改成你的** — CNC profile 是最完整的範本，fork 一份改成你的 vertical 是最快路徑（詳見 [docs/profile-development.md](docs/profile-development.md)）

---

### Cloud first, on-prem later

預設**不需要任何特殊硬體** — 用一般電腦的 Claude Code 直接跑就行（雲端 Anthropic API）。

什麼時候才考慮地端 LLM（GB10 / Ollama）？

| 你的情境 | 建議 |
|---|---|
| 想先試試看、確認價值 | ☁️ **雲端 Claude Code，不用買硬體** |
| 跑了 1-2 週覺得有用 | ☁️ 繼續雲端，確認團隊接受度 |
| 客戶會稽核（IATF / ISO 醫材 / 圖紙不可外流） | 🏠 才考慮地端 — 詳見 [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md) |
| 公司本來就買了 AI 硬體想物盡其用 | 🏠 直接接上就好 |

**先別被「AI 要花一筆設備錢」嚇跑** — v0.1 純雲端就能跑完整流程。

---

## Repo 結構

```
manufacturing-skill/
├── manufacturing.md          # 靈魂入口文件 — 先讀這個
├── plugin.json               # Claude Code plugin manifest
├── core/                     # 普世製造業基本功
│   ├── commands/             # /quote /order-status /bom-check /inspect …
│   ├── agents/               # 5 隻 universal persona
│   ├── skills/               # 6 段流程 + 通用 skill
│   ├── know-how/             # ISO 9001、Lean、OEE、MRP
│   └── hooks/                # pre-quote / post-order / pre-ship / on-error
├── profiles/
│   ├── cnc-machining/        # ★ v1 唯一完整 profile
│   ├── pcb-assembly/         # Stub — 歡迎 contribute
│   ├── injection-molding/    # Stub
│   ├── food-processing/      # Stub
│   └── pharma/               # Stub
├── adapters/claude-code/     # 一鍵安裝
├── infra/                    # MCP server、地端 LLM 設定
├── docs/
│   ├── explainers/           # 三張可印 A3 的繁中說明卡
│   ├── architecture.md
│   ├── adoption-guide.md     # 給 AI 導入顧問的 playbook
│   ├── profile-development.md  # 給想做新 vertical profile 的開發者
│   └── ROADMAP.md
└── examples/                 # 合成 demo data — 絕對不要放真實客戶資料
```

---

## 三種人各看什麼

本 plugin 預設有三張可印 A3 的繁中說明卡（呼應「印出來掛牆」精神）：

- **`docs/explainers/01-架構總覽.html`** — 給老闆。5 分鐘看懂這能解決什麼。
- **`docs/explainers/02-IT部門系統說明.html`** — 給 IT。把 AI 術語對照成傳統 IT（Agent ≈ RPA、MCP ≈ ESB）。
- **`docs/explainers/03-使用者cheatsheet.html`** — 給業助 / 廠長 / 品管。每天會用到的指令快查。
- **`docs/explainers/04-懶人包-5分鐘上手.html`** — ⭐ **給「不想看文字直接看截圖」的人**。一頁式視覺操作流程。

直接用瀏覽器打開 HTML 檔即可，無 build step、無外部依賴、印 A3 看得清楚。

---

## 我要在自己的工廠導入

→ 讀 [docs/adoption-guide.md](docs/adoption-guide.md)。

裡面有 Jason 用過的導入順序、踩雷清單、客製化指引。

如果你是想做新 vertical profile（例如自己加食品廠或射出廠），→ 讀 [docs/profile-development.md](docs/profile-development.md)。

---

## Roadmap

| 版本             | 內容                                                                                             | 預期           |
| ---------------- | ------------------------------------------------------------------------------------------------ | -------------- |
| **v0.1**（目前） | Core + CNC profile + 3 張 explainer + Claude Code adapter                                        | 2026-04        |
| v0.2             | 補完一個其他 vertical profile（看社群貢獻）                                                      | TBD            |
| v0.3             | Cursor / Gemini CLI adapter                                                                      | v0.1 stable 後 |
| v1.0             | 第一個機械業二代協進會企業真實導入 case study                                                    | TBD            |
| v2.0             | 自建 CLI runtime（Telegram bot 整合、地端 orchestrator — 見 [docs/ROADMAP.md](docs/ROADMAP.md)） | 看市場         |

---

## 一起 contribute

PR 都歡迎，特別是：

- 新 vertical profile（PCB / 射出 / 食品 / 製藥 — 看 stub 裡的 README 知道要做什麼）
- ERP connector 實作（SAP / Oracle / 鼎新 / Workday）
- explainer 卡片翻譯成其他語言
- 真實導入 case study

---

## License

MIT。Fork 走、商用、不用回饋（但回饋了會很開心）。

---

## 致謝

由 [SIMHOPE](https://www.simhope.com.tw)（台灣精密機械製造商）內部實踐後 open source。

維護者：[Jason Lin](mailto:jasonlin@simhope.com.tw)，SIMHOPE 生成式 AI 專案執行專員。

架構靈感來自 [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)（六層 agent 系統）與 Anthropic [superpowers](https://github.com/anthropics/superpowers) skill 規範。
