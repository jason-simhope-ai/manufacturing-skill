# Changelog

All notable changes to manufacturing-skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

**Digital-twin team (v0.2.0-alpha, experimental).** A seventh layer (TEAM) and a third tier (`team/`) that give each position a copilot "twin" in chat — a copilot, not a replacement. Alpha stops at `observe / suggest / draft`: there are no write tools, no long-term memory, and T3 (high-assurance custom projects) is always refused. Design: [spec](docs/superpowers/specs/2026-10-05-digital-twin-team-design.md).

### Added

- **`TEAM.md`** — agent bootstrap (≤ 6,000 B): one-line definition, six inviolable rules, startup algorithm, progressive-disclosure map. Humans start at `team/README.zh-TW.md` (10 minutes).
- **`team/`** — the third tier. `roster.example.yaml` (synthetic, generic departments and job titles), `twins/` (`_template.md` plus three example twins: production, QA and engineering department heads), `policies/` (`core-rules.md` shared preamble, `restricted.md` T3 policy), `gate/need-a-twin.md` (the "do we need a twin?" gate), `local/README.md` (gitignored local overlays).
- **Three categories** on every capability — `strengthen` / `create` / `outsource` — with mandatory `today` and `humanStillDoes`. `outsource` must be dormant in a twin file and can only be woken by a roster opt-in: at most one per twin, capped at `draft`, review within 90 days, mandatory teach-back and manual practice. Missing labels are hard errors.
- **`team/tools/`** — `teamctl.py` (`check`, `roster`, `audit-verify`), `build.py` (deterministic `team/.build/`), `deid.py` (source-side de-identification), `_teamlib.py` (hand-written validator with error codes `E0xx` / `W0xx`), `lint-allow.txt`, `pre-commit-names.sample`.
- **`infra/chat-gateway/`** — stdlib-only Python 3.11 chat gateway: routing (@mention every turn), identity and tier filters, rate limits, sanitizer (`<<UNTRUSTED>>` envelopes, tripwires, DLP), output filter, approval book (structured clicks only, args-hash bound, 30-minute TTL, single use; no executable actions in alpha), hash-chained audit log, mock adapter and mock driver. Slack and Discord adapters and the Claude Code driver (fixed restricted flag set) ship but are **not exercised in CI against real platforms and need credentials**.
- **`python3 infra/chat-gateway/demo.py`** — a two-minute offline demo (no credentials, no network) with a golden transcript check.
- **`/team` command** (`core/commands/team.md`) — `status`, `ask <twin> <message>`, `check`, `gate <position>`, `demo`. `ask` is a preview that bypasses the gateway (no tier routing, no audit); twins with a tier ceiling above T1 are refused.
- **Tests** — `tests/team/` (fixture runner and unit tests for the validator, build and deid) and `tests/gateway/` (gateway unit, security and driver tests, plus the demo golden transcript).
- **CI steps 18–22** (appended to `validate`, same job) — Step 18 "Team — check (schema, refs, categories, budgets, names, secrets)" (`teamctl check --ci`) plus 18b "Team — build determinism" (two builds, byte-identical); Step 19 "Team — lint fixtures" (`tests/team/run.py` and `tests/team/test_team.py`); Step 20 "Chat gateway — unit and security tests (offline)" (`tests/gateway/`); Step 21 "Chat gateway — demo golden transcript" (`demo.py --check`); Step 22 "install.sh — team tier smoke" (`team/` and `TEAM.md` installed; `team/.build` and `team/local` not). Each step asserts a non-zero test count and fails with `::error`. The workflow keeps the top-level `permissions: contents: read` and the SHA-pinned `actions/checkout` (v4.4.0) from the CI hardening entry below.
- **Docs** — new README sections (EN / zh-TW), Layer 7 in `docs/architecture.md`, a v0.2.0-alpha entry and v0.2.x candidates in `docs/ROADMAP.md`, "導入分身團隊的順序" in `docs/adoption-guide.md`, a Team tier section in `INVENTORY.md`.
- **`docs/owner-one-page.zh-TW.md` (董事長一頁)** — one printable page for the owner who signs: the three things signed (the 「AI 賦能原則」, a 4-week pilot approval, a budget approval), what it costs (cost lines with every figure the repo does not have marked 【缺：由導入負責人填】, and which monthly figures do *not* apply to the twin pilot), what staff gain and keep in the three categories 強化既有優勢／創造新能力／外包既有工作, the five worst cases and who owns each, the one-sentence stop (any manager → the key keeper stops the gateway and revokes the bot and API key within 30 minutes; the owner holds no key), the 第 4 週決策表 with thresholds left blank for the owner, and a three-line statement for a customer auditor with what it cannot guarantee. Linked from `README.zh-TW.md` (decision-maker entry), `team/README.zh-TW.md`, `docs/adoption-guide.md`, `INVENTORY.md` and the top of `infra/chat-gateway/README.md`.

### Changed

- **`install.sh` copies `team/` by default** (without `team/.build/` and `team/local/`; `.installed` gains `"team": true`). Claude Code does not auto-load it, so v0.1.5 behavior is unchanged and the core-only agent count stays 6.
- **`docs/architecture.md`** — corrects the core agent count from 5 to 6 (`engineering-change-manager` was missing); now describes seven layers and three tiers.
- **`SECURITY.md`** — scope table and "Operating securely" extended for `team/` and `infra/chat-gateway/`.
- **DLP precision and state-dir UX.** `受限` / `軍規` / `軍工` / `管制` skip negated and unrelated-word forms (`不受限制`, `將軍規模`, `監管制度`); a checksum-valid 8-digit number is a UBN only with a cue within 12 characters (統編, VAT, 公司, 發票 ...), and dates need a strong cue. A gateway refusal over a stale audit log now prints the directory, the safe fix and the env var; new `teamctl state-reset --confirm` moves the state dir aside (never deletes). The explainer stat panel counts team-tier twins; `_teamlib.py` gets a module map.
- **CI hardening** — `.github/workflows/ci.yml` now sets `permissions: contents: read`, pins `actions/checkout` to a full commit SHA (v4.4.0), pins `pyyaml` to `>=6,<7`, and only cancels in-progress runs for pull requests (never for `main`).
- **Atomic install swap**: the new tree is built in a staging dir next to the target (same filesystem), then swapped in with `mv`. The old install moves to `manufacturing-skill.bak.<timestamp>.<pid>`; if the swap fails, it is moved back automatically and the installer exits non-zero. Only the newest 3 backups are kept (older `manufacturing-skill.bak.*` dirs are deleted; the output says so and prints an undo command).
- **python3 is only required when it is actually used**: multi-profile installs (conflict scan + `active-profiles.json`) and profiles with `extends:` files (which also need PyYAML). A single plain profile installs without python3; `active-profiles.json` is then skipped and readers fall back to `active-profile.json`.
- **Stub-profile warning**: installing a profile with `"status": "stub"` prints a warning block (profile files installed: 0, core layer only; for `food-processing` "HACCP / food-safety content is NOT included", for `pharma` "GxP content is NOT included") and the profile's `warnings` array. Alpha profiles with `warnings` (e.g. `injection-molding`) print them too. When only stubs are installed, the "Try in Claude Code" hints no longer suggest the CNC drawing example.
- **`--list` / picker** show `alpha` profiles with 🧪 instead of ❓.
- **CI `install.sh — smoke` step** now also checks: re-install leaves exactly one backup; invalid names (`../x`, `..`, `a b`, `*`) fail and leave a pre-existing install byte-identical; a simulated swap failure (`MFG_INSTALL_TEST_FAIL_SWAP=1`, test hook) restores the previous install; the stub warning appears for `food-processing`; missing `~/.claude` without a TTY exits 2.
- **Round-3 team-tier fixes.** Gateway DLP now also blocks emails and Taiwan phone numbers at T2 and masks them in replies (`redactions.pii` counts them); `[附件]` file-name lines are wrapped as `<<UNTRUSTED>>` and taint the turn; `--script` replays are validated up front (one-line error with the line number, exit 65), use the script's `ts` as the clock (no wall-clock rate limiting) and the demo banner says replies are canned. `deid.py` reports whether a denylist loaded (and how many entries), what it did not scan, ragged CSV rows, and scans part numbers only with `--partno-pattern`. SECURITY.md, the adoption guide (Day 1 pass condition, audit-key trust model, gate G7 answered by the human in the roster snippet) and `.gitignore` (`*.deid.csv`) now match the code.
- **Front-line round (team tier).** Capabilities now say who does the task today (`affectedRoles`) and, when that is someone other than the twin's own position, carry that person's sign-off (`doerAckedOn`); new lint codes `E061`–`E064` and `W009`, and `E038` uses a documented word list (`REVIEW_ONLY_WORDS`, now also for `create`, judged per role line) so "看過沒問題就送出" / "若有意見再補充" fail. The QA and production twins split each line by doer vs manager; the engineer's NCR history lookup is now its own dormant outsource (`ncr-lookup`). A `VACANT` position needs `vacancyApprovedBy`/`vacancyApprovedOn` to enable a twin. Replies read "建議（草稿）" / "分身的看法：" with a fixed "這是參考，不是指示" line; 「我不同意」/「分身錯了」, 「我親手做了」 and twin-free days (`channels[].twinFreeDays`) are answered without the model and audited as anonymous counts (`human_override`, `practice_checkin`, `twin_free_day`; `audit-verify` prints them per channel/capability, never per user); `channels[].learners` get learner mode (≤ suggest, similar cases and counter-examples only, kept out of the channel window) with optional `predictFirstDefault`. Docs: "who owns a mistake" in `core-rules.md`, the README FAQ and adoption principle 8; the README FAQ now defers "will it replace me" to the signed principles (signing date must be posted); a "給主管" box; a paper 8-question gate; the one-page `team/for-frontline.zh-TW.md`; `demo.py --plain` (beats 1–3, zh-TW, no token or audit lines).
- **`team/tools/_teamlib.py` split into `team/tools/teamlib/`** (`schema`, `io`, `compile`, `validate`); `_teamlib.py` stays as a compatibility shim with the same public names. No behaviour change (identical build `sourceHash`).
- **Owner scenario round (R8).** One pilot schedule everywhere: **4 weeks = 1 week mock rehearsal (Wave 0) + 3 weeks test workspace (Wave 1)**, decided on week 4 Friday with the 第 4 週決策表 (boundary crossings, expected 0; both managers still reviewing weekly; count of human-changed 🧭 conclusions; a 3-question anonymous staff questionnaire), go / extend / stop thresholds blank for the owner; G1 hours and baselines are reference only and time saved is not a success metric (principle 7 no longer contradicts the gate). Spec §13 and the adoption guide's waves and day-by-day table follow it (spec revision v2.4). The principle template gains a commitment period (at least until v1.0), clause 9 「違反時」 (who receives a report, who may stop the twin, when the owner hears), 「外包既有工作預設休眠」 in clause 1 with an owner checkbox for the pilot, 「pilot 總負責人」 and 「機密事件受理人」 in clause 6, two 5-line sign-off blocks (pilot approval, budget approval) and a six-line glossary; deployment checklist A gains 「負責：」 on the posted signing date and a stop drill. Three-category wording is zh-TW first (English field name in parentheses) in the adoption guide, `team/README.zh-TW.md`, `team/for-frontline.zh-TW.md` and `README.zh-TW.md`. 「五件事」→「六件事」. The paper gate uses the G1–G9 numbering and every question is phrased so 是 = continue. `team/policies/core-rules.md` starts with 「本檔給模型讀」; the example roster's gate reasons use concrete synthetic hours.
- **Data-flow honesty (zh-TW).** `README.zh-TW.md` and explainers 01, 02, 04 no longer say data never leaves / air-gap without qualification: 圖紙、報價、客戶資料（T2）與高安規專案資料（T3）不出公司；分身只處理 T0／T1，T1 會經聊天平台與雲端模型. Explainer 01's sidebar becomes 「部署與資料流向」 with a 分身層 row and explainer 02 gains a 7.TWIN layer; explainer 01's glossary calls core agents 「AI 角色」 and keeps 分身 for position twins. The three monthly cost figures are labelled (README NT$650 = a personal Claude Code subscription; explainer ~NT$3,000 = on-prem GB10 upkeep, original estimate; consulting NT$380,000~530,000 = SI quote for the 6-week agent/MCP path); none is the twin pilot cost. **The explainer PNGs in `docs/explainers/screenshots/` were not regenerated and need a re-capture after merge.**
- **Server name.** Bare `scheduler-mcp` used as a server name in `core/`, `examples/` and `docs/` is now `manufacturing-scheduler` (the directory `infra/mcp-servers/scheduler-mcp` is unchanged); the single-line edits match PR #18 word for word. `docs/ROADMAP.md` marks the ETO profile ✅ with PR #32's wording.

### Fixed

- **CI profile-extends lint (step 10a) no longer passes vacuously** — it now also lints the `tests/extends/case-*/profile.md` fixtures (error cases must be rejected, others accepted) alongside real `profiles/` files, and fails if zero files were linted.
- **CI core heading-anchor guard (step 10b) now actually runs on PRs** — checkout uses `fetch-depth: 0`, a failing diff is an error instead of a silent skip, the step reports whether core files were touched, and its logic moved into an argv/env-driven Python block (no filename or heading interpolated into `python3 -c`, no hidden errors, dead check removed).
- **`install.sh --list` and the interactive picker no longer abort** under `set -euo pipefail` when a `profile.json` has no `"status"` key (e.g. `cnc-machining`); a missing status still means `complete`. CI now smoke-tests `--list`, `--core-only` and single-profile installs.
- **`install.sh` no longer leaves a half-built install behind.** Every check (profile names, profile dirs, python3 / PyYAML when needed, conflict scan) now runs before the existing install is touched. Previously `install.sh ..`, a missing python3, missing PyYAML or a bad `extends:` target failed *after* the old install had been moved to `.bak`, leaving `plugins/manufacturing-skill/` without `.installed`.
- **Profile names are validated** (`[A-Za-z0-9_-]`, no leading `-`): `..`, `../x`, `a/b`, names with spaces and `*` are rejected up front; `*` is no longer glob-expanded against the current directory.
- **Backups can no longer collide or nest**: two installs in the same second used to nest the second backup inside the first, and a third failed with `Directory not empty`.
- **Missing `~/.claude` with no TTY** (CI, piped input) now prints why and exits 2 instead of exiting silently after the `Create it? [y/N]` prompt.
- **Interactive picker**: entering `08` or `09` no longer aborts with "value too great for base".
- **`install.sh -h`** prints the whole usage block (the last two examples were cut off).
- **CRLF profile files with `extends:` are now resolved.** `has_extends` matched `^---$`, so a CRLF file (`---\r`) was never seen as having frontmatter and was copied raw, with `extends:` unresolved. It now strips `\r` first. New root `.gitattributes` (`* text=auto eol=lf`, `*.sh` / `*.py` `eol=lf`) keeps Windows checkouts from converting the installer and tools to CRLF.
- **`.installed` is always valid JSON.** `source`, `pluginVersion` and the profile names are now JSON-escaped (via python3 `json` when available; pure-bash fallback escapes `\` and `"`). Previously a repo path containing `"` or `\` produced invalid JSON that `/manufacturing` could not read. CI now installs from a repo path and a `HOME` containing a space and `"`, and validates `.installed` with `python3 -m json.tool` (python and no-python paths).
- **`/team` and `TEAM.md` resolve `$ROOT` before running anything.** Tool and gateway paths are now `$ROOT/team/tools/…` / `$ROOT/infra/chat-gateway/…` (cwd, then the `.installed` `source` clone, then the installed copy), so `/team` works from a user's project directory; on the installed copy (no `infra/`) every subcommand except `gate` — `/team demo` included — says to run from a repo checkout. A test keeps bare paths out. Docs now say 6 core agents (README × 2, `manufacturing.md`, `docs/index.html`), 11 commands (`plugin-mapping.md`), and `INVENTORY.md` matches this tree (257 tracked files).
- **CI core heading-anchor guard (step 10b) handles non-ASCII core paths** — the changed-file list is now read with `git diff -z` (NUL-separated, unquoted) instead of line-split `--name-only` output; previously a path such as `core/skills/01-報價.md` arrived in git's quoted/escaped form, `git show` could not resolve it, and its removed headings were never checked.

### Security

- **Data tiers T0–T3.** Slack, Discord and cloud models are capped at T1; T2 is allowed only on the local mock adapter; unsure means one tier up.
- **T3 is refused.** Any T3 channel or twin in the roster makes the gateway exit 3; `act` and `act-with-approval` autonomy, dual-approval settings, hash mismatches, suspected tokens and missing environment variables make it exit 78 (fail closed). The DLP keyword tripwire also covers 航太, 軍工, 軍規, 醫材/醫療器材, ITAR, EAR, CUI, 外銷許可 and 管制 (T3; QC compounds such as 管制圖 are excluded) and US$/USD/萬元/千元 amounts (T2). It is a word match, not content understanding, and the docs now say so.
- **No secrets, names or platform ids in the repo.** Credentials come only from `MFG_TEAM_*` environment variables; real rosters, identities and bindings live in gitignored `team/local/`; CI scans tracked files for tokens, names and platform ids. The name denylist is local, so the real name defense is the pre-commit hook.
- **Audit.** Append-only, HMAC-SHA256 chained per tier under `MFG_TEAM_AUDIT_HMAC_KEY`, with a signed `audit/checkpoint.json` (per-tier count, last seq, head). `audit-verify` detects edits, deletions, reordering, truncation, a removed tier file, seq gaps and malformed lines; content is stored as a keyed tag, never text. Copying the checkpoint off-host on a schedule is the operator's job.
- **Hardening (security and code review, round 2).** Alpha caps cloud models and SaaS chat at T1 with no waiver (lint `E047`, gateway refuses at load; the Slack-T2 `riskAcceptance` path was removed). The claude-code driver runs in `team/.build/ref/` (identities, bindings, roster and other prompts out of reach) and re-checks `promptSha` on every call, as does the gateway. Input is NFKC-normalised and stripped of format and zero-width characters before DLP, tripwires and routing. The local denylist feeds inbound DLP and the output filter. Approved actions execute exactly as hashed. `deid.py` fails closed (emails, phones, names with titles, contact columns; `--allow-residual` to override) and writes 0600 files. Taint now decays once the offending message leaves the channel window. `_teamlib` loads every regex from `chat_gateway/patterns.py`.
- **Gateway process/network boundary review (EXT).** A failed chat post is audited as `post_failed` and skipped instead of stopping the gateway; `nan`/`inf`/out-of-range budgets and timeouts refuse start (exit 64); roster ids must match the lint patterns; Slack/Discord approval ids and nonces must match in full and attachment names lose C1 and U+2028/U+2029 line breaks; Discord requires a guild allowlist. The claude-code driver caps stdout at 1 MB, rejects duplicate keys, deep nesting and invalid UTF-8, kills its process group on every path with a hard deadline, uses a fixed temp-file prefix, requires absolute realpath-resolved paths with no symlink under `ref/`, and runs an absolute `claude` with a fixed `PATH`.
- **EXT follow-up.** Approval clicks carry `channel_ref` and count only in the card's own channel (EXT-03); the claude-code child gets a private 0700 `HOME` under the state dir and proxy variables only with `MFG_TEAM_PASS_PROXY_ENV=1`; the data root may not overlap the state, config or repo dirs nor hold symlinks, and the state dir must be 0700-safe (EXT-05/13/14). SaaS inbox capped at 256 events (`overflow` audited), repeated click notices collapsed, Slack cards cut to 3,000 chars, top-level errors print the class name only (EXT-12/15–17).
- **Daily budget is now a persisted ceiling for the claude-code driver.** `MFG_TEAM_DAILY_BUDGET_USD` is required with `--driver claude-code` (unset or not a positive finite number refuses start, exit 64; still optional for the mock driver). The day's spend per twin is kept in `$MFG_TEAM_STATE_DIR/daily-spend.json` (0600 JSON keyed by UTC date, read and written under a file lock, shared with cron `post` processes), so a restart no longer resets it; an invalid, symlinked or group/other-accessible file refuses start (exit 78) instead of starting from zero. A call whose cost the CLI does not report, and a failed call, is charged at the per-call cap; if the file cannot be written the gateway stops calling the model. New module `chat_gateway/spend.py`; 13 new tests.


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
