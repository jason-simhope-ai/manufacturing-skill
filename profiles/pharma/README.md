# profiles/pharma/ (stub)

> Status: **🚧 stub** — only `profile.json` + this README.
>
> ⚠️ **製藥業導入 AI 合規門檻極高**。需要有 GMP / CSV / Data Integrity 經驗的 contributor。

---

## 製藥業 AI 的特殊性

與其他垂直領域最大不同：

1. **CSV (Computer System Validation)** — 所有電腦系統（包括 AI）使用前須驗證
2. **ALCOA+ 資料完整性** — Attributable / Legible / Contemporaneous / Original / Accurate / + Complete / Consistent / Enduring / Available
3. **21 CFR Part 11** — 電子紀錄與電子簽章規範
4. **Annex 11** — 歐盟電腦化系統規範
5. **每張 Batch Record 都是法律文件** — AI 不可直接產出，只可輔助

---

## 建議的 AI 應用範圍（v1 stub 階段建議）

✅ **可用 AI 的低風險場景：**

- 報價（非 GxP）
- 排程
- 文件草稿（後續仍須 QA 審核 + 簽署）
- 偏差初步分析建議
- 設備保養排程

❌ **不可直接用 AI 的場景：**

- Batch Record 直接產出
- 放行決策（Release）
- 任何進到 GxP 系統的資料未經人類 QA 簽認

---

## Wanted contributions

### Agents

- `qa-pharmacist` — 品保藥師（審核、放行）
- `validation-engineer` — IQ/OQ/PQ、清潔驗證、CSV
- `deviation-handler` — 偏差處理流程

### Skills

- `batch-record-review`
- `process-validation` (PV)
- `computer-system-validation` (CSV) — 包括 AI agent 自身的 CSV
- `data-integrity-check` (ALCOA+)

### Know-how

- `gmp` (PIC/S, EU GMP, US FDA cGMP)
- `ich-q-series` (Q7 API GMP, Q8 QbD, Q9 QRM, Q10 PQS)
- `21-cfr-part-11`
- `annex-11`
- `data-integrity-alcoa-plus`

---

## How to contribute

由於合規敏感性，請聯絡 [Jason Lin](mailto:jasonlin@simhope.com.tw) 討論 contribution 形式（公開 PR vs 私下協作）。

---

## 為什麼 v1 仍保留此 stub

- 標示框架的擴展性（連製藥都能裝）
- 給對「製藥廠也想用 manufacturing-plugin」的潛在客戶一個入口
- 預留正式 profile 的成長空間
