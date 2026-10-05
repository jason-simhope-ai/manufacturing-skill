# 停機與外洩處置 runbook（twin gateway，pilot 用）

一頁版。出事時照順序做，**先停再查**。每一步做完在「處置紀錄」寫下時間與執行人。
部署方式見 [DEPLOY.md](DEPLOY.md)；稽核日常作業見 [docs/audit-operations.md](../../docs/audit-operations.md)。

## 什麼時候啟動

任一項發生就啟動，不必等確認：

- T2／T3 內容出現在分身頻道或分身回覆（含 `dlp_blocked` 以外的人工發現）。
- `audit-verify` 失敗，或 `--anchor` 比對失敗。
- 出現未核准的 Slack scope、app 或頻道成員；gateway 因 scope 檢查拒絕啟動（exit 78）。
- token、API key 或 HMAC 金鑰可能外流（貼進聊天、commit、截圖、工作站遺失）。
- 廠商條款變更、或主管要求暫停。

## 0. 先凍結（1 分鐘內，任何有 sudo 的管理員）

用**和部署單元相同**的那一種（DEPLOY.md 第 3 節；預設是固定帳號）：

```bash
# 預設單元（User=mfg-twin）
sudo -u mfg-twin env MFG_TEAM_STATE_DIR=/var/lib/mfg-twin/state \
    PYTHONPATH=/opt/mfg-twin/current/infra/chat-gateway python3 -m chat_gateway freeze

# 替代單元（DynamicUser=yes，主機上沒有 mfg-twin 帳號）：root 直接建立旗標檔
sudo touch /var/lib/mfg-twin/state/frozen
```

- 確認輸出印的路徑就是單元的 `MFG_TEAM_STATE_DIR`。`freeze` 不會建立不存在的 state dir：路徑、帳號或權限不對時 exit 78 並印出路徑，**不要**以為已經凍結。
- 效果：在 state dir 寫入旗標檔 `frozen`。gateway 在**每個事件前**檢查它，而且在貼出回覆前、執行已核准的動作前**再檢查一次**：不呼叫模型、不排程貼文、不執行核准；凍結當下正在產生的回覆會被丟棄（稽核 `frozen`／`frozen_in_flight`）；所有尚未決定的核准卡立即失效（稽核 `approval_expired`／`frozen`），解凍後也不會恢復，要重新申請。被 @ 或在凍結中按核准卡的人收到「分身暫停服務中」（每人每頻道每分鐘最多一則），每個事件記一筆稽核 `frozen`。
- 凍結是**軟停**：程式仍連著 Slack。確定要切斷時接著做步驟 1–2。
- 解除（只有在處置結束、負責人同意後），一樣用對應單元的那一行：

```bash
sudo -u mfg-twin env MFG_TEAM_STATE_DIR=/var/lib/mfg-twin/state \
    PYTHONPATH=/opt/mfg-twin/current/infra/chat-gateway python3 -m chat_gateway unfreeze
# DynamicUser：用 mv 保留凍結時間（不要 rm）
sudo mv /var/lib/mfg-twin/state/frozen /var/lib/mfg-twin/state/frozen.last
```
- 在 Slack 的 `/team freeze` 只是說明這個指令；聊天文字本身**不能**凍結或解凍任何東西。

## 1. 停服務（5 分鐘內，IT）

```bash
sudo systemctl stop mfg-twin-gateway.service
sudo systemctl disable mfg-twin-gateway.service      # 防止重開機後自動起來
sudo systemctl list-timers | grep mfg-twin           # 有排程貼文 timer／cron 也一併停掉
```

## 2. 撤銷憑證（30 分鐘內，IT；順序由外到內）

| 憑證 | 在哪裡撤銷 | 撤銷後確認 |
| ---- | ---------- | ---------- |
| Slack bot token（`xoxb-`） | Slack app 設定 → OAuth & Permissions → Revoke tokens；或直接把 app 從測試 workspace 移除 | gateway 再啟動時 `auth.test` 失敗 |
| Slack app-level token（`xapp-`） | Slack app 設定 → Basic Information → App-Level Tokens → Revoke | Socket Mode 連不上 |
| Anthropic API key | Anthropic Console → API Keys → 停用該服務帳號的 key | 用舊 key 呼叫回 401 |
| Discord bot token（若有） | Developer Portal → Bot → Reset Token | 舊 token 登入失敗 |

撤銷後，把 `EnvironmentFile`（見 DEPLOY.md）裡的舊值刪掉，不要留著「之後再用」。

## 3. 輪替 HMAC 金鑰（稽核金鑰與核准金鑰）

只有在金鑰可能外流、或保管人異動時做。**先封存舊鏈，再換金鑰**，不要直接覆蓋：

1. 用**舊**金鑰跑一次 `python3 -m chat_gateway audit-verify <state>/audit --anchor <主機外最近一份 heads> --heads-out heads-final.json`，把輸出與 `heads-final.json` 交給簽收人。
2. 停服務，把整個 `<state>/audit/` 打包成 `audit-<日期>-<舊金鑰代號>.tar`，計算 SHA-256，連同 `heads-final.json` 存到主機外的唯讀／WORM 位置（保存 ≥ 1 年）。
3. 從 state dir 移走 `audit/`（`teamctl state-reset --confirm` 只在開發機用；正式環境用 `mv` 改名並記錄）。
4. 產生新金鑰（各 ≥ 32 字元隨機值）寫入 `EnvironmentFile`，啟動服務；新鏈從 seq 1 開始。
5. 在處置紀錄寫明：舊鏈封存檔名與雜湊、新鏈起始時間、新金鑰保管人。

舊鏈只能用舊金鑰驗證；舊金鑰若要銷毀，先確認封存檔已用它驗證過並留下紀錄。細節見 [docs/audit-operations.md](../../docs/audit-operations.md)。

## 4. 保全稽核鏈

- 不要刪除、不要 `state-reset` 正式主機的 state dir。
- 用目前金鑰跑 `audit-verify --anchor <最近一次主機外 heads>`，把輸出原文貼進處置紀錄。
- 把 `<state>/audit/` 複製到主機外（唯讀），計算 SHA-256。稽核紀錄只有 keyed tag 與長度，沒有訊息原文；要知道「當時問了什麼」，向 Slack 管理員申請該頻道匯出。

## 5. 通報（誰在什麼時候被通知）

| 時限 | 通知誰 | 誰負責 |
| ---- | ------ | ------ |
| 立即 | IT／資安主管（pilot 核准人） | 發現者 |
| 1 小時內 | 導入負責人、稽核金鑰保管人、簽收人 | IT |
| 1 個工作天內 | 資料提供部門主管；若涉及客戶資料，法務 | IT／資安主管 |
| 依合約 | 客戶（若保密合約要求通報） | 法務 |

聯絡人姓名與電話寫在本機的 `team/local/playbook.local.md`（不進 repo），不要寫在這裡。

## 處置紀錄（每次一份，存本機或內部系統）

```
事件編號：            發現時間：            發現人（職稱）：
觸發條件：
0 凍結   時間／執行人：
1 停服務 時間／執行人：
2 撤銷   Slack bot／app token、API key 各自時間／執行人：
3 金鑰   是否輪替；舊鏈封存檔名與 SHA-256：
4 稽核   audit-verify 輸出（原文）：
5 通報   對象與時間：
根因與改善：
解凍或結束 pilot 的決定（誰、何時）：
```
