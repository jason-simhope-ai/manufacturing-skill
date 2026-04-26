# Profile Development — 怎麼長一個新 Vertical Profile

> 給「想為自己的工廠 / 客戶 / 社群 contribute 一個新 profile」的人看。

---

## 為什麼會需要新 profile

`manufacturing-skill` v1 完整支援 CNC machining。但你可能是：

- PCB 組裝廠
- 射出成型廠
- 食品廠
- 製藥廠
- 板金 / 沖壓
- 模具製造
- 紡織
- 化工
- 客戶有特殊體系（醫材 ISO 13485、航太 AS9100、油氣 API）

每個 vertical 有自己的 agent、skill、know-how、合規要求。`profiles/<your-vertical>/` 就是 overlay 它們的地方。

---

## 5 步驟長新 profile

### Step 1. Fork CNC profile 當起點

```bash
cp -r profiles/cnc-machining profiles/<your-vertical>
cd profiles/<your-vertical>
```

CNC profile 是最完整的範本。先 fork、再改。

### Step 2. 改 `profile.json`

```json
{
  "name": "your-vertical",
  "displayName": "你的領域中文名",
  "displayNameEn": "Your Vertical (English)",
  "version": "0.1.0",
  "extends-core": true,
  "agents": ["..."], // 列出你會放的 agents
  "skills": ["..."], // 列出你會放的 skills
  "knowHow": ["..."], // 列出你會放的 know-how
  "complianceFrameworks": ["..."], // 你領域的合規體系
  "tags": ["..."]
}
```

### Step 3. 改 `manufacturing.md`（profile 級的 overlay 說明）

寫清楚這個 profile：

- 解決什麼問題
- 在 core 上面加 / 改了什麼
- 適合誰用
- 不適合誰用

### Step 4. 改 / 加 agents / skills / know-how

對每個 vertical-specific 的角色 / 技能 / 知識，新增對應檔案。**保留 frontmatter 格式**（`name`, `description`, `model`, `tools` 等），這樣 Claude Code 才認得。

如果你的 vertical 不需要某個 core agent（如純量產廠不需要 `prototype-coordinator`），有兩種處理：

- (a) 留著但寫 prompt 「在純量產情境不要 dispatch 我」
- (b) 在 `profile.json` 的 `overrides.removed: ["prototype-coordinator"]` 標明（v0.2 計畫支援）

### Step 5. 改 hook（如有需要）

每個 vertical 有不同的「閘門」與「通知」需求。Examples：

- 食品廠：`pre-batch-release` hook 強制 HACCP CCP 全通過
- 製藥：`pre-batch-release` hook 強制 QA 簽認
- PCB：`pre-smt-line-start` hook 強制錫膏量檢查通過

放在 `profiles/<your-vertical>/hooks/`。

---

## 常見錯誤

### ❌ 直接改 core/

如果你只是要 customize 給自己用，**不要**改 core/。改 profile/。
理由：core/ 改了會被未來 plugin 升級覆蓋；profile/ 是你的領域不會。

### ❌ Agent prompt 寫死公司名

```
# 不要這樣
"你是 ABC 公司的報價師..."

# 改成
"你是製造業報價師..."  # 通用
# 然後在公司客製層用 ABC-specific overrides
```

### ❌ Profile 之間互相 import

不允許 `profile-A` 引用 `profile-B`。要共用的東西放 `core/`。

### ❌ 只寫 agent 沒寫 know-how

agent prompt 引用 `know-how/` 是預期的。沒對應的 know-how → agent 答得空泛。

### ❌ 忘記寫 stub 警告

如果你的 profile 還在開發中，在 `profile.json` 加 `"status": "stub"`、在 README.md 標明「WIP」，避免使用者誤裝。

---

## Override 規則（詳細）

### Filename-based override

```
core/agents/quote-specialist.md           → 預設
profiles/cnc-machining/agents/quote-specialist.md  → override
```

`bash adapters/claude-code/install.sh cnc-machining` 後，`~/.claude/plugins/manufacturing-skill/agents/quote-specialist.md` = profile 版。

### 加碼

```
profiles/cnc-machining/agents/cnc-programmer.md  → 純加（core 沒這隻）
```

### 部分內容繼承（v1 暫不支援，v0.2 計畫）

未來會支援在 profile agent prompt 開頭寫：

```markdown
<!-- extends: core/agents/quote-specialist.md -->

[在這裡只寫差異 / 加碼內容]
```

v1 先靠完整檔案 override。

---

## Profile 命名規範

- 全小寫、`-` 分隔（不用 `_` 或 camelCase）
- 描述性、不要簡寫太狠
- 範例：
  - ✅ `cnc-machining`、`pcb-assembly`、`injection-molding`、`food-processing`
  - ❌ `cnc`、`pcb`、`food`、`injection`

---

## Vertical-specific 內容範例

不同 vertical 的 know-how 重點：

| Vertical          | 必備 know-how                             |
| ----------------- | ----------------------------------------- |
| CNC machining     | IATF 16949, 切削參數, 刀具壽命, GD&T      |
| PCB assembly      | IPC-A-610, J-STD-001, MSL, ESD            |
| Injection molding | 模流分析, 常見不良對策, polymer 資料庫    |
| Food              | HACCP, ISO 22000, 過敏原管理, 保存期      |
| Pharma            | GMP, ICH Q-series, 21 CFR Part 11, ALCOA+ |
| Sheet metal       | 折彎工藝, 沖壓力計算, 板材 nesting        |
| Mold making       | 模具設計原則, 鋼料選擇, 熱處理            |

---

## 貢獻流程（如果想 PR 回來）

1. Fork `https://github.com/jason-simhope-ai/manufacturing-skill`
2. 建你的 profile 在 `profiles/<your-vertical>/`
3. 加幾個 example file 到 `examples/`（合成資料、不要客戶機密）
4. 更新主 README 的 profile 表格
5. 提 PR：
   - Title: `feat(profile): add <vertical> profile`
   - Body: 描述這個 profile 對應什麼產業、貢獻者背景、合規範圍
6. 我會 review、可能要求改、然後合進去

---

## 商業協作（私下開發 profile）

如果你的 profile 有商業價值不想開源：

- Fork 整個 repo 為私 repo（MIT 允許）
- 自己內部用 / 賣給客戶
- 不需要 PR 回來

如果你想雇人開發 profile：

- 找有該 vertical 經驗 + 寫過 AI agent prompt 的人
- 預算參考：1 個完整 profile = 4-8 週工作量
- 或聯絡 [Jason Lin](mailto:jasonlin@simhope.com.tw) 詢問顧問服務

---

## 常見問題

**Q: profile 和 plugin 有什麼差別？**
A: plugin = 整個 manufacturing-skill（core + 多個 profile）。profile = 一個 vertical（CNC / 食品 / ...）的 overlay 包。

**Q: 一次能裝多個 profile 嗎？**
A: v1 一次只能 active 一個 profile。如果你的工廠橫跨多個 vertical（如同時做 CNC + 板金），建議：

- (a) 開兩個 plugin 安裝目錄，分別 active 不同 profile
- (b) 自製 hybrid profile 把兩種都包進去
- (c) 等 v0.2 預計支援多 profile 同時 active

**Q: profile 多大算合理？**
A: 參考 CNC profile：~ 4 agents + 3 skills + 4 know-how + 1 hook，約 50KB markdown。太大表示應該拆。

**Q: profile 一定要寫繁中嗎？**
A: agent prompt 與 know-how 預設繁中（台灣製造業情境）。國際 contributor 可寫英文，但建議至少 README 提供繁中翻譯方便台灣用戶。
