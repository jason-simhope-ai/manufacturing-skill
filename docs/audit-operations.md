# 稽核作業手冊（twin gateway）

適用：`infra/chat-gateway/` 的 HMAC 雜湊鏈稽核日誌（`$MFG_TEAM_STATE_DIR/audit/`）。設計見 [spec §9.6、§11.6](superpowers/specs/2026-10-05-digital-twin-team-design.md)；部署見 [DEPLOY.md](../infra/chat-gateway/DEPLOY.md)；出事時見 [RUNBOOK.md](../infra/chat-gateway/RUNBOOK.md)。

## 1. 它證明什麼、不證明什麼

| 能證明 | 不能證明 |
| ------ | -------- |
| 沒有金鑰的人沒有改、刪、插、重排或截掉任何一筆（`audit-verify`） | 持有稽核金鑰的人沒有重寫整條鏈（對稱金鑰：能驗證就能偽造） |
| 和上一次送到主機外的 heads 相比，紀錄沒有變少、沒有被換掉（`--anchor`） | 主機外 heads 之後、下一次送出前的變動（最多差一個週期） |
| `--anchor` 比同目錄或 `--heads-out` 目錄裡任何一份有效簽章的 heads 舊時直接失敗（擋住「日誌＋`latest.json` 一起回滾」） | 主機上的 heads 也一起被刪或回滾時的回滾：只有**主機外**那份能證明（殘餘風險，見下） |
| 每個事件的動作、決策、拒絕原因、操作者代號（keyed）、分級 | 訊息原文：日誌只存 keyed tag 與長度（T2 以上連長度都不存）；要原文需向 Slack 申請頻道匯出 |

**殘餘風險（必須接受或補強）：**

- **錨點與日誌放在同一台主機上，就能一起被回滾。** 持有主機 root 的人可以把 `audit/`、`checkpoint.json` 與 `heads/` 全部還原成上週的樣子，主機上的驗證會通過。所以每週把 heads 送到主機外**是必要步驟，不是選項**；簽收人比對的是主機外那份。
- **資料夾掃描與模型讀檔之間有時間差。** gateway 在每次呼叫前掃描 `MFG_TEAM_DATA_T1`，但掃描完到模型讀檔（最多 60 秒）之間被改動或新增的檔案不會再被掃描；資料夾只給資料窗口寫入（DEPLOY.md 第 2 節）。

所以職責要分開：**金鑰保管人**（IT，不是導入負責人、不是簽收人）在主機上跑驗證；**簽收人**（不持有金鑰）只比對 heads 與主機外副本並簽名。

## 2. 每週作業（SOP）

每週一上午由 **systemd timer**（`mfg-twin-audit-weekly.timer`，DEPLOY.md 第 3 節）以服務帳號自動執行第 1–2 步，人執行第 3–4 步。不要用 cron：cron 讀不到 root `0600` 的 `EnvironmentFile`，金鑰不在時驗證會退回公開 demo 金鑰並顯示 FAILED，看起來像竄改。

**第一週**（上線當天，DEPLOY.md D7）還沒有上週的 heads：以服務帳號手動跑一次**只有** `--heads-out` 的驗證，把結果 `cp` 成 `latest.json` 並推到主機外。**第二週起**才有 `--anchor`；timer 腳本在沒有 `latest.json` 時直接失敗（exit 2），不會自動略過比對。

1. **驗證並產出 heads**（`infra/chat-gateway/audit-weekly.sh` 做的事；服務帳號，金鑰由 `EnvironmentFile` 提供，`PYTHONPATH=/opt/mfg-twin/current/infra/chat-gateway` 由 timer 單元設定，不需要 PyYAML）：

   ```bash
   W=$(date +%G-W%V)
   python3 -m chat_gateway audit-verify /var/lib/mfg-twin/state/audit \
       --anchor /var/lib/mfg-twin/heads/latest.json \
       --heads-out /var/lib/mfg-twin/heads/heads-$W.json
   ```

   - `--anchor`：上週的 heads。任何分級的筆數或最後 seq 變小、或上週的 head 已不在鏈上（整段回滾或重寫）就失敗（exit 1）。同一目錄（或 `--heads-out` 的目錄）裡若有比 anchor 新、簽章有效的 heads 檔，也失敗：表示 anchor 被換成舊的。
   - `--heads-out`：只有全部驗證通過才寫出；內容是各分級的筆數、最後 seq、head MAC，加上簽章，沒有任何訊息內容。
   - 輸出另有一行 `deny events (all tier files, …): dlp_blocked=… policy_denied=… frozen=… config_refused=…`，是簽收單 deny 類事件數的來源（涵蓋所有分級檔；`policy_denied`、`config_refused` 大多在 `sys`）。

2. **送到主機外（必要）**（只推不拉，目的地對服務主機唯讀或 WORM；佔位 `<ARCHIVE_USER>`、`<ARCHIVE_HOST>`、`<ARCHIVE_PATH>`、推送金鑰見 DEPLOY.md 第 3 節的填寫表）：

   ```bash
   rsync -a --chmod=F0440 -e "ssh -i /var/lib/mfg-twin/.ssh/heads_push_ed25519 -o BatchMode=yes" \
       /var/lib/mfg-twin/heads/heads-$W.json <ARCHIVE_USER>@<ARCHIVE_HOST>:<ARCHIVE_PATH>/
   cp /var/lib/mfg-twin/heads/heads-$W.json /var/lib/mfg-twin/heads/latest.json   # 推送成功後才更新
   ```

   主機上的 `latest.json` 只是方便；**比對以主機外那一份為準**。若懷疑主機被動過，從主機外取回上週的檔案當 `--anchor`。沒有 archive 主機時，由簽收人每週取走 heads 存在自己可控的唯讀位置（記在簽收單）；不能省略。

3. **簽收**：簽收人從主機外取本週與上週的 heads，確認本週的 `seq` 與各分級 `count` 不小於上週、驗證輸出為 `OK`，填寫簽收單（`journalctl -u mfg-twin-audit-weekly` 有該次輸出原文）。
4. **異常**：驗證失敗、anchor 失敗、heads 沒按時送達 → 依 [RUNBOOK.md](../infra/chat-gateway/RUNBOOK.md) 凍結並處置，不要 `state-reset`。

### 簽收單（每週一份）

```
週次：YYYY-Www            gateway 主機：<代號>        commit：<git rev-parse HEAD>
audit-verify 結果：OK / FAILED（附原文輸出）
anchor 比對：OK / FAILED / 第一週無 anchor
本週 heads：seq=____  各分級 count（heads 裡有哪些就填哪些，沒有的寫「—」）：T0=__  T1=__  sys=__
上週 heads：seq=____  （主機外檔名：__________________）
heads 檔主機外位置與檔名：______________________
本週 deny 類事件數（dlp_blocked / policy_denied / frozen / config_refused）：____ / ____ / ____ / ____
異常與處置：無 / 事件編號 ____
執行人（金鑰保管人，職稱）：________  日期：____
簽收人（不持有金鑰，職稱）：________  日期：____  簽名：________
```

deny 類事件數取自 `audit-verify` 輸出的 `deny events (all tier files, …)` 那一行（所有分級檔加總；只 grep 單一分級檔會少算）。

## 3. 金鑰輪替（含舊鏈封存）

觸發：保管人異動、金鑰可能外流、每 12 個月、或 pilot 結束。

1. 凍結（RUNBOOK 第 0 節對應單元的那一行），停服務。
2. 用**舊**金鑰：`python3 -m chat_gateway audit-verify <state>/audit --anchor <主機外最近一份 heads> --heads-out heads-final-<日期>.json`（必須 OK；不 OK 就先走 RUNBOOK）。
3. 封存：`tar -C <state> -cf audit-<日期>.tar audit`，`sha256sum audit-<日期>.tar > audit-<日期>.tar.sha256`；把 tar、sha256 與 `heads-final` 送到主機外唯讀位置。
4. 移走舊鏈：`mv <state>/audit <state>/audit.archived-<日期>`，確認主機外副本可讀後再刪本機副本。
5. 產生新金鑰（≥ 32 字元隨機值）寫入 `EnvironmentFile`；啟動；新鏈從 seq 1 開始。
6. 紀錄：舊鏈封存檔名、SHA-256、最後 seq、`heads-final` 檔名、新鏈起始時間、新舊保管人。下一次每週作業的 `--anchor` 從新鏈第一份 heads 開始。

舊金鑰只用於日後驗證封存檔：由保管人另存（例如密封信封或公司的祕密管理系統），標明「只用於驗證 <日期> 以前的封存」。

## 4. 金鑰遺失

- 遺失後，現有鏈無法再驗證，也無法續寫（gateway 啟動時會拒絕：鏈與 checkpoint 對不上新金鑰）。
- 處置：把現有 `audit/` 原樣封存（tar＋SHA-256＋主機外），在紀錄中註明「金鑰遺失，<日期> 以前的紀錄只能以主機外 heads 與封存雜湊佐證，無法重新驗 MAC」，然後依第 3 節第 5–6 步用新金鑰開新鏈。
- 主機外的每週 heads 仍可證明「封存檔在那些時間點已存在多少筆」，但無法重新驗證每一筆的 MAC。
- 預防：金鑰至少兩份、分開保存，由不同人保管（兩份都是完整簽章金鑰；這只降低遺失風險，不改變對稱金鑰的信任模型）。

## 5. 保存

- 稽核鏈與封存檔：pilot 結束後保存 ≥ 1 年（或依公司文件保存政策取較長者）。
- 每週 heads 與簽收單：與稽核鏈同期保存。
- 刪除時記錄刪除日期、範圍與核准人。

## 6. 對應 ISO/IEC 27001:2022 附錄 A（通用說明）

下表只說明本系統的哪些機制可作為證據，**不代表**已符合任何控制；適用性與充分性由貴公司的 ISMS 判定。

| 控制（通用名稱） | 本系統可提供的證據 | 仍需貴公司補的 |
| ---------------- | ------------------ | -------------- |
| 5.15 存取控制、5.18 存取權限 | `identities.local.yaml` 只認平台 user id；頻道提問名單；稽核 `operator`／`operator_ref` | 人員異動 1 個工作天內移除、每週名單覆核紀錄 |
| 5.19–5.22 供應商關係與監控 | [DEPLOY.md](../infra/chat-gateway/DEPLOY.md) 第 8 節廠商檢查表 | 書面回覆、DPA、年度覆核 |
| 5.23 雲端服務的資訊安全 | SaaS 與雲端模型上限 T1（設定拒載、lint E047） | 雲端使用政策、核准紀錄 |
| 5.24–5.26 事件管理與應變 | `freeze` kill switch、[RUNBOOK.md](../infra/chat-gateway/RUNBOOK.md)、稽核 `frozen` 事件 | 通報名單、演練紀錄 |
| 5.28 證據蒐集 | 雜湊鏈、簽章 checkpoint、主機外 heads、封存 SHA-256 | 證據保管鏈（誰在何時取用） |
| 5.33 紀錄保護 | 本手冊第 2–5 節 | WORM 或唯讀儲存、保存政策 |
| 8.2 特權存取、8.5 安全鑑別 | 專用服務帳號、祕密只在環境變數、模型子行程環境白名單 | 主機登入控管、金鑰保管紀錄 |
| 8.12 資料外洩防護 | 輸入 DLP、輸出過濾、資料夾掃描、starter denylist（**字詞告警，不是防線**） | 去識別流程、人工抽查、教育訓練 |
| 8.15 日誌、8.16 監控活動 | 每個事件與每個拒絕都有稽核紀錄；每週驗證與簽收 | 異常事件的審閱與追蹤 |
| 8.17 時鐘同步 | 紀錄含時間戳記與全域 seq | 主機 NTP 設定 |
| 8.24 密碼學的使用 | HMAC-SHA256、衍生子金鑰、金鑰輪替程序（第 3 節） | 金鑰管理政策 |
| 8.32 變更管理 | 版本固定、`config_loaded` 記錄 CLI 版本與旗標檢查、DEPLOY 第 7 節更新與回滾 | 變更核准紀錄 |
