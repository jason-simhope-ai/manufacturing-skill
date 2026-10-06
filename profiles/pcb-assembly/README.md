# profiles/pcb-assembly/ (alpha)

> Status: **🧪 alpha** — has content, but not validated by an active EMS / SMT practitioner.
> Looking for an SMT process engineer or EMS quality engineer to review and extend.

---

## Who this is for

PCB assembly / EMS (electronics manufacturing services) shops — SMT lines, THT / wave or selective soldering, and box build — that want an AI assistant which speaks the trade: solder paste, stencils, reflow profiles, AOI / SPI / ICT / FCT, IPC-A-610 classes, MSL.

Typical reader: an operations or quality lead at a mid-size EMS plant that already runs an MES and wants help with **quality analytics** (FPY, defect Pareto) and **DFM feedback** — and a small IT team evaluating what the plugin actually connects to.

## What's in v0.1.0 alpha

| Type     | Item                                                     | Notes                                                                                |
| -------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Agent    | [`smt-process-engineer`](agents/smt-process-engineer.md) | Print / placement / reflow parameter reasoning, DFM feedback to customer and layout  |
| Agent    | [`ems-quality-analyst`](agents/ems-quality-analyst.md)   | AOI / SPI / ICT / FCT defect analysis, first-article checks, MSL handling, IPC-A-610 |
| Skill    | [`smt-dfm-review`](skills/smt-dfm-review.md)             | DFM checklist: land patterns, stencil apertures, spacing, MSL parts, panelization    |
| Skill    | [`aoi-defect-pareto`](skills/aoi-defect-pareto.md)       | MES / machine CSV export → per-station FPY, DPMO, Pareto, owner-assigned action list |
| Know-how | [`ipc-a-610-basics`](know-how/ipc-a-610-basics.md)       | Classes 1/2/3, the four conditions, acceptance-criteria families (no clause text)    |
| Know-how | [`smt-common-defects`](know-how/smt-common-defects.md)   | Tombstoning, bridging, head-in-pillow, voids, insufficient solder — causes and fixes |

Every file carries an alpha warning header. Numbers are labelled **範例** (example) or **需驗證** (needs verification).

## What it does — and does not do

**Does:**

- Review a new board's Gerber / BOM / centroid for DFM risks and phrase them as options for the customer
- Walk through SPI → placement → reflow when diagnosing a soldering defect, in that order
- Turn an exported AOI / SPI / ICT / FCT CSV into FPY, DPMO, a Pareto and an action list
- Explain which IPC-A-610 criteria family a disputed joint belongs to, and which class the customer must confirm
- Lay out MSL floor-life levels and what to check before a reel goes back on the line

**Does not:**

- ❌ **Connect to your MES.** There is no MES integration in alpha. Quality data must be **exported** (read-only account, customer names and serial numbers removed) and handed in as CSV. A future `mes-connector` should follow the read-only interface pattern of [`infra/mcp-servers/erp-connector/contract.py`](../../infra/mcp-servers/erp-connector/contract.py) — see `wantedContributions` in [profile.json](profile.json).
- ❌ **Schedule SMT lines.** Core [`production-planner`](../../core/agents/production-planner.md) uses job-shop heuristics; it does not model changeovers, feeder setup, MSL bake windows or stencil life. Use it for discussion, not as a finite-capacity scheduler.
- ❌ **Change a reflow profile, print parameters, AOI thresholds or test programs on the line.** The agents propose a change and a verification plan; a named human signs off.
- ❌ **Approve a deviation, concession or MRB disposition.** That stays with quality management and the customer.
- ❌ **Reproduce IPC standards.** IPC documents are paid standards; this profile summarises and points to the right section. Final acceptance is made by trained inspectors against the customer-specified revision.

## Compliance frameworks referenced

IPC-A-610, IPC J-STD-001, IPC-7711/7721, IPC J-STD-020 / J-STD-033, ANSI/ESD S20.20 or IEC 61340-5-1, ISO 9001, IATF 16949 (automotive EMS, optional), RoHS / REACH. Revisions and exemptions change — every revision-specific statement is labelled 需驗證.

## What ALPHA means honestly

- ✅ Content is coherent and based on public IPC summaries and general SMT practice
- ✅ Sufficient for: framework demonstration, a first conversation with an EMS plant, "does AI understand our trade?" sanity test, a first defect Pareto from exported data
- ⚠️ Not sufficient for: production decisions, customer audits, replacing a process or quality engineer
- ❌ No active EMS engineer has reviewed this profile end-to-end

If you adopt this profile, **expect to correct it**. Please file PRs back so the next EMS shop benefits.

## Still missing (contribution welcome)

See [profile.json](profile.json) `wantedContributions`. Highlights:

- `mes-connector` contract (read-only work orders, equipment state, AOI / SPI / ICT / FCT results)
- `smt-line-scheduling` skill (changeover, feeders, MSL bake, stencil life)
- `pcb-test-engineer` and `box-build-coordinator` agents
- `msl-management`, `esd-control`, `j-std-001`, `rework-process` know-how
- `pre-smt-line-start` hook

---

## How to contribute

1. Fork the repo and read [docs/profile-development.md](../../docs/profile-development.md)
2. Edit any file in `agents/` / `skills/` / `know-how/`, or start a new one from [`_templates/agent-starter.md`](_templates/agent-starter.md)
3. List new files in [profile.json](profile.json) (CI fails on unlisted files)
4. Say in the PR what was wrong, what is right, and how you know

To move from alpha to beta or complete, open a [Profile contribution issue](../../.github/ISSUE_TEMPLATE/profile-contribution.yml) first so we can align scope.

---

## Commercial collaboration

If your company is an EMS / PCBA shop and you'd like a profile validated against your actual lines, MES exports and customer requirements, contact [Jason Lin](mailto:jasonlin@simhope.com.tw).
