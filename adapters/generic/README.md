# Generic adapter — 純 markdown 匯出（experimental, v0.3 preview）

把 manufacturing-skill 的內容（core + 你選的 profile，`extends:` 已解析）匯出成**純 markdown**，給 Claude Code 以外的 LLM agent 用。

適用情境：

- **Cursor** — 丟進 `.cursor/rules/` 或專案資料夾，用 `@` 引用
- **Gemini CLI / Codex** — 當作 `GEMINI.md` / `AGENTS.md` 旁的參考文件
- **地端 Ollama / LM Studio / Open WebUI** — 把單一 agent 或整份 bundle 當 system prompt
- **直接列印** — 給還沒用 AI 的同仁當 SOP 手冊看

匯出內容與 `bash adapters/claude-code/install.sh <profiles>` 安裝的內容**完全相同**：同樣的 core → profile overlay 順序、同樣的多 profile 衝突檢查（`_multiprofile.py`）、同樣的 `extends:` 解析器（`_resolve_extends.py`）。export.py 直接 import 這兩個 helper，不另外實作一套規則。

> 專屬的 Cursor / Gemini CLI / Codex adapter 仍在 [ROADMAP v0.3](../../docs/ROADMAP.md) 上。這個 generic adapter 是「最低公約數」：任何吃 markdown 的工具都能用。

---

## 用法

```bash
python3 adapters/generic/export.py --profiles cnc-machining --out ./export
python3 adapters/generic/export.py --profiles cnc-machining,injection-molding --out ./export --format bundle
python3 adapters/generic/export.py --core-only --out ./export --include agents,skills --reproducible
```

| 參數 | 說明 |
|---|---|
| `--profiles P1[,P2...]` | 要疊加的 profile（逗號分隔，同 install.sh）。與 `--core-only` 二選一 |
| `--core-only` | 只匯出 core，不疊 profile |
| `--out DIR` | 輸出資料夾（不存在會自動建立） |
| `--format files\|bundle` | `files`（預設）= 資料夾樹；`bundle` = 單一 markdown 檔 |
| `--include KINDS` | 只匯出部分種類：`know-how,skills,agents,hooks,commands`（預設全部） |
| `--reproducible` | `MANIFEST.json` 不寫 `generatedAt` 時間戳，同輸入 → byte-identical 輸出 |
| `--force` | `files` 格式：DIR 已有上次匯出時，先刪掉 `agents/ skills/ know-how/ hooks/ commands/ MANIFEST.json` 再寫（DIR 內其他檔案不動） |

需求：Python 3.10+。只有在 profile 檔案用到 `extends:` 時才需要 PyYAML（與 install.sh 相同）。

錯誤時以非 0 結束並印出一行 `error: ...`：未知 profile、多 profile 檔案衝突（同 `install.sh --list-conflicts`）、`extends:` 解析失敗、`--include` 拼錯。

---

## 兩種格式

### `--format files`（預設）

```
export/
├── MANIFEST.json      # 匯出了什麼、來自哪個 profile、版本、每檔 sha256
├── agents/*.md
├── skills/*.md
├── know-how/*.md
├── hooks/*.md
└── commands/*.md      # playbook（見下方說明）
```

每個檔案保留原本的 YAML frontmatter。`MANIFEST.json` 每筆紀錄含 `path`、`origin`（`core` / `profile` / `profile+extends`）、`source`（repo 內原始路徑）、`extends`（若有）、`sha256`、`bytes`；最上層含 `pluginVersion` 與每個 profile 的 `version` / `status`。

### `--format bundle`

單一檔案 `manufacturing-skill.<profiles>.md`（多 profile 用 `+` 連接，例如 `manufacturing-skill.cnc-machining+injection-molding.md`；core-only 為 `manufacturing-skill.core.md`）：

1. 開頭一段「如何搭配任何 LLM agent 使用」（中英對照）
2. 目錄（依 Agents → Skills → Know-how → Hooks → Playbooks 排序）
3. 每個檔案一節：frontmatter 轉成小表格（含 `_source_` 來源列），內文標題自動降三級以維持目錄結構

輸出完全 deterministic：檔案依種類 + 檔名排序，bundle 內沒有時間戳。

---

## Slash commands → Playbooks

`core/commands/*.md` 在 Claude Code 是 `/quote`、`/8d` 這類 slash commands。匯出時每個檔案開頭會加一段說明：**`/name` 語法只在 Claude Code 有效**，在其他 agent 請用自然語言，例如「依照 quote playbook 處理這張 RFQ」。

Hooks 同理：開頭加註 **documentation only**，它們是檢查清單，不會自動觸發。

---

## 範例

### Cursor（`.cursor/rules/`）

```bash
python3 adapters/generic/export.py --profiles cnc-machining \
  --out .cursor/rules/manufacturing-skill --reproducible
```

在 Cursor chat 用 `@agents/quote-specialist.md`、`@skills/01-報價.md` 引用需要的檔案即可。若你的 Cursor 版本只自動套用 `.mdc` 規則，可以另外寫一個很短的 `.cursor/rules/manufacturing.mdc` 當入口，例如：

```markdown
---
description: 製造業報價 / 排程 / 品檢問題時參考 manufacturing-skill
alwaysApply: false
---
報價問題請以 manufacturing-skill/agents/quote-specialist.md 的角色回答，
並依 manufacturing-skill/skills/01-報價.md 的步驟執行。
```

不建議把整份 bundle 設成 always-apply 規則 —— 太大，會吃掉每次對話的 context。

### 通用 system prompt（Ollama / Open WebUI / 任何 chat API）

只取需要的角色 + 流程，控制在幾千 token 內：

```bash
python3 adapters/generic/export.py --profiles cnc-machining --out ./sp --include agents,skills
cat ./sp/agents/quote-specialist.md ./sp/skills/01-報價.md > system-prompt.md
```

把 `system-prompt.md` 貼進 system prompt 欄位（或 Ollama `Modelfile` 的 `SYSTEM """..."""`），再用一般對話：「這是客戶的 RFQ，請依報價流程產出報價單」。

長 context 模型（10 萬 token 以上）可以直接把整份 bundle 當參考文件上傳。

---

## 不會匯出的東西

- **Hooks 不會執行** —— 只是文件。Claude Code 以外沒有對應的 lifecycle 機制，請由 agent 或人工在 `trigger` 時機自行檢查。
- **MCP servers 不包含** —— `profile.json` 裡的 `mcp.recommended` 只是建議清單，不會被打包；ERP / MES / 檔案系統連線請在你的工具裡自行設定。
- **Profile 的 `commands/`** —— 與 install.sh 相同，commands 只來自 core。
- `_templates/`、`profile.json`、`manufacturing.md`（profile 說明）、`examples/`、`docs/` 不在匯出範圍。

---

## 大小參考（v0.1.5）

| 匯出 | 檔案數 | bundle 大小 | 粗估 token |
|---|---|---|---|
| `--core-only` | 39 | ~147 KB | ~45k |
| `--profiles cnc-machining` | 51 | ~185 KB | ~56k |
| `--profiles cnc-machining,injection-molding` | 55 | ~211 KB | ~64k |
| `--profiles cnc-machining --include agents` | 10 | ~39 KB | ~12k |

內容以繁中為主，token 數依模型 tokenizer 不同會有 ±30% 差異。

---

## 相關文件

- [Claude Code adapter 對映表](../claude-code/plugin-mapping.md) —— overlay 規則來源
- [Profile 開發指南](../../docs/profile-development.md) —— `extends:` 與多 profile 規則
- 測試：`python3 tests/generic/test_export.py`
