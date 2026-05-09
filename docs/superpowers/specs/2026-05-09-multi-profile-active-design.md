# Multi-Profile Active — v0.2 Design Spec

- **Date**: 2026-05-09 (v1), revised same-day (v2), approved 2026-05-09 (Jason merged spec PR #13)
- **Author**: Jason Lin (SIMHOPE) + Claude
- **Status**: ✅ Approved by Jason 2026-05-09 — implementation under way on `claude/c4-multiprofile-impl`
- **Target version**: 0.1.5 experimental (per Q5 recommendation)
- **Related**: [docs/ROADMAP.md](../../ROADMAP.md) v0.2 line item _"多 profile 同時 active（橫跨 vertical 的工廠用）"_
- **Predecessor**: [2026-05-08-profile-inheritance-design.md](2026-05-08-profile-inheritance-design.md) — multi-active is the natural follow-up that exercises the inheritance mechanism in the multi-profile case.

## Revision history

| Version | Date       | What changed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1      | 2026-05-09 | Initial draft.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| v2      | 2026-05-09 | Adversarial self-review found 2 HIGH + 5 MEDIUM + 3 LOW gaps. Patched: (H1) restate `commands/` is core-only — multi-profile inherits this invariant. (H2) Specify `active-profiles.json` aggregation rules: list fields union, scalars take primary profile's value with all others recorded under `bySource`. (M1) Hook execution order across profiles documented as alphabetical at install time. (M2) Duplicate profile in arg list warns instead of silently dedupes. (M3) `--list-conflicts` with no args runs all-pairs scan. (M4) Drop the "remove singular field in v0.3" timeline; keep it indefinitely. (M5) Conflict scan must precede backup. (L1) Pick "active profiles" as canonical term. (L2) `--list-conflicts` exit code stated. (L3) Hypothetical profiles disclaimed. |

---

## 1. Problem statement

Today, `bash adapters/claude-code/install.sh <profile>` accepts exactly **one** profile. The user picks CNC **or** injection-molding, never both. The active install at `~/.claude/plugins/manufacturing-skill/` reflects one vertical.

This breaks down for real factories that span verticals:

- A factory that **machines metal AND molds plastic** in the same shop (real example: medical-device manufacturers, automotive suppliers with both metal trim and plastic interior parts)
- A **job shop** that takes mixed work — CNC + sheet metal + light injection
- An **EMS** that does PCB assembly + plastic enclosure injection

These factories want the CNC-specific personas (`cnc-programmer`, `tool-life-engineer`) **and** the injection personas (`mold-designer`) live at the same time, plus presumably a unified `quote-specialist` that knows about both.

Today the user has three bad options:

1. Install only one profile and live with missing personas for the other vertical
2. Install one, then manually `cp` files from the other profile into `~/.claude/plugins/manufacturing-skill/` (drift, no version tracking)
3. Fork the project and create a custom `cnc+injection` profile (a maintenance nightmare)

None scale. We need first-class multi-profile-active.

### 1.1 Non-goals

- **Auto-merge of conflicting profile content.** If profile A has its own `quote-specialist.md` and profile B also has its own `quote-specialist.md`, we will NOT try to auto-merge them into one. The semantics are too domain-sensitive (which IATF wins, the CNC PPAP version or the medical-device PPAP version?). Conflict = hard error, user picks.
- **Cross-profile inheritance.** A profile cannot `extends:` another profile's file. (Already disallowed in the inheritance spec; reaffirmed here.)
- **Unbounded profile count.** Design supports N profiles in theory but expects 2-3 in practice. We won't optimize for installing 10 profiles at once.
- **Post-install profile add/remove without re-install.** v1 multi-active still goes through `install.sh` for any change. Hot-add of a profile is out of scope.

---

## 2. Use cases

| Scenario                                                 | Profiles                                         | Behavior                                                                                                                                                                                                                                                    |
| -------------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **U1** Pure CNC shop                                     | cnc-machining only                               | Today's behavior, unchanged. Single-profile-active is the trivial case of multi-profile-active with N=1.                                                                                                                                                    |
| **U2** Metal + plastic manufacturer                      | cnc-machining + injection-molding                | Both profiles' personas, skills, know-how are installed alongside core. CNC's `cnc-programmer` and injection's `mold-designer` both available. **No file-name collisions today** so no conflict.                                                            |
| **U3** Both profiles try to override `quote-specialist`  | cnc-machining + injection-molding (hypothetical) | If both profiles add their own `agents/quote-specialist.md`, install.sh refuses with "conflict: agents/quote-specialist.md exists in both cnc-machining and injection-molding — pick one." Resolution: user removes one or commits to the merge themselves. |
| **U4** Both profiles add own hook to same lifecycle slot | hypothetical: A and B both have `pre-quote.md`   | Same as U3. Refuse on filename collision.                                                                                                                                                                                                                   |
| **U5** Three profiles, one collision                     | A + B + C, where A and B collide on one file     | Refuse. Clear error names the colliding file and the two source profiles. C is irrelevant to the conflict but install still aborts.                                                                                                                         |
| **U6** Switch from single to multi without uninstall     | was `cnc-machining`, now wants `+ injection`     | Re-running `install.sh cnc-machining,injection-molding` does the right thing — old install backed up, new install reflects both. Same behavior as today's profile-switch, just N=2.                                                                         |

---

## 3. Design — "Refuse on Conflict"

The mental model is **set union, with no auto-resolution**:

```
installed_files = core_files
for profile in active_profiles:
    for file in profile.files:
        if file.basename in installed_files and \
           installed_files[file.basename].source != profile:
            CONFLICT — abort install
        installed_files[file.basename] = file (replacing core if filename matches)
```

Three rules:

- **Profile vs core**: if a profile contains an `agents/X.md`, it replaces (or extends, see inheritance spec) `core/agents/X.md`. **This is unchanged from v0.1.4.**
- **Profile vs profile**: if two active profiles both contain a file with the same basename under the same kind (`agents`/`skills`/`know-how`/`hooks`), install.sh **refuses** with a precise error.
- **Inheritance still works**: a profile's file can `extends: core/...` and the resolver runs as today. Multi-profile doesn't change inheritance semantics; it just runs the dispatch loop over more files.

The whole point of refuse-on-conflict is **predictability**. The user never wonders "which version of `quote-specialist` did I get?" because the install either succeeded (no ambiguity) or failed (with a clear name-the-file error).

### 3.1 Why not "last-one-wins" or "first-one-wins"

We considered ordered priority resolution: `install.sh cnc,injection` means CNC wins on collision. Rejected because:

1. **Silent semantic drift**: a user who reorders the args (or the install.sh interactive picker re-orders profile selections) silently gets a different model. The order would have to be visible in `.installed` and consciously chosen — additional UX surface.
2. **Inheritance interactions are unintuitive**: if both CNC and injection profiles `extends: core/quote-specialist`, "CNC wins" means injection's delta is silently dropped. The user doesn't get either's customization correctly.
3. **Domain risk**: in manufacturing, the cost of a wrong-but-plausible answer (an agent that mixes IATF 16949 with FDA) is high. Refusing is safer than guessing.

If a future use case really demands ordered resolution, we can add it as an opt-in `--allow-overrides` flag in v0.3+. For v1 multi-active, refuse is right.

### 3.2 What "conflict" precisely means

- Same `<kind>/<basename>.md` in two different active profiles → conflict
- Same kind but different basenames (e.g., `cnc/agents/cnc-programmer.md` vs `injection/agents/mold-designer.md`) → no conflict, both installed
- Frontmatter conflicts inside a single inherited file are NOT this layer's concern; they're handled by the inheritance resolver per file.

### 3.3 Scope: which kinds get profile overlays (H1)

Multi-profile inherits the existing single-profile invariant: `install.sh` overlays exactly four kinds — `agents/`, `skills/`, `know-how/`, `hooks/`. **`commands/` is core-only**, both for single and multi-profile. Profiles cannot contribute or override commands; the inheritance spec already rejects `extends:` on commands (Q3 / spec §10.1) and the install loop has never copied `profiles/<X>/commands/`.

Multi-profile does not change this. If a future profile authors a `profiles/<X>/commands/foo.md`, install.sh ignores it (currently) and CI Step 8's orphan check will already fire. The conflict scan (§5) operates only on the four overlaid kinds.

### 3.4 Hook execution order across profiles (M1)

Multiple active profiles may each contribute non-conflicting hooks (different basenames, e.g., `pre-quote.md` from one profile, `pre-injection-quote.md` from another). Both are installed alongside core hooks at `~/.claude/plugins/manufacturing-skill/hooks/`.

**Runtime execution order is determined by Claude Code, not by manufacturing-skill.** Today's Claude Code dispatches hooks alphabetically by filename. Authors who care about ordering should encode it in the filename (e.g., `01-pre-quote.md` before `02-pre-quote-cnc.md`). Multi-profile spec does not introduce an additional ordering layer.

### 3.5 Hypothetical profile names in this spec (L3)

Examples below reference hypothetical future profiles like `future-medical-cnc`. These do **not** exist in the repo today (only the 5 profiles in `plugin.json`'s `profiles.available`). They illustrate conflict scenarios that v1 multi-active must handle without requiring real conflicting profiles to land first.

---

## 4. CLI surface

### 4.1 Argument parsing

`install.sh` accepts a comma-separated list:

```bash
bash adapters/claude-code/install.sh cnc-machining,injection-molding
bash adapters/claude-code/install.sh "cnc-machining, injection-molding"   # whitespace tolerated
bash adapters/claude-code/install.sh cnc-machining                         # single, unchanged
bash adapters/claude-code/install.sh --core-only                           # unchanged
```

Comma-separation is the ergonomic choice (matches `apt install`, `pip install` patterns). Order is **not significant** in v1 — the resolver builds an unordered set. (In v0.3+ when we might allow ordered overrides, order becomes meaningful and we'd document it then.)

Whitespace around commas is stripped. Empty entries are ignored: `cnc-machining,,injection-molding` → 2 profiles. Duplicates are de-duped **and warned** (M2): `cnc-machining,cnc-machining` → 1 profile + stderr line `WARN: duplicate profile 'cnc-machining' in argument list, ignoring`. Silent dedup is wrong because the dup is usually a typo or a copy-paste error worth surfacing.

### 4.2 Interactive picker

Today the picker shows numbered options 1..N and accepts a single number. v1 multi-active extends this to comma-separated:

```
manufacturing-skill installer · choose profile(s)

  1) ✅ cnc-machining
  2) 🧪 injection-molding (alpha)
  3) 🚧 pcb-assembly (stub)
  4) 🚧 food-processing (stub)
  5) 🚧 pharma (stub)
  0) (core-only, no profile)

Tip: enter `1` for CNC only, `1,2` for CNC + injection, etc.
Default: 1  (press Enter to accept)

Select [0-5, comma-separated for multi]:
```

Single-number entries continue to work. New: `1,2` parses as `[cnc-machining, injection-molding]`.

### 4.3 New flags

- `--list-conflicts <p1>,<p2>,...` — dry-run check on a specific profile list: parses the args, reports any file conflicts that would prevent install. **Exit 0** if clean, **exit 1** if any conflict found. No filesystem mutation.
- `--list-conflicts` (M3) — no args form: scans **all profile pairs** in `plugin.json`'s `profiles.available` and reports every conflict. Useful for repo-level health checks ("which combinations does our repo currently support?"). Same exit codes as the targeted form.

This lets users probe combinations safely without committing to install.

---

## 5. Resolution algorithm (install.sh)

After argument parsing yields a list `ACTIVE_PROFILES = [p1, p2, ...]`:

**M5 — atomicity:** all validation runs **before any filesystem mutation, including backup**. Today's `install.sh` creates `${TARGET_DIR}.bak.<timestamp>` early in the run (before Stage 1). v0.2 reorders: validate + conflict-scan first, then backup, then Stages 1–4. A profile-list failure must not destroy a working install.

1. **Validate each profile exists.** For every `p_i`, check `profiles/<p_i>/profile.json` exists. Any missing → exit 1, list missing.
2. **Conflict scan** (new, before any filesystem mutation):
   - For each `kind` ∈ {agents, skills, know-how, hooks}:
     - Build a map `seen: basename → profile_name` over all active profiles
     - For each `p_i`, walk `profiles/<p_i>/<kind>/*.md` (excluding `_*.md`)
     - If a basename is already in `seen` from a different profile → record conflict `(kind, basename, p_seen, p_i)`
   - If any conflicts → print all of them clearly, exit 1.
3. **Stage 1** (unchanged): copy `core/` into target.
4. **Stage 2** (multi-pass): for each active profile in order, run today's overlay logic (extends-aware dispatch). Order between profiles doesn't matter because step 2 already proved no two profiles touch the same file.
5. **Stage 3** (manifest): write `active-profiles.json` (plural) listing all active profile manifests; deprecate `active-profile.json` singular (keep symlink/copy of first profile for backwards-compat in v0.1.x consumers).
6. **Stage 4** (.installed): record list of active profiles.

The conflict scan is the only new step. Steps 1, 3, 4 are minor extensions.

### 5.1 Worked example — clean install

```bash
$ bash install.sh cnc-machining,injection-molding

→ Validating profiles... ok (cnc-machining, injection-molding)
→ Scanning for file conflicts across profiles...
  agents:    no conflicts (cnc-machining: 4, injection-molding: 1)
  skills:    no conflicts (cnc-machining: 3, injection-molding: 1)
  know-how:  no conflicts (cnc-machining: 4, injection-molding: 2)
  hooks:     no conflicts (cnc-machining: 1, injection-molding: 0)
→ Installing core layer...
→ Overlaying profile: cnc-machining... (4 agents, 3 skills, 4 know-how, 1 hook)
→ Overlaying profile: injection-molding... (1 agent, 1 skill, 2 know-how, 0 hooks)
→ Total active: core + 2 profiles, 11 agents / 15 skills / 14 know-how / 5 hooks

✅ Installation complete.
```

### 5.2 Worked example — conflict

```bash
$ bash install.sh cnc-machining,future-medical-cnc

→ Validating profiles... ok
→ Scanning for file conflicts across profiles...
  agents:    ❌ CONFLICT
    agents/quote-specialist.md present in both:
      - cnc-machining
      - future-medical-cnc
  skills:    no conflicts
  know-how:  ❌ CONFLICT
    know-how/iatf-16949.md present in both:
      - cnc-machining
      - future-medical-cnc

❌ Cannot install — conflicting files in active profiles.
   Resolve by either:
     (a) Pick only one of [cnc-machining, future-medical-cnc]
     (b) Create a merged profile that combines both
   See docs/profile-development.md#multi-profile-active for guidance.
```

The error is **specific to the file**, lists **all conflicts at once** (not just the first), and points to documented resolution paths.

---

## 6. .installed format change

### 6.1 Today (v0.1.x)

```json
{
  "installedAt": "2026-05-09T07:24:47Z",
  "pluginVersion": "0.1.4",
  "activeProfile": "cnc-machining",
  "source": "/path/to/repo"
}
```

### 6.2 Proposed (v0.2.x)

```json
{
  "installedAt": "2026-05-09T08:00:00Z",
  "pluginVersion": "0.2.0",
  "activeProfiles": ["cnc-machining", "injection-molding"],
  "activeProfile": "cnc-machining",
  "source": "/path/to/repo"
}
```

- New field `activeProfiles` (plural, array): canonical list, always present in v0.2+.
- Old field `activeProfile` (singular, kept indefinitely — M4): kept for backwards compatibility with v0.1.x readers (e.g., the `/manufacturing` slash command's status display). Holds the **first** entry of `activeProfiles`. Cost is one line; v0.3 removal was promised in v1 of this spec but is dropped — keeping it forever is harmless and avoids breaking external scripts that already read it.

`active-profile.json` (the copied profile manifest) likewise gains a sibling `active-profiles.json` (an array of manifests). The singular file is kept as a copy of the **first** manifest indefinitely, same rationale as the singular field.

### 6.3 `active-profiles.json` aggregation rules (H2)

`active-profiles.json` is read by the `/manufacturing` slash command, future tooling, and anything that wants to know "what's installed." It must be deterministic and unambiguous when multiple profiles' manifests are stitched together.

**Format:**

```json
{
  "schema": 1,
  "primary": "cnc-machining",
  "profiles": [
    {
      /* full profile.json contents of cnc-machining */
    },
    {
      /* full profile.json contents of injection-molding */
    }
  ],
  "aggregated": {
    "applicableTo": [
      "job-shop",
      "low-volume-mass",
      "prototype",
      "tooling",
      "plastic",
      "thermoplastic",
      "thermoset"
    ],
    "tags": [
      "metal",
      "subtractive",
      "precision",
      "cnc",
      "plastic",
      "injection",
      "molding"
    ],
    "complianceFrameworks": [
      "ISO 9001",
      "IATF 16949",
      "AS9100 (aerospace, optional)",
      "GD&T (drawing standard)",
      "ISO 13485 (medical, optional)",
      "FDA 21 CFR (food contact, optional)",
      "RoHS / REACH (EU sales)",
      "UL 94 (flame rating)"
    ],
    "mcp": {
      "recommended": ["scheduler-mcp", "erp-connector"],
      "optional": ["cam-software-bridge", "tool-database"]
    }
  }
}
```

**Aggregation rules** (mirror the inheritance spec's frontmatter merge):

- **`profiles[]`**: full profile.json copies, in arg order. Reader can always retrieve a specific profile's original manifest.
- **`primary`**: the first profile in arg order. The legacy `active-profile.json` (singular) is a copy of `profiles[0]`.
- **`aggregated`** is the union view, useful for the slash command's status display:
  - **List fields** (`applicableTo`, `tags`, `complianceFrameworks`, `mcp.recommended`, `mcp.optional`, `wantedContributions`, `warnings`): **union with order preserved** (each profile's entries appended after the previous), de-duplicated. Same default as the inheritance frontmatter merge.
  - **Scalar fields** are **not aggregated** (no meaningful merge for `name`, `displayName`, `version`, `description`, `extends-core`, `status`, `createdBy`). Readers should consult `profiles[i]` directly when they need a scalar.
  - **`status`**: not aggregated. The most-conservative status (`stub` < `alpha` < `complete`) wins for "is this install stable?" questions, but that's a derived view a reader can compute; we don't bake it into `aggregated`.

**Schema versioning**: the new `schema: 1` field lets future readers detect format changes. Currently no migration mechanism — we'll add one if/when schema 2 happens.

---

## 7. Implementation footprint

| File                                     | Change                                                                                                                                                                                                                                 |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `adapters/claude-code/install.sh`        | Argument parser accepts comma-separated list + interactive picker accepts comma-separated. New `conflict_scan()` function. Stage 2 loops over profile list. Stage 3-4 write plural fields. New `--list-conflicts` flag. ~80 LoC delta. |
| `adapters/claude-code/plugin-mapping.md` | Document the multi-profile case + conflict rules.                                                                                                                                                                                      |
| `docs/profile-development.md`            | New section "多 profile 同時 active" with U2-U5 worked examples and resolution recipes.                                                                                                                                                |
| `core/commands/install-profile.md`       | Update the slash-command docs: now accepts comma-separated profile names; supports `add` semantics (appends to existing active profiles)? See Q1.                                                                                      |
| `core/commands/manufacturing.md`         | Status output reads `activeProfiles` (plural) when present, falls back to singular for v0.1.x installs.                                                                                                                                |
| `.github/workflows/ci.yml`               | New CI Step 12 — for every pair of profiles (`profiles/A`, `profiles/B`), run conflict_scan. Guarantees no new profile contribution silently collides with an existing one.                                                            |
| `tests/multiprofile/` (new)              | Golden-file fixtures: clean-install (no conflict), conflict-detected, partial-conflict (3 profiles, 2 collide).                                                                                                                        |
| `plugin.json`                            | Bump to 0.2.0 (or 0.1.5 if rolled out incrementally).                                                                                                                                                                                  |
| `CHANGELOG.md`                           | New version entry.                                                                                                                                                                                                                     |

**Total estimate**: ~330 lines added + ~30 modified. Single PR, full-day work. (v1 estimated ~250; v2 added the `active-profiles.json` aggregation logic, the warn-on-duplicate path, the no-args `--list-conflicts` mode, and the conflict-scan-before-backup reorder.)

---

## 8. CI guardrails (Step 12)

The conflict scan is the new defense. Without CI, two contributors can independently land profile changes that conflict pairwise — neither PR sees the conflict in isolation.

### Step 12 — Pairwise profile conflict scan

For every unordered pair `(A, B)` of profiles in `plugin.json`'s `profiles.available`, run conflict_scan(A, B). Report every conflict with file/profile names. CI fails if **any** pair conflicts.

This is O(n²) on profile count but n is small (currently 5; even if we triple it, 15² = 225 pairs which all complete in seconds).

The check runs even in single-profile-active world today — it just rarely finds conflicts because no current profile pair clashes. Once shipped, contributing a new profile that shares a filename with an existing profile fails CI immediately.

**Refinement** (post-review): we may want to allow a profile pair to opt-in to declared exclusivity (`profiles.json` `incompatibleWith: [<other-profile>]`) so that CI doesn't require pair-compatibility for genuinely contradictory profiles (e.g., a hypothetical `gmp-validated` vs `lab-prototyping` that semantically can't coexist). Not in v1; flagged as Q4.

---

## 9. Migration

Today's repo has 5 profiles, **none of which collide** pairwise (verified: only `cnc-machining` and `injection-molding` have content; their files don't share basenames). So the conflict scan is a no-op on day 1.

Existing single-profile installs continue to work — single-profile is just multi-profile with N=1. Users with old `.installed` files written by v0.1.x continue to function; the `/manufacturing` status command falls back to reading the singular field.

No data migration required. Pure additive feature.

---

## 10. Open questions for review

### Q1 — `/install-profile` slash-command semantics: replace vs add

The current `/install-profile <name>` instructs the user to re-run `install.sh <name>`, which **replaces** the current active profile. With multi-active:

- **(a) Replace** semantics: `/install-profile cnc-machining,injection-molding` replaces whatever was active.
- **(b) Add** semantics: `/install-profile injection-molding` appends to current active. To replace, use `/install-profile --replace <list>`.

Recommendation: **(a) Replace, plus a separate `/add-profile`** that explicitly appends. Replace is the common case (re-running install reflects the desired full state). Add is its own command for clarity. ✅ Confirm?

### Q2 — Profile-set declaration in plugin.json

Should `plugin.json` declare commonly-used profile combinations, or stay agnostic?

- **(a) Stay agnostic**: user assembles combinations themselves; we don't curate.
- **(b) Add `profileSets` field**:
  ```json
  "profileSets": {
    "cnc+injection": ["cnc-machining", "injection-molding"],
    "ems-full": ["pcb-assembly", "injection-molding"]
  }
  ```
  And `install.sh @cnc+injection` resolves to the set.

Recommendation: **(a)**. Profile sets are a coordination layer that adds complexity without proven need. If users ask for it, we add in v0.3. ✅ Confirm?

### Q3 — Order significance

Currently spec says **order is not significant** in v1 (refuse on any conflict, no priority resolution). Is that the right call?

- Pro: Predictable, no silent semantic drift, no UX surface for re-ordering.
- Con: A factory that genuinely wants "CNC wins over Injection on contested files" has no path. They'd need to fork.

Recommendation: **stay with order-insignificant in v1**, revisit in v0.3 with an opt-in `--order-priority` flag if real use cases emerge. ✅ Confirm?

### Q4 — Declared incompatibility

Should profiles be able to declare `incompatibleWith: [<other>]` in profile.json, so that CI doesn't expect them to coexist?

- Use case: `gmp-pharma` and `rapid-prototype` might semantically conflict (one demands traceability, the other prizes velocity); even if no file collision exists, mixing them is nonsense.
- Without this field: CI's pair scan finds no collision → green. User can install both → resulting install is semantically incoherent but technically functional.

Recommendation: **defer to v0.3**. v1 multi-active doesn't need this; the file-collision check is the structural guard. Semantic incompatibility is a documentation concern (each profile's README warns when relevant). ✅ Confirm?

### Q5 — Roll out path (mirrors C2's Q5)

- **(a) Bundle into v0.2.0** alongside other v0.2 work (auto-explainer expansion, community profile completion).
- **(b) Ship as v0.1.5** experimental, ahead of v0.2.0 — same pattern as inheritance shipped in v0.1.4.
- **(c) Wait until a real factory asks** for multi-profile.

Recommendation: **(b) v0.1.5 experimental**. Independent of remaining v0.2 work; mechanism is well-bounded; refuse-on-conflict makes it safe to ship without a real consumer driving the design. The first multi-vertical factory consumer will validate it post-ship. ✅ Confirm?

---

## 11. Approval block

| Question | Recommendation                                                         | Approved?           |
| -------- | ---------------------------------------------------------------------- | ------------------- |
| Q1       | Replace by default; separate `/add-profile` for additive case          | ✅ 2026-05-09 Jason |
| Q2       | Stay agnostic, no `profileSets` in v1                                  | ✅ 2026-05-09 Jason |
| Q3       | Order-insignificant in v1 (refuse on conflict; no priority resolution) | ✅ 2026-05-09 Jason |
| Q4       | Defer declared-incompatibility to v0.3                                 | ✅ 2026-05-09 Jason |
| Q5       | Ship as v0.1.5 experimental, not bundled with full v0.2                | ✅ 2026-05-09 Jason |
