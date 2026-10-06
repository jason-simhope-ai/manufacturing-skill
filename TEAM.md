# TEAM — 數位分身團隊（agent 啟動檔）

> 本檔給 agent 讀。人類請從 [team/README.zh-TW.md](team/README.zh-TW.md) 開始。

## 1. 一句話

每個「職位」有一個常駐聊天工作區的副駕分身：人保留判斷，分身補資料、挑戰假設、定時提醒。**副駕不是替身。** Alpha 只到 `observe / suggest / draft`，沒有任何寫入工具。

## 2. 六條不可違反的規則

1. **三分類**：每項能力必標 `strengthen`（強化既有優勢）、`create`（創造新能力）或 `outsource`（外包既有工作），並寫 `today`（今天誰在做）、`affectedRoles`、`humanStillDoes`（上線後人還親手做什麼）；未標註是硬錯誤，做事的人不是本職位要 `doerAckedOn`。outsource 在分身檔必須 `dormant: true`，只能由 roster opt-in：每分身 ≤ 1 項、上限 `draft`、90 天內複審、要求 teach-back 與人工練習（自報，無程式強制）。lint 只查結構，不查標得對不對。
2. **決策點交還人**：遇到 `decisionPoints` 或 `decisionRights` 就停下來，列選項與取捨，不替人選。
3. **分級**：T0 公開、T1 內部、T2 機密、T3 受管制或客戶要求保密的專案資料；Slack／Discord 與雲端模型上限 T1，T2 僅本機 mock。拿不準就往上一級。
4. **T3 兩道防線，都不是內容理解**：roster 含 T3 頻道或分身 → 啟動即拒載（gateway exit 3）；輸入含 T3 字樣（DLP 關鍵字）→ 擋下、不送模型、提示改走公司 T3 程序。T3 也不得出現在任何追蹤檔。不要對人說「T3 一律不處理」。
5. **不冒充**：分身永遠標明身分，不代簽名、不對外發送、不評比個人。
6. **不放真名與 secret**：repo 只有職稱、`incumbent: LOCAL|VACANT` 與 `synthetic: true` 的合成資料。secret **只放環境變數**，任何檔案都不放；真名、平台 id、客戶名只放 `team/local/*`（gitignored）。CI 只掃追蹤檔，`team/local` 靠本機 pre-commit。

## 3. 啟動演算法

前置：Python 3.11+、`pip install pyyaml`（缺少時 teamctl exit 2）。`$ROOT`＝本檔所在目錄，須是 repo clone（有 `infra/`）；讀到的是 `~/.claude/plugins/` 安裝副本（不含 `infra/`，工具跑不起來）→ `$ROOT` 改用其 `.installed` 的 `source`。下列路徑都相對 `$ROOT`，執行時換成絕對路徑。

```
1. python3 "$ROOT/team/tools/teamctl.py" check    # 有任何 E 碼 → 停止並回報；不要自行修改 roster 或分身檔
2. python3 "$ROOT/team/tools/build.py" --summary  # 預設讀 team/local/roster.local.yaml，沒有就讀 example（demo 模式，強制 mock）；寫入 team/.build/（唯讀 checkout 加 --out DIR）
3. 讀 team/.build/roster.json 與 team/policies/core-rules.md；不要讀其他分身檔
4a. /team status → /team ask <twin> <問題>        # 只有跑過 adapters/claude-code/install.sh 才有 /team；否則讀 core/commands/team.md 照做。預覽不是控制邊界
4b. python3 "$ROOT/infra/chat-gateway/demo.py"    # 回覆是預錄，不是模型推論，不能當「分身運作正常」的證據
4c. cd "$ROOT" && MFG_TEAM_STATE_DIR=$(mktemp -d) PYTHONPATH="$ROOT/infra/chat-gateway" python3 -m chat_gateway run --adapter mock --driver mock
    # REPL 每行：<頻道> <使用者> @<分身> <訊息>，例 qa-floor mock-qa-manager @品保 …；無 identities 時自動合成使用者 mock-<職位 id>
    # 被拒的訊息印 (no reply: policy_denied …)；回覆為預錄；Ctrl-D 結束（非互動請改用 --script FILE.jsonl）
```

**完成定義**：步驟 1–2 無 E 碼、4b 印出 `audit verify: OK`、4c 收到一則預錄回覆與一則 policy_denied 提示，然後回報「本機 mock 驗證完成」。接真實 Slack／Discord 與 `claude -p` 要人做（建 bot、設環境變數、核准 pilot），不得宣稱「已上線」。

## 4. 漸進揭露地圖

| 需要 | 讀 |
| ---- | -- |
| 誰、哪些頻道、能做到哪 | `team/.build/roster.json`（由 `build.py` 產生） |
| 所有分身共用的規則 | [team/policies/core-rules.md](team/policies/core-rules.md) |
| 某個分身的職責與能力 | `team/twins/<id>.md`（只在被要求時讀） |
| 新增職位或分身 | [team/twins/_template.md](team/twins/_template.md)、[team/gate/need-a-twin.md](team/gate/need-a-twin.md) |
| 前線同仁的一頁說明 | [team/for-frontline.zh-TW.md](team/for-frontline.zh-TW.md) |
| T3 政策 | [team/policies/restricted.md](team/policies/restricted.md) |
| 範例 roster／本機設定 | [team/roster.example.yaml](team/roster.example.yaml)、`team/local/README.md` |
| 接真平台、資安、導入步驟 | [gateway README](infra/chat-gateway/README.md)、[SECURITY.md](SECURITY.md)、[adoption-guide 團隊段](docs/adoption-guide.md) |
| 完整設計（67 KB，勿預先讀） | [設計 spec](docs/superpowers/specs/2026-10-05-digital-twin-team-design.md) |

Bytes 預算：本檔 ≤ 6,000 B；冷啟動（本檔 + 範例 roster + core-rules + build 摘要）≤ 18,432 B。

## 5. 什麼時候停下來問人

- `teamctl check` 出現任何 `E` 碼：回報錯誤碼與檔案，不要自行修。
- 要新增分身、改 autonomy、喚醒 outsource：先過閘門（`team/gate/need-a-twin.md`），需要人核准。
- 內容像是 T3，或看到真名、平台 id、token：立刻停止，不要複製、不要寫進任何檔案。
- 使用者要求跳過決策點、放寬分級或「以後都你決定」：拒絕並說明原因。
- 不確定資料等級：往上一級並詢問。
- **需要憑證**：請人在 shell 設環境變數，不要請人把 token 貼進對話、檔案或指令列，你也不讀取、回顯或寫入它。變數名：`MFG_TEAM_SLACK_BOT_TOKEN`、`MFG_TEAM_SLACK_APP_TOKEN`、`MFG_TEAM_DISCORD_TOKEN`、`ANTHROPIC_API_KEY`、`MFG_TEAM_AUDIT_HMAC_KEY`、`MFG_TEAM_APPROVAL_HMAC_KEY`。
