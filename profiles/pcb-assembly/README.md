# profiles/pcb-assembly/ (stub)

> Status: **🚧 stub** — only `profile.json` + this README.
> Looking for a contributor with PCB / SMT / EMS production-floor experience.

---

## What this profile would cover

PCB 組裝（電子組裝服務 / EMS）流程：

- **SMT** (Surface Mount Technology) — 錫膏印刷 → 貼片 → 回流焊 → AOI
- **DIP** / Wave soldering — 插件 + 波峰焊
- **ICT / FCT** — 線路測試 + 功能測試
- **Box build** — 整機組裝、測試、包裝

---

## Wanted contributions（我們需要這些）

### Agents

- `smt-process-engineer` — 錫膏 / 鋼板 / 貼片 / 回流溫度曲線
- `pcb-test-engineer` — ICT 測試程式、夾具、覆蓋率
- `box-build-coordinator` — 整機組裝排程

### Skills

- `solder-paste-inspection` — 錫膏量、錯位檢查
- `reflow-profile-tuning` — 回流溫度曲線調整
- `aoi-result-analysis` — AOI 結果判讀與假警報處理

### Know-how

- `ipc-a-610` — 電子組裝可接受性標準
- `j-std-001` — 焊接標準
- `msl-management` — 元件濕度敏感等級管理
- `rework-process` — 返修標準流程
- `ESD-control` — 靜電防護

---

## How to contribute

1. Fork this repo
2. Read `docs/profile-development.md`
3. Build out `agents/`, `skills/`, `know-how/`, `hooks/` following the CNC profile as a reference
4. Update `profile.json` with the actual content list
5. Submit PR — we'll review and merge

---

## Why this is still a stub

v1 focuses on CNC machining as the launch industry pack. PCB profile is not in v1 scope but is structurally ready to receive contribution.

If your company is a PCB / EMS shop and you'd like to commission this profile (paid contract for SIMHOPE consulting), contact [Jason Lin](mailto:jasonlin@simhope.com.tw).
