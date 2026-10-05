# Pilot 部署檢核表（twin gateway，T0/T1，測試 workspace）

> **狀態：** 本頁的 systemd 單元與網路設定是建議範本，**沒有在真實主機上驗證過**；repo 內的程式也從未連過真的 Slack 或真的 `claude` CLI（CI 只用假 transport 與假 CLI）。上線第一天請照「首日驗收清單」逐項確認，並把結果用固定格式回報。
>
> 相關文件：[README](README.md)（指令與環境變數）· [RUNBOOK.md](RUNBOOK.md)（停機與外洩處置）· [docs/audit-operations.md](../../docs/audit-operations.md)（稽核週作業）· [SECURITY.md](../../SECURITY.md)

範圍假設：測試用 Slack workspace、2 個分身、2–3 位試用者、1–2 個綁定頻道、只有 T0/T1、4 週。

## 1. 主機與帳號

- [ ] **專用主機或 VM**（或專用容器主機），不跟其他服務、不跟任何人的工作站共用。
- [ ] **專用 OS 帳號 `mfg-twin`**，不能登入互動 shell；不用任何人的個人帳號跑 gateway。**預設用固定帳號**（下面的單元），因為 RUNBOOK 的凍結指令、每週稽核 timer 都以這個帳號執行；systemd `DynamicUser=` 是替代寫法（見第 3 節末），凍結方式不同。

```bash
sudo useradd --system --user-group --home-dir /var/lib/mfg-twin --shell /usr/sbin/nologin mfg-twin
```
- [ ] 主機磁碟加密、只開管理用的 SSH（金鑰登入、限定來源）。
- [ ] 時間同步（chrony／systemd-timesyncd）：稽核紀錄的時間戳記與每日預算依賴系統時鐘。
- [ ] 套件：Python 3.11+（單元用 `/usr/bin/python3`）；`slack_sdk` 裝進同一個 Python（只裝 Slack：`sudo python3 -m pip install 'slack_sdk>=3.27,<4'`；`requirements-optional.txt` 會連 discord.py 一起裝）；`teamctl`／`build.py` 需要 PyYAML（`sudo apt install python3-yaml` 或 `sudo python3 -m pip install 'pyyaml>=6,<7'`，缺少時 teamctl exit 2；gateway 本身與 `python3 -m chat_gateway audit-verify` 不需要）；每週稽核推送需要 `rsync` 與 `ssh`（`sudo apt install rsync openssh-client`）。

## 2. 目錄配置

| 路徑 | 擁有者／權限 | 內容 |
| ---- | ------------ | ---- |
| `/opt/mfg-twin/releases/<commit>/` | root，唯讀 | 審過的 repo 版本（含 `team/.build/`）。`/opt/mfg-twin/current` 指向目前版本 |
| `/var/lib/mfg-twin/state/` | 服務帳號，`0700` | `MFG_TEAM_STATE_DIR`：稽核鏈、限流、driver 暫存、凍結旗標、資料夾掃描快取。**不可是 symlink**（啟動拒絕，exit 78），上層目錄不可讓其他帳號寫入（程式只檢查 state dir 本身，上層由管理員負責） |
| `/var/lib/mfg-twin/claude-config/` | 服務帳號，`0700` | `MFG_TEAM_CLAUDE_CONFIG_DIR`：服務帳號專用，不可是任何人的 `~/.claude` |
| `/var/lib/mfg-twin/heads/` | 服務帳號，`0750` | 每週稽核 heads（`latest.json`、`heads-<週>.json`）；正本在主機外 |
| `/etc/mfg-twin/names.denylist` | root:mfg-twin，`0640` | `MFG_TEAM_DENYLIST`：本機 denylist，從 `team/tools/denylist.starter.txt` 起步，再加自己的客戶與專案代號（不進 repo）。非 mock adapter 沒有載入 denylist 會拒絕啟動（exit 64） |
| `/srv/mfg-twin/data-t1/` | 資料窗口寫入，服務帳號唯讀 | `MFG_TEAM_DATA_T1`：只放 `deid.py` 去識別後的 T1 匯出檔；不可放在任何人的家目錄或 `~/.*` 隱藏目錄下 |
| `/etc/mfg-twin/gateway.env` | root，`0600` | 祕密（見第 4 節） |

建立目錄與 denylist（固定帳號）：

```bash
sudo install -d -o mfg-twin -g mfg-twin -m 0700 /var/lib/mfg-twin /var/lib/mfg-twin/state /var/lib/mfg-twin/claude-config
sudo install -d -o mfg-twin -g mfg-twin -m 0750 /var/lib/mfg-twin/heads
sudo install -d -o root -g mfg-twin -m 0750 /etc/mfg-twin
sudo install -o root -g mfg-twin -m 0640 /opt/mfg-twin/current/team/tools/denylist.starter.txt /etc/mfg-twin/names.denylist
sudoedit /etc/mfg-twin/names.denylist      # 加上自己的客戶、專案、圖號代號；T3 等級的行寫成 T3:<regex>
```

資料夾在啟動與每次呼叫前都會被掃描（≤ 2 MB 的文字檔：UTF-8、Big5、有 BOM 的 UTF-16；DLP 字詞＋本機 denylist＋私鑰／token／`api_key=` 等 secret 形狀）：T3 或 secret 命中拒絕啟動（exit 3）或拒絕該次呼叫（`policy_denied data_root:T3`），T2 命中只在 stderr 告警；超過 5,000 個檔案、含 symlink、FIFO／裝置檔（`data_root:special_file`，不會開啟）或 roster／identity 檔都會拒絕。**掃描讀不了的檔案預設也拒絕**（PDF、Word／Excel、圖片、其他二進位檔、沒有 BOM 的 UTF-16、超過 2 MB 的檔案：exit 3／`data_root:unscanned`），因為 `claude` 的 Read 工具能直接讀 PDF 與圖片。請轉成 ≤ 2 MB 的 UTF-8 文字匯出檔再放進來。`MFG_TEAM_DATA_ALLOW_UNSCANNED=1` 可以放行這些檔案（只在 stderr 告警），**代價是模型會讀到沒檢查過的內容**：只有在資料窗口逐檔人工確認過、並記錄在部署紀錄時才設。這仍是字詞告警，不是內容理解；掃描與模型讀檔之間（每次呼叫最多 60 秒）被改動或新增的檔案不會再被掃描（殘餘風險，見 SECURITY.md），所以資料夾只給資料窗口寫入。

## 3. systemd 單元（範本）

`/etc/systemd/system/mfg-twin-gateway.service`（預設：固定帳號 `mfg-twin`）：

```ini
[Unit]
Description=manufacturing-skill twin gateway (pilot, T0/T1)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mfg-twin
Group=mfg-twin
ReadWritePaths=/var/lib/mfg-twin
WorkingDirectory=/opt/mfg-twin/current
EnvironmentFile=/etc/mfg-twin/gateway.env
Environment=PYTHONPATH=/opt/mfg-twin/current/infra/chat-gateway
Environment=MFG_TEAM_STATE_DIR=/var/lib/mfg-twin/state
Environment=MFG_TEAM_CLAUDE_CONFIG_DIR=/var/lib/mfg-twin/claude-config
Environment=MFG_TEAM_DATA_T1=/srv/mfg-twin/data-t1
Environment=MFG_TEAM_ROSTER=/opt/mfg-twin/current/team/.build/roster.json
Environment=MFG_TEAM_DENYLIST=/etc/mfg-twin/names.denylist
Environment=MFG_TEAM_PASS_PROXY_ENV=1
ExecStartPre=/usr/bin/python3 -m chat_gateway self-check --adapter slack --driver claude-code
ExecStart=/usr/bin/python3 -m chat_gateway run --adapter slack --driver claude-code
Restart=on-failure
RestartSec=30
# 拒絕啟動（exit 3 = T3／資料夾、64 = 參數或缺 denylist、78 = 設定）不要無限重啟；
# 70 = 內部錯誤（例如連不到 Slack 時只印 `internal error: URLError`）會依 RestartSec 重試
RestartPreventExitStatus=3 64 78

# 檔案系統：除了 /var/lib/mfg-twin 全部唯讀
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ReadOnlyPaths=/srv/mfg-twin/data-t1
# 權限
NoNewPrivileges=yes
CapabilityBoundingSet=
RestrictSUIDSGID=yes
LockPersonality=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
UMask=0077
# 網路：只能連到出口 proxy（見第 5 節）
IPAddressDeny=any
IPAddressAllow=localhost
IPAddressAllow=10.0.0.10/32
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

[Install]
WantedBy=multi-user.target
```

凍結（RUNBOOK 第 0 節，這個單元用這一行）：

```bash
sudo -u mfg-twin env MFG_TEAM_STATE_DIR=/var/lib/mfg-twin/state \
    PYTHONPATH=/opt/mfg-twin/current/infra/chat-gateway python3 -m chat_gateway freeze
```

替代寫法（`DynamicUser=`，每次啟動配一個臨時 uid，主機上沒有 `mfg-twin` 帳號）：把 `User=`、`Group=`、`ReadWritePaths=` 換成

```ini
DynamicUser=yes
StateDirectory=mfg-twin
StateDirectoryMode=0700
LoadCredential=names.denylist:/etc/mfg-twin/names.denylist
Environment=MFG_TEAM_DENYLIST=%d/names.denylist
```

（state 實際在 `/var/lib/private/mfg-twin/`，`/var/lib/mfg-twin` 是指向它的 symlink；denylist 以 systemd credential 傳入，因為臨時 uid 不在 `mfg-twin` 群組；`claude-config/` 沒有固定擁有者可以預先建立。這些都是預設改用固定帳號的原因。）
**這個寫法下 `sudo -u mfg-twin … freeze` 不能用**（沒有該帳號；以 root 執行 `freeze` 會因 state dir 擁有者不符而 exit 78）。改用 root 直接建立旗標檔，gateway 只檢查檔案是否存在：

```bash
sudo touch /var/lib/mfg-twin/state/frozen                                   # 凍結
sudo mv /var/lib/mfg-twin/state/frozen /var/lib/mfg-twin/state/frozen.last  # 解凍（用 mv，不要 rm：保留凍結時間，凍結前發出的核准卡維持失效）
```

上線前跑 `systemd-analyze security mfg-twin-gateway.service`，把分數與未通過項目附在部署紀錄。

排程貼文（`post`）與每週稽核都用 **systemd timer**（不要用 cron：cron 讀不到 root `0600` 的 `EnvironmentFile`），以同一個服務帳號、同一個 `EnvironmentFile` 執行。`teamctl roster --crontab` 印的只是排程時間範本，沒有帶環境與 `--adapter slack`，不能直接貼進 crontab。

每週稽核（`/etc/systemd/system/mfg-twin-audit-weekly.service` 與 `.timer`；腳本是 repo 內的 `infra/chat-gateway/audit-weekly.sh`）：

```ini
# mfg-twin-audit-weekly.service
[Unit]
Description=mfg-twin weekly audit verify and off-host heads push

[Service]
Type=oneshot
User=mfg-twin
Group=mfg-twin
WorkingDirectory=/opt/mfg-twin/current
EnvironmentFile=/etc/mfg-twin/gateway.env
Environment=PYTHONPATH=/opt/mfg-twin/current/infra/chat-gateway
Environment=MFG_TEAM_STATE_DIR=/var/lib/mfg-twin/state
Environment=HEADS_DIR=/var/lib/mfg-twin/heads
Environment=ARCHIVE_DEST=<ARCHIVE_USER>@<ARCHIVE_HOST>:<ARCHIVE_PATH>/
Environment=PUSH_KEY=/var/lib/mfg-twin/.ssh/heads_push_ed25519
ExecStart=/bin/sh /opt/mfg-twin/current/infra/chat-gateway/audit-weekly.sh

# mfg-twin-audit-weekly.timer
[Unit]
Description=Weekly audit verify (Monday 07:10)

[Timer]
OnCalendar=Mon *-*-* 07:10
Persistent=true

[Install]
WantedBy=timers.target
```

`sudo systemctl enable --now mfg-twin-audit-weekly.timer`；失敗時 `systemctl status mfg-twin-audit-weekly.service` 會是 failed，請接進既有監控或每週一人工確認。主機外位置由管理員填寫下表（存進部署紀錄）：

| 佔位 | 填什麼 | 例 |
| ---- | ------ | -- |
| `<ARCHIVE_HOST>` | 主機外保存位置（另一台主機，服務主機對它只能推、不能讀或刪） | 稽核檔案伺服器的主機名 |
| `<ARCHIVE_USER>` | 該主機上只用來收 heads 的帳號（`authorized_keys` 加 `restrict,command="rrsync -wo <ARCHIVE_PATH>"`） | `audit-archive` |
| `<ARCHIVE_PATH>` | 收件目錄（WORM 或每日快照、服務主機不可改） | `/srv/audit-heads/mfg-twin` |
| `PUSH_KEY` | 服務帳號的推送金鑰：`sudo -u mfg-twin ssh-keygen -t ed25519 -N '' -f /var/lib/mfg-twin/.ssh/heads_push_ed25519`，公鑰交給 archive 主機管理者；第一次以 `sudo -u mfg-twin ssh -i … <ARCHIVE_USER>@<ARCHIVE_HOST>` 接受主機金鑰 | — |

主機防火牆要允許服務主機連到 `<ARCHIVE_HOST>` 的 22 port（timer 不在 gateway 單元的 `IPAddressDeny=` 內）。沒有可用的 archive 主機時，替代做法是由簽收人每週從主機取走 `heads-<週>.json` 存到自己可控的唯讀位置，並在簽收單記錄；**主機外副本是必要的**，只留在主機上的 heads 會跟日誌一起被回滾（docs/audit-operations.md 第 1 節）。

## 4. 祕密注入

- [ ] 所有祕密只放 `/etc/mfg-twin/gateway.env`（root:root `0600`，systemd 以 root 讀取後才降權），**不寫進** unit 檔、repo、shell history 或聊天：

```
MFG_TEAM_SLACK_BOT_TOKEN=...
MFG_TEAM_SLACK_APP_TOKEN=...
ANTHROPIC_API_KEY=...
MFG_TEAM_AUDIT_HMAC_KEY=...        # ≥ 32 字元隨機值；保管人 = IT（不是導入負責人、不是簽收人）
MFG_TEAM_APPROVAL_HMAC_KEY=...     # 另一把，≥ 32 字元
HTTPS_PROXY=http://10.0.0.10:3128
NO_PROXY=localhost,127.0.0.1
```

- [ ] 產生金鑰：`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`。
- [ ] **mock 試跑與 demo 金鑰不要碰正式 state dir**：未設金鑰時 gateway 用公開的 demo 金鑰寫稽核鏈；之後換成真金鑰啟動會 exit 78（「audit chain … was started under the public demo key」）。試跑一律用另一個目錄，例如 `MFG_TEAM_STATE_DIR=/tmp/mfg-twin-rehearsal`。若已經發生：照訊息把 `/var/lib/mfg-twin/state/audit` 封存（docs/audit-operations.md 第 3 節第 3–5 步）後重新開鏈；這是設定錯誤，不是竄改。
- [ ] 知悉殘餘風險：執行中的行程環境可由同一 uid 與 root 從 `/proc/<pid>/environ` 讀到。`DynamicUser=` 讓這個 uid 不屬於任何人；模型子行程只拿到白名單變數（`PATH`、`HOME`、`CLAUDE_CONFIG_DIR`、`ANTHROPIC_API_KEY`，以及 `MFG_TEAM_PASS_PROXY_ENV=1` 時的 proxy 變數），拿不到 Slack token 與 HMAC 金鑰。
- [ ] 輪替與撤銷步驟見 [RUNBOOK.md](RUNBOOK.md) 第 2、3 節。

## 5. 出口網路（egress allowlist）

`IPAddressAllow=` 只能寫 IP，而 Slack 與 Anthropic 的 IP 會變，所以做法是：**服務只能連到一台出口 proxy**（上面的 `10.0.0.10`），proxy 再依網域放行：

| 用途 | 網域（以廠商文件為準，上線前確認） |
| ---- | ---------------------------------- |
| Slack Web API 與 Socket Mode | `slack.com`、`*.slack.com`（含 `wss-primary.slack.com` 等 WebSocket 端點） |
| Anthropic API（`claude` CLI） | `api.anthropic.com` |

- [ ] 其他網域一律拒絕並記錄。`claude` CLI 可能嘗試連線遙測或更新網域：被擋下時確認功能不受影響，並在 `MFG_TEAM_CLAUDE_CONFIG_DIR/settings.json` 關閉非必要流量與自動更新（以該版 CLI 文件為準）。
- [ ] 不開任何入站連接埠（Slack 用 Socket Mode，沒有 Request URL）。
- [ ] proxy 若做 TLS 檢查，CA 憑證用 `SSL_CERT_FILE`／`NODE_EXTRA_CA_CERTS` 傳入（`MFG_TEAM_PASS_PROXY_ENV=1` 才會轉給子行程）。

## 6. 日誌與保存

- gateway 的 stderr 進 journald：設定 `SystemMaxUse=`／`MaxRetentionSec=`（建議 ≥ 90 天），journald 只有類別名稱與檔名，沒有訊息原文。
- 稽核鏈 `state/audit/` 是 append-only，gateway **不會**自己輪替：每週 `audit-verify --heads-out` 並把 heads 送到主機外（上面的 timer）；金鑰輪替或 pilot 結束時整包封存（≥ 1 年）。程序見 [docs/audit-operations.md](../../docs/audit-operations.md)。每筆約 0.5–1 KB，4 週 pilot 通常在數 MB 以內。

## 7. 更新與回滾

更新（pilot 期間原則上**不升級**；只有安全修正才做，且要 IT 核准）：

1. 在另一台機器審過新 commit，記錄 `git rev-parse HEAD`。
2. `git clone` 到 `/opt/mfg-twin/releases/<commit>/`（root 擁有、唯讀），在該目錄跑：
   `python3 -m unittest discover -s tests/gateway -p 'test_*.py'`、`python3 team/tools/teamctl.py check`、`python3 team/tools/build.py`（後兩者需要 PyYAML）。
3. 記錄 `pip freeze`、`claude --version`；`slack_sdk` 版本先在內部鏡像或離線審過。
4. `python3 -m chat_gateway freeze` → `systemctl stop` → 把 `/opt/mfg-twin/current` 改指新版本 → `systemctl start` → 看 `config_loaded` 稽核紀錄的 `driver_info`（CLI 版本、旗標檢查）→ `unfreeze`。

回滾：凍結 → 停服務 → `current` 改回上一個 release → 啟動 → 確認 `audit-verify` OK → 解凍。state dir 與稽核鏈不隨版本回滾（版本間格式相容）；**不要**把 state dir 一起還原成舊快照，那會讓下一次 `--anchor` 比對失敗（正確地）。

## 8. T1 pilot 廠商檢查表（需書面確認，存入供應商評估紀錄）

| 廠商 | 項目 | 要確認的事（以合約與書面回覆為準，不要用網頁摘要代替） |
| ---- | ---- | ------------------------------------------------------ |
| Slack | 方案 | 測試 workspace 的方案層級；訊息保存期限能否設定；能否匯出頻道紀錄（事故調查需要）；稽核日誌（audit logs API）是否包含在方案內 |
| Slack | 設定 | Slack Connect 關閉、只允許管理員安裝 app、只允許管理員把人加入綁定頻道、app 只裝這一個 |
| Slack | 資料 | 資料存放地區；是否用客戶資料訓練模型（含 Slack AI 功能）及如何關閉；DPA 是否已簽 |
| Anthropic API | 使用與訓練 | 商業 API 的輸入輸出是否用於訓練（預設與例外情況） |
| Anthropic API | 保存 | API 請求與回應的保存天數；是否需要、能否申請零保存（zero data retention）；安全事件時的保存例外 |
| Anthropic API | 地區與分包 | 處理地區、次處理者清單、跨境傳輸條款；DPA 是否已簽 |
| Anthropic API | 帳號 | 用組織的服務帳號與獨立 API key，設定用量上限；不用任何人的個人訂閱 |
| `claude` CLI | 遙測 | CLI 會送出哪些遙測、能否關閉；自動更新能否關閉（pilot 期間版本固定） |
| 客戶合約 | 第三方 AI | 試點涉及的資料是否受客戶保密合約限制（是否禁止交給第三方 AI 服務）；**先查合約，不要先試** |

任何一項答案不可接受，或 pilot 期間條款變更，即停止 pilot（RUNBOOK 啟動條件）。

## 9. 首日驗收清單（pilot day one）

每一項都要有證據（指令輸出原文、截圖或稽核紀錄 seq）。任何一項失敗：凍結，回報，不要繞過。

先做 D0：mock 演練用**另一個** state dir（`MFG_TEAM_STATE_DIR=/tmp/mfg-twin-rehearsal`），不要在 `/var/lib/mfg-twin/state` 用 demo 金鑰跑任何指令（第 4 節）。回覆頁尾的 `稽核 #n` 是那則回覆（`msg_out`）的 seq；被拒的那筆（`policy_denied`、`dlp_blocked`）在它之前，證據請寫被拒那筆的 seq。

| # | 項目 | 做法 | 通過條件 |
| - | ---- | ---- | -------- |
| D1 | 版本固定 | 記錄 `git rev-parse HEAD`、`pip freeze`、`claude --version` | 與核准的版本清單一致 |
| D2 | 旗標檢查 | `systemctl start` 後讀 `/var/lib/mfg-twin/state/audit/sys/audit.jsonl` 最後一筆 `config_loaded`；`journalctl -u mfg-twin-gateway` 有 `self-check: denylist: /etc/mfg-twin/names.denylist (N entries)` | `driver_info.flag_check` = `ok`，`cli_version` 與 D1 相同（repo 驗證過的版本：2.1.289），`driver_info.denylist.entries` > 0 |
| D3 | Scope 檢查 | 正常啟動；再暫時多加 `reactions:write` 並重裝 app、重啟 | 正常時啟動；多給 scope 時 exit 78 並列出該 scope；移除後恢復 |
| D4 | 連線與回答 | 試用者在綁定頻道 @分身 問一個 T1 問題 | 回覆在 thread 內、有前綴與 `稽核 #seq` 頁尾 |
| D5 | 被拒事件 | 依序：DM 機器人、在未綁定頻道 @、不 @ 直接說話、貼 P7「這張單報價 125 萬、成本 98 萬，要不要接」、貼 P2「The defense program fixture drawing DWG-4471 needs an export license before we send it to the subcontractor」 | DM／未綁定／未 @ 無回覆但有 `policy_denied`；P7 `dlp_blocked dlp:T2`；P2 回「此內容可能屬 T3…」（需 D2 的 denylist 已載入） |
| D6 | 資料夾掃描 | 在 `MFG_TEAM_DATA_T1` 放一個含 T3 字樣的測試檔，再 @ 分身；移除後改放一個 PDF 再問；移除後再問 | 有 T3 檔時回「資料夾內有不符本頻道分級…」，稽核 `policy_denied data_root:T3`；PDF 時同樣回覆，稽核 `data_root:unscanned`；移除後恢復 |
| D7 | 稽核（第一週） | 以服務帳號：`python3 -m chat_gateway audit-verify /var/lib/mfg-twin/state/audit --heads-out /var/lib/mfg-twin/heads/heads-day1.json`（第一週**只有** `--heads-out`，沒有 anchor），`cp` 成 `latest.json`，並推到主機外（第 3 節的 rsync 指令） | `audit verify: OK`；heads 檔已在主機外；`latest.json` 存在，第二週起 timer 自動加 `--anchor` |
| D8 | 凍結演練 | 用 RUNBOOK 第 0 節**對應目前單元**的原文指令（固定帳號：`sudo -u mfg-twin … freeze`；DynamicUser：`sudo touch <state>/frozen`）→ @ 分身 → 解凍（`… unfreeze` 或 `sudo mv <state>/frozen <state>/frozen.last`）→ 再 @ | 凍結時回「分身暫停服務中」、稽核 `frozen`；解凍後恢復；全程 ≤ 5 分鐘 |
| D9 | 撤銷演練（可選，建議在測試 app 做） | 依 RUNBOOK 第 2 節撤銷 bot token | gateway 無法連線；換新 token 後恢復 |

回報格式（固定，當天交 IT／資安主管）：

```
Pilot day-one report
date: YYYY-MM-DD    host: <主機代號>    operator: <職稱>
commit: <git rev-parse HEAD>    claude --version: <輸出>    slack_sdk: <版本>
D1 version pin      PASS|FAIL  evidence: <檔名或 seq>
D2 flag check       PASS|FAIL  driver_info: <原文>
D3 scope check      PASS|FAIL  refusal text: <原文>
D4 connect/answer   PASS|FAIL  audit seq: <n>
D5 denied events    PASS|FAIL  audit seqs: <n,...>
D6 data-root scan   PASS|FAIL  audit seq: <n>
D7 audit verify     PASS|FAIL  heads file: <名稱與主機外位置>
D8 freeze drill     PASS|FAIL  duration: <分鐘>
D9 revoke drill     PASS|FAIL|SKIPPED
open issues: <無／列出>
decision: CONTINUE | FROZEN | STOP
```
