# CLAUDE.md

Guide for coding agents (Claude Code and others) working in this repo. Keep it short; follow the links for detail.

## What this is

Claude Code plugin: AI starter kit for manufacturers. A universal `core/` plus vertical `profiles/` overlays, installed by `adapters/claude-code/install.sh`.
Audience is Taiwan manufacturing (zh-TW first). Current version lives in [plugin.json](plugin.json); history in [CHANGELOG.md](CHANGELOG.md).

## Repo map

Top-level layout; not exhaustive. [INVENTORY.md](INVENTORY.md) is the current map of every directory and file, so check it (or `ls`) before assuming a path exists or does not.

- `core/` universal agents, skills, commands, know-how, hooks (apply to any factory)
- `profiles/<vertical>/` overlay: `profile.json` + `agents/ skills/ know-how/ hooks/`; `_templates/` is exempt from CI
- `adapters/` one directory per target; `adapters/claude-code/` holds `install.sh`, `_resolve_extends.py`, `_multiprofile.py`, [plugin-mapping.md](adapters/claude-code/plugin-mapping.md)
- `infra/` MCP server templates (`mcp-servers/`), on-prem LLM guides (`on-prem/`) and other deployable services; see INVENTORY.md
- `docs/` [architecture](docs/architecture.md), [profile-development](docs/profile-development.md), [adoption-guide](docs/adoption-guide.md), [ROADMAP](docs/ROADMAP.md), `explainers/` (HTML cards)
- `tests/` one subdirectory per area (resolver golden files, helper unit tests, ...); which ones CI runs is listed in `ci.yml`
- `scripts/` maintenance scripts such as `regen_explainers.py`
- `examples/` synthetic demo data only
- Entry points: [manufacturing.md](manufacturing.md), [INVENTORY.md](INVENTORY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md)

## Language conventions

- zh-TW (Traditional Chinese): agent prompts, skills, know-how, explainers.
- English: code, comments, frontmatter keys, `profile.json`, commit messages, this file.
- Commits: Conventional Commits (`feat|fix|docs|chore|refactor|test|ci`, optional scope). Imperative subject, under 72 chars, no trailing period. Body explains why.
- English know-how is allowed but add a short zh-TW summary.

## What CI enforces (replay locally before pushing)

Workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml); it is the source of truth for the step list, which grows over time, so read it rather than trusting a list here. Needs `python3` and PyYAML (`pip install pyyaml`).

Replay every `run:` block (skips steps with an `if:` condition, such as PR-only checks, and the pip step; steps that need the network cannot be replayed offline, so note them in the PR instead):

```bash
python3 - <<'PY'
import yaml, subprocess, sys
steps = yaml.safe_load(open(".github/workflows/ci.yml"))["jobs"]["validate"]["steps"]
bad = []
for s in steps:
    r = s.get("run")
    if not r or "if" in s or r.startswith("pip install"):
        continue
    print("==", s["name"], flush=True)
    if subprocess.run(["bash", "-c", r]).returncode:
        bad.append(s["name"])
print("FAILED:", bad or "none")
sys.exit(bool(bad))
PY
```

Or run single checks (examples of what the steps cover; `ci.yml` has the full set):

- JSON: every `*.json` parses (`python3 -m json.tool <file>`); 2-space indent.
- `plugin.json` has `name displayName version license profiles` and `profiles.available`.
- Frontmatter (YAML, real parse): `core/agents` and `profiles/*/agents` need `name description model`; `core/commands` need `name description allowed-tools`; skills need `name description`. Files starting with `_` are skipped.
- `bash -n adapters/claude-code/install.sh`
- No bash 4+ in install.sh: `grep -nE '\$\{[a-zA-Z_]+,,\}|\$\{[a-zA-Z_]+\^\^\}|declare -A|mapfile' adapters/claude-code/install.sh` must print nothing.
- Markdown internal links: every relative link in every `*.md` must resolve inside the repo (code blocks and inline code are ignored; URLs and `#anchors` skipped). Replayed by the loop above.
- `python3 tests/extends/run.py` (add `--case <name>` for one fixture)
- `python3 tests/multiprofile/test_multiprofile.py`
- `python3 scripts/regen_explainers.py --check` (drift of AUTO sections; fix with `python3 scripts/regen_explainers.py` and commit)
- `bash adapters/claude-code/install.sh --list-conflicts` (all profile pairs from `plugin.json`; same as `python3 adapters/claude-code/_multiprofile.py scan-all`)
- `extends:` lint for every profile file that declares it; on PRs, removing a `## ` heading in `core/*/*.md` fails if a profile still has `<!-- replace-section: <heading> -->` for it unless the same PR updates that profile.

## Add or change a profile

Detail: [docs/profile-development.md](docs/profile-development.md). Start from `cp -r profiles/cnc-machining profiles/<name>` or a stub's `_templates/`.

- Name: lowercase, `-` separated, descriptive (`injection-molding`, not `injection`).
- `profile.json` required: `name displayName version description extends-core applicableTo tags agents skills knowHow hooks`. `extends-core` is a boolean; the other lists are arrays. Add `status` (`stub|alpha|beta|complete`) while WIP.
- Register the name in `plugin.json` `profiles.available` and in the matching status list (`complete|alpha|stub`).
- Manifest vs filesystem, both directions: each entry in `agents|skills|knowHow|hooks` needs `profiles/<name>/{agents,skills,know-how,hooks}/<item>.md`; each non-`_` `.md` on disk must be listed (orphan check).
- Pairwise conflicts: no two profiles may share a `<kind>/<basename>.md`. Use vertical-specific names; customise core files via `extends:` instead of copying them.
- `extends:` only targets `core/<kind>/<name>` (agents, skills, know-how, hooks; not commands). Never extend across profiles; shared material goes in `core/`. Each such file needs exactly one of `<!-- inherit -->` or `<!-- override-body -->`.
- Changing status or schema of `plugin.json` / `profile.json` needs maintainer review.
- After adding or removing any agent/skill/know-how/hook: run `python3 scripts/regen_explainers.py` and commit the HTML. Update `INVENTORY.md` and the README profile table if relevant.
- Never touch `core/` for one factory's needs; customise in a profile.

## Never

- No real customer, company, drawing, price or part-number data. No real person names (maintainer credits excepted). Use synthetic examples.
- No secrets, tokens, credentials, internal hostnames or IPs.
- Do not hard-code a company name in an agent prompt; write the role generically.
- Hard numbers (cutting parameters, shrinkage, costs, tolerances, lead times) must cite a source or be labelled `需驗證`. Prefer "see supplier datasheet" over fake precision.
- Do not hand-edit anything between `<!-- AUTO-START: <id> -->` and `<!-- AUTO-END: <id> -->` in `docs/explainers/*.html`; change the source data and regenerate.
- Do not claim on-prem, offline or no-egress properties the code does not guarantee. Cloud Claude Code is the default path; state exactly what leaves the machine, and check against [infra/on-prem/gb10-setup.md](infra/on-prem/gb10-setup.md) before wording such claims.
- Keep `install.sh` bash 3.2-safe (macOS default): no `declare -A`, `mapfile`, `${v,,}`, `${v^^}`. Python 3.10+ for MCP servers, type-hint public functions.
- Explainers stay self-contained: no CDN, no build step, A3-print-friendly.
- Do not push to `main` or bypass CI. Do not promote a profile's status or edit `install.sh`/CI without flagging it for maintainer review.

## Where real factory data goes

Outside this repo (private fork, private repo, or local path). `.gitignore` blocks `.env*`, `**/secrets/`, `**/credentials/`, `examples/**/real_*`, `*_real.*`, `customer_*`, runtime data and logs, but it is only a safety net: check `git status` and `git diff --cached` yourself. Found real data already committed: stop and follow [SECURITY.md](SECURITY.md).

## Areas under active change

These parts of the repo are moving. Before you document, reference or depend on any of them, check that the path exists in your checkout and look at the open PR list (`gh pr list`) for work in flight:

- team tier and chat gateway
- the scheduler MCP server and other MCP server templates
- adapters for other tools (a generic adapter)
- profile layout, loadable plugin packaging, and profile status (alpha profiles, new verticals)

Do not describe something as present because a PR mentions it; describe what is in your checkout. When your change touches one of these areas, re-read the matching section of [INVENTORY.md](INVENTORY.md) and `ci.yml`.

## Before you push

1. Replay the CI block above; all steps must pass.
2. Ran `python3 scripts/regen_explainers.py` if any agent/skill/know-how/hook/version changed.
3. Add one line under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md) (`### Added|Changed|Fixed`).
4. Scan the diff for real names, company data, secrets and unlabelled hard numbers.
5. Branch from `main`, Conventional Commit subject, one logical change per commit.
