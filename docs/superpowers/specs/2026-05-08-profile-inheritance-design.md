# Profile Inheritance Mechanism — v0.2 Design Spec

- **Date**: 2026-05-08
- **Author**: Jason Lin (SIMHOPE) + Claude
- **Status**: 📋 Draft — pending review by Jason
- **Target version**: 0.2.0
- **Related**: [docs/ROADMAP.md](../../ROADMAP.md) v0.2 line item _"部分內容繼承（profile agent prompt 開頭可寫 `<!-- extends: core/... -->` 不用 copy 整檔）"_

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
- A profile file **must declare** all the same required frontmatter fields the corresponding core file declares (name, description, model for agents, etc.) — they get merged with the rule "profile wins on conflict."
- **No `extends` = whole-file override** (current v0.1.x behavior preserved).

### 5.2 Body merge directives

Inside the markdown body, two directives control what happens to the inherited body:

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

### 5.3 What if both `<!-- inherit -->` and `<!-- replace-section -->` appear?

`replace-section` directives are processed against the inherited body **first**, then `<!-- inherit -->` outputs the modified body. So order in the profile file is:

1. Profile-specific frontmatter (overrides core frontmatter on conflict)
2. Optional profile-specific lead text (output verbatim)
3. `<!-- inherit -->` (outputs the modified core body)
4. Optional profile-specific trailing text (output verbatim)
5. `<!-- replace-section: X -->` blocks may appear **anywhere before `<!-- inherit -->`** to declare replacements; they don't render at their declaration site.

If `<!-- inherit -->` is **omitted entirely** in an `extends:` file, the profile body fully replaces core's body, and only the frontmatter is merged. (Useful when the prompt is a structural rewrite but you want to inherit the contract metadata.)

---

## 6. Resolution algorithm (install.sh)

For each `profiles/<active>/<kind>/<file>.md`:

1. **Parse frontmatter.** If no `extends` field → fall back to v0.1.x whole-file override (copy as-is). Done.
2. **Resolve `extends` path.** Must point at a real file in `core/<kind>/`. CI step (Step 10, see §10) enforces this.
3. **Load core file.** Parse frontmatter and body separately.
4. **Merge frontmatter:** start with core's, overwrite with profile's keys. Result is the output frontmatter.
5. **Process body:**
   a. Scan profile body for `<!-- replace-section: X -->` directives. Each one captures the markdown block from itself up to the next `##` heading or `<!-- inherit -->`, whichever comes first; that block is the **replacement content** for section `X`.
   b. Apply each captured replacement to the **core body** (not profile body): find the `## X` heading in core, replace its section with the captured content.
   c. Walk the profile body. For each token:
      - `<!-- inherit -->` → emit the (possibly-replaced) core body
      - `<!-- replace-section: X -->` plus the block that follows up to the next `##` → emit nothing (already processed)
      - other content → emit verbatim
6. **Write output:** assembled frontmatter + assembled body → `~/.claude/plugins/manufacturing-skill/<kind>/<file>.md`.

**Failure modes:**

- `extends` points to nonexistent core file → install.sh exits 1 with the path that's missing.
- `replace-section: X` references a heading that doesn't exist in core → install.sh exits 1.
- `<!-- inherit -->` appears more than once → install.sh exits 1 (single inheritance point only).
- Required frontmatter field absent in both core and profile → install.sh exits 1.

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
tools: [Read, Glob, Grep, Bash]
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

### 7.3 Install output (after `bash install.sh cnc-machining`)

`~/.claude/plugins/manufacturing-skill/agents/quote-specialist.md`:

```markdown
---
name: quote-specialist
description: 報價師 — CNC 精密加工版（含 IATF 16949 PPAP 與 FAI 要求）
model: claude-sonnet-4-6
tools: [Read, Glob, Grep, Bash]
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

Frontmatter is the merged version (description from CNC profile wins, others same). Body is core + appended CNC section.

---

## 8. Migration plan

The four current `profiles/cnc-machining/` agents and three skills don't conflict with core (they're CNC-specific personas like `cnc-programmer` that don't exist in core). They stay as **whole-file mode** with no `extends` — zero migration cost. Same for injection-molding's `mold-designer`.

The first profile to actually use `extends:` will be a hypothetical future PR (e.g., when the CNC profile decides it wants its own flavored `quote-specialist`). Today, **no profile file collides with a core file by name**. We can ship the inheritance mechanism without migrating anything.

This is also why we can introduce this in v0.2 without breaking anyone — it's purely additive.

---

## 9. Implementation footprint

### 9.1 Code changes

| File                                  | Change                                                                                                       |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `adapters/claude-code/install.sh`     | Detect `extends:` in profile files; if present, call new `_resolve_extends.py` instead of plain `cp`.        |
| `adapters/claude-code/_resolve_extends.py` (new) | The merge resolver. Pure stdlib Python (already a dependency for CI). ~150 lines.                |
| `.github/workflows/ci.yml`            | New step (10) — validate `extends:` paths exist in core, `replace-section:` headings exist in target.        |
| `docs/profile-development.md`         | New section — "Inheriting vs overriding core files."                                                          |
| `docs/superpowers/specs/...md` (this) | This spec.                                                                                                    |

`install.sh` stays POSIX-bash 3.2 compatible — the resolver is delegated to Python, which CI already requires.

### 9.2 Lines of code estimate

- `_resolve_extends.py`: ~150 lines (frontmatter parse + body section parse + replace + emit)
- `install.sh` delta: ~30 lines (detect `extends:`, dispatch)
- `ci.yml` Step 10: ~50 lines (path resolution + heading check)
- Docs: ~80 lines

**Total: ~310 lines added, ~5 modified.** Single PR, mergeable in a half-day session.

### 9.3 Test plan

Tested via golden-file fixtures, not unit tests:

- `tests/extends/case-01-pure-inherit/` — only `<!-- inherit -->`, no overrides; output should byte-equal core + merged frontmatter
- `tests/extends/case-02-append/` — `<!-- inherit -->` + trailing section, like §7's example
- `tests/extends/case-03-section-replace/` — `<!-- replace-section -->` for one section
- `tests/extends/case-04-no-inherit-marker/` — extends but no `<!-- inherit -->`, body fully replaced
- `tests/extends/case-05-error-bad-extends-path/` — invalid `extends:` path → expects exit 1
- `tests/extends/case-06-error-bad-replace-heading/` — `replace-section` for missing heading → expects exit 1

CI runs all 6 cases via a new `make test-extends` target.

---

## 10. CI guardrails (new step 10)

Beyond resolution-time errors, CI catches design problems statically:

- For every `profiles/<X>/<kind>/<file>.md` with `extends:`:
  - Target `core/<kind>/<file>.md` must exist
  - Each `<!-- replace-section: X -->` must match a `## X` heading in the target core file
  - `<!-- inherit -->` may appear at most once
  - Required frontmatter fields are satisfied after the merge (not before)

This step lives in `.github/workflows/ci.yml` and uses the same Python resolver as install.sh, in `--lint` mode.

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

### Q5 — Roll out path

Three options:

- **(a) Ship in v0.2.0 alongside other v0.2 work** (multi-profile-active, auto-explainer-HTML). Single big release.
- **(b) Ship in v0.1.4 as opt-in beta**, mark `extends:` as experimental, gather a real use case, formalize in v0.2.0.
- **(c) Wait until a profile actually needs it, then ship.**

**My recommendation: (b).** v0.2 is otherwise multi-week work; shipping inheritance alone in v0.1.4 lets the mechanism land while the rest of v0.2 is in flight, and a real future profile-extending PR validates the design. ✅ Confirm?

---

## 12. What this unblocks

After v0.1.4 (or v0.2.0):

- Hypothetical: pharma profile can add ALCOA+ data-integrity reminders to **every** core agent without copying 6 full files.
- Hypothetical: aerospace profile (future) can override `09-檢驗.md` to insist on FAI / DPD-CMM workflows, while inheriting the rest of the inspection skill.
- Real near-term: when a CNC sub-vertical (e.g., medical-device CNC) appears, it can `extends` the CNC profile's files (NB: §1.1 forbids cross-profile, so it would extend core directly with a CNC-medical-leaning delta).

---

## 13. Approval block

When Jason confirms the open questions above, this spec moves from 📋 Draft → ✅ Approved, and the implementation PR can begin.

| Question | Recommendation         | Approved?        |
| -------- | ---------------------- | ---------------- |
| Q1       | HTML-comment syntax    | ⬜               |
| Q2       | Allow multiple replaces | ⬜               |
| Q3       | Agents/skills/hooks/know-how only | ⬜    |
| Q4       | Document, no code      | ⬜               |
| Q5       | Ship as v0.1.4 beta    | ⬜               |
