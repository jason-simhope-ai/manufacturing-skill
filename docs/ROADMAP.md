# Roadmap

> manufacturing-skill 路線圖。版本與時程會依社群回饋與商業合作機會調整。

---

## v0.1 (current — 2026-04)

第一個可發行版本：

- ✅ 六層架構（USE / FLOW / ROLE / INFRA / REF / HOOK）
- ✅ Core 完整：6 段流程、5 隻 agent、11 個 skill（6 段流程 + 5 個通用）、8 份 know-how、4 個 hook
- ✅ CNC profile 完整：4 agent、3 skill、4 know-how、1 hook
- ✅ 4 個 stub profile（PCB / 射出 / 食品 / 製藥）
- ✅ Claude Code adapter（含 install.sh）
- ✅ scheduler-mcp 範例（含 mock data 可立即跑）
- ✅ erp-connector contract（template，實作交給用戶）
- ✅ GB10 地端 LLM 安裝指南
- ✅ 4 張繁中 explainer 圖卡（架構 / IT / cheatsheet / 5 分鐘懶人包）
- ✅ 完整 docs（architecture / adoption-guide / profile-development / 此 ROADMAP）
- ✅ 合成 demo data（examples/）

---

## v0.1.4 (2026-05-09)

**Pulled forward from v0.2**: profile inheritance shipped early as experimental.

- ✅ **部分內容繼承**（`extends: core/<kind>/<name>` + `<!-- inherit -->` / `<!-- replace-section -->` / `<!-- override-body -->`）— see [CHANGELOG `[0.1.4]`](../CHANGELOG.md) and [spec](superpowers/specs/2026-05-08-profile-inheritance-design.md)

## v0.1.5 (2026-05-09)

**Pulled forward from v0.2**: multi-profile active shipped early as experimental.

- ✅ **多 profile 同時 active**（`install.sh cnc-machining,injection-molding` + refuse-on-conflict + `active-profiles.json` aggregation + `/add-profile` slash command + CI pairwise scan）— see [CHANGELOG `[0.1.5]`](../CHANGELOG.md) and [spec](superpowers/specs/2026-05-09-multi-profile-active-design.md)

## v0.2.0-alpha (2026-10-05，實驗性)

**Pulled forward from v2.0**: 只提前「聊天分身」，**不**自建 LLM runtime。設計見 [spec](superpowers/specs/2026-10-05-digital-twin-team-design.md)。

已出貨（experimental，預設安裝但不影響 v0.1.5 既有行為）：

- ✅ **第 7 層 TEAM 與第三階 `team/`**：職位 → 分身 → 能力（三分類 `strengthen` / `create` / `outsource`）→ 頻道；`TEAM.md`（agent 啟動檔）、`team/README.zh-TW.md`（人讀 10 分鐘）、範例 roster、3 個通用職稱分身檔、共用政策、「需要分身嗎？」閘門
- ✅ **工具**：`teamctl`（check / roster / audit-verify）、`build`、`deid`；手寫驗證器 + 錯誤碼，CI 與 gateway 載入時都強制
- ✅ **Chat gateway**（`infra/chat-gateway/`，Python 3.11、核心只用 stdlib）：mock adapter 與 mock driver 完整測試；Slack / Discord adapter 與 Claude Code driver 已隨附，但未在 CI 對真實平台測試、需要憑證
- ✅ **2 分鐘離線 demo**：`python3 infra/chat-gateway/demo.py`（零憑證、零網路）
- ✅ **資料分級 T0–T3**：SaaS 聊天與雲端模型上限 T1；T3 一律拒載
- ✅ `/team` 指令（預覽用，不經 gateway）
- ⚠️ **刻意不做**：沒有長期記憶、沒有任何寫入動作（分身工具恆為唯讀、autonomy 上限 `draft`）

### v0.2.x 候選（spec §14 延後項目，尚未排期）

- 🎯 T3 執行期：獨立 enclave 主機、scope token、記憶牆、地端模型 allowlist、雙人核准（需自架聊天、專屬地端模型、客戶書面同意、滲透測試）
- 🎯 動作執行：`execute()`、副作用與可逆性標註、四眼核准、ERP `CallContext` 與核准 token（需先有可寫入的工具）
- 🎯 長期記憶管線：記憶候選 → 人工審查 → markdown；crypto-shred
- 🎯 Slack 上的 T2 執行期（`riskAcceptance` + 已驗證的 T2 模型路由 + DLP）
- 🎯 gateway 內建 cron（目前用 `post` 子指令 + OS cron）
- 🎯 入站 HTTP（Slack Events 驗簽、Discord Interactions）
- 🎯 分身互相交棒、DM、每則訊息自訂顯示名稱、附件解析
- 🎯 `openai-compatible` / `anthropic-messages` driver
- 🎯 加工部主管分身、profile 提供的分身、LINE / Teams / Mattermost adapter、hook 事件橋接到聊天
- 🎯 JSON Schema 檔；SBOM、`pip-audit`、`--require-hashes`、CODEOWNERS；kill switch `/team freeze`（上 pilot 前）
- 🎯 設備接單設計（ETO）profile（v0.3 需求）

## v0.2 (預計 2026-Q3)

**主題：profile 多樣化 + override 機制成熟**

- 🎯 補完一個社群 profile（最有可能：射出成型，因為下一個目標客戶可能是射出廠）
- ✅ ~~部分內容繼承~~（v0.1.4 提早出貨）
- ✅ ~~多 profile 同時 active~~（v0.1.5 提早出貨）
- ✅ GitHub Actions CI（v0.1.1 起；v0.1.3 加結構檢查；v0.1.4 加 inheritance lint；v0.1.5 加 multi-profile pairwise scan）
- 🎯 自動產生 explainer HTML（從 plugin.json + manifests 動態 render）— 部分達成（v0.1.4 stat panel auto-regen + drift detection），更全面的 catalog 自動化仍 pending

---

## v0.3 (預計 2026-Q4)

**主題：跨平台 adapter**

- 🎯 Cursor adapter
- 🎯 Gemini CLI adapter
- 🎯 Codex adapter
- 🎯 Generic adapter（純 markdown export，給其他 LLM agent 用）
- 🎯 多語 explainer（簡中、英文）

---

## v1.0 (預計 2027-Q1)

**主題：第一個真實導入 case study**

- 🎯 1-2 家指標客戶完整導入
- 🎯 公開 case study（含 ROI 數據、踩雷教訓、最終流程）
- 🎯 IATF 16949 客戶稽核通過實證
- 🎯 plugin 穩定性達生產級
- 🎯 完整文件、有教學影片
- 🎯 公開課程（線下 / 線上）

---

## v2.0 (預計 2027-2028)

**主題：自建 CLI runtime**

對應原始 design 中的圖二：

```
manufacturing-cli (自建 orchestrator)
   ├─ 不依賴 Claude Code
   ├─ 整合 Telegram bot（業助 / 廠長手機通知）— 聊天 gateway 已於 v0.2.0-alpha 提前出貨（mock / Slack / Discord；LINE / Teams / Telegram 仍待評估）
   ├─ 接 IoT / sensor 即時資料
   ├─ 多 agent 協作引擎（仿原始圖二的 wrapper + subagent 模式）— 分身互相交棒延後；alpha 的分身只建議人去 @ 另一個分身
   └─ 純地端可運行
```

**為什麼放這麼後面**：

- v0.1-v1.0 先用 Claude Code 證明價值（聊天分身的 gateway 也是以 Claude Code 為 driver，不自建 LLM runtime）
- 如果市場真的需要 vendor-neutral runtime，再自建
- 自建的開發成本巨大，要有商業 case 支撐

---

## 未排版本但已收集的想法

### 整合方向

- 與 PLM 系統整合（PTC Windchill / SAP PLM / 鼎新 PLM）
- 與 CAD 軟體整合（SolidWorks / Fusion 360 / NX）→ 直接讀 .step 檔
- 與 CAM 軟體整合（Mastercam / NX CAM）→ G-code 自動 review
- 與 IoT 平台整合（PTC ThingWorx / AWS IoT）→ 即時設備狀態
- 與 BI 工具整合（Power BI / Tableau）→ AI 產出送進 dashboard

### 模型方向

- Fine-tune 製造業專屬模型（基於 Qwen / Llama）
- 量化壓縮版（讓更便宜硬體也跑得動）
- 多模態強化（圖紙判讀更準）

### 商業方向

- 認證計畫：「manufacturing-skill 認證顧問」
- 認證計畫：「manufacturing-skill 認證工程師」
- 聯名計畫：與 ERP 廠商合作預先 connector
- 教材：免費線上課（培養生態系）

---

## 不打算做的事（Anti-roadmap）

明確 **NO** 的方向，避免使用者誤期待：

- ❌ Mobile app（不是 plugin 的事）
- ❌ 雲端 SaaS 版（違背地端優先精神）
- ❌ 自家 LLM 訓練（Anthropic / Mistral / Qwen 已經做得很好）
- ❌ 取代 ERP / MES（永遠是 add-on）
- ❌ 客戶端的圖紙判讀 ML（pure CV 任務，不適合 LLM agent）

---

## 如何影響 roadmap

1. **GitHub Issues** — 開 feature request，標 `enhancement` 或 `vertical-profile`
2. **PR** — 直接 contribute，最快納入
3. **商業合作** — 想要某 vertical / 某整合提早做？聯絡 Jason 談 sponsorship
4. **社群討論** — 製造業 AI 導入社群 / Discord（規劃中）

---

## 路線圖修訂歷史

| 日期       | 版本 | 修改                      |
| ---------- | ---- | ------------------------- |
| 2026-04-26 | v0.1 | 初版，含 v0.1 ~ v2.0 規劃 |
| 2026-10-05 | v0.2.0-alpha | 新增分身團隊（TEAM 層、chat gateway）出貨條目與 v0.2.x 候選；v2.0 的 bot 項目註記 gateway 已提前出貨 |
