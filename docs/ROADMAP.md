# Roadmap

> manufacturing-skill 路線圖。版本與時程會依社群回饋與商業合作機會調整。

---

## v0.1 (current — 2026-04)

第一個可發行版本：

- ✅ 六層架構（USE / FLOW / ROLE / INFRA / REF / HOOK）
- ✅ Core 完整：6 段流程、5 隻 agent、9 個 skill、4 份 know-how、4 個 hook
- ✅ CNC profile 完整：4 agent、3 skill、4 know-how、1 hook
- ✅ 4 個 stub profile（PCB / 射出 / 食品 / 製藥）
- ✅ Claude Code adapter（含 install.sh）
- ✅ scheduler-mcp 範例（含 mock data 可立即跑）
- ✅ erp-connector contract（template，實作交給用戶）
- ✅ GB10 地端 LLM 安裝指南
- ✅ 3 張繁中 explainer 圖卡（架構 / IT / cheatsheet）
- ✅ 完整 docs（architecture / adoption-guide / profile-development / 此 ROADMAP）
- ✅ 合成 demo data（examples/）

---

## v0.2 (預計 2026-Q3)

**主題：profile 多樣化 + override 機制成熟**

- 🎯 補完一個社群 profile（最有可能：射出成型，因為下一個目標客戶可能是射出廠）
- 🎯 部分內容繼承（profile agent prompt 開頭可寫 `<!-- extends: core/... -->` 不用 copy 整檔）
- 🎯 多 profile 同時 active（橫跨 vertical 的工廠用）
- 🎯 GitHub Actions CI（lint markdown frontmatter、驗證 plugin.json schema）
- 🎯 自動產生 explainer HTML（從 plugin.json + manifests 動態 render）

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
   ├─ 整合 Telegram bot（業助 / 廠長手機通知）
   ├─ 接 IoT / sensor 即時資料
   ├─ 多 agent 協作引擎（仿原始圖二的 wrapper + subagent 模式）
   └─ 純地端可運行
```

**為什麼放這麼後面**：

- v0.1-v1.0 先用 Claude Code 證明價值
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
