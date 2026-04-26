# manufacturing-skill

> AI starter kit for manufacturers — fork it, profile it, ship it.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)](https://claude.com/claude-code)
[![繁體中文](https://img.shields.io/badge/lang-%E7%B9%81%E4%B8%AD-red)](README.zh-TW.md)

A Claude Code plugin that gives any manufacturing company a 30-minute path to a working AI assistant — tailored to their vertical, runnable on their own GPU.

> 中文讀者請看 [README.zh-TW.md](README.zh-TW.md)

---

## What this is

`manufacturing-skill` is a **Claude Code plugin** built around a **core + profile overlay** architecture for manufacturing AI adoption.

- **Core layer** — universal manufacturing primitives that apply to _any_ factory: 6-stage flow (quote → order → schedule → produce → inspect → ship), 5 agent personas (quote specialist, sales coordinator, production planner, quality inspector, inventory manager), and a baseline know-how library (ISO 9001, Lean, OEE, MRP).
- **Profile layer** — vertical-specific overlays. v1 ships a complete **CNC machining** profile (4 specialist agents, 3 skills, 4 know-how docs covering IATF 16949, tool life, cutting parameters, job-shop vs. mass production). Stub profiles for PCB assembly, injection molding, food processing, and pharma are scaffolded for community / customer contribution.
- **Infra layer** — MCP server templates for ERP/MES connectivity, on-prem LLM setup guides (Ollama on NVIDIA GB10), and reference configurations.
- **Adapter layer** — a Claude Code adapter (v1). Cursor / Gemini / Codex adapters are post-v1.

---

## Why this exists

Manufacturing AI adoption usually fails on three things:

| Problem                    | Traditional answer                                             | What this plugin gives you                                                           |
| -------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| AI doesn't speak factory   | Train your own LLM, write all the prompts yourself             | 5 built-in agent personas + 4 know-how docs — AI understands ISO/Lean/OEE on day one |
| Every factory is different | Hire an SI, pay for full custom build                          | Core + profile overlay — fork, edit your profile, done                               |
| IT blocks cloud SaaS       | Cannot pass customer audits (drawings must not leave premises) | On-prem-first design with GB10/Ollama runtime                                        |

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/jason-simhope-ai/manufacturing-skill.git manufacturing-skill
cd manufacturing-skill

# 2. Install into Claude Code
bash adapters/claude-code/install.sh

# 3. Try it
# In Claude Code, type:
/quote @examples/sample-drawing/bracket.png
```

You should get a structured quote within 60 seconds.

For on-prem (no internet, IT-friendly) setup, see [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md).

---

## Repo layout

```
manufacturing-skill/
├── manufacturing.md          # The soul — read this first
├── plugin.json               # Claude Code plugin manifest
├── core/                     # Universal manufacturing primitives
│   ├── commands/             # /quote /order-status /bom-check /inspect …
│   ├── agents/               # 5 universal personas
│   ├── skills/               # 6-stage flow + utility skills
│   ├── know-how/             # ISO 9001, Lean, OEE, MRP
│   └── hooks/                # pre-quote / post-order / pre-ship / on-error
├── profiles/
│   ├── cnc-machining/        # ★ Complete v1 profile
│   ├── pcb-assembly/         # Stub — community wanted
│   ├── injection-molding/    # Stub
│   ├── food-processing/      # Stub
│   └── pharma/               # Stub
├── adapters/claude-code/     # Plugin install adapter
├── infra/                    # MCP servers, on-prem LLM setup
├── docs/
│   ├── explainers/           # Three printable Traditional-Chinese cards (boss / IT / operator)
│   ├── architecture.md
│   ├── adoption-guide.md     # For consultants deploying to customers
│   ├── profile-development.md  # For people creating new vertical profiles
│   └── ROADMAP.md
└── examples/                 # Synthetic demo data — never put real customer data here
```

---

## For three audiences

This plugin ships with three printable Traditional-Chinese explainer cards, designed in the spirit of "印出來掛牆" (print and pin to the wall):

- **`docs/explainers/01-架構總覽.html`** — for owners and second-generation manufacturers (機械業二代協進會). 5-minute "what is this and what does it solve."
- **`docs/explainers/02-IT部門系統說明.html`** — for IT departments. Architecture, security, ops perspective. Maps AI/agent terminology to traditional IT terms (Agent ≈ RPA, MCP ≈ ESB, Local LLM ≈ self-hosted server).
- **`docs/explainers/03-使用者cheatsheet.html`** — for daily users (sales assistants, plant managers, QC). Every command, every keystroke they need.

Open the HTML files directly in any browser — no build step, no external dependencies, prints cleanly to A3.

---

## Adopting in your factory

If you want to deploy this to your own factory, read [docs/adoption-guide.md](docs/adoption-guide.md) — it's a consultant playbook with deployment order, common pitfalls, and customization patterns.

If you're a developer / SI wanting to build a profile for a new vertical (e.g., your own injection molding or food processing setup), read [docs/profile-development.md](docs/profile-development.md).

---

## Roadmap

| Version            | Content                                                                                                           | Target                |
| ------------------ | ----------------------------------------------------------------------------------------------------------------- | --------------------- |
| **v0.1** (current) | Core + CNC profile + 3 explainers + Claude Code adapter                                                           | 2026-04               |
| v0.2               | One additional complete vertical profile (community-driven)                                                       | TBD                   |
| v0.3               | Cursor / Gemini CLI adapters                                                                                      | After v0.1 stabilizes |
| v1.0               | First real-world adoption case study from 機械業二代協進會                                                        | TBD                   |
| v2.0               | Self-hosted CLI runtime (Telegram bot integration, on-prem orchestrator — see [docs/ROADMAP.md](docs/ROADMAP.md)) | Market-driven         |

---

## Contributing

PRs welcome. Especially:

- New profile contributions (PCB / injection / food / pharma — see stub READMEs for what's needed)
- ERP connector implementations (SAP / Oracle / 鼎新 / Workday)
- Translations of explainer cards to other languages
- Real-world deployment case studies

---

## License

MIT. Fork it, ship it commercially, no obligation to upstream.

---

## Credits

Created at [SIMHOPE](https://www.simhope.com.tw) (a Taiwan precision machining manufacturer), open-sourced for the broader machinery industry.

Maintained by [Jason Lin](mailto:jasonlin@simhope.com.tw), SIMHOPE Generative AI Specialist.

Architectural inspiration from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (six-layer agent system) and Anthropic's [superpowers](https://github.com/anthropics/superpowers) skill conventions.
