# Profile Inheritance Mechanism — v0.2 Design Spec

- **Date**: 2026-05-08（v1）, **revised 2026-05-09**（v2）
- **Author**: Jason Lin (SIMHOPE) + Claude
- **Status**: 📋 Draft v2 — pending review by Jason
- **Target version**: 0.2.0 (or 0.1.4-experimental — see Q5)
- **Related**: [docs/ROADMAP.md](../../ROADMAP.md) v0.2 line item _"部分內容繼承（profile agent prompt 開頭可寫 `<!-- extends: core/... -->` 不用 copy 整檔）"_

## Revision history

| Version | Date       | Author        | What changed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | ---------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1      | 2026-05-08 | Claude        | Initial draft.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| v2      | 2026-05-09 | Claude        | Adversarial self-review pass found 3 high-severity gaps and 4 medium issues. Patched: (H1) frontmatter list-field merge defaults to **union**, scalars to profile-wins, with `<field>-replace: true` opt-out. (H2) CI Step 10 does **bidirectional** heading check; core PR that renames a referenced heading is rejected unless profile is updated in the same PR. (H3) `extends:` without `<!-- inherit -->` is now a **hard error** unless the profile declares `<!-- override-body -->` to opt out explicitly. (M1) directive parser strips fenced/inline code blocks first. (M2) `install.sh --resolve` flag prints merged output for review. (M3) Q5 split into Q5a (timing) and Q5b (semver expression). (M4) `tests/extends/` directory creation called out in §9.1. (L4/L5) §5.3 ↔ §6 ordering aligned; commands rejection enforced at install.sh + CI both. |

---

## 1. Problem statement

Today, profile-level customization is **whole-file replacement**: if a profile wants to tweak `quote-specialist`'s agent prompt, the profile must copy the entire `core/agents/quote-specialist.md` (currently ~94 lines) into `profiles/<X>/agents/quote-specialist.md` and edit. From `adapters/claude-code/install.sh`:

```bash
# Stage 1: copy core
cp -r "${PLUGIN_ROOT}/core/agents"   "${TARGET_DIR}/agents"

# Stage 2: overlay profile (filename-based override)
cp -r "${PROF_DIR}/agents/." "${TARGET_DIR}/agents/" 2>/dev/null || true
```

This causes three concrete problems:

1. **Drift.** When `core/agents/quote-specialist.md` gets a security or capability update, every profile that copied it must manually re-merge. There is no warning when this drift happens.
2. **Authoring friction.** A CNC profile that just wants to inject 20 lines of IATF-16949 context into the universal quote-specialist must own and re-validate ~100 lines of unrelated logic.
3. **Reviewability.** A profile maintainer's actual delta vs core is invisible in PRs — the diff shows a "new file" instead of "+20 lines, -3 lines vs core."

The override mechanism is correct as a **fallback** (some profile-specific agents really do want to start fresh), but it should not be the **only** mechanism.

### 1.1 Non-goals

- **Cross-profile inheritance** — `profiles/A/agents/X.md` extending `profiles/B/agents/X.md`. Already explicitly disallowed in `adapters/claude-code/plugin-mapping.md` (avoids diamond inheritance). Stays disallowed.
- **Multi-level inheritance** — extending a file that itself extends another. Single-hop only: profile → core, no chains.
- **Runtime resolution** — keep extension resolution at install-time. Claude Code reads finished `~/.claude/plugins/.../agents/*.md` files, not extension directives. (Reasoning in §4.)

---

## 2. Use cases driving the design

| Profile scenario                                                                                                                                                                       | What inheritance must support                  |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **CNC profile wants `quote-specialist` to also know about IATF-16949 PPAP requirements** when costing aerospace parts.                                                                  | Append a section after a known anchor          |
| **Injection-molding profile wants to replace the "material library" section** of `quote-specialist` (which is steel-biased) with a polymer-grade version.                              | Replace one named section, keep the rest       |
| **Pharma profile wants to add a frontmatter field** `gxp_validated: false` to every core agent it inherits, without changing prompt body.                                              | Merge frontmatter, leave body untouched        |
| **PCB profile wants `08-檢驗.md` skill exactly as core** — no changes — but also wants this fact to be visible (the manifest should still mention the skill is "inherited as-is").     | Inherit-with-no-overrides should be expressible |

These four shapes — **append, section-replace, frontmatter-merge, pure-inherit** — are the union of what real profile authors will need. The design must cover all four cleanly.

---

## 3. Current vs proposed mental model

### 3.1 Current (v0.1.x)

```
┌─────────────────────────┐    ┌──────────────────────────────────┐
│ core/agents/X.md        │    │ profiles/CNC/agents/X.md         │
│ (200 lines, full body)  │ ❌►│ (200 lines, full body, edited)   │
└─────────────────────────┘    └──────────────────────────────────┘
                                       │
                                       ▼ install.sh overlay
                              ┌──────────────────────────────────┐
                              │ ~/.claude/plugins/.../agents/X.md│
                              │ (CNC version wins, core gone)    │
                              └──────────────────────────────────┘
```

### 3.2 Proposed (v0.2)

```
┌─────────────────────────┐    ┌──────────────────────────────────┐
│ core/agents/X.md        │    │ profiles/CNC/agents/X.md         │
│ (200 lines, full body)  │ ──►│ extends: core/agents/X            │
│                         │    │ + 20 lines delta, edits 1 section │
└─────────────────────────┘    └──────────────────────────────────┘
                                       │
                                       ▼ install.sh, with merge step
                              ┌──────────────────────────────────────┐
                              │ ~/.claude/plugins/.../agents/X.md    │
                              │ (220 lines: core + profile delta merged)│
                              └──────────────────────────────────────┘
```

The key shift: the profile file declares what it wants to **change**, install.sh produces the **resolved** file. Whole-file override (3.1) remains available as a no-`extends` opt-out.

---

## 4. Why install-time resolution, not runtime

Claude Code reads agent / skill / command markdown verbatim as prompts. There is no plugin-side hook to interpret directives during runtime. The two viable resolution sites are:

- **install.sh (chosen).** Profile delta is resolved once during `bash install.sh <profile>`. Output is concrete files Claude Code reads as-is. Post-install drift is impossible. Easy to debug — `cat ~/.claude/plugins/.../agents/X.md` shows the literal prompt the model sees.
- **Runtime template engine.** Would require either a custom Claude Code hook or a sidecar process that re-renders on every Claude session. Adds a moving part, makes debugging harder, no upside for our use cases.

Trade-off accepted: **install.sh becomes more complex.** This is fine — the script today is ~250 lines of mostly `cp -r`, and the merge step is contained.

---

## 5. Proposed syntax

### 5.1 Extension declaration (frontmatter)

A profile file declares inheritance via a single new YAML frontmatter field:

```yaml
---
name: quote-specialist
description: 報價師 — CNC 客製化版（含 IATF 16949 PPAP 要求）
model: claude-sonnet-4-6
extends: core/agents/quote-specialist
---
```

**Rules:**

- `extends` value is a path **without `.md` extension**, relative to repo root, pointing to the source-of-truth core file.
- `extends` is **only allowed** in `profiles/<X>/<kind>/<file>.md`. A core file with `extends` is a CI error.
- A profile file **must declare** all the same required frontmatter fields the corresponding core file declares (name, description, model for agents, etc.). Merge rules are **per-field** (see §6.4).
- **No `extends` = whole-file override** (current v0.1.x behavior preserved).

### 5.2 Body merge directives

Inside the markdown body, three directives control what happens to the inherited body. **Directives inside fenced (` ``` `) or inline (`` ` ``) code are not processed** — they're treated as documentation examples (see §6.5).

#### `<!-- inherit -->`

Insert the entire core body verbatim at this point. Most common pattern:

```markdown
<!-- inherit -->

## CNC-specific addendum

When the part has IATF 16949 implications:
- Always include PPAP cost line
- Flag any FAI requirement explicitly
```

#### `<!-- replace-section: <heading> -->`

Replace a named `## heading` section from core with this profile's body until the next `##` heading. Heading must match exactly (whitespace-trimmed).

```markdown
<!-- inherit -->

<!-- replace-section: 材料庫 -->
## 材料庫

熱塑性塑膠（核心）：PA66、ABS、PC、POM、PBT、PEEK
熱固性塑膠（特殊）：環氧、酚醛
（替代 core 中的金屬材料庫，因為射出廠不會用到）
```

This isn't a markdown comment — it's a structured directive parsed by the install-time resolver. We use `<!-- ... -->` so it survives in raw markdown without rendering anywhere a user would see it (and stays harmless if the resolver is bypassed).

#### `<!-- override-body -->`

Explicit opt-in to "I really do want to discard the entire core body and only inherit frontmatter."

```markdown
---
name: quote-specialist
description: 完全特化的 pharma 版報價師，prompt 結構重寫
model: claude-sonnet-4-6
extends: core/agents/quote-specialist
---

<!-- override-body -->

（completely rewritten prompt body that does not inherit any of core's body）
```

This pattern is rare but legitimate (a profile occasionally needs to rewrite the prompt structurally while still benefiting from frontmatter inheritance and the manifest pointer to its core sibling).

### 5.3 Directive ordering

The resolver applies directives in this order, **regardless of their physical position in the profile file**:

1. **Mode detection.** Profile body must contain exactly one of `<!-- inherit -->` or `<!-- override-body -->`. Both present → CI/install error. Neither present → CI/install error (this used to be a silent fall-through in v1; v2 makes it an explicit choice).
2. **Section-replace collection.** Resolver scans the profile body for all `<!-- replace-section: X -->` directives. Each captures the markdown block that follows up to (but not including) the next `## ` heading or the next directive. Collected as a `{section_name → replacement_text}` map.
3. **Body assembly.** If mode is `<!-- inherit -->`: take core body, apply the replacement map (each `## X ... <next-##>` block in core is swapped with the corresponding replacement). Then walk the profile body in order and emit: profile lead-in text → modified core body at the `<!-- inherit -->` position → profile trailing text. `replace-section` directives and their captured content are not emitted at their declaration site. If mode is `<!-- override-body -->`: emit profile body verbatim, ignore replace-section directives (warn).

Authors are encouraged but not required to declare `replace-section` blocks **before** the `<!-- inherit -->` marker — it reads more naturally — but the resolver does not enforce position.

---

## 6. Resolution algorithm (install.sh)

For each `profiles/<active>/<kind>/<file>.md`:

1. **Parse frontmatter.** If no `extends` field → fall back to v0.1.x whole-file override (copy as-is). Done.
2. **Resolve `extends` path.** Must point at a real file in `core/<kind>/`. CI step (Step 10, see §10) enforces this.
3. **Load core file.** Parse frontmatter and body separately.
4. **Merge frontmatter (per-field rules).** This is more nuanced than "profile wins":
   - **Scalar fields** (string, number, bool — `name`, `description`, `model`, `argument-hint`, etc.): profile value wins on conflict, falls back to core if profile omits.
   - **List fields** (`tools`, `tags`, `applicableTo`, `keywords`, `complianceFrameworks`, etc.): **default = union (core ∪ profile, deduplicated)**. This matches the most common authoring intent — adding without losing core capabilities.
   - **List replace-instead-of-union opt-out**: a profile can declare `<field>-replace: true` (e.g., `tools-replace: true`) to force replacement semantics for that one field. Required when the profile genuinely needs to drop core entries (rare).
   - **Dict / nested fields**: deep-merge with the same per-field rules applied recursively. Profile keys win at every level.
   - **Required-field check is post-merge**: a field that's required by frontmatter rules (see ci.yml step 4) only needs to exist in the merged output, not in the profile file standalone.
5. **Strip code regions before directive scan** (see §6.5). Apply to a working copy of the profile body; the original is preserved for verbatim emission of code examples.
6. **Mode detection.** Working copy must contain exactly one of `<!-- inherit -->` or `<!-- override-body -->`. Anything else (zero or two markers) → install.sh exits 1.
7. **Section-replace collection.** Walk the working copy for `<!-- replace-section: X -->`. Capture the block from each directive up to the next `## ` heading or directive. Build the `{section: replacement}` map. Each `X` must match exactly one `## X` heading in core (post-NFKC normalization, see L2).
8. **Body assembly:**
   - If mode is `<!-- inherit -->`: apply replacements to a copy of the core body; then walk the **original profile body** and at the `<!-- inherit -->` marker substitute the modified core body. `replace-section` markers and their captured blocks are skipped during this walk.
   - If mode is `<!-- override-body -->`: emit profile body with the `<!-- override-body -->` marker stripped; warn (not error) if `replace-section` markers exist (they're ignored).
9. **Write output:** assembled frontmatter + assembled body → `~/.claude/plugins/manufacturing-skill/<kind>/<file>.md`.

### 6.5 Code-region stripping (M1)

Before directive scanning, the resolver creates a working copy of the body where:
- Triple-backtick fences (` ``` ... ``` `) and their contents are replaced with placeholders (preserving line counts so error messages stay aligned).
- Inline `` `code` `` spans are replaced with placeholders.

This means an author can write:

````markdown
範例：profile 檔內這樣使用 inherit

```markdown
<!-- inherit -->

## 新章節
```
````

without the inner `<!-- inherit -->` being treated as a directive. The same strip-then-scan pattern is already used by C1's markdown link checker.

### 6.6 Failure modes (consolidated)

| Condition                                                                                       | Install.sh | CI Step 10 |
| ----------------------------------------------------------------------------------------------- | ---------- | ---------- |
| `extends:` path does not resolve to a `core/<kind>/<name>.md`                                   | exit 1     | error      |
| `extends:` used in a `core/` file                                                               | exit 1     | error      |
| `extends:` used for a command (`profiles/<X>/commands/<Y>.md`)                                  | exit 1     | error      |
| Both `<!-- inherit -->` and `<!-- override-body -->` present                                    | exit 1     | error      |
| Neither `<!-- inherit -->` nor `<!-- override-body -->` present (with `extends:`)               | exit 1     | error      |
| `<!-- inherit -->` appears more than once                                                       | exit 1     | error      |
| `<!-- replace-section: X -->` heading not found in core                                         | exit 1     | error      |
| Multiple `## X` headings in core (ambiguous target)                                             | exit 1     | error (warn-only on core PR if no profile uses it) |
| Required frontmatter field absent in merged output                                              | exit 1     | error      |
| Profile declares `<field>-replace: true` for a field that doesn't exist in frontmatter         | warn       | warn       |
| `<!-- replace-section: X -->` present but mode is `<!-- override-body -->`                      | warn       | warn       |

---

## 7. Worked example (CNC + quote-specialist)

### 7.1 `core/agents/quote-specialist.md` (today)

```markdown
---
name: quote-specialist
description: 報價師
model: claude-sonnet-4-6
tools: [Read, Glob, Grep, Bash]
---

# 報價師（quote-specialist）

你是製造業報價工程師...

## 報價步驟

1. 讀圖紙與規格
2. 估材料
3. 估工時
...

## 材料庫

常用金屬：S45C、SUS304、SUS316、AL6061、AL7075...

## 輸出格式

報價單應包含：項次、單價、總價、交期、備註
```

### 7.2 `profiles/cnc-machining/agents/quote-specialist.md` (proposed)

```markdown
---
name: quote-specialist
description: 報價師 — CNC 精密加工版（含 IATF 16949 PPAP 與 FAI 要求）
model: claude-sonnet-4-6
tools: [WebFetch]
extends: core/agents/quote-specialist
---

<!-- inherit -->

## CNC 特殊條款

當客戶為汽車 / 醫療 / 航太行業時：

- IATF 16949: 必須在報價內列 PPAP 文件成本（通常 NT$ 8,000 ~ 30,000）
- FAI（首件檢驗）：需在交期欄位明確扣 1-2 工作天
- 客戶提供 LCL（Letter of Compliance）模板時，比對其 spec 與 PPAP Level 對齊
```

This profile file is **15 lines**. The current equivalent (full copy + edits) would be ~110 lines. Drift risk is eliminated — when core's "材料庫" section is updated, CNC's installed agent picks up the change next install.

Note the `tools: [WebFetch]` line: the **resolved output** will have `tools: [Read, Glob, Grep, Bash, WebFetch]` (union of core + profile). If the CNC profile actually wanted to **strip** Bash from the inherited list — say, for a security-hardened deployment — it would need:

```yaml
tools: [Read, Glob, Grep, WebFetch]
tools-replace: true
```

### 7.3 Install output (after `bash install.sh cnc-machining`)

`~/.claude/plugins/manufacturing-skill/agents/quote-specialist.md`:

```markdown
---
name: quote-specialist
description: 報價師 — CNC 精密加工版（含 IATF 16949 PPAP 與 FAI 要求）
model: claude-sonnet-4-6
tools: [Read, Glob, Grep, Bash, WebFetch]
---

# 報價師（quote-specialist）

你是製造業報價工程師...

## 報價步驟
1. 讀圖紙與規格
...

## 材料庫
常用金屬：S45C、SUS304、SUS316、AL6061、AL7075...

## 輸出格式
報價單應包含：項次、單價、總價、交期、備註

## CNC 特殊條款

當客戶為汽車 / 醫療 / 航太行業時：
- IATF 16949: 必須在報價內列 PPAP...
```

Frontmatter is the merged version: `description` from CNC profile wins (scalar field), `tools` is unioned (list field default). Body is core + appended CNC section.

### 7.4 Pre-merge inspection: `install.sh --resolve`

Reviewers and authors can preview the merged output without committing to a full install:

```bash
$ bash adapters/claude-code/install.sh --resolve cnc-machining/agents/quote-specialist
# (prints the resolved file content above to stdout)
```

This is a no-op against `~/.claude/plugins/`; it only reads and merges. A future CI step uses this to post the resolved diff as a PR comment when an `extends:` profile file is touched (M2 — see §10).

---

## 8. Migration plan

The four current `profiles/cnc-machining/` agents and three skills don't conflict with core (they're CNC-specific personas like `cnc-programmer` that don't exist in core). They stay as **whole-file mode** with no `extends` — zero migration cost. Same for injection-molding's `mold-designer`.

The first profile to actually use `extends:` will be a hypothetical future PR (e.g., when the CNC profile decides it wants its own flavored `quote-specialist`). Today, **no profile file collides with a core file by name**. We can ship the inheritance mechanism without migrating anything.

This is also why we can introduce this in v0.2 without breaking anyone — it's purely additive.

---

## 9. Implementation footprint

### 9.1 Code changes

| File                                                       | Change                                                                                                                                                                         |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `adapters/claude-code/install.sh`                          | Detect `extends:` in profile files; if present, call new `_resolve_extends.py` instead of plain `cp`. Also add `--resolve <profile>/<kind>/<file>` flag to print merged output. |
| `adapters/claude-code/_resolve_extends.py` (new)           | The merge resolver. Pure stdlib + PyYAML (already a CI dep). ~200 lines now (per-field merge + code-region strip raised the count vs v1's 150).                                |
| `tests/extends/` (new directory)                            | Golden-file fixtures, one per case in §9.3. Required because the resolver has subtle behavior worth pinning down.                                                              |
| `.github/workflows/ci.yml`                                 | New Step 10 — bidirectional schema check (see §10): profile→core resolution + core→profile heading-anchor protection + commands rejection. Plus optional Step 11 for resolved-diff PR comment. |
| `docs/profile-development.md`                              | New section — "Inheriting vs overriding core files," covers per-field merge, `<!-- inherit -->`/`<!-- override-body -->`/`<!-- replace-section -->`, and the bilingual heading constraint (Q4 / L2). |
| `docs/superpowers/specs/2026-05-08-profile-inheritance-design.md` (this) | This spec.                                                                                                                                                          |

`install.sh` stays POSIX-bash 3.2 compatible — the resolver is delegated to Python, which CI already requires.

### 9.2 Lines of code estimate

- `_resolve_extends.py`: ~200 lines (frontmatter parse + per-field merge + code-region strip + body section parse + replace + emit + `--resolve` mode)
- `install.sh` delta: ~40 lines (detect `extends:`, dispatch, `--resolve` flag)
- `ci.yml` Step 10: ~80 lines (bidirectional resolution + heading-anchor check + commands rejection)
- `ci.yml` Step 11 (optional, M2): ~30 lines (post resolved-diff PR comment on extends touches)
- `tests/extends/` fixtures: ~100 lines across 6+ golden files
- Docs: ~120 lines

**Total: ~570 lines added, ~10 modified.** Still single-PR sized (full day of focused work, not half-day as v1 estimated).

### 9.3 Test plan

Tested via golden-file fixtures (no unit-test framework — fixtures are simpler and more reviewable):

| Fixture                                    | Tests                                                                            |
| ------------------------------------------ | -------------------------------------------------------------------------------- |
| `case-01-pure-inherit/`                    | only `<!-- inherit -->`, no overrides; output byte-equals core (with merged FM)  |
| `case-02-append/`                          | `<!-- inherit -->` + trailing section (the §7 worked example)                    |
| `case-03-section-replace/`                 | one `<!-- replace-section: X -->` block applied                                  |
| `case-04-multiple-replace/`                | two `<!-- replace-section -->` blocks (per Q2 — multiples allowed)               |
| `case-05-override-body/`                   | `<!-- override-body -->` for full structural rewrite                             |
| `case-06-frontmatter-list-union/`          | `tools` field unions correctly (H1)                                              |
| `case-07-frontmatter-list-replace-flag/`   | `tools-replace: true` strips core entries (H1 opt-out)                           |
| `case-08-error-no-mode-marker/`            | `extends:` without `<!-- inherit -->` or `<!-- override-body -->` → exit 1 (H3)  |
| `case-09-error-both-mode-markers/`         | both `<!-- inherit -->` and `<!-- override-body -->` → exit 1 (H3)               |
| `case-10-error-bad-extends-path/`          | invalid `extends:` path → exit 1                                                 |
| `case-11-error-bad-replace-heading/`       | `replace-section` for missing heading → exit 1                                   |
| `case-12-error-extends-on-command/`        | `extends:` in a `commands/` file → exit 1 (Q3 / L5)                              |
| `case-13-codeblock-escape/`                | `<!-- inherit -->` inside `\`\`\` ... \`\`\`` is **not** processed (M1)         |

CI runs all 13 fixtures via a new `make test-extends` target (or just `python tests/extends/run.py`).

---

## 10. CI guardrails

Beyond resolution-time errors, CI catches design problems statically. v2 makes this **bidirectional** to address H2.

### 10.1 Step 10 — Profile-side validation (every `extends:` file)

For each `profiles/<X>/<kind>/<file>.md` with `extends:`:

- Target `core/<kind>/<basename>.md` must exist.
- `extends:` is **not allowed** in `core/` files or in `profiles/<X>/commands/` (Q3 / L5).
- Body must contain exactly one of `<!-- inherit -->` or `<!-- override-body -->` (H3).
- `<!-- inherit -->` may appear at most once.
- Each `<!-- replace-section: X -->` must match a `## X` heading in the target core file (post-NFKC normalization).
- After running the resolver in `--lint` mode, all required frontmatter fields are satisfied in the merged output.

### 10.2 Step 10b — Core-side anchor protection (H2)

The fragile case is: a core PR renames `## 材料庫` to `## 材料庫（含 supplier）`. CNC profile's `<!-- replace-section: 材料庫 -->` silently breaks at install time, but the core PR has already merged.

**Defense:** when CI runs on a PR that touches `core/<kind>/<file>.md`:

1. Compute the diff of `## ` headings between base and PR.
2. For every removed/renamed heading, search all `profiles/*/<kind>/*.md` files for a `<!-- replace-section: <removed-heading> -->` reference.
3. If any profile references the removed heading and the same PR doesn't update that profile too → CI fails on the **core PR**, not later on install.

This means a core author who renames a heading must either: (a) update all referencing profiles in the same PR, or (b) restore the old heading. Both are acceptable; silent breakage is not.

### 10.3 Step 10c — Optional: resolved-diff PR comment (M2)

When a PR touches any `extends:` profile file:

1. CI runs `install.sh --resolve` against the touched files on both base and HEAD.
2. Posts a sticky PR comment with a unified diff of the **resolved output**, not the profile delta.

This means reviewers see what the model actually sees, not just the 15-line delta. Especially valuable when `replace-section` interactions get subtle.

This step is **opt-in** (controlled by a label or repo setting) — it adds latency and posts a comment on every push. v1 of the implementation can ship without it; we can add later if review fatigue justifies it.

### 10.4 Implementation reuse

All of 10.1, 10.2, 10.3 use the same Python resolver as `install.sh`, just invoked in different modes (`--lint`, `--lint-anchors`, `--resolve`). One implementation, multiple call sites.

---

## 11. Open questions for review

These need Jason's call before I write code:

### Q1 — Directive syntax: HTML comments vs YAML frontmatter

I chose HTML-comment directives (`<!-- inherit -->`, `<!-- replace-section: X -->`) because they're invisible when the file is rendered as markdown anywhere (GitHub preview, Claude Code's reader, IDE preview). The alternative is YAML-frontmatter directives:

```yaml
---
extends: core/agents/quote-specialist
inherit: true
replace-sections:
  材料庫: |
    ...replacement content...
---
```

**Pros of YAML approach:** all metadata in one place, easier to validate.
**Cons:** putting markdown body content inside YAML strings is awful to read and edit; section content with code blocks needs careful escaping.

**Recommendation:** stay with HTML-comment approach. ✅ Confirm?

### Q2 — Should `replace-section` support multiple sections?

The spec lets you have multiple `<!-- replace-section: A -->` and `<!-- replace-section: B -->` blocks. Should we **disallow more than one** to keep profiles simple? My take: allow multiple, document carefully. Multiple replacements is a valid use case (an injection profile might rewrite both `材料庫` and `輸出格式`).

**Recommendation:** allow multiple. ✅ Confirm?

### Q3 — Does `extends` work for skills, hooks, know-how, commands too?

The mechanism is content-agnostic. But:

- **skills:** yes, same need as agents (skills are also large prompts)
- **hooks:** they're tiny (~30 lines) and rarely warrant inheritance — but mechanism shouldn't gate it
- **know-how:** yes, especially for adding industry-specific examples to core know-how
- **commands:** **no recommended**. Slash commands are short and structurally tight; encourage profiles to add new commands (different filename) rather than redefine universal ones.

**Recommendation:** support `extends` for agents, skills, hooks, know-how. Disallow for commands (CI rejects). ✅ Confirm?

### Q4 — Bilingual / mixed-language `replace-section` headings

Current core docs are zh-TW. Future profiles might be in English. The `replace-section: 材料庫` directive matches Chinese section headings exactly. If someone writes `<!-- replace-section: Material Library -->` against a Chinese core, no match → CI error. That's the right behavior, but worth mentioning in docs.

**Recommendation:** document the constraint, no mechanism change needed.

### Q5a — Roll out timing

Three options:

- **(a) Ship in v0.2.0 alongside other v0.2 work** (multi-profile-active, auto-explainer-HTML). Single big release.
- **(b) Ship in the next patch release as opt-in experimental**, mark `extends:` as experimental, gather a real use case, formalize in v0.2.0.
- **(c) Wait until a profile actually needs it, then ship.**

**My recommendation: (b).** v0.2 is otherwise multi-week work; shipping inheritance alone in the next patch lets the mechanism land while the rest of v0.2 is in flight, and a real future profile-extending PR validates the design. ✅ Confirm?

### Q5b — How to express "experimental" in semver (M3)

If Q5a = (b), pick how to express the experimental status:

- **(α) `0.1.4`, plain.** Document `extends:` as experimental in `CHANGELOG.md` and `docs/profile-development.md`. plugin.json schema unchanged.
- **(β) `0.1.4-experimental.1`** (SemVer pre-release identifier). Requires loosening `plugin.json`'s version regex; CI step 2 updated.
- **(γ) Add `experimental` flag inside `plugin.json`.** Per-feature granularity for future use:
  ```json
  "experimental": ["profile-inheritance"]
  ```
  Plus a CI warning when an experimental feature is used in a non-experimental profile.

**My recommendation: (α).** It's the lowest-friction option for a project this small; we don't have multiple experimental features yet. (β) and (γ) are over-engineered for v0.1.x. ✅ Confirm?

---

## 12. What this unblocks

After v0.1.4 (or v0.2.0):

- Hypothetical: pharma profile can add ALCOA+ data-integrity reminders to **every** core agent without copying 6 full files.
- Hypothetical: aerospace profile (future) can override `09-檢驗.md` to insist on FAI / DPD-CMM workflows, while inheriting the rest of the inspection skill.
- Real near-term: when a CNC sub-vertical (e.g., medical-device CNC) appears, it can `extends` the CNC profile's files (NB: §1.1 forbids cross-profile, so it would extend core directly with a CNC-medical-leaning delta).

---

## 13. Approval block

When Jason confirms the open questions above, this spec moves from 📋 Draft v2 → ✅ Approved, and the implementation PR can begin.

| Question | Recommendation                              | Approved? |
| -------- | ------------------------------------------- | --------- |
| Q1       | HTML-comment syntax                         | ⬜        |
| Q2       | Allow multiple replace-section blocks       | ⬜        |
| Q3       | Agents/skills/hooks/know-how only; commands rejected at install + CI | ⬜ |
| Q4       | Document the bilingual heading constraint, NFKC-normalize on match | ⬜ |
| Q5a      | Ship as next-patch experimental, not bundled with full v0.2  | ⬜  |
| Q5b      | Plain `0.1.4` + CHANGELOG flag, no schema changes            | ⬜  |

### v2 patch summary (what changed since v1 review)

- **H1** — frontmatter list-field merge defaults to **union** (not replace), with `<field>-replace: true` opt-out. Scalars still profile-wins. Worked example shows `tools` union.
- **H2** — CI Step 10b protects core-side heading renames against silent breakage. Renaming a referenced heading without updating the profile fails the **core PR**, not the install months later.
- **H3** — `extends:` without `<!-- inherit -->` is no longer a silent fall-through. Author must explicitly choose `<!-- inherit -->` or `<!-- override-body -->`. CI + install.sh both enforce.
- **M1** — directive parser strips fenced and inline code regions before scanning, matching C1's link-checker pattern.
- **M2** — `install.sh --resolve <profile>/<kind>/<file>` flag prints merged output. Optional CI Step 10c posts resolved-diff PR comments.
- **M3** — Q5 split into Q5a (timing) and Q5b (semver expression with three options α/β/γ).
- **M4** — `tests/extends/` directory creation explicit in §9.1 footprint table.
- **L4** — §5.3 and §6 directive ordering aligned: position-independent collection, deterministic emission.
- **L5** — `extends:` on `commands/` files explicitly rejected at both install.sh (exit 1) and CI Step 10.
