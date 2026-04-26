# Contributing to manufacturing-skill

Thanks for considering a contribution. This project exists to make manufacturing AI adoption less painful, and every contribution — code, profile content, real-world feedback — moves that forward.

## Quick map of where things live

```
manufacturing-skill/
├── manufacturing.md              # The "soul" doc — read this first
├── INVENTORY.md                  # One-page entry-point map
├── core/                         # Universal manufacturing primitives
├── profiles/                     # Vertical overlays (CNC, PCB, ...)
├── adapters/claude-code/         # Claude Code installer
├── infra/                        # MCP servers + on-prem guides
├── docs/                         # Architecture, adoption guide, explainers
└── examples/                     # Synthetic demo data only
```

When in doubt, [INVENTORY.md](INVENTORY.md) is the index.

## Ways to contribute

| Contribution                                                     | Where                                                                    | Difficulty                                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Fix a typo / improve wording                                     | Anywhere                                                                 | Trivial — direct PR                                                     |
| Add a profile starter (PCB / injection / food / pharma)          | `profiles/<vertical>/_templates/` → use as template                      | Low                                                                     |
| Promote a stub profile to alpha (1 agent + 1 skill + 1 know-how) | `profiles/<vertical>/{agents,skills,know-how}/`                          | Medium — see [docs/profile-development.md](docs/profile-development.md) |
| Complete a vertical profile to production grade                  | Same                                                                     | High — should come from a domain practitioner                           |
| Add an ERP connector implementation                              | `infra/mcp-servers/erp-connector-<vendor>/`                              | High — see `infra/mcp-servers/erp-connector/contract.py`                |
| Translate explainer cards                                        | `docs/explainers/`                                                       | Low                                                                     |
| Real-world adoption case study                                   | `docs/case-studies/<company-or-anonymous>.md` (create the dir if needed) | Low — high impact                                                       |

## Workflow

1. **Fork** the repo on GitHub.
2. **Create a branch** from `main`. Naming: `feat-<short-topic>` for features, `fix-<short-topic>` for fixes, `docs-<short-topic>` for documentation.
3. **Make your changes**. Keep commits focused — one logical change per commit.
4. **Verify locally** by running the install script against your changes if you touched the plugin structure: `bash adapters/claude-code/install.sh <profile>`.
5. **Open a PR** against `main`. Use the PR template; the checklist is short.
6. **Respond to review.** The maintainer (currently Jason) reviews most PRs within a week. If a PR sits longer, ping in the PR thread.

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature, agent, skill, or know-how
- `fix:` bug fix
- `docs:` documentation only
- `chore:` tooling / repo housekeeping
- `refactor:` code change that's neither a feature nor a fix
- `test:` adding or updating tests
- `ci:` CI / GitHub Actions changes

Optional scope: `feat(profile): add injection-molding alpha`.

Subject line: imperative mood, under 72 characters, no trailing period.
Body (when needed): explain _why_, not _what_. Wrap at ~72 chars.

## Style guide

### For Markdown content (agents / skills / know-how)

- **Frontmatter is required.** Match the format already in `core/agents/quote-specialist.md` (or the relevant template).
- **Language:** agent prompts and know-how default to **繁體中文** (Traditional Chinese — the primary user audience is Taiwan manufacturing). English contributions are welcome but please add a brief 繁中 summary.
- **Length:** lean. A great agent prompt is 80–200 lines. If a know-how doc passes 300 lines, it should probably be split.
- **Honesty:** if a section relies on values that vary in practice (cutting parameters, polymer shrinkage, machine costs), say so explicitly. Better "see your supplier datasheet" than a fake-precise number that someone treats as authoritative.

### For code (install.sh, MCP servers, etc.)

- **install.sh** must stay POSIX-bash-3.2 compatible (macOS default bash).
- **Python MCP servers** target Python 3.10+ (the manufacturing GitHub runner standard). Type-hint public functions.
- **JSON files** must be valid (CI checks this). Indent 2 spaces.

### For HTML explainers / landing page

- **Self-contained.** No external CDN, no bundlers, no build step. CSS inline in `<style>`.
- **Print-friendly.** Test that the page prints to A3 landscape without overflow.
- **Mobile-friendly.** Use responsive grids (the existing files are good references).

## What needs review vs what doesn't

**Doesn't need review** (you can merge yourself if you ever get write access):

- Typos
- Translation improvements
- Adding a `_templates/` file inside a stub profile

**Needs maintainer review** (always):

- Promoting a profile's `status` field (stub → alpha → beta → complete)
- Anything touching `install.sh` or CI
- Schema changes to `plugin.json` or `profile.json`
- New top-level files

## Code of conduct

Be respectful. Assume good intent. Manufacturing is a domain where people have spent decades learning specific things — when someone with 20 years on the shop floor disagrees with the AI's output, listen carefully and correct the prompt rather than the practitioner.

Discriminatory, harassing, or personal-attack behavior gets you removed from the project. There's no formal CoC document yet because the contributor base is small; this paragraph is the policy.

## Questions

- General questions / discussion: open a [GitHub Issue](https://github.com/jason-simhope-ai/manufacturing-skill/issues) with the "question" label.
- Security issues: do **not** open a public issue — see [SECURITY.md](SECURITY.md).
- Commercial collaboration / paid profile development: email <jasonlin@simhope.com.tw>.

Thanks for being here.
