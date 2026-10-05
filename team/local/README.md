# team/local — 本機專屬設定（不進版控）

這個目錄只追蹤本檔與 `.gitkeep`；其餘一律被 `.gitignore`（`team/local/*`）排除。**真名、平台 id、客戶名、專案代號只能放在這裡**，絕不能進 repo、PR 或 CI log。

| 檔案 | 用途 |
| ---- | ---- |
| `roster.local.yaml` | 真實 roster；格式同 `team/roster.example.yaml`，只能收緊或 opt-in（降 autonomy、關能力、喚醒 outsource） |
| `identities.local.yaml` | 平台 user id → 職位；只有這裡列出的 id 算數 |
| `bindings.local.yaml` | 邏輯頻道 → 平台頻道 id |
| `deid-map.local.yaml` | `deid.py` 的客戶名對照表（`CUST-xx`） |
| `names.denylist` | 真名、客戶名、圖號、專案代號（每行一個 Python regex）；供 `deid.py`、pre-commit hook 與 gateway（輸入 DLP、輸出過濾、資料夾掃描）使用。一般行命中視為 T2，`T3:` 開頭的行命中視為 T3。起始內容可從 `team/tools/denylist.starter.txt` 複製 |
| `playbook.local.md` | 逐人導入筆記 |
| `personal/<twin-id>.local.md` | 在職者偏好（白名單欄位，本文 ≤ 900 B） |

**token、金鑰也不放這裡**：只放環境變數（`MFG_TEAM_*`、`ANTHROPIC_API_KEY`），gateway 看到設定檔裡像 token 的內容會拒絕啟動（exit 78）。分身要讀的排程／NCR 資料放在 repo 外的資料夾（`MFG_TEAM_DATA_T1`），做法見 [team/README.zh-TW.md](../README.zh-TW.md) 的「資料餵入」。

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
# 範例：客戶代號樣式、圖號樣式（命中視為 T2）
ACME-\d{4}
DWG-[A-Z]{2}\d{5}
# 命中視為 T3（和內建 T3 字詞一樣擋下）：高安規專案代號
T3:PRJ-SP\d{3}
```

先放通用起始清單，再加自己的：`cat team/tools/denylist.starter.txt >> team/local/names.denylist`。起始清單補的是內建字詞擋不到的中英同義詞與金額寫法（pilot 審查的 7 句實測句子，沒載入時全部通過、載入後全部擋下）；它仍是字詞告警，誤擋時改寫該行的排除條件，每季覆核一次。

`deid-map.local.yaml` 由 `team/tools/deid.py` 自動建立與更新。**來源匯出檔與輸出檔都放在 repo 外**（`/tmp` 或 `$MFG_TEAM_DATA_T1`），不要放在 clone 裡；對照表放 `team/local/`（已被 `.gitignore` 擋）：

```
export EXPORT=/tmp/ncr-export && mkdir -p -m 700 "$EXPORT"      # 來源檔 ncr.csv 也放這裡，用完刪除
python3 team/tools/deid.py --in "$EXPORT/ncr.csv" --out "${MFG_TEAM_DATA_T1:-$EXPORT}/ncr.deid.csv" \
    --map team/local/deid-map.local.yaml --drop inspector,phone \
    --partno-pattern 'DWG-[A-Z]{2}\d{5}'      # 你自己的圖號／料號樣式；不給就不掃圖號
```

跑完會印出「掃了什麼、沒掃什麼」：有沒有載入 denylist、載入幾行（沒有會警告）、圖號是否掃描，並提醒你抽查至少 10 列。`residual hits=0` 只代表「已掃的樣式沒命中」，不是「乾淨」。`.gitignore` 另外擋 `*.deid.csv` 與 `team/local/**/*.csv` 作為最後防線，但不要靠它。

驗證：`python3 team/tools/teamctl.py check`（預設讀 `team/local/roster.local.yaml`，並檢查上述 overlay）。
