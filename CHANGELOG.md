# Changelog

All notable changes to manufacturing-skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

— Nothing yet.

## [0.1.1] — 2026-04-26

### Added

- **OSS professional polish**: `CONTRIBUTING.md`, this `CHANGELOG.md`, `SECURITY.md`, and `.github/` directory with three issue-form templates (bug / feature / profile-contribution) plus a PR template.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): runs on every push and PR; validates JSON files, sanity-checks `plugin.json`, and lint-checks markdown frontmatter. Intentionally minimal — does not invoke Claude or actually install the plugin.
- **`profiles/injection-molding/` promoted from stub to alpha**: 1 agent (`mold-designer`), 1 skill (`shot-weight-calc`), 2 know-how docs (`common-defects`, `polymer-material-database`). Every file labelled "alpha — needs validation by an injection-molding practitioner."
- `plugin.json` now distinguishes `profiles.alpha` from `profiles.stub` and `profiles.complete`.

### Changed

- `INVENTORY.md` updated: injection-molding moved from "stub" line to its own "alpha" line.
- `profiles/injection-molding/README.md` rewritten from "stub-only, looking for contributor" framing to "alpha — needs validation."

## [0.1.0] — 2026-04-26

Initial public release. Built from the [v0.1 design spec](docs/superpowers/specs/2026-04-26-manufacturing-skill-design.md).

### Added

- **Six-layer architecture** (USE / FLOW / ROLE / INFRA / REF / HOOK) with **two-stage overlay** (core + profile).
- **`core/`** complete:
  - 7 slash commands (`/quote`, `/order-status`, `/bom-check`, `/inspect`, `/install-profile`, `/manufacturing`, `/manufacturing init`)
  - 5 universal agent personas (quote-specialist, sales-coordinator, production-planner, quality-inspector, inventory-manager)
  - 9 skills (6 flow stages 報價 → 出貨 + 3 utility skills: bom-management, capacity-planning, spc-basics)
  - 4 know-how documents (ISO 9001, Lean/5S, OEE, MRP basics)
  - 4 lifecycle hooks (pre-quote, post-order, pre-ship, on-error)
- **CNC machining profile** (the v1 reference complete profile):
  - 4 specialist agents (cnc-programmer, tool-life-engineer, fixture-designer, prototype-coordinator)
  - 3 skills (g-code-review, cutting-parameter-calc, fixture-design-patterns)
  - 4 know-how (IATF 16949, 刀具壽命管理, 切削參數查表, 開發工廠 vs 量產)
  - 1 hook (pre-cnc-program-checkin)
- **Stub profiles** for PCB assembly, injection molding, food processing, pharma — each with a `_templates/agent-starter.md` ready to fill in.
- **Claude Code adapter** (`adapters/claude-code/`): `install.sh` with interactive profile picker, `--core-only` and `--list` flags, POSIX-bash-3.2 compatible.
- **Reference MCP servers** (`infra/mcp-servers/`):
  - `scheduler-mcp/` — runnable stub with mock data for production-scheduling tools
  - `erp-connector/` — interface contract (`contract.py`) for SAP / Oracle / 鼎新 / Workday adapters
- **On-prem deployment guide** (`infra/on-prem/gb10-setup.md`): NVIDIA GB10 + Ollama setup for air-gapped operation.
- **Four printable Traditional-Chinese explainer cards** (`docs/explainers/`):
  - 01 架構總覽 (for owners)
  - 02 IT 部門系統說明 (for IT depts; AI-to-traditional-IT term mapping)
  - 03 使用者 cheatsheet (for daily users)
  - 04 懶人包 5 分鐘上手 (for "just show me, don't make me read" people)
- **Four PNG snapshots** of the explainer cards in `docs/explainers/screenshots/`.
- **Live demo banner** (`docs/demo/`): real Claude Opus 4.7 response captured live, rendered as a Claude.ai-styled HTML page in both 繁中 and English. The captured response notably caught a real engineering contradiction in the customer RFQ (SUS304 stainless cannot be anodized).
- **Landing page** (`docs/index.html`): single-page marketing site for the project, served via GitHub Pages from `/docs`.
- **Documentation set**:
  - `docs/architecture.md` — six-layer architecture deep-dive for developers
  - `docs/adoption-guide.md` — 6-week deployment playbook for AI consultants
  - `docs/profile-development.md` — guide for creating new vertical profiles
  - `docs/ROADMAP.md` — versions v0.1 → v2.0
  - `INVENTORY.md` — one-page entry-point map of the entire repo
- **MIT License**.
- **Bilingual READMEs**: `README.md` (English) + `README.zh-TW.md` (繁體中文).
- Synthetic demo data in `examples/` (no real customer information).

### Notes

- Authoring credit: created at SIMHOPE (Taiwan precision machining); maintained by Jason Lin (<jasonlin@simhope.com.tw>).
- Architectural inspiration credited in README to [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) and Anthropic's [superpowers](https://github.com/anthropics/superpowers) skill conventions.

[Unreleased]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jason-simhope-ai/manufacturing-skill/releases/tag/v0.1.0
