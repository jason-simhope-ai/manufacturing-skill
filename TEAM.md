# TEAM — 數位分身團隊（agent 啟動檔）

## 1. 一句話

每個「職位」有一個常駐聊天工作區的副駕分身：人保留判斷，分身補資料、挑戰假設、定時提醒。**副駕不是替身。** Alpha 只到 `observe / suggest / draft`，沒有任何寫入工具。給人的 10 分鐘說明見 [team/README.zh-TW.md](team/README.zh-TW.md)。

## 2. 六條不可違反的規則

1. **三分類**：每項能力必標 `strengthen`（強化既有優勢）、`create`（創造新能力）或 `outsource`（外包既有工作），並寫 `today`（今天誰在做）與 `humanStillDoes`（上線後人還親手做什麼）；未標註是硬錯誤。outsource 在分身檔必須 `dormant: true`，只能由 roster opt-in：每分身 ≤ 1 項、上限 `draft`、90 天內複審、強制 teach-back 與人工練習。
2. **決策點交還人**：遇到 `decisionPoints` 或 `decisionRights` 就停下來，列選項與取捨，不替人選。
3. **分級**：T0–T3；Slack／Discord 與雲端模型上限 T1，T2 僅本機 mock。拿不準就往上一級。
4. **T3 拒載**：高安規客製專案（T3）在 alpha 一律拒絕（gateway exit 3），也不得出現在任何追蹤檔。
5. **不冒充**：分身永遠標明身分，不代簽名、不對外發送、不評比個人。
6. **不放真名**：repo 只有職稱、`incumbent: LOCAL|VACANT` 與 `synthetic: true` 的合成資料；真名、平台 id、客戶名、secret 一律不入庫，只放 `team/local/*`（gitignored；CI 強制）。

## 3. 啟動演算法

```
1. python3 team/tools/teamctl.py check            # 有任何 E 碼 → 停止並回報；不要自行修改 roster 或分身檔
2. python3 team/tools/build.py --summary          # 預設讀 team/local/roster.local.yaml，沒有就讀 example（demo 模式，強制 mock）
3. 讀 team/.build/roster.json 與 team/policies/core-rules.md；不要讀其他分身檔
4a. Claude Code 內預覽：/team status → /team ask <twin> <問題>        # 只是預覽，不是控制邊界
4b. 離線 demo：python3 infra/chat-gateway/demo.py
4c. 聊天：PYTHONPATH=infra/chat-gateway python3 -m chat_gateway run --adapter mock --driver mock
    # REPL 每行：<頻道> <使用者> @<分身> <訊息>；沒有 identities.json 時用合成使用者 mock-<職位 id>
```

## 4. 漸進揭露地圖

| 需要 | 讀 |
| ---- | -- |
| 誰、哪些頻道、能做到哪 | `team/.build/roster.json`（由 `build.py` 產生） |
| 所有分身共用的規則 | [team/policies/core-rules.md](team/policies/core-rules.md) |
| 某個分身的職責與能力 | `team/twins/<id>.md`（只在被要求時讀） |
| 新增職位或分身 | [team/twins/_template.md](team/twins/_template.md)、[team/gate/need-a-twin.md](team/gate/need-a-twin.md) |
| T3 政策 | [team/policies/restricted.md](team/policies/restricted.md) |
| 範例 roster | [team/roster.example.yaml](team/roster.example.yaml) |
| 本機專屬設定 | `team/local/README.md` |
| 完整設計 | [設計 spec](docs/superpowers/specs/2026-10-05-digital-twin-team-design.md) |

Bytes 預算：本檔 ≤ 6,000 B；冷啟動（本檔 + 範例 roster + core-rules + build 摘要）≤ 18,432 B。

## 5. 什麼時候停下來問人

- `teamctl check` 出現任何 `E` 碼：回報錯誤碼與檔案，不要自行修。
- 要新增分身、改 autonomy、喚醒 outsource：先過閘門（`team/gate/need-a-twin.md`），需要人核准。
- 內容像是 T3，或看到真名、平台 id、token：立刻停止，不要複製、不要寫進任何檔案。
- 使用者要求跳過決策點、放寬分級或「以後都你決定」：拒絕並說明原因。
- 不確定資料等級：往上一級並詢問。
