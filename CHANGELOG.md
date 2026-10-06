# Changelog

All notable changes to manufacturing-skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`docs/consulting/`** — consultant deliverables kit (zh-TW, generic, placeholder fees only): 90-minute discovery workshop, IT / security data-flow questionnaire, SOW template, one-page pilot sign-off, per-wave deliverables checklist; linked from `docs/adoption-guide.md`.
- **`CLAUDE.md`** — contributor guide for coding agents: repo map, language conventions, CI rules with local replay commands, profile checklist, and the never-list.
- **`profiles/food-processing/` promoted from stub to alpha** (`0.1.0-alpha`): 2 agents (`haccp-coordinator`, `traceability-officer`), 2 skills (`haccp-plan-review` — Codex 12 steps / 7 principles checklist + CCP decision tree; `batch-traceability-recall-drill` — one-up / one-down trace, timed mock recall, mass balance), 2 know-how docs (`haccp-iso22000-basics`, `food-defects-and-ccp-examples`), and a food-specific `pre-ship` hook override (CCP record sign-off, CoA, lot / expiry consistency, allergen label vs. recipe, cold-chain temperature records). Every file carries an alpha header; all critical limits are labelled as examples and Taiwan regulatory specifics as "needs verification" (需驗證). Agents explicitly never sign off a CCP deviation, release product, or decide a recall — a human does.
- `profiles/food-processing/profile.json` gains `warnings` (does not replace a qualified HACCP team / regulatory counsel), expanded `complianceFrameworks` (HACCP, ISO 22000, FSSC 22000, ISO/TS 22002-1, Taiwan Food Safety and Sanitation Act / GHP / HACCP regulation / traceability rules, TQF) and updated `wantedContributions`.
- `profiles/food-processing/README.md` rewritten in zh-TW for non-technical successors, with short LINE-oriented usage tips and a clear does / does-not table.
- **`profiles/pcb-assembly/` promoted from stub to alpha** (`0.1.0-alpha`): 2 agents (`smt-process-engineer` — print / placement / reflow reasoning and DFM feedback; `ems-quality-analyst` — AOI / SPI / ICT / FCT defect analysis, first-article checks, MSL handling), 2 skills (`smt-dfm-review` — land pattern / stencil / spacing / MSL / panelization checklist; `aoi-defect-pareto` — exported CSV → per-station FPY, DPMO, Pareto and action list), 2 know-how docs (`ipc-a-610-basics` — classes, conditions, criteria families without reproducing clause text; `smt-common-defects` — tombstoning, bridging, head-in-pillow, voids, insufficient solder). Every file carries an alpha header; numbers are labelled 範例 (example) or 需驗證 (needs verification). Both agents refuse to change a line reflow profile without human sign-off and never approve deviations. No MES integration yet — data must be exported; a read-only `mes-connector` following the `erp-connector` contract pattern is listed in `wantedContributions`.
- `profile.json` for pcb-assembly gains `complianceFrameworks` (IPC-A-610, J-STD-001, IPC-7711/7721, J-STD-020/033, ESD, ISO 9001, IATF 16949 optional, RoHS / REACH), `warnings` and an updated `wantedContributions` list.
- **`profiles/pharma/` promoted from stub to alpha** (`0.1.0-alpha`, GMP / GxP for API, drug product and medical devices): 2 agents (`deviation-capa-coordinator` — deviation fact summary, classification suggestion, investigation structure, impact-assessment prompts, CAPA and effectiveness-check drafts; `batch-record-reviewer` — completeness / signature / calculation / chronology / ALCOA+ pre-check before QA review), 2 skills (`deviation-investigation-5whys-fishbone` — Is / Is-not, 6M fishbone, evidence plan, 5 Whys to a system-level cause, CAPA with predefined effectiveness criteria; `batch-record-completeness-review` — reviewer checklist, ALCOA+ data-integrity signals, top-10 common findings), 2 know-how docs (`gmp-gxp-basics` — ICH Q10 pillars, documentation hierarchy, GDP, deviation vs OOS vs OOT, ALCOA+, common inspection findings; `validation-and-change-control` — DQ/IQ/OQ/PQ, process validation lifecycle, CSV, change-control flow, revalidation triggers), and a new `pre-batch-release` hook (QA release document-completeness check: batch record reviewed, CoA, deviations / OOS closed, change controls approved). The hook uses its own name rather than overriding core `pre-ship`, so it cannot collide with another profile's `pre-ship` override. Every file carries an alpha header and labels numbers 範例 / 需驗證. Every output is marked `AI-DRAFT — 非 GMP 紀錄`: agents never close a deviation, approve a CAPA, invalidate an OOS or release a batch.
- `profiles/pharma/profile.json` gains `warnings` (does not replace the QA / QP release decision, regulatory affairs, or a validated system; AI output is never a GMP record; the plugin itself is not CSV-validated), expanded `complianceFrameworks` (PIC/S GMP incl. Annex 11 / 15, EU GMP, 21 CFR 210 / 211 / 820, ICH Q7 / Q9(R1) / Q10, 21 CFR Part 11, ALCOA+ data integrity, ISO 13485, Taiwan PIC/S GMP and medical-device QMS regulations — specifics marked 需驗證) and updated `wantedContributions`.
- `profiles/pharma/README.md` rewritten in zh-TW for non-technical successors, with LINE-oriented usage tips (de-identify first, never paste AI output into a GMP record) and a does / does-not table.
- **`profiles/machinery-eto/` added as alpha** (`0.1.0-alpha`, machinery / equipment makers that build to order — special-purpose machines, automation cells, machine-tool / forming / molding-class equipment): 3 agents (`eto-quote-engineer` — option / configuration-based machine quoting, cost structure, always lists assumptions and open specs, dispatches part-level quoting to core `quote-specialist`; `project-engineer` — spec freeze, design reviews, long-lead procurement, FAT / SAT preparation, never replaces the PM's commitments; `commissioning-service-coordinator` — site readiness, SAT records and punch lists, handover pack, spare-parts list, after-sales triage and escalation, never promises dates), 3 skills (`eto-quote-breakdown` — option table with mandatory status, design-hour / bought-out / in-house split, FAT / transport / installation / training / documentation / spares / warranty lines, transparent risk markup, validity and exchange-rate clauses; `spec-freeze-and-design-review` — freeze checklist, DR1 / DR2 / DR3 checklists, post-freeze re-quote triggers; `fat-sat-acceptance` — FAT and SAT checklists, punch-list grading, acceptance record format, warranty-start options), 3 know-how docs (`eto-vs-mts-quoting`, `machinery-safety-ce-basics` — ISO 12100 risk-assessment flow, safety functions, CE technical file under 2006/42/EC and the new Machinery Regulation (EU) 2023/1230, Taiwan machinery safety-information declaration; `project-handover-and-after-sales` — handover pack, spares vs consumables, example SLA and escalation matrix), and a `pre-quote` hook override that keeps every core part-level check and adds ETO gates (no formal quote while the spec is not frozen — budgetary only; every undecided option marked `[需澄清]`). No other profile overrides `pre-quote`, so the pairwise scan stays clean. Every file carries an alpha header; all numbers are labelled 範例 and every regulatory item 需驗證. Quotes are engineering estimates; CE / safety sign-off is a human engineer's and nothing in the profile is a safety assessment.
- `plugin.json`: `machinery-eto` added to `profiles.available` and `profiles.alpha`. `INVENTORY.md`, `README.md`, `README.zh-TW.md`, `core/commands/install-profile.md`, the profile-contribution issue template and explainer 01 (stat panel regenerated; agent / know-how overlay rows and legend list the machinery-ETO items) updated.
- **CI guardrails for profile contributors** (three new steps appended to `.github/workflows/ci.yml`): `Profiles — every profiles/<dir> is registered in plugin.json` (an unregistered profile was silently skipped by the manifest, explainer-stat and pairwise-conflict steps; also checks that `profile.json` `status` matches the `plugin.json` list that names it), `Agents — tool allowlist` (every `core/**/agents`, `profiles/**/agents` and `profiles/**/_templates/agent-*.md` must declare `tools` within `Read, Grep, Glob` plus the read-only `mcp__manufacturing-scheduler__*` tools; `Bash` only with a `<!-- tools: bash-justified: <reason> -->` marker in the body, never in starter templates; `WebFetch` and anything else are rejected), and `Explainer 01 — overlay rows vs stat panel` (the hand-edited agent / know-how / hook overlay rows and their `CNC a + alpha α b` labels must equal the regenerated stat numbers).
- Explainer 01 hook row now shows the three alpha hooks (`pre-ship` food, `pre-batch-release` pharma, `pre-quote` machinery-ETO) that the stat panel already counted; label is `CNC 1 + alpha α 3`.

### Changed
- **IATF 16949 / PPAP know-how promoted from the CNC profile to core** (`core/know-how/iatf-16949.md`) so injection-molding and every other profile get it; generalised for any automotive-supplier process with a new per-process section (machining / injection / die-casting / stamping / EMS). The CNC profile manifest drops `iatf-16949` (3 know-how left); profile-level counts, INVENTORY, architecture docs and the explainer were updated.
- **PPAP table corrected**: Level 1 is PSW-only, Level 5 is review at the supplier's site (was "internal audit"), the 18 elements are retained for every level (the level only decides what is submitted), and the claim that ISO 9001 requires Cpk ≥ 1.33 was removed (1.67 / 1.33 are PPAP initial-study readings, not ISO 9001 requirements; details still flagged 需驗證 for IATF-auditor review).
- `plugin.json`: `food-processing`, `pcb-assembly` and `pharma` moved from `profiles.stub` to `profiles.alpha` (now `injection-molding`, `food-processing`, `pcb-assembly`, `pharma`); `profiles.stub` is now empty (`[]`, key kept for CI).
- `scripts/regen_explainers.py`: alpha counts now sum over every profile in `profiles.alpha` (was hard-coded to injection-molding); hooks stat shows the alpha share when non-zero. Explainer 01 stat panel regenerated, and its agent / know-how overlay rows and legend now show the PCB alpha items.
- `INVENTORY.md`, `README.md`, `README.zh-TW.md`, `core/commands/install-profile.md` and the profile-contribution issue template: food-processing, pcb-assembly and pharma shown as alpha (READMEs also correct injection-molding, which was still shown as stub); core know-how count is 9 and CNC know-how is 3 after the IATF 16949 promotion.
- **`docs/profile-development.md` rewritten** to match what CI actually enforces: a `profile.json` template with every required field (`applicableTo`, `description`, `hooks`, plus `status`, `warnings`, `wantedContributions`, `complianceFrameworks`), an `extends:` example with every required frontmatter field (`model` included), the `plugin.json` registration step (`profiles.available` + status list), frontmatter specs per file type, the tool policy, the no-real-names / no-real-prices rule with the 需驗證 labelling convention, the alpha-only status model (no stubs, no `overrides.removed`), multi-profile co-activation rules (hook-name ownership, no cross-profile `extends:`), the 13-item checklist of files to update, and the exact local CI replay command. Scaffold step now copies an alpha profile (not `cnc-machining`).
- **Agent tools minimised**: `Bash` removed from the 6 core agents, the 4 CNC agents, the food / injection / PCB profile agents and from every profile `_templates/agent-starter.md` (none of their bodies run anything). `profiles/pharma/agents/deviation-capa-coordinator.md` keeps `Bash` for its CSV trend step and carries the justification marker. Core commands' `allowed-tools` are unchanged by this entry.
- `bug-report.yml` (Active profile) gains `machinery-eto`; quickstart and explainer 04 install-menu samples now list all six profiles in installer order with `0-6`, and stop calling the alpha profiles stubs; `core/commands/init.md` question 1 lists the five alpha profiles incl. machinery ETO instead of "stub"; `CONTRIBUTING.md`, the PR template, `feature-request.yml` and both READMEs no longer describe stub promotion or "fork the CNC profile" as the path for a new profile.
- **Generic adapter (experimental, v0.3 preview)** — `adapters/generic/export.py` exports the same merged content `install.sh` would install (core + profile overlay, `extends:` resolved, multi-profile conflict scan) as plain markdown for non-Claude agents (Cursor, Gemini CLI, Codex, on-prem Ollama, print). Reuses `adapters/claude-code/_resolve_extends.py` and `_multiprofile.py` rather than reimplementing them. Two formats: `--format files` (directory tree + `MANIFEST.json` with source, origin, versions and sha256 per file) and `--format bundle` (single `manufacturing-skill.<profiles>.md` with bilingual how-to preamble, table of contents and per-file frontmatter tables). Slash commands are exported as "playbooks" and hooks are marked documentation-only. `--include` filters kinds; `--reproducible` drops the MANIFEST timestamp for byte-identical output. Docs in `adapters/generic/README.md` (zh-TW).
- **CI step "Generic adapter — export tests"** — `tests/generic/test_export.py` (12 stdlib unittest cases: core-only / single-profile file sets, profile override precedence, all `tests/extends` success fixtures exported identically to the resolver's expected output, resolver-failure / conflict / unknown-profile / bad `--include` exits, bundle + MANIFEST determinism, MANIFEST sha256 integrity, `--force` overwrite guard).
### Fixed
- **Resolver ignores directives and headings inside fenced code** (`_resolve_extends.py`) — `<!-- inherit -->` / `<!-- override-body -->` / `<!-- replace-section: X -->` examples inside ``` or ~~~ fences are now skipped by both validation and assembly (they previously passed validation but were substituted in the output, producing a corrupted file with exit 0). `## ` lines inside fences no longer end a replace-section block, and no longer split sections of the core body. Validation and assembly now share one offset-preserving scan.
- **Resolver rejects bad `extends:` values with a clean error** — a list, mapping, int or empty `extends:` and unparsable YAML frontmatter now exit non-zero with a one-line `::error` instead of a Python traceback. `--out` creates missing parent directories.
- **`extends:` path check no longer bypassable** — the core-containment test compared string prefixes, so `core-evil/...` passed; the path is now normalised and checked by components (absolute paths, `..` and non-`core/` roots are rejected before any file is touched).
- **`tests/extends/run.py` cannot pass vacuously** — fails when zero cases are discovered (and prints the count), when the cases do not exercise every directive type (`inherit`, `override-body`, `replace-section`) plus an error case, when an error case crashes with a traceback or emits other than one `::error` line, or when `lint` disagrees with `resolve`. Adds fixtures `case-14` to `case-24` (fenced markers, fenced headings, bad `extends` types, bad YAML, `core-evil` prefix, `..` traversal).
- **Multi-profile collision scan is case-insensitive** (`_multiprofile.py`) — `Quote.md` vs `quote.md` now collide (macOS/Windows filesystems fold case); a missing kind directory is treated as empty; a non-dict `mcp` in a manifest no longer crashes aggregation. 8 new unit tests (16 total).
- **`infra/mcp-servers/erp-connector/contract.py`** — every tool now takes a typed, frozen `CallContext` (`operator_id`, `role`, `channel`, `request_id`, `classification` T0–T3, tz-aware `timestamp`, optional `approval_token`) as its first argument. The free-string `operator` parameter is removed (it could be forged). **Breaking for existing connector implementations.**
- Write tools (`create_sales_order`, `create_purchase_request`, `update_inventory_movement`, `close_sales_order`) now require a keyword-only `idempotency_key` and return a `WriteResult` (status `committed` / `replayed` / `refused`, plus audit fields) instead of a bare `str` / `bool`, so a refusal is no longer conflated with a failure.
- Read tools return typed results with price and customer-contact fields masked by role (`masked_fields` lists what was hidden); inventory quantities and ledger `qty` are `Decimal`, timestamps are timezone-aware (CODE-AUDIT F26).
- `infra/mcp-servers/erp-connector/README.md` — rewritten for the new interface: `CallContext` fields, masking defaults, approval-token flow, implementation checklist, security notes (read-only service account for queries, write tools gated by approval token + role, log every call with the `CallContext`).
- `SECURITY.md` — ERP bullet now names the `CallContext` / `idempotency_key` fields instead of `operator`.
- `verify_approval(token, action_hash)` hook plus `authorize_write()` helper on the ERP contract: implementations must verify an approval token bound to the action hash (signature, expiry, approver different from requester, approver role allowed for the tool via `approver_roles`) before any write, and one approval (`approval_id`) authorises exactly one write (`approval_already_used`).
- Canonical approval hash and token format defined in `contract.py` (`canonical_args`, `compute_action_hash`, `issue_approval_token`, `verify_approval_token`, golden vector in the tests): Decimal/int -> normalised decimal string, datetime -> UTC `Z`, float rejected. Nothing signs tokens in production yet; the chat gateway will adopt this format when its execute path lands.
- `to_jsonable()` for result types, `aware()` for naive ERP timestamps (result types now reject naive datetimes), `ListResult.total_matched` may be `None` (`has_more`), `sensitive_groups` for custom masked fields; default `record_audit` writes JSON lines to stderr instead of an unconfigured logger.
- `max_rows` (default 200, hard cap 1000) and `fields` (allowlist) on the new list tools `list_customers`, `list_parts`, `list_inventory`; default masking of `price` and `customer_contact` field groups unless the role is granted them (deny by default).
- `infra/mcp-servers/erp-connector/mock_connector.py` and `mock-data/erp_mock.json` — reference `MockErpConnector` over synthetic data demonstrating masking, row caps, idempotent writes and refusal without a valid approval token.
- `tests/mcp/test_erp_contract.py` (stdlib `unittest`) with a reusable `ConformanceSuite` mixin to run against your own connector, and a CI step "erp-connector — contract tests".
- ERP contract hardening: `DEFAULT_APPROVER_ROLES` now use team roster position ids (`sales-manager`, `production-manager`; `APPROVER_ROLE_ID_RE` = the team linter's position-id pattern); approval token is `v2` and binds the requester (`approval_requester_mismatch`); approval secrets must be `bytes` of at least 32 bytes (`approval_misconfigured` on verify); `ApprovalStore` / `InMemoryApprovalStore` / `JsonFileApprovalStore` make single use survive restarts; `project_fields()` masks recursively and case-insensitively; `ConformanceSuite` now requires `written_count` and `make_restarted_connector` and checks ERP writes after every test. **Breaking for token issuers and connector test subclasses.**
- **`infra/mcp-servers/scheduler-mcp`** is now a genuine MCP stdio server (JSON-RPC 2.0: `initialize`, `tools/list`, `tools/call`, `ping`) using only the Python standard library (3.10+). The README now shows the real tool names and arguments, a `claude mcp add` example, and a manual smoke test; `tests/mcp/test_scheduler_mcp.py` runs in CI.
- **scheduler-mcp** (`manufacturing-scheduler`): `validate()` now supports boolean / array / object / null; an internal validation bug is reported as `-32603 internal error: <ExceptionClass>` instead of `-32602 unknown tool`. List tools (`list_work_orders`, `find_bottlenecks`) take `limit` (default 50, max 200, above max is `-32602`) and `offset`, and return `has_more`; `list_work_orders` also filters by `so_id` / `customer`. The JSON-RPC plumbing is a reusable `McpServer` class. `find_bottlenecks` is documented and tested as inclusive (`load_pct >= threshold`), matching `production-planner`.
- **One server name**: `manufacturing-scheduler` in `server.py`, its README (`claude mcp add` with an absolute path and a local/project/user scope table), `core/` agents, commands, skills and hooks, and `profiles/cnc-machining/profile.json`. `production-planner`, `sales-coordinator` and `/order-status` now list the concrete `mcp__manufacturing-scheduler__<tool>` names in `tools` / `allowed-tools` and say which tool answers which question.
- **scheduler-mcp** survives hostile input: a non-UTF-8 byte, deeply nested JSON (`RecursionError`) or a lone surrogate echoed into a reply no longer ends the session; each gives a `-32700`/`-32603` reply (or a normal one) and the server keeps serving. Replies are written ASCII-escaped with `allow_nan=False`.
- **No write-back wording**: skills, hooks and the cnc-machining `tool-life-engineer` no longer tell the AI to write to or close orders in `manufacturing-scheduler` (it is read-only); the human / ERP-MES operator does the write. `morning-briefing` now lists the scheduler read tools; `SECURITY.md` no longer calls the server a stub.
- **scheduler-mcp**: `get_machine_load` now honours `days_ahead`, inputs are validated against each tool's schema, errors no longer leak raw exception text, and missing mock data fails at start-up instead of returning empty results. `erp-connector/README.md` no longer lists `get_sales_order` / `list_open_pos`, which are not in `contract.py`.
- **Least-privilege tool lists (B08):** removed the `Bash` tool from the 6 core agents (`engineering-change-manager`, `inventory-manager`, `production-planner`, `quality-inspector`, `quote-specialist`, `sales-coordinator`) and from the `/quote`, `/bom-check`, `/inspect`, `/8d` commands; they only need `Read` / `Grep` / `Glob`. `Bash` stays on `/install-profile` and `/add-profile` (they run `install.sh`). Profile agents and the remaining commands are unchanged.
- **`post-order` hook (B21):** customer PO acknowledgement is now generated as a draft for a human to review and send, instead of being sent automatically by email / Telegram.
- **README demo captions (B07):** the hero demo is now labelled honestly as a response to a persona prompt pasted into claude.ai (web), not a recording of the installed plugin running in Claude Code.
- **`examples/sample-drawing/bracket.md` (B36):** expected demo output now states that the pre-quote hook passes on completeness while the SUS304 + anodize contradiction is caught by `quote-specialist`, matching the quickstart.
- **`docs/permissions-template.md`** (zh-TW): recommended Claude Code `permissions` `allow` / `ask` / `deny` snippet for a factory workstation (read-only tools allowed, network egress and destructive commands denied), with its limits stated; linked from `docs/adoption-guide.md` (B08).
- **README.zh-TW.md FAQ:** "Can I use it from LINE?" — current copy-paste workflow, no LINE gateway today (B22, docs part only).
- **`examples/company-facts.template.md`** — zh-TW fill-in template (machines and hourly rates, materials, compliance frameworks, quoting margin bands and risk add-ons, lead-time norms, approvals, data-classification rules). All numbers are labelled placeholders; copy to `company-facts.md` outside the repo.
- **`docs/data-classification.md`** — four-tier (T0 public / T1 internal / T2 confidential / T3 restricted) data classification with a cloud / on-prem / no-AI rule table and a note on consumer vs commercial API terms.
- **`docs/adoption-guide.md`** — new section on using company-facts and where real factory data should live; fixed the wrong `infra/mock-data/machine_loads.json` path (mock data lives in `infra/mcp-servers/scheduler-mcp/mock-data/` and holds loads, not rates).
- **`.gitignore`** — real-factory-data block (`company-facts.md`, `customer-data/`, `drawings/`, `rfq/`, `logs/`, `*.dwg`, `*.step`, `*.stp`, `*.iges`) with `!examples/**` so synthetic examples stay tracked.
- **Mock-data labelling** in `/order-status`, `/morning-briefing` and `/manufacturing`: without an MCP connection output must be labelled 「模擬資料」; removed the `git log` status-inference fallback from `/morning-briefing`.
- **Docs: state the real data flow.** Removed "drawings never leave the company / runs on your own machine" claims from the READMEs, `manufacturing.md`, the landing page and explainers 01/02. The plugin's prompts and files stay local, but the default model is Anthropic's cloud (Claude Code), so pasted or attached content is sent to the model provider under its terms; on-prem (GB10 / Ollama) is an option that this project has not verified end-to-end. Added a data-flow section to both READMEs.
- **Docs: `infra/on-prem/gb10-setup.md`** now carries an "unverified" warning, no longer ships a JSON snippet with comments, and tells IT how to verify isolation themselves (egress deny + traffic observation). The beginner quickstart no longer advises `sudo`, covers Git Bash on Windows, and adds the missing "open Claude Code in the repo folder" step.
- **CI hardening** — `.github/workflows/ci.yml` now sets `permissions: contents: read`, pins `actions/checkout` to a full commit SHA (v4.4.0), pins `pyyaml` to `>=6,<7`, and only cancels in-progress runs for pull requests (never for `main`).
- **Claude Code now actually loads the plugin.** Until now it loaded nothing from the install (checked with claude 2.1.289: `claude plugin list` showed no plugin). `~/.claude/plugins/` is never scanned for hand-copied plugins, the root `plugin.json` is not a manifest (and `repository` as an object fails validation), flat `skills/*.md` are not skills, and markdown `hooks/*.md` are not hooks. `install.sh` now, inside the staging dir and before the atomic swap:
  - moves each `skills/<x>.md` to `skills/<name>/SKILL.md` (`<name>` = frontmatter `name:`, else the file name). Two skills mapping to one name fail before the swap and leave the existing install untouched. The overlay and conflict scan still go by file name.
  - writes `.claude-plugin/plugin.json` from `plugin.json` with only the fields Claude Code accepts (`repository` → its URL string). Without python3 it writes a minimal one: name, version and description. The root `plugin.json` is still copied for `/manufacturing` and CI.
  - rewrites repo paths in the installed command / agent / skill / hook / know-how bodies (`core/skills/01-報價.md` → `skills/01-quote/SKILL.md`, `core/agents/x.md` → `agents/x.md`, `profiles/<active>/<kind>/x.md` → the installed path, plus `](../skills/x.md)` links). Only exact strings are changed and only in the staged copies. It uses python3 when present and an equivalent `sed -E` otherwise.
  - links `~/.claude/skills/manufacturing-skill → ../plugins/manufacturing-skill` after the swap. Claude Code loads it as `manufacturing-skill@skills-dir`. If a real directory already exists there, the installer leaves it alone and warns. The output tells you to restart Claude Code or run `/reload-plugins`, and prints the `claude --plugin-dir` and local-marketplace alternatives. To uninstall, remove the plugin dir and the link.
  - `hooks/*.md` remain process documents for agents to read. They are not Claude Code hooks (`Hooks (0)`), and the docs now say so.
  - New CI step `install.sh — Claude Code layout (manifest, SKILL.md dirs, symlink)` checks all of this for core-only, single-profile, multi-profile, re-install and no-python installs. It also checks a duplicate skill name and a real directory at the link path, and runs `claude plugin validate` when the CLI is on PATH. `adapters/claude-code/plugin-mapping.md` has been rewritten to match.
- **CI profile-extends lint (step 10a) no longer passes vacuously** — it now also lints the `tests/extends/case-*/profile.md` fixtures (error cases must be rejected, others accepted) alongside real `profiles/` files, and fails if zero files were linted.
- **CI core heading-anchor guard (step 10b) now actually runs on PRs** — checkout uses `fetch-depth: 0`, a failing diff is an error instead of a silent skip, the step reports whether core files were touched, and its logic moved into an argv/env-driven Python block (no filename or heading interpolated into `python3 -c`, no hidden errors, dead check removed).
- **CI core heading-anchor guard (step 10b) handles non-ASCII core paths** — the changed-file list is now read with `git diff -z` (NUL-separated, unquoted) instead of line-split `--name-only` output; previously a path such as `core/skills/01-報價.md` arrived in git's quoted/escaped form, `git show` could not resolve it, and its removed headings were never checked.
- **`install.sh --list` and the interactive picker no longer abort** under `set -euo pipefail` when a `profile.json` has no `"status"` key (e.g. `cnc-machining`); a missing status still means `complete`. CI now smoke-tests `--list`, `--core-only` and single-profile installs.
- **`install.sh` no longer leaves a half-built install behind.** Every check (profile names, profile dirs, python3 / PyYAML when needed, conflict scan) now runs before the existing install is touched. Previously `install.sh ..`, a missing python3, missing PyYAML or a bad `extends:` target failed *after* the old install had been moved to `.bak`, leaving `plugins/manufacturing-skill/` without `.installed`.
- **Profile names are validated** (`[A-Za-z0-9_-]`, no leading `-`): `..`, `../x`, `a/b`, names with spaces and `*` are rejected up front; `*` is no longer glob-expanded against the current directory.
- **Backups can no longer collide or nest**: two installs in the same second used to nest the second backup inside the first, and a third failed with `Directory not empty`.
- **Missing `~/.claude` with no TTY** (CI, piped input) now prints why and exits 2 instead of exiting silently after the `Create it? [y/N]` prompt.
- **Interactive picker**: entering `08` or `09` no longer aborts with "value too great for base".
- **`install.sh -h`** prints the whole usage block (the last two examples were cut off).
- **CRLF profile files with `extends:` are now resolved.** `has_extends` matched `^---$`, so a CRLF file (`---\r`) was never seen as having frontmatter and was copied raw, with `extends:` unresolved. It now strips `\r` first. New root `.gitattributes` (`* text=auto eol=lf`, `*.sh` / `*.py` `eol=lf`) keeps Windows checkouts from converting the installer and tools to CRLF.
- **`.installed` is always valid JSON.** `source`, `pluginVersion` and the profile names are now JSON-escaped (via python3 `json` when available; pure-bash fallback escapes `\` and `"`). Previously a repo path containing `"` or `\` produced invalid JSON that `/manufacturing` could not read. CI now installs from a repo path and a `HOME` containing a space and `"`, and validates `.installed` with `python3 -m json.tool` (python and no-python paths).
- **Atomic install swap**: the new tree is built in a staging dir next to the target (same filesystem), then swapped in with `mv`. The old install moves to `manufacturing-skill.bak.<timestamp>.<pid>`; if the swap fails, it is moved back automatically and the installer exits non-zero. Only the newest 3 backups are kept (older `manufacturing-skill.bak.*` dirs are deleted; the output says so and prints an undo command).
- **python3 is only required when it is actually used**: multi-profile installs (conflict scan + `active-profiles.json`) and profiles with `extends:` files (which also need PyYAML). A single plain profile installs without python3; `active-profiles.json` is then skipped and readers fall back to `active-profile.json`.
- **Stub-profile warning**: installing a profile with `"status": "stub"` prints a warning block (profile files installed: 0, core layer only; for `food-processing` "HACCP / food-safety content is NOT included", for `pharma` "GxP content is NOT included") and the profile's `warnings` array. Alpha profiles with `warnings` (e.g. `injection-molding`) print them too. When only stubs are installed, the "Try in Claude Code" hints no longer suggest the CNC drawing example.
- **`--list` / picker** show `alpha` profiles with 🧪 instead of ❓.
- **CI `install.sh — smoke` step** now also checks: re-install leaves exactly one backup; invalid names (`../x`, `..`, `a b`, `*`) fail and leave a pre-existing install byte-identical; a simulated swap failure (`MFG_INSTALL_TEST_FAIL_SWAP=1`, test hook) restores the previous install; the stub warning appears for `food-processing`; missing `~/.claude` without a TTY exits 2.

## [0.1.5] — 2026-05-09

**Multi-profile active** ships as **experimental**. `install.sh` now accepts a comma-separated list of profiles (`cnc-machining,injection-molding`) and overlays them all alongside core. A factory that genuinely spans verticals — CNC + injection, EMS + plastic enclosure, mixed job shop — no longer has to pick exactly one.

### Added

- **`adapters/claude-code/_multiprofile.py`** — multi-profile helper. Three subcommands: `scan <p1> <p2> ...` (collision detection across active profiles), `scan-all` (enumerate every pair from `plugin.json`'s `profiles.available`), `aggregate <p1> <p2> ...` (emit the new `active-profiles.json`).
- **Comma-separated profile arg** in `install.sh`: `bash install.sh cnc-machining,injection-molding`. Whitespace tolerated, empty entries skipped, duplicates warn-and-deduped instead of silently dropped (M2 in spec §4.1).
- **Comma-separated interactive picker**: tip "enter `1,2` for multi-profile" rendered in the prompt; `1,2` parses to `[cnc-machining, injection-molding]`.
- **`install.sh --list-conflicts [<list>]`** — dry-run conflict scan. With args: scan a specific profile combination. With no args: enumerate all pairs from `plugin.json` (same as CI Step 12). Exit 0 clean, exit 1 on any conflict.
- **`active-profiles.json`** (new file in install dir) — schema-versioned aggregated view: `primary` (first profile), `profiles[]` (full manifest copies in arg order), `aggregated` (list-typed metadata unioned: `tags`, `applicableTo`, `complianceFrameworks`, `mcp.recommended`/`optional`, `wantedContributions`, `warnings`).
- **`/add-profile <name>`** — new slash command for additive semantics ("add this profile to whatever is already active"). Mirrors `/install-profile` which is replace semantics.
- **CI Step 12** — pairwise profile conflict scan over every unordered pair in `plugin.json`'s available list. Catches the case where two contributors independently land profile changes that silently collide pairwise.
- **CI Step 13** — `tests/multiprofile/test_multiprofile.py` (8 in-process tests covering `scan_set` / `scan_pair` / `aggregate_profiles` against synthetic mini-repos plus a guard that the real repo's profile pairs scan clean).

### Changed

- **`install.sh` validation order** (M5 atomicity per spec): validate-each-profile-exists + cross-profile-conflict-scan now run **before** the existing-install backup step. A bad arg list no longer destroys a working install.
- **`.installed` format** (additive): adds `activeProfiles` array. Singular `activeProfile` retained indefinitely, set to first profile in the active list, for backwards compatibility with v0.1.x readers (`/manufacturing` slash command etc.).
- **`/install-profile` and `/manufacturing` slash command docs** updated to document multi-profile syntax and active-profiles.json reading order (plural first, fall back to singular).
- **`adapters/claude-code/plugin-mapping.md`**: new section on multi-profile install + `--list-conflicts` dry-run.
- **`docs/profile-development.md`**: new section "多 profile 同時 active" with the refuse-on-conflict rule, dry-run instructions, naming guidance for new profile contributors, and `active-profiles.json` schema.
- **`docs/ROADMAP.md`**: marks the v0.2 line items "多 profile 同時 active" and (partially) "自動產生 explainer HTML" as shipped early in v0.1.4 / v0.1.5.
- **`plugin.json` version**: 0.1.4 → 0.1.5.

### Notes — experimental status

`extends:` (v0.1.4) and multi-profile-active (v0.1.5) are both **experimental**. No current profile in this repo uses either feature in a way that exercises the conflict-resolution edge cases. Both features are opt-in and have well-bounded refuse-loudly semantics — using them is safe, and not using them keeps the v0.1.x install path unchanged.

The first real consumer of multi-profile-active (a factory that genuinely needs CNC + injection, or PCB + plastic enclosure, etc.) will validate the design against a live use case before we lock the contract for v0.2.

### Notes — Python dependency

Multi-profile install (≥ 2 profiles) requires Python 3 on the install machine. Single-profile installs without `extends:` files continue to install with no Python dependency. `install.sh` detects the missing dependency at the point where it actually needs Python and prints a clear install message before bailing.

### Spec & approval

[Full design spec](docs/superpowers/specs/2026-05-09-multi-profile-active-design.md) — drafted v1, adversarial-reviewed to v2 patching 2 HIGH + 5 MEDIUM + 3 LOW gaps, approved by Jason 2026-05-09 with all 5 Q-block recommendations accepted (HTML-comment-style reject; profile-set agnosticism; v1 order-insignificant; defer declared-incompatibility; ship as v0.1.5 experimental).

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

[Unreleased]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jason-simhope-ai/manufacturing-skill/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jason-simhope-ai/manufacturing-skill/releases/tag/v0.1.0
