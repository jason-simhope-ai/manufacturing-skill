# Changelog

All notable changes to manufacturing-skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

— Nothing yet.

## [0.1.4] — 2026-05-09

**Profile inheritance mechanism** ships as **experimental**. Profiles can now declare `extends: core/<kind>/<name>` in frontmatter and incrementally merge against a core file at install time, instead of copy-pasting the whole core file as v0.1.x required.

### Added

- **`adapters/claude-code/_resolve_extends.py`** — install-time merge resolver. Pure stdlib + PyYAML. Handles per-field frontmatter merge (lists union by default, scalars profile-wins, `<field>-replace: true` opt-out), three body directives (`<!-- inherit -->`, `<!-- replace-section: <heading> -->`, `<!-- override-body -->`), NFKC-normalized heading match, and code-block-aware directive scanning so authored docs with example markdown don't trigger directives.
- **`tests/extends/`** — 13 golden-file fixtures pinning down resolver behaviour: pure inherit, append, single replace-section, multiple replace-sections, override-body, list union, list replace-flag opt-out, and 6 error cases (missing mode marker, both markers, bad extends path, bad replace heading, extends-on-command, code-block escape). Runner: `python tests/extends/run.py`.
- **`install.sh --resolve <profile>/<kind>/<file>`** — preview merged output without committing to a full install. Useful for PR reviewers to see what the model actually reads after merge, not just the profile delta.
- **CI Step 10a** — lint every profile file with `extends:` against the resolver in lint mode.
- **CI Step 10b** — bidirectional heading-anchor protection. A core PR that renames or removes a `## ` heading still referenced by any profile's `<!-- replace-section: <heading> -->` fails on the **core PR**, not silently at install time months later.
- **CI Step 10c** — runs the 13-fixture test suite on every CI run.

### Changed

- **`adapters/claude-code/install.sh`** Stage 2: per-file dispatch. Files with `extends:` go through the resolver; files without continue to use plain `cp` (v0.1.x whole-file override). Detects Python via `py` launcher (Windows), `python3`, or `python`, with `--version` sanity check to dodge Microsoft Store stubs that exit 49 on actual use.
- **`docs/profile-development.md`** — new "部分內容繼承 — `extends:`" subsection replaces the old "v0.2 計畫" placeholder. Documents the three directives, frontmatter merge rules, `--resolve` preview, and limitations (no commands extends, no cross-profile inheritance, NFKC heading match).
- **`plugin.json` version**: 0.1.3 → 0.1.4.

### Notes — experimental status

`extends:` is shipped as **experimental** for v0.1.4. The mechanism is not used by any current profile in this repo (CNC, injection-molding); both still use whole-file overrides which continue to work unchanged. The first real consumer of `extends:` will validate the design against a live use case before we lock the contract in v0.2.

If you hit a resolver bug or have feedback on the directive surface, open an issue and tag `extends-experimental`.

### Notes — Python / PyYAML dependency

A profile using `extends:` requires Python 3 + PyYAML on the install machine. Profiles that don't use `extends:` continue to install with no Python dependency at all. `install.sh` detects the missing dependency and prints a clear install-pip command before bailing.

### Spec

Full design rationale: [docs/superpowers/specs/2026-05-08-profile-inheritance-design.md](docs/superpowers/specs/2026-05-08-profile-inheritance-design.md). Approved 2026-05-09 after a v1 → v2 self-review pass that surfaced 3 high-severity gaps (frontmatter list merge, core-side heading rename protection, silent fall-through on missing inherit marker), all patched in v2.

## [0.1.3] — 2026-05-08

Documentation-only release. No agent / skill / command behaviour changes; the
plugin surface is identical to v0.1.2. Released so that the polished onboarding
materials are reachable via a tagged version, and so the GitHub Release page
reflects the live README state instead of the v0.1.2 snapshot.

### Added

- **Beginner quickstart guide** (`docs/quickstart-for-beginners.zh-TW.md`) —
  6-step walkthrough for users who have never installed a CLI tool, written for
  non-engineer factory staff. Includes Windows / macOS terminal basics, "what
  Claude Code is" plain-Chinese framing, install troubleshooting, and a
  cost-expectations section.
- **Quickstart visual assets** (`docs/quickstart-screenshots/`) — 7 step-by-step
  images: real screenshots for steps 1-3 (download page, first launch, sign-in)
  and HTML-rendered mockups for steps 4-6 (main window, profile picker, /quote
  success). `CAPTURE-GUIDE.md` documents how each was produced.
- **`/quote` live-demo GIFs** (`docs/demo/quote-demo.gif`, `quote-demo-en.gif`)
  — 19-second screen recordings of the real /quote flow, embedded in both
  README files and the beginner guide. Bilingual (繁中 + EN).
- **Six-capability demo slide** (`docs/demo/slides/`) — HTML + retina PNG, used
  in introductions to position what the plugin actually does end-to-end.

### Changed

- **`README.zh-TW.md`** reworked per first-round demo feedback: removed
  二代協進會 references that were specific to one audience, tightened the
  positioning paragraph, embedded the GIF demo above the fold.
- **Quickstart for beginners** facts corrected: install path, profile picker
  behaviour, IATF gloss, and step counts now match what install.sh actually
  does.
- **`plugin.json` version**: 0.1.2 → 0.1.3.

### Notes

- This release is the cumulative result of PRs #1, #2, #4, #5, #6, and #7,
  all merged between 2026-04-27 and 2026-04-27. PR #3 was a closed duplicate
  of #4.
- No `core/` or `profiles/` content changed in this window — the plugin
  installation experience is byte-identical to v0.1.2 once installed.

## [0.1.2] — 2026-04-26

### Added

- **3 reference know-how docs** in `core/know-how/` that core agents repeatedly need:
  - `gd-and-t.md` — 14 GD&T symbols (ASME Y14.5-2018), feature control frame parsing, MMC/LMC/RFS modifiers, datum 3-2-1 system, anti-patterns. Notes ISO 1101 differences and the 2018-removed Concentricity / Symmetry.
  - `fmea-pfmea.md` — AIAG-VDA harmonized 7-step method (post-2019), S/O/D scoring with AP (Action Priority) replacing legacy RPN, worked PFMEA template row.
  - `incoterms.md` — INCOTERMS 2020 covering all 11 terms, risk-vs-cost transfer diagram, FOB-vs-FCA on containers gotcha, 5 most-used patterns for Taiwan manufacturers.
- **2 daily-use slash commands** in `core/commands/`:
  - `/morning-briefing` — plant-manager 8 AM standup briefing aggregating yesterday's results, today's deliveries, this week's risks, pending decisions, equipment items. Dispatches to 4 core agents in parallel. Documents graceful degradation when scheduler-mcp / erp-connector aren't connected.
  - `/8d` — triggers the 8D customer-complaint flow with worked example output for all eight disciplines.
- **`8d-report-writing` skill** in `core/skills/`: full SOP for D1-D8 with completion signals, customer-deliverable template, corrective-action strength hierarchy (training weakest, source-elimination strongest), Why-5 worked example escalating from "operator carelessness" to a real systemic root cause, 9-item self-checklist.
- **Engineering Change Management bundle** — fills one of the largest baseline gaps:
  - `core/agents/engineering-change-manager.md` — cross-functional ECM lead persona owning ECN/ECO from request to closure. Worked impact-analysis example covering all 13 axes plus Class II classification reasoning.
  - `core/skills/engineering-change-process.md` — 5-step SOP (ECR → Impact → CCB → Implementation → Verification & Closure) with 13-item impact-analysis checklist, 9-item sync-update list, hard-cutover-vs-soft-transition decision.
  - `core/know-how/eco-ecn.md` — conceptual basis: ISO 9001 §8.5.6 + IATF 16949 §8.5.6.1 mapping, document hierarchy showing how a single drawing rev cascades to BOM/SOP/PFMEA/Control Plan/Work Instruction, recommended tooling by factory size.

### Changed

- **CI frontmatter check** now uses real PyYAML parsing instead of string-grep — eliminates false negatives when YAML key names appear inside markdown body examples.
- **`.github/ISSUE_TEMPLATE/config.yml`** added: disables blank issues, routes 4 non-bug intents (questions, security, commercial, "where do I find X") to the right destination instead of bug-report by default.
- **CI status badge** added to README.md and README.zh-TW.md.
- **`plugin.json` version**: 0.1.1 → 0.1.2.
- **`INVENTORY.md` counts** updated: agents 5→6, commands 7→9, skills 9→11 (with 8d-report-writing), know-how 4→7. Added new entries to relevant sections.
- **`docs/explainers/01-架構總覽.html`** sidebar metrics updated to match the new counts (10 agents shown including profile additions, 14 skills, 11 know-how, plus the new commands listed).

### Notes

- v0.1.2 was scoped from a v0.1.1 review pass; see [the v0.1.2 design spec](docs/superpowers/specs/2026-04-26-v0.1.2-polish-and-three-bundles-design.md) for the full reasoning.
- All new content shipped with the same honesty constraints as v0.1.1 — references the canonical industry source (ASME Y14.5, AIAG-VDA, INCOTERMS, Ford 8D, ISO 9001 §8.5.6) for each topic, and flags areas where convention differs (US vs EU drawings, legacy AIAG vs harmonized).

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

[Unreleased]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jason-simhope-ai/manufacturing-skill/releases/tag/v0.1.0
