# Security Policy

## Reporting a vulnerability

**Do not open a public GitHub issue for security problems.**

Email <jasonlin@simhope.com.tw> with:

- A description of the vulnerability
- Steps to reproduce (or a proof-of-concept)
- The version / commit hash you tested against
- Your assessment of impact (who can do what to whom)

You should get a response within 5 working days. If you don't, send a follow-up email — assume the first one was lost in spam, not ignored on purpose.

## What's in scope

| Component                                                                      | In scope                                                                                                                      |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `core/` and `profiles/*/` agent prompts and skills                             | Prompt-injection, role-confusion, data-exfiltration via crafted user input                                                    |
| `adapters/claude-code/install.sh`                                              | Path-traversal, accidental file overwrite, unsafe handling of unusual inputs                                                  |
| `infra/mcp-servers/scheduler-mcp/server.py` (the stub)                         | Memory-safety, input validation — though the stub is not intended for production                                              |
| `infra/mcp-servers/erp-connector/contract.py`                                  | Interface design that would make secure implementation hard                                                                   |
| Example data in `examples/`                                                    | Accidental inclusion of real customer data                                                                                    |
| `team/` manifests, twin files and roster (`team/tools/` included)              | Prompt-injection via twin or roster content; category mislabelling (an `outsource` capability labelled `strengthen`/`create`); real names or ids slipping past the lint |
| `infra/chat-gateway/`                                                          | Authentication bypass (identity or channel spoofing), approval forgery or replay, audit-log tampering, tier bypass (T2/T3 content reaching a SaaS channel or cloud model) |
| The four `docs/explainers/*.html` and `docs/demo/*.html` and `docs/index.html` | Cross-site scripting via injected content (currently no JS executes user-controlled data, but if that changes, file an issue) |

## What's out of scope

- **Bugs in Claude itself** — report those to Anthropic via [the official channel](https://www.anthropic.com/responsible-disclosure-policy).
- **Bugs in `~/.claude/` plugin loading** — that's Claude Code's responsibility; report to Anthropic.
- **Vulnerabilities in user-implemented ERP connectors** — if you ship `erp-connector-acme/`, you own its security.
- **Risk that AI gives wrong manufacturing advice** — that's accuracy, not security. Open a regular issue.
- **GitHub Pages site availability / DNS / CDN** — that's GitHub's infrastructure, not ours.

## Disclosure timeline

We follow a coordinated-disclosure model:

1. **Day 0**: You email the report.
2. **By day 5**: We acknowledge and start investigating.
3. **By day 30**: We aim to have a fix in `main`. For complex issues, we'll communicate a longer timeline.
4. **After fix lands**: We publish a security advisory in the GitHub repo's Security tab, crediting the reporter (unless you prefer to stay anonymous).

For low-impact issues we may discuss publicly on a GitHub issue with your permission.

## What this project does NOT do

To set expectations clearly:

- **No bug bounty.** This is an open-source project with a small maintainer base; we cannot pay for findings. We will credit you publicly if you want.
- **No CVE registration on our end** — we have not registered as a CNA. If a CVE is appropriate, we'll work with you to file one through MITRE.
- **No managed security audit** — the codebase has not been independently audited. The honest assessment: it's small, mostly markdown, the risk surface is limited, but production deployments touching real factory data should add their own audit.

## Operating securely with this plugin

If you're an enterprise IT team adopting `manufacturing-skill`:

- Run the local LLM (Ollama on GB10 or similar) on the **internal network only**. Never expose Ollama's port to the public internet.
- The plugin reads agent prompts and skills as **untrusted** user-controllable text — if you customize a profile, review the prompt for injection vectors before deploying widely.
- Your ERP connector implementation handles real customer data. Use a service account with **read-only access** for queries; restrict write tools (`create_sales_order`, etc.) by role.
- Log every AI-driven action that touches the ERP. The contract in `infra/mcp-servers/erp-connector/contract.py` includes an `operator` audit field on every write tool — keep it.
- Customer drawings, BOMs, and pricing are sensitive. Verify `.gitignore` excludes your real data directories before any team member runs `git add`.

For a deeper deployment-security checklist, see [`infra/on-prem/gb10-setup.md`](infra/on-prem/gb10-setup.md).

## Operating the twin gateway

The digital-twin gateway (`infra/chat-gateway/`, experimental) and the `team/` tier add a chat-facing attack surface. Design rationale: [`docs/superpowers/specs/2026-10-05-digital-twin-team-design.md`](docs/superpowers/specs/2026-10-05-digital-twin-team-design.md) §11. Operating rules:

- **Secrets come from environment variables only** (`MFG_TEAM_*`: platform tokens, HMAC keys, API key). Never put them in the roster, twin files, bindings or any tracked file; run the bot under a dedicated service account, not a personal login. The gateway refuses to start (exit 78) if a config file looks like it contains a token, and prints only variable names when one is missing.
- **T3 (high-assurance custom project data) never goes on SaaS chat or a cloud model.** Slack/Discord and cloud models are capped at T1; the alpha gateway refuses to start (exit 3) if the roster contains any T3 channel or twin, and a keyword tripwire blocks, and advises on, messages containing obvious T3 wording (defence, aerospace, military-spec, medical-device, ITAR/EAR/CUI, export permit). Both are config- and word-level controls, not content understanding: T3 text that avoids those words is not recognised, so people and process must keep T3 out. T2 (drawings, BOMs, quotes, customer names) is mock-only with a local model in alpha: `policy.cloudTierCeiling` and `saasTierCeiling` above T1 are a lint error (E047) and refused by the gateway, with no waiver; T2 off-premises is deferred. When unsure of a tier, go one tier up; a channel's tier only goes up, never down.
- **The audit log is a keyed hash chain.** Each record is chained with HMAC-SHA256 under `MFG_TEAM_AUDIT_HMAC_KEY`, and the gateway rewrites a signed checkpoint file, `audit/checkpoint.json` (per tier: record count, last seq, head MAC), after every append. `teamctl audit-verify` (with the key set) detects edited, deleted, reordered or truncated records, a removed tier file and gaps in the global seq. The checkpoint cannot detect a rollback of *both* the log and the checkpoint, so copying the checkpoint (or the heads that `audit-verify` prints) off-host or to write-once storage on a schedule is the operator's job. Someone other than the adoption lead should run the verification and sign off the heads. The log stores keyed tags, not message text. The adoption lead does not act as approver and does not hold the audit key or the checkpoint copies.
- **Identity is the platform user id in `team/local/identities.local.yaml`, never a display name.** Bot authors (including other twins), external shared channels, other guilds and DMs are ignored. Request only the minimum platform scopes (`users:read` is for `is_bot` and team membership).
- **Chat content is untrusted.** Quotes, code blocks, attachments and tool output carry no instruction authority; the gateway wraps them in randomized `<<UNTRUSTED ...>>` envelopes, applies NFKC and strips invisible, format, bidi and variation-selector characters before DLP and tripwires, and downgrades a turn that trips an injection tripwire (no approval cards, no URLs, autonomy at most `suggest`). An approval is valid only as a structured click bound to the exact action hash; text such as "approved" is never accepted. The DLP tripwire is an alarm, not a defence.
- **Keep real names, ids and customer or project codes out of tracked files.** `teamctl check --ci` (and CI) scans for names, platform ids, emails and secrets, but it cannot see your private denylist: copy `team/tools/pre-commit-names.sample` into your git hooks and fill `team/local/names.denylist` locally. The gateway also loads that denylist (or `MFG_TEAM_DENYLIST`) and treats a hit as T2 on input and output. Local overlays (`team/local/*`, `*.local.yaml`, `team/.build/`, `logs/`, audit and memory directories) are gitignored; keep them that way.
- **Go-live gates.** Alpha = mock mode and all tests green, T0/T1 data only. Pilot = a test Slack/Discord workspace, minimum scopes, weekly audit-hash sign-off. Anything beyond that (T2 on SaaS, T3) is out of scope for this repository.
- **Residual risks your policies must cover:** shadow AI (staff pasting data into personal AI accounts), a compromised workstation, chat and cloud vendor data retention, semantically plausible but wrong output (a mis-quoted price or spec), over-privileged platform admins, and misconfiguration.
