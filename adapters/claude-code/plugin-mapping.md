# Claude Code Adapter — Plugin Mapping

How `manufacturing-skill` 的 platform-neutral 內容映射到 Claude Code 的實際 plugin 結構。

---

## Source → Target

```
Source (this repo)                      Target (~/.claude/plugins/manufacturing-skill/)
────────────────────                    ─────────────────────────────────────────────────
core/commands/*.md            ────►     commands/*.md
core/agents/*.md              ────►     agents/*.md       ┐
profiles/<active>/agents/*.md ────►     agents/*.md       ┘ ← profile overrides core
core/skills/*.md              ────►     skills/*.md       ┐
profiles/<active>/skills/*.md ────►     skills/*.md       ┘
core/know-how/*.md            ────►     know-how/*.md     ┐
profiles/<active>/know-how/*.md ────►   know-how/*.md     ┘
core/hooks/*.md               ────►     hooks/*.md        ┐
profiles/<active>/hooks/*.md  ────►     hooks/*.md        ┘
plugin.json                   ────►     plugin.json
profiles/<active>/profile.json ────►    active-profile.json
```

---

## Override 規則（filename-based）

```
core/agents/quote-specialist.md           ← 預設
profiles/cnc-machining/agents/quote-specialist.md  ← override（同名取代）
```

只要 profile 內存在同名檔案，install.sh 在 overlay 階段會直接覆蓋掉 core 的版本。

不允許跨 profile 繼承（避免菱形繼承）。

---

## Claude Code 認識什麼

Claude Code 預期 plugin 內：

- `commands/` — slash commands，frontmatter 含 `name`, `description`, `allowed-tools`, `argument-hint`
- `agents/` — agent personas，frontmatter 含 `name`, `description`, `model`, `tools`
- `skills/` — skills，frontmatter 含 `name`, `description`, `when_to_use`
- `hooks/` — lifecycle hooks（v1 用 markdown 描述，未來可加 JSON 配置）
- `know-how/` — 任意 markdown，agent 透過 Read tool 引用

`plugin.json` 提供 plugin 元資訊，Claude Code 啟動時讀取。

---

## 安裝後的目錄樹

```
~/.claude/plugins/manufacturing-skill/
├── plugin.json              # plugin 元資訊
├── active-profile.json      # 目前 active profile manifest
├── .installed               # 安裝紀錄（時間、版本、profile）
├── commands/
│   ├── quote.md
│   ├── order-status.md
│   ├── bom-check.md
│   ├── inspect.md
│   ├── install-profile.md
│   └── manufacturing.md
├── agents/
│   ├── quote-specialist.md       # core
│   ├── sales-coordinator.md      # core
│   ├── production-planner.md     # core
│   ├── quality-inspector.md      # core
│   ├── inventory-manager.md      # core
│   ├── cnc-programmer.md         # profile (cnc)
│   ├── tool-life-engineer.md     # profile (cnc)
│   ├── fixture-designer.md       # profile (cnc)
│   └── prototype-coordinator.md  # profile (cnc)
├── skills/
│   ├── 01-報價.md
│   ├── 02-接單.md
│   ├── 03-排程.md
│   ├── 04-生產.md
│   ├── 05-檢驗.md
│   ├── 06-出貨.md
│   ├── bom-management.md
│   ├── capacity-planning.md
│   ├── spc-basics.md
│   ├── g-code-review.md          # profile
│   ├── cutting-parameter-calc.md # profile
│   └── fixture-design-patterns.md # profile
├── know-how/
│   ├── iso-9001.md
│   ├── lean-5s.md
│   ├── oee.md
│   ├── mrp-basics.md
│   ├── iatf-16949.md             # profile
│   ├── 刀具壽命管理.md            # profile
│   ├── 切削參數查表.md            # profile
│   └── 開發工廠-vs-量產.md         # profile
└── hooks/
    ├── pre-quote.md
    ├── post-order.md
    ├── pre-ship.md
    ├── on-error.md
    └── pre-cnc-program-checkin.md # profile
```

---

## 切換 profile

```bash
bash adapters/claude-code/install.sh injection-molding
```

會清掉舊的 `~/.claude/plugins/manufacturing-skill/`（先備份），重裝 core + 指定 profile。

---

## 解除安裝

```bash
rm -rf ~/.claude/plugins/manufacturing-skill/
```

---

## 驗證安裝

在 Claude Code 內：

```
/manufacturing doctor
```

會檢查：

- plugin.json 是否能讀
- active-profile.json 對齊
- agents / skills / commands 數量是否符合 manifest
- MCP servers 是否啟動（如有設定）

---

## 未來：其他 adapter

預留位置：

- `adapters/cursor/` — Cursor IDE
- `adapters/gemini-cli/` — Gemini CLI
- `adapters/codex/` — Codex
- `adapters/generic/` — 純 markdown export，給其他 LLM agent 用

每個 adapter 讀取相同的 source（core/ + profiles/），只是映射到該 platform 的目錄結構。
