# Profile Development — 怎麼長一個新 Vertical Profile

> 給「想為自己的工廠 / 客戶 / 社群 contribute 一個新 profile」的人看。
> **照這份文件逐步做，CI 應該一次全綠。** 如果你照做卻紅燈，那是文件的 bug，請開 issue。

---

## 0. 先看這張表（TL;DR）

| 你要做的事             | 一句話                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------- |
| 起手                   | 複製一個現有 **alpha** profile、刪掉內容、留下骨架（§2）                                                |
| 寫 `profile.json`      | 11 個欄位 CI 強制（§3）；alpha 還要有 `status` / `warnings` / `wantedContributions` / `complianceFrameworks` |
| **登記 `plugin.json`** | `profiles.available` + `profiles.alpha` 兩處（§4）。沒登記 = 其他 CI 步驟會**悄悄跳過**你的 profile    |
| agent 的 `tools`       | 只准 `[Read, Grep, Glob]`；要 `Bash` 必須在內文放理由標記（§6）。CI 會擋                                |
| 內容                   | 不放真人 / 真公司 / 真價格；硬數字標「範例」、法規標「需驗證」（§7）                                    |
| 狀態                   | 只有 `alpha`（和 CNC 的 `complete`）；**沒有 stub 了**（§8）                                            |
| 多 profile 同時啟用    | 不能同名檔、不能跨 profile `extends:`、hook 名稱不要撞（§10）                                           |
| 要手改的地方           | 13 項清單（§11）                                                                                        |
| 提 PR 前               | 本機重跑全部 CI 步驟（§12）                                                                             |

---

## 1. 為什麼會需要新 profile

`manufacturing-skill` 的 core 是任何製造業都適用的流程（報價 → 接單 → 排程 → 生產 → 檢驗 → 出貨）。每個產業另有自己的 agent、skill、know-how、合規要求，
`profiles/<your-vertical>/` 就是 overlay 它們的地方。現有的 profile：

| Profile             | 狀態     | 說明                         |
| ------------------- | -------- | ---------------------------- |
| `cnc-machining`     | complete | 唯一完整的參考實作           |
| `injection-molding` | alpha    | 塑膠射出成型                 |
| `pcb-assembly`      | alpha    | PCB 組裝 / EMS               |
| `food-processing`   | alpha    | 食品加工（HACCP）            |
| `pharma`            | alpha    | 製藥 / 醫材（GMP）           |
| `machinery-eto`     | alpha    | 機械設備製造（ETO 接單設計） |

還沒有的（歡迎貢獻）：鈑金 / 沖壓、模具製造、紡織、化工、醫材 ISO 13485 專門版、航太 AS9100、油氣 API 等。

---

## 2. 起手：複製一個 alpha profile、清空內容

**不要**複製 `cnc-machining`：它是唯一沒有 `status`、沒有 `README.md`、沒有 `_templates/` 的 profile，骨架跟現行慣例不一樣。
複製任一個 alpha profile；`pharma`（有 `_templates/agent-starter.md`）或 `machinery-eto`（最新、README 結構最完整）都可以：

```bash
cp -r profiles/pharma profiles/<your-vertical>
cd profiles/<your-vertical>
rm -f agents/*.md skills/*.md know-how/*.md hooks/*.md   # 清掉被複製來的內容
rm -rf README.md _templates                              # 這兩個含指向被複製 profile 的相對連結，留著會讓連結檢查失敗；README 見 §9
cd ../..
```

> 命名：全小寫、`-` 分隔、描述性（`sheet-metal-stamping` ✅；`stamping`、`sheetMetal`、`sheet_metal` ❌）。

清空後的骨架：

```text
profiles/<your-vertical>/
├── profile.json        # §3
├── README.md           # §9：自己重寫，誠實寫「這個 alpha 代表什麼」
├── agents/             # §5、§6
├── skills/
├── know-how/
├── hooks/              # 可選
└── _templates/         # 可選：以 _ 開頭的檔案不被 CI 當成內容（orphan / frontmatter check 跳過），但 `tools` 守門仍會檢查 agent-*.md
```

**alpha 的最低標準**：1 個 agent + 1 個 skill + 1–2 份 know-how；每個檔案檔頭有 alpha 警語（§7）；`profile.json` 至少 3 條 `warnings`；
README 寫清楚「做什麼 / 不做什麼 / 還缺什麼」。

---

## 3. `profile.json`（可直接複製的範本）

CI 的「profile.json schema sanity」要求 **11 個欄位**：
`name displayName version description extends-core applicableTo tags agents skills knowHow hooks`
（其中 `agents skills knowHow hooks applicableTo tags` 必須是 list、`extends-core` 必須是 boolean）。
再加上 alpha 慣例欄位 `status`、`warnings`、`wantedContributions`、`complianceFrameworks`、`displayNameEn`
（CI 不強制，但 `install.sh`、`/manufacturing`、`active-profiles.json` 會讀，審稿者也會要求）。

```json
{
  "name": "your-vertical",
  "displayName": "你的領域中文名",
  "displayNameEn": "Your Vertical (English)",
  "version": "0.1.0-alpha",
  "status": "alpha",
  "extends-core": true,
  "description": "一到三句話：這個 profile 解決什麼問題、適合誰。Alpha — 內容基於公開標準摘要與業界通識，需要該行業的實務工作者驗證。",
  "applicableTo": ["your-process-or-product-type"],
  "tags": ["your-vertical", "alpha"],
  "agents": ["my-first-agent"],
  "skills": ["my-first-skill"],
  "knowHow": ["my-first-know-how"],
  "hooks": [],
  "wantedContributions": [
    "還缺什麼（一行一項）：例如某某 agent / skill / know-how",
    "Validation by an active <your-trade> practitioner of all alpha content"
  ],
  "complianceFrameworks": [
    "ISO 9001:2015",
    "你的行業標準或法規（版次與適用範圍需驗證）"
  ],
  "warnings": [
    "Alpha 內容基於公開標準摘要與業界通識，未經在職實務工作者驗證",
    "所有數字（工時、費率、比例、期間）都是『範例』，以貴公司實績與合約為準",
    "法規、標準版次與主管機關程序一律標『需驗證』，以官方公告與標準原文為準",
    "AI 輸出是草稿，簽核 / 放行 / 驗收由人類權責人員負責"
  ]
}
```

| 欄位                                      | 規則                                                                                                                                  |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                                    | 等於資料夾名                                                                                                                          |
| `version`                                 | alpha 一律 `0.1.0-alpha`（升級由 maintainer 決定）                                                                                    |
| `status`                                  | `alpha`。**必須和 `plugin.json` 登記的清單一致**（§4）。不寫 = 被當成 `complete`                                                      |
| `agents` / `skills` / `knowHow` / `hooks` | 檔名（不含 `.md`）。**資料夾裡每個 `.md` 都要列、列的每個都要存在**（orphan check + manifest check）。沒有 hook 就寫 `[]`，欄位不能省 |
| `warnings`                                | 至少 3 條；寫給「裝了這個 profile 的人」看，不是給 reviewer                                                                           |
| `wantedContributions`                     | 老實列出還缺的東西，這是下一位貢獻者的待辦清單                                                                                        |
| ~~`overrides.removed`~~                   | **不存在**（舊版文件寫過「v0.2 計畫支援」，schema 不認得，別用）。不要的 core agent 請在 prompt 內文說明「在這個情境不要 dispatch 我」 |

---

## 4. 登記 `plugin.json`（最容易漏、而且 CI 不會自己提醒你的舊版陷阱）

在 `plugin.json` 的 `profiles` 加**兩處**：

```json
"profiles": {
  "available": ["cnc-machining", "...", "your-vertical"],
  "complete": ["cnc-machining"],
  "alpha": ["...", "your-vertical"],
  "stub": [],
  "default": "cnc-machining"
}
```

- `available`：所有可安裝 profile 的名單。
- `alpha`（或 `complete`）：和你 `profile.json` 的 `status` 對應的那份清單。

**未登記的 profile 會被悄悄略過**：「Profile manifests vs filesystem」、「Explainer auto-sections」（統計面板）、
「Multi-profile — pairwise conflict scan」都只看 `profiles.available`。沒有登記時你的 PR 可以全綠，
但新 profile 和其他 profile 的撞名完全沒人掃、explainer 統計也沒算到你。
所以 CI 另有一道 **「Profiles — every profiles/&lt;dir&gt; is registered in plugin.json」**：
資料夾存在卻沒登記、`status` 與清單不一致、清單裡有不存在的名字，都會直接失敗。

登記後馬上重生 explainer 統計（否則「Explainer auto-sections — drift check」會紅）：

```bash
python3 scripts/regen_explainers.py
```

---

## 5. 各類檔案的 frontmatter 規格

「CI 強制」是現在 CI 真的會擋的欄位；其他是現行 alpha profile 的慣例（請跟著做，審稿者會看）。

| 類型         | 位置                 | CI 強制                          | 慣例                                                                               |
| ------------ | -------------------- | -------------------------------- | ---------------------------------------------------------------------------------- |
| **agent**    | `agents/<name>.md`   | `name` `description` `model`；`tools`（§6） | `displayName`、`status: alpha`                                          |
| **skill**    | `skills/<name>.md`   | `name` `description`             | `displayName`、`when_to_use`、`status: alpha`                                      |
| **hook**     | `hooks/<name>.md`    | （不查）                         | `name` `displayName` `trigger` `status: alpha`，加 `profile: <your-vertical>`      |
| **know-how** | `know-how/<name>.md` | （不查）                         | `title` `tags` `status: alpha` `last-reviewed: YYYY-MM-DD` `source:`（誠實寫來源） |

agent 範例（直接複製這段，它已經符合下面的 `tools` 規則）：

```markdown
---
name: my-first-agent
displayName: 我的第一個 agent / My First Agent
description: 一句話：做什麼、給誰用、不做什麼
model: sonnet
tools: [Read, Grep, Glob]
status: alpha
---
```

---

## 6. 工具（`tools:`）政策：最小權限

- **agent 預設只宣告 `[Read, Grep, Glob]`。** 不要宣告 `Bash`、`WebFetch`、`Write`、`Edit`。
- agent 內文**真的要執行東西**（例如對使用者給的 CSV 跑統計）才可以加 `Bash`，而且必須在內文放一行理由標記：

  ```markdown
  <!-- tools: bash-justified: <一句話：跑什麼、為什麼不能只靠 Read / Grep> -->
  ```

  目前唯一的例子：`profiles/pharma/agents/deviation-capa-coordinator.md`（對去識別化的偏差 CSV 做唯讀分群統計）。
- 不要只因為「可能用得到」就加 `Bash`。agent prompt 只是在讀檔案、整理、起草，就不需要。
- `_templates/agent-starter.md` **永遠不得**宣告 `Bash`（貢獻者會整份複製）。
- 省略 `tools:` 等於繼承全部工具，也是違規。
- 背景：profile 內容在客戶端會被送進雲端模型；權限只管「動作」，不管「資料送去哪」，所以內容規則（§7）也要遵守。

CI 步驟 **「Agents — tool allowlist」** 會檢查 `core/**/agents/*.md`、`profiles/**/agents/*.md`、`profiles/**/_templates/agent-*.md`：
`tools` 必須是 `{Read, Grep, Glob}` 的子集；`Bash` 只有在內文有上述標記時才放行；唯讀的 scheduler MCP 工具（名稱以 `mcp__manufacturing-scheduler__` 開頭，例如 `mcp__manufacturing-scheduler__list_work_orders`）依前綴放行，其他 MCP server 的工具仍不允許（要新增前綴請另開 PR 改 CI `MCP_PREFIXES`）；標記存在但沒宣告 `Bash` 也算錯（避免殘留）。
要放寬 allowlist 請另開 PR 改 CI 並說明理由。

`extends:` 的 agent（§9）：CI 檢查的是 profile 檔本身的 `tools`；合併後預設與 core 的 list **union**，不會憑空多出權限。

---

## 7. 內容規則：不放真名、不放真價格、需驗證要標清楚

1. **不放真實的人名、客戶名、公司名、供應商名、品牌型號報價。** 用「範例公司」「甲客戶」「供應商 A」「某 OEM」。
   不要把你任職公司的機密（客戶規範、內部 SOP、報價歷史、良率數據）寫進來 —— 只用公開標準的摘要、一般業界通識、你自己重新整理的觀念。
   Agent prompt 也不要寫死公司名（`你是 ABC 公司的報價師` ❌ → `你是製造業報價師` ✅；公司客製請在你私有的 fork 做）。
2. **不放真實單價 / 報價 / 費率。** 需要數字來示範時用明顯的範例值，並標「（範例）」。
3. **「需驗證」標示法**（`pcb-assembly` / `food-processing` / `pharma` / `machinery-eto` 已經照這個做）：
   - **檔頭**：每個 agent / skill / hook / know-how 檔頭放一段 alpha 警語（可直接複製）：

     ```markdown
     > ⚠️ **Alpha**：本檔基於公開標準摘要與業界通識整理，**未經在職 <你的行業> 實務工作者驗證**。
     > 所有數字都是「範例」，法規與標準版次標「需驗證」。AI 輸出是草稿，簽核由人類負責。
     ```

   - **行內**：每個硬數字（工時、費率、比例、公差、溫度、期間、加成）寫成「（範例）」或「（範例，需驗證）」；
     每個法規 / 標準的條文、版次、適用日期、主管機關程序寫「（需驗證）」。標在**每一個**數字 / 條文旁，不要只在段落開頭標一次。
   - **`profile.json` 的 `warnings`**：至少 3 條，用 §3 範本的句型（未經驗證 / 數字是範例 / 法規需驗證 / AI 不簽核）。
   - 來源：有來源就寫在 know-how 的 `source:`；寫不出來源的數字就是「範例」。
4. **誠實限制：這條規則目前沒有 CI 自動掃描**（沒有人名 / 價格的 pattern 檢查）。審稿者會人工看；請自己再讀一次 diff。

---

## 8. 狀態模型：只有 alpha（沒有 stub 了）

| `status`   | 意思                                                         | 誰能設定                      |
| ---------- | ------------------------------------------------------------ | ----------------------------- |
| `alpha`    | 有真實內容（≥ 1 agent + 1 skill + 1–2 know-how）、標明需驗證 | **新 profile 一律從這裡開始** |
| `complete` | 在職實務工作者驗證過、可正式使用（目前只有 CNC）             | 只有 maintainer               |
| `stub`     | 舊的「半成品」狀態。**目前 0 個，不再接受新的 stub PR**      | —                             |

- 新 profile 不要寫 `"status": "stub"`，也不要先放空殼。內容還不夠就先不要 PR；做到 alpha 最低標準再送。
- 「profile 還在開發中」的警示用 `warnings` + README「還缺什麼」表達，不是靠 `stub`。
- alpha → complete 需要在職實務工作者驗證並由 maintainer 改狀態；請在 PR 描述附上驗證者背景（不需實名，寫職稱與年資）。

---

## 9. `README.md` 與 Override 規則

### profile 的 `README.md`

對照 `profiles/machinery-eto/README.md`：適合誰 / 這個 alpha 有什麼 / 做什麼與不做什麼 / 給不懂技術的同事怎麼用 / 還缺什麼（對應 `wantedContributions`）/ 如何貢獻。
不再使用 `manufacturing.md`（那是 CNC 當年的 overlay 說明檔，現行 alpha 都用 `README.md`）。

### Filename-based override（預設行為）

```text
core/agents/quote-specialist.md                     → core 預設
profiles/<your-vertical>/agents/quote-specialist.md → 同名檔 = 整份取代 core 版（install 時）
profiles/<your-vertical>/agents/<new-name>.md       → 新名字 = 純加（最安全）
```

**能用新檔名就用新檔名。** 同名覆寫 core 檔會佔用那個檔名：同時啟用的其他 profile 如果也覆寫同一個檔，install 會拒絕（§10）。

### 部分繼承 — `extends:`

不想為了加 20 行條款而複製整份 core agent？用 `extends:`。**`extends:` 的檔案仍須有完整必備 frontmatter（含 `model`）**，
因為 CI 的 frontmatter 檢查看的是 profile 裡的原始檔，不是合併後的結果：

```markdown
---
name: quote-specialist
description: 報價師（<你的行業>版）
model: sonnet
tools: [Read, Grep, Glob]
extends: core/agents/quote-specialist
---

<!-- inherit -->

## <你的行業> 特殊條款

- 範例：特殊工序的外發成本必須獨立列一行（範例，需驗證）
- 範例：首件檢驗需預留 1–2 個工作天（範例）
```

預覽合併結果（不寫進 `~/.claude/`）：

```bash
bash adapters/claude-code/install.sh --resolve <your-vertical>/agents/quote-specialist
```

| Directive                             | 用途                                                           |
| ------------------------------------- | -------------------------------------------------------------- |
| `<!-- inherit -->`                    | 在這個位置插入 core 的整份 body                                |
| `<!-- replace-section: <heading> -->` | 替換 core 中 `## <heading>` 那段（用下面的內容），其他段落保留 |
| `<!-- override-body -->`              | 不繼承 core body，profile 自己重寫整段（只繼承 frontmatter）   |

- 每個 `extends:` 檔**必須**恰好有 `<!-- inherit -->` 或 `<!-- override-body -->` 其中一個（不能兩個、不能都沒有）。
- Frontmatter 合併：scalar 欄位 profile 蓋過 core；list 欄位（`tools` `tags` ...）預設 union，要強制取代就加 `<field>-replace: true`。
- `extends:` 只支援 `agents` / `skills` / `know-how` / `hooks`，**不支援 `commands`**。
- `replace-section: X` 的 `X` 必須完全等於 core 檔裡某個 `## X` 標題（NFKC normalize 後比對）。core 側改標題時，CI（PR 才跑）會檢查有沒有 profile 還在引用。
- **目前 repo 裡沒有任何 profile 實際使用 `extends:`**；可跑的範例在 `tests/extends/case-*/`（`python3 tests/extends/run.py`）。
  你若是第一個，請在 PR 描述附上 `--resolve` 的輸出。

完整 spec：[docs/superpowers/specs/2026-05-08-profile-inheritance-design.md](superpowers/specs/2026-05-08-profile-inheritance-design.md)。

---

## 10. 多 profile 同時啟用：你的 profile 不能害別人裝不起來

使用者可以一次裝多個 profile：`bash adapters/claude-code/install.sh cnc-machining,injection-molding`。
你的 profile 要能和**任何其他已登記的 profile**共存。規則：

1. **同名檔衝突 = 拒絕安裝。** 兩個 active profile 若各有同名 `<kind>/<basename>.md`（含 hook），install.sh 直接拒絕（在備份前，不會毀掉現有安裝）。
   CI 的 **「Multi-profile — pairwise conflict scan」** 會把 `profiles.available` 內每一對都掃過 —— **前提是你有登記（§4）**。
2. **不得跨 profile `extends:`。** `profiles/A/...` 不能 extends `profiles/B/...`，也不能 import 對方。
   `extends:` 只能指向 `core/`。共用的東西放 `core/`（另開 PR 討論）。
3. **不要覆寫 core hook 的同名檔，除非你確定沒人要。** 目前 hook 檔名的擁有者：

   | Hook 檔名                 | 擁有者（profile） | 備註                                    |
   | ------------------------- | ----------------- | --------------------------------------- |
   | `pre-quote`               | `machinery-eto`   | 取代 core `pre-quote`（保留零件級檢查） |
   | `pre-ship`                | `food-processing` | 取代 core `pre-ship`（加食品放行要件）  |
   | `pre-cnc-program-checkin` | `cnc-machining`   | 純新增                                  |
   | `pre-batch-release`       | `pharma`          | 純新增（刻意不覆寫 `pre-ship`）         |

   你要加閘門就**用新名字**（例如 `pre-<你的閘門>`），像 pharma 那樣。覆寫 `pre-quote` / `pre-ship` / `post-order` / `on-error` 的 profile，
   在多 profile 情境下必定與已佔用的 profile 衝突。
4. **每個 profile 都各自覆寫 `agents/quote-specialist.md` ❌。** 那是 core 的職責；真的要客製就 `extends:`，並且知道同一個檔名只能有一個 profile 動它。
5. **跨 PR 的撞名只有合併後才爆。** 兩個 PR 各自單看都是綠的。送 PR 前請先 `git fetch origin && git merge origin/main`（或 rebase），
   再跑一次 `bash adapters/claude-code/install.sh --list-conflicts`（全 repo 所有 pair）。

自己試：

```bash
bash adapters/claude-code/install.sh --list-conflicts                                  # 全 repo 所有 pair（CI 跑的）
bash adapters/claude-code/install.sh --list-conflicts cnc-machining,<your-vertical>    # 指定組合
python3 tests/multiprofile/test_multiprofile.py                                        # helper 單元測試
```

範例輸出：

```text
::error::hooks/pre-quote.md present in multiple profiles: machinery-eto, your-vertical
1 file collision(s) across 2 profiles
```

多 profile install 後會多一個 `~/.claude/plugins/manufacturing-skill/active-profiles.json`（`primary`、`profiles[]`、
list 欄位 union 後的 `aggregated`：`tags` `applicableTo` `complianceFrameworks` `wantedContributions` `warnings` ...）。
所以你的 `warnings` 會和其他 profile 的合併顯示給使用者。
完整 spec：[docs/superpowers/specs/2026-05-09-multi-profile-active-design.md](superpowers/specs/2026-05-09-multi-profile-active-design.md)。

---

## 11. 必改清單（新 profile 一共要動這些地方）

| #   | 檔案                                                                                  | 要改什麼                                                                                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `profiles/<name>/`（`profile.json`、`README.md`、內容檔）                             | §2 – §8                                                                                                                                                                                                               |
| 2   | `plugin.json`                                                                         | `profiles.available` + `profiles.alpha`（§4）                                                                                                                                                                         |
| 3   | `docs/explainers/01-架構總覽.html` — **自動區**                                       | `python3 scripts/regen_explainers.py`（統計面板的 agents / skills / know-how / hooks / profiles 數字）                                                                                                                |
| 4   | `docs/explainers/01-架構總覽.html` — **手改區**                                       | ROLE（agents）、REF（know-how）、HOOK（hooks）三列：每個你的內容加一個 `<div class="item alpha">…</div>`，並更新該列標籤的 `alpha α N`；圖例的 Alpha 名單也加上你。skills 沒有 row。CI「Explainer 01 — overlay rows vs stat panel」會比對 |
| 5   | `INVENTORY.md`                                                                        | 你的 profile 區塊（Manifest / Agents (n) / Skills / Know-how / Hooks / 預留範本）、檔案統計                                                                                                                           |
| 6   | `README.md`                                                                           | Profile layer 說明、「Three paths」第 2 點、Repo tree、Contributing 列舉                                                                                                                                              |
| 7   | `README.zh-TW.md`                                                                     | 同上（說明、Repo 結構、「不是 CNC 廠也能用嗎」）                                                                                                                                                                      |
| 8   | `core/commands/install-profile.md`                                                    | profile 表加一列                                                                                                                                                                                                      |
| 9   | `core/commands/init.md`                                                               | 問題 1 的選項加一列                                                                                                                                                                                                   |
| 10  | `.github/ISSUE_TEMPLATE/bug-report.yml`                                               | 「Active profile」下拉加你的 profile 名                                                                                                                                                                               |
| 11  | `.github/ISSUE_TEMPLATE/profile-contribution.yml`                                     | 「Which vertical?」下拉：把 `(new)` 改成 `(currently alpha)`，名稱與資料夾名一致                                                                                                                                      |
| 12  | `docs/quickstart-for-beginners.zh-TW.md` + `docs/explainers/04-懶人包-5分鐘上手.html` | 安裝選單範例（兩處都要；順序是資料夾字母序，編號與 `Select [0-N]` 一起改）                                                                                                                                            |
| 13  | `CHANGELOG.md`                                                                        | `## [Unreleased]` 下加 `### Added`（新 profile）／`### Changed`（改到的既有檔案）各一至數行，英文、一行一事                                                                                                           |

提醒：

- **先 #3 再 #4**：先 regen 看統計數字，手改的 row 要等於它。
- `CHANGELOG.md` 每個 PR 都改同一區塊，容易衝突；解衝突時兩邊都留，`### Added` / `### Changed` 標題不要重複。
- 計數類（INVENTORY、README 的「N 隻 agent」）是手寫的，改完請 `grep -rn` 一下舊數字。
- 若你自己加了 `_templates/agent-starter.md`，`tools` 必須是 `[Read, Grep, Glob]`，而且不要放指向其他檔案的相對連結（連結檢查會掃到）。

---

## 12. 本機重跑 CI（提 PR 前一定要做）

CI 只有一個 job（`.github/workflows/ci.yml`）。把它的 `run:` 全部依序抽出來，用和 GitHub 一樣的 `bash -e -o pipefail` 跑：

```bash
pip install --quiet pyyaml
python3 - <<'PY'
import subprocess, sys, yaml
steps = yaml.safe_load(open(".github/workflows/ci.yml", encoding="utf-8"))["jobs"]["validate"]["steps"]
failed = []
for s in steps:
    if "run" not in s:
        continue
    if "if" in s:   # 只在 pull_request 事件才跑（core 標題錨點保護）
        print(f"SKIP  {s['name']}   (if: {s['if']})")
        continue
    r = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", s["run"]])
    print(f"{'PASS' if r.returncode == 0 else 'FAIL'}  {s['name']}")
    if r.returncode:
        failed.append(s["name"])
print("\nFAILED:" if failed else "\nall steps passed", *failed, sep="\n  ")
sys.exit(1 if failed else 0)
PY
```

「PR 才跑」那一步（`Profile extends — core heading-anchor protection`）只在你改了 `core/*/*.md` 的 `## ` 標題時才有意義，會被跳過；
改 core 標題時請手動跑 `python3 adapters/claude-code/_resolve_extends.py --repo-root . lint-anchors <core 檔> "<標題>"`。

CI 步驟對照（失敗時看步驟名就知道去哪修）：

| 步驟名                                                            | 擋什麼                                                                |
| ----------------------------------------------------------------- | --------------------------------------------------------------------- |
| JSON syntax validation                                            | 任何 `.json` 語法錯                                                   |
| plugin.json schema sanity                                         | `plugin.json` 缺頂層欄位                                              |
| Profile manifests vs filesystem                                   | `available` 的 profile 缺 `profile.json`、manifest 列了不存在的檔     |
| Agent / command markdown frontmatter                              | agent 缺 `name description model`；skill 缺 `name description`        |
| install.sh syntax / no bash 4+ syntax                             | 安裝腳本語法與 bash 3.2 相容                                          |
| profile.json schema sanity                                        | §3 的 11 個必填欄位、list / boolean 型別                              |
| Profile filesystem vs manifest (orphan check)                     | 資料夾裡有 `.md` 卻沒列進 `profile.json`                              |
| Markdown internal link check                                      | 壞掉的相對連結                                                        |
| Profile extends — resolver fixtures / lint                        | `extends:` 的路徑、模式標記、replace-section 標題、合併後 frontmatter |
| Explainer auto-sections — drift check                             | 統計面板沒 regen                                                      |
| Multi-profile — pairwise conflict scan / helper unit tests        | 已登記 profile 之間同名檔                                             |
| Profiles — every profiles/&lt;dir&gt; is registered in plugin.json | 資料夾沒登記、`status` 與清單不一致（§4）                             |
| Agents — tool allowlist                                           | `tools` 超出 `Read/Grep/Glob`（`mcp__manufacturing-scheduler__*` 除外）、`Bash` 沒有理由標記（§6） |
| Explainer 01 — overlay rows vs stat panel                         | 手改的 overlay row / 標籤與統計面板數字不一致（§11 #4）               |

除了 CI，PR 前建議再跑：

```bash
bash adapters/claude-code/install.sh --list-conflicts           # 全 repo pairwise
bash adapters/claude-code/install.sh --resolve <p>/<kind>/<f>   # 有用 extends 才需要
```

---

## 13. 常見錯誤

- **直接改 `core/`** ❌ — 只是要客製給自己用，**不要**改 `core/`，改 profile。core 的改動會影響所有 profile 的使用者，需另開 PR 討論；core 改標題還會被錨點保護擋。
- **沒登記 `plugin.json`** ❌ — 其他 CI 步驟會悄悄略過你的 profile（§4）。
- **`profile.json` 缺 `applicableTo` / `description` / `hooks`** ❌ — CI 必填（§3）。沒有 hook 也要寫 `"hooks": []`。
- **`extends:` 檔缺 `model`** ❌ — §9。合併後才有的欄位不算數，原始檔要自己有。
- **agent 宣告 `Bash` / `WebFetch`** ❌ — §6。起手用 §5 的範例，不要從舊檔複製 `Bash`。
- **Agent prompt 寫死公司名、放真實單價與人名** ❌ — §7。
- **Profile 之間互相 import / extends** ❌ — 不允許 `profile-A` 引用 `profile-B`。要共用的東西放 `core/`。
- **只寫 agent 沒寫 know-how** ❌ — agent prompt 引用 `know-how/` 是預期的；沒對應的 know-how → agent 答得空泛。
- **寫 `"status": "stub"`** ❌ — §8：沒有 stub 了。

---

## 14. Vertical-specific 內容範例

不同 vertical 的 know-how 重點（你的行業沒在表裡就是機會）：

| Vertical          | 必備 know-how                             |
| ----------------- | ----------------------------------------- |
| CNC machining     | 切削參數, 刀具壽命, GD&T（IATF 在 core）  |
| PCB assembly      | IPC-A-610, J-STD-001, MSL, ESD            |
| Injection molding | 模流分析, 常見不良對策, polymer 資料庫    |
| Food              | HACCP, ISO 22000, 過敏原管理, 保存期      |
| Pharma            | GMP, ICH Q-series, 21 CFR Part 11, ALCOA+ |
| Machinery ETO     | 規格凍結, CE / 機械安全, FAT / SAT, 售後  |
| Sheet metal       | 折彎工藝, 沖壓力計算, 板材 nesting        |
| Mold making       | 模具設計原則, 鋼料選擇, 熱處理            |

---

## 15. 貢獻流程（PR 回來）

1. Fork `https://github.com/jason-simhope-ai/manufacturing-skill`
2. 照 §2 – §10 建你的 profile
3. 加幾個 example file 到 `examples/`（合成資料、不要客戶機密）— 可選
4. 照 §11 更新所有清單
5. 照 §12 本機重跑 CI，全綠再送
6. 提 PR：
   - Title: `feat(profile): add <vertical> profile`
   - Body: 這個 profile 對應什麼產業、貢獻者背景（職稱 / 年資即可）、合規範圍、你有 / 沒有驗證什麼
7. 我會 review、可能要求改、然後合進去

---

## 16. 商業協作（私下開發 profile）

如果你的 profile 有商業價值不想開源：

- Fork 整個 repo 為私 repo（MIT 允許）
- 自己內部用 / 賣給客戶
- 不需要 PR 回來

如果你想雇人開發 profile：

- 找有該 vertical 經驗 + 寫過 AI agent prompt 的人
- 預算參考：1 個完整 profile = 4-8 週工作量
- 或聯絡 [Jason Lin](mailto:jasonlin@simhope.com.tw) 詢問顧問服務

---

## 17. 常見問題

**Q: profile 和 plugin 有什麼差別？**
A: plugin = 整個 manufacturing-skill（core + 多個 profile）。profile = 一個 vertical（CNC / 食品 / ...）的 overlay 包。

**Q: 一次能裝多個 profile 嗎？**
A: 可以。`bash adapters/claude-code/install.sh cnc-machining,injection-molding`；只要沒有同名檔衝突（§10）。橫跨多個 vertical 的工廠（CNC + 板金、EMS + 塑膠殼）就是這樣用。

**Q: profile 多大算合理？**
A: alpha 起手 1 agent + 1 skill + 1–2 know-how；現有 alpha 是 1–3 個 agent。CNC profile：~ 4 agents + 3 skills + 3 know-how + 1 hook，約 50KB markdown。太大表示應該拆。

**Q: profile 一定要寫繁中嗎？**
A: agent prompt 與 know-how 預設繁中（台灣製造業情境）。國際 contributor 可寫英文，但建議至少 README 提供繁中翻譯方便台灣用戶。
