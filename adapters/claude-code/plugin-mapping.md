# Claude Code Adapter — Plugin Mapping

How `manufacturing-skill` 的 platform-neutral 內容映射到 Claude Code 的實際 plugin 結構。

---

## Source → Target

```
Source (this repo)                      Target (~/.claude/plugins/manufacturing-skill/)
────────────────────                    ─────────────────────────────────────────────────
core/commands/*.md            ────►     commands/*.md
core/agents/*.md              ────►     agents/*.md                  ┐
profiles/<active>/agents/*.md ────►     agents/*.md                  ┘ ← profile overrides core
core/skills/<x>.md            ────►     skills/<name>/SKILL.md       ┐ <name> = frontmatter `name:`
profiles/<active>/skills/<x>.md ──►     skills/<name>/SKILL.md       ┘ （沒有 name 就用檔名 <x>）
core/know-how/*.md            ────►     know-how/*.md                ┐
profiles/<active>/know-how/*.md ────►   know-how/*.md                ┘
core/hooks/*.md               ────►     hooks/*.md                   ┐ 文件，不是 Claude Code hook（見下）
profiles/<active>/hooks/*.md  ────►     hooks/*.md                   ┘
plugin.json                   ────►     .claude-plugin/plugin.json   ← 產生的 Claude Code manifest（白名單欄位）
plugin.json                   ────►     plugin.json                  ← 原樣複製（/manufacturing、CI 讀它）
profiles/<active>/profile.json ────►    active-profile.json
                                        ~/.claude/skills/manufacturing-skill → ../plugins/manufacturing-skill（symlink）
```

順序：先照檔名 overlay（core → profile，conflict scan 照舊以 `<kind>/<檔名>.md` 判斷），**之後**才在暫存樹裡做三件事，最後整棵 `mv` 換上（atomic swap 不變）：

1. **Skills 改成資料夾**：`skills/<x>.md` → `skills/<name>/SKILL.md`。兩個檔對到同一個 `<name>`（不分大小寫）→ 在換上之前失敗，現有 install 不動。
2. **路徑改寫**：command / agent / skill / hook / know-how 內文引用的 repo 路徑（`core/skills/01-報價.md`、`core/agents/quote-specialist.md`、`profiles/cnc-machining/know-how/iatf-16949.md` …）在 install 裡不存在，改成安裝後的路徑（`skills/01-quote/SKILL.md`、`agents/quote-specialist.md`、`know-how/iatf-16949.md`）。只改**完全相符**、對得到實際來源檔的字串；`profiles/<p>/...` 只在 `<p>` 是 active profile 時改。markdown 連結 `](../skills/<x>.md)` 一起改，SKILL.md 因為深一層，`](../` 變 `](../../`。只動暫存樹，repo 不動。有 python3 用 python，沒有就用同一套規則的 `sed -E`（CI 比對兩者輸出一致）。
3. **Manifest**：從根目錄 `plugin.json` 產生 `.claude-plugin/plugin.json`，只留 Claude Code 接受的欄位（`name`、`displayName`、`version`、`description`、`author`{name, email, url}、`homepage`、`repository`、`license`、`keywords`）；`repository` 物件轉成它的 `url` 字串。沒有 python3 時只寫 `name`、`version`、`description`（`claude plugin validate` 會多一個「沒有 author」警告，仍通過）。

---

## Override 規則（filename-based）

```
core/agents/quote-specialist.md           ← 預設
profiles/cnc-machining/agents/quote-specialist.md  ← override（同名取代）
```

只要 profile 內存在同名檔案，install.sh 在 overlay 階段會直接覆蓋掉 core 的版本。

不允許跨 profile 繼承（避免菱形繼承）。

---

## Claude Code 認識什麼（claude 2.1.289 實測）

- **Manifest 一定要在 `.claude-plugin/plugin.json`**。根目錄的 `plugin.json` 不算 manifest；原樣搬過去也會被拒（`repository` 必須是字串）。
- `commands/*.md` — slash commands，frontmatter 含 `name`, `description`, `allowed-tools`, `argument-hint`
- `agents/*.md` — agent personas，frontmatter 含 `name`, `description`, `model`, `tools`
- **`skills/<name>/SKILL.md`** — 一個 skill 一個資料夾。平放的 `skills/*.md` 不會被載入。
- **Hooks 只認 `hooks/hooks.json`**（event + matcher + command）。我們的 `hooks/*.md`（pre-quote、post-order …）是**流程文件**，給 agent 用 Read 讀，**不是** Claude Code hook，也不會自動觸發。`claude plugin details` 會顯示 `Hooks (0)`，這是預期的。
- `know-how/`、`active-profile*.json`、`.installed` — loader 不看，agent / command 用 Read 讀。
- **`~/.claude/plugins/` 不會被掃描**：那是 marketplace / `claude plugin install` 管的地方，自己丟一個資料夾進去不會載入。所以 install.sh 另外建 symlink（下一節）。

---

## 怎麼被載入（三條路）

install 留在 `~/.claude/plugins/manufacturing-skill/`（commands 讀這個路徑下的 `.installed`），然後：

1. **skills-dir plugin（install.sh 預設）**：`~/.claude/skills/manufacturing-skill → ../plugins/manufacturing-skill`。`~/.claude/skills/` 底下有 `.claude-plugin/plugin.json` 的資料夾，Claude Code 會當成 `manufacturing-skill@skills-dir` 載入（user scope）。
   - 那個位置已經有**真的資料夾**（不是 symlink）→ install.sh 不動它，印警告並跳過；指向別處的舊 symlink → 改指到這次的 install。
   - Windows（Git Bash / MSYS）需要能建原生 symlink（開發人員模式或系統管理員）；建不起來就印警告，改用下面兩條路。
2. **單次 session**：`claude --plugin-dir ~/.claude/plugins/manufacturing-skill`
3. **本機 marketplace**：在某個資料夾放 `.claude-plugin/marketplace.json`，`plugins[].source` 指到 install 目錄，再 `claude plugin marketplace add <那個資料夾>` + `claude plugin install manufacturing-skill@<marketplace 名稱>`。

裝完要**重新啟動 Claude Code 或執行 `/reload-plugins`** 才會生效。

---

## 安裝後的目錄樹（cnc-machining 為例）

```
~/.claude/skills/manufacturing-skill  →  ../plugins/manufacturing-skill   (symlink)

~/.claude/plugins/manufacturing-skill/
├── .claude-plugin/
│   └── plugin.json          # Claude Code manifest（產生的，白名單欄位）
├── plugin.json              # repo 根目錄 plugin.json 原樣複製
├── active-profile.json      # 第一個 profile 的 manifest
├── active-profiles.json     # aggregated（有 python3 時）
├── .installed               # 安裝紀錄（時間、版本、profiles、source）
├── commands/                # 10 個：quote、order-status、bom-check、inspect、8d、
│   └── *.md                 #   manufacturing、init、install-profile、add-profile、morning-briefing
├── agents/
│   ├── quote-specialist.md       # profile (cnc) 版，取代 core
│   ├── sales-coordinator.md      # core
│   ├── production-planner.md     # core
│   ├── quality-inspector.md      # core
│   ├── inventory-manager.md      # core
│   ├── engineering-change-manager.md # core
│   ├── cnc-programmer.md         # profile (cnc)
│   ├── tool-life-engineer.md     # profile (cnc)
│   ├── fixture-designer.md       # profile (cnc)
│   └── prototype-coordinator.md  # profile (cnc)
├── skills/
│   ├── 01-quote/SKILL.md         # ← core/skills/01-報價.md
│   ├── 02-order/SKILL.md         # ← 02-接單.md
│   ├── 03-schedule/SKILL.md      # ← 03-排程.md
│   ├── 04-produce/SKILL.md       # ← 04-生產.md
│   ├── 05-inspect/SKILL.md       # ← 05-檢驗.md
│   ├── 06-ship/SKILL.md          # ← 06-出貨.md
│   ├── 8d-report-writing/SKILL.md
│   ├── bom-management/SKILL.md
│   ├── capacity-planning/SKILL.md
│   ├── engineering-change-process/SKILL.md
│   ├── spc-basics/SKILL.md
│   ├── cutting-parameter-calc/SKILL.md   # profile
│   ├── fixture-design-patterns/SKILL.md  # profile
│   └── g-code-review/SKILL.md            # profile
├── know-how/
│   ├── iso-9001.md  lean-5s.md  oee.md  mrp-basics.md  …   # core
│   ├── iatf-16949.md             # profile
│   ├── 刀具壽命管理.md            # profile
│   ├── 切削參數查表.md            # profile
│   └── 開發工廠-vs-量產.md         # profile
└── hooks/                        # 流程文件（不是 Claude Code hook）
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

會清掉舊的 `~/.claude/plugins/manufacturing-skill/`（先備份），重裝 core + 指定 profile。`~/.claude/skills/manufacturing-skill` symlink 指向固定路徑，不用重建。

## 多 profile 同時 active（v0.1.5+）

```bash
bash adapters/claude-code/install.sh cnc-machining,injection-molding
```

兩個（或更多）profile 一起 install。**install.sh 在動到現有 install 之前先跑完所有檢查**（profile 名稱、profile 目錄、需要時的 python3 / PyYAML、跨 profile conflict scan）：兩個 profile 若各自包含同名 `<kind>/<basename>.md`，install 拒絕並列出衝突檔。新版本先在同一個 `plugins/` 目錄下的暫存目錄組好，再用 `mv` 換上；舊版移到 `manufacturing-skill.bak.<時間>.<pid>`（只保留最新 3 份），換上途中失敗會自動搬回舊版。任何一步失敗都以非 0 結束，現有 install 不受影響（atomicity）。

設定後 `~/.claude/plugins/manufacturing-skill/` 多兩個檔：

| 檔                     | 內容                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------- |
| `active-profile.json`  | 第一個 profile 的 manifest（v0.1.x 相容；singular field）                           |
| `active-profiles.json` | v0.1.5+ aggregated 視圖：schema-versioned + 所有 profile manifest + list 欄位 union |
| `.installed`           | 多了 `activeProfiles: [...]` 陣列；`activeProfile` 仍保留為第一個 profile 名稱      |

不確定組合會不會衝突，先 dry-run：

```bash
bash adapters/claude-code/install.sh --list-conflicts cnc-machining,injection-molding
# 或：bash install.sh --list-conflicts  （無參數 → 掃所有 pair）
```

詳：[`docs/superpowers/specs/2026-05-09-multi-profile-active-design.md`](../../docs/superpowers/specs/2026-05-09-multi-profile-active-design.md)。

---

## 解除安裝

```bash
rm -rf ~/.claude/plugins/manufacturing-skill
rm -f  ~/.claude/skills/manufacturing-skill      # symlink（不要加結尾 /）
# 舊版備份（可選）：rm -rf ~/.claude/plugins/manufacturing-skill.bak.*
```

確認：`claude plugin list` 不再列出 `manufacturing-skill@skills-dir`。

---

## 驗證安裝

終端機：

```bash
claude plugin validate ~/.claude/plugins/manufacturing-skill   # √ Validation passed
claude plugin list                                             # manufacturing-skill@skills-dir · Status: √ loaded
claude plugin details manufacturing-skill                      # Skills / Agents 清單
```

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
- `adapters/generic/` — 純 markdown export，給其他 LLM agent 用 —— **已出貨（experimental, v0.3 preview）**：`export.py` 直接 import 本目錄的 `_multiprofile.py` / `_resolve_extends.py`，輸出與 install.sh 相同的 overlay 結果，見 [`adapters/generic/README.md`](../generic/README.md)

每個 adapter 讀取相同的 source（core/ + profiles/），只是映射到該 platform 的目錄結構。
