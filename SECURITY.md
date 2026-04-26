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
