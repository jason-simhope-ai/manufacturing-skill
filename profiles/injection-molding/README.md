# profiles/injection-molding/ (alpha)

> Status: **🧪 alpha** — has content, but not validated by an active injection-molding practitioner.
> Looking for a contributor with mold design + injection molding production experience to review and extend.

---

## What's in v0.1.1 alpha

| Type     | Item                                                                 | Notes                                                                          |
| -------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Agent    | [`mold-designer`](agents/mold-designer.md)                           | DFM check, gating/runner concepts, cooling layout, ejection strategy           |
| Skill    | [`shot-weight-calc`](skills/shot-weight-calc.md)                     | Shot weight + machine selection (≤80% barrel) + clamping force quick-check     |
| Know-how | [`common-defects`](know-how/common-defects.md)                       | Decision tree: short shot / sink / warpage / flash / silver streak / weld line |
| Know-how | [`polymer-material-database`](know-how/polymer-material-database.md) | Quick-reference table for 14 common thermoplastics                             |

All four files are explicitly labelled with an alpha warning header.

## What this profile covers (and what's still missing)

**Covered:**

- Initial DFM judgement on a customer drawing
- Shot weight + clamping force estimation for machine selection
- First-line troubleshooting of the 6 most-cited defects
- Material processing window quick-reference

**Missing (contribution welcome — see [profile.json](profile.json)'s `wantedContributions`):**

- `molding-process-engineer` agent (cycle parameter tuning, real-time defect mitigation)
- `mold-maintenance-coordinator` agent (mold life tracking, preventive maintenance)
- `cooling-time-calc` skill (full cycle time estimation)
- `moldflow-analysis-review` skill (Moldflow / Moldex3D output interpretation)
- `DFM-for-injection` deep-dive know-how
- Hooks for batch release / mold checkout

---

## What v0.1.1 ALPHA means honestly

- ✅ Content is coherent and based on standard industry references
- ✅ Sufficient for: framework demonstration, sales conversation with an injection-molding shop, "does AI understand our trade?" sanity test
- ⚠️ Not sufficient for: production decisions, customer audit, replacing a process engineer
- ❌ No active injection-molding engineer has reviewed this profile end-to-end

If you adopt this profile in production, **expect to need to correct it** as you find inaccuracies. Please file PRs back so the next adopter benefits.

---

## How to contribute

### To improve existing alpha content

1. Fork the repo
2. Edit any file in `agents/` / `skills/` / `know-how/`
3. Note the change in your PR description (what was wrong, what's right, how you know)
4. Optional: bump `profile.json` `version` to `0.1.1-alpha` etc.

### To promote this profile from alpha to beta or complete

Open a [Profile contribution issue](../../.github/ISSUE_TEMPLATE/profile-contribution.yml) so we can align scope before you spend a week of work.

The `complete` bar requires:

- All 3 planned agents (mold-designer / process-engineer / maintenance-coordinator)
- At least 4 skills
- At least 5 know-how docs
- 1+ profile-specific hook
- Validation by an active injection-molding practitioner (PR co-signed)

---

## Commercial collaboration

If your company is a plastic factory and you'd like a custom `injection-molding-<your-company>` profile validated against your actual machines, dies, and materials, contact [Jason Lin](mailto:jasonlin@simhope.com.tw).
