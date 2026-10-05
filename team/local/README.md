# team/local — 本機專屬設定（不進版控）

這個目錄只追蹤本檔與 `.gitkeep`；其餘一律被 `.gitignore`（`team/local/*`）排除。**真名、平台 id、客戶名、專案代號只能放在這裡**，絕不能進 repo、PR 或 CI log。

| 檔案 | 用途 |
| ---- | ---- |
| `roster.local.yaml` | 真實 roster；格式同 `team/roster.example.yaml`，只能收緊或 opt-in（降 autonomy、關能力、喚醒 outsource） |
| `identities.local.yaml` | 平台 user id → 職位；只有這裡列出的 id 算數 |
| `bindings.local.yaml` | 邏輯頻道 → 平台頻道 id |
| `deid-map.local.yaml` | `deid.py` 的客戶名對照表（`CUST-xx`） |
| `names.denylist` | 真名、客戶名、圖號、專案代號（每行一個 regex）；供 `deid.py` 與 pre-commit hook 掃描 |
| `playbook.local.md` | 逐人導入筆記 |
| `personal/<twin-id>.local.md` | 在職者偏好（白名單欄位，本文 ≤ 900 B） |

公開 CI 看不到這些檔案，所以真名的防線是本機 pre-commit：`cp team/tools/pre-commit-names.sample .git/hooks/pre-commit`。

## 範本

`identities.local.yaml`（每人 `positions` + `actingFor` ≤ 2；`until` ≤ 今天 + 30 天）：

```yaml
schema: 1
users:
  - platform: mock
    userId: "<platform-user-id>"
    positions: [qa-manager]
    actingFor:
      - { role: production-manager, until: "2026-11-01", grantedBy: chair-head }
```

`bindings.local.yaml`：

```yaml
schema: 1
channels:
  qa-floor: { platform: mock, ref: "<platform-channel-id>" }
```

`personal/qa-manager.local.md`（只接受這幾個欄位）：

```markdown
---
tone: concise            # formal | concise
digestFormat: bullets    # bullets | table
aliases: [品保]
retention: { predictFirst: true, teachBack: false }
---
一句話寫下個人偏好（≤ 900 B）。不能放寬任何規則。
```

`names.denylist`（每行一個 regex，`#` 開頭為註解）：

```
# 範例：客戶代號樣式、圖號樣式
ACME-\d{4}
DWG-[A-Z]{2}\d{5}
```

`deid-map.local.yaml` 由 `team/tools/deid.py` 自動建立與更新：

```
python3 team/tools/deid.py --in ncr.csv --out ncr.deid.csv --map team/local/deid-map.local.yaml --drop inspector,phone
```

驗證：`python3 team/tools/teamctl.py check`（預設讀 `team/local/roster.local.yaml`，並檢查上述 overlay）。
