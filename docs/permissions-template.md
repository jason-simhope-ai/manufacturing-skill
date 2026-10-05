# 工廠工作站權限範本（Claude Code `permissions`）

> 給 IT / 導入負責人。目的：**最小權限**。讓 Claude Code 在工廠電腦上只做「讀文件、整理、產生草稿」，
> 就算讀到被塞了惡意指令的 RFQ / PDF（prompt injection），也無法把資料送出去或刪東西。
> 這是建議起點，不是資安認證；請依你們的環境調整，並以 [Claude Code 官方權限文件](https://docs.claude.com/en/docs/claude-code/settings) 的最新語法為準。

---

## 這個 repo 已經做了什麼

本 plugin 的 6 隻核心 agent 與 `/quote`、`/bom-check`、`/inspect`、`/8d` 四個指令，**不再宣告 `Bash` 工具**，只留 `Read` / `Grep` / `Glob`。
仍保留 `Bash` 的指令與原因：

| 指令 | 為什麼還要 `Bash` |
| --- | --- |
| `/install-profile`、`/add-profile` | 要執行 `bash adapters/claude-code/install.sh`（含 `--list-conflicts` 衝突掃描） |
| `/init`、`/manufacturing`、`/morning-briefing`、`/order-status` | 本次未審查，維持原狀（另案處理） |
| `cnc-machining` / `injection-molding` 產業包內的 agent | 產業包內容另案處理，目前仍宣告 `Bash` |

> 重點：agent / command 宣告的 `tools` 只是「這個角色能用什麼」。**主對話本身**仍可能有 Bash，
> 所以仍要靠下面的 `permissions` 在整台電腦層級設防。

---

## 建議的 `settings.json`

放在專案的 `.claude/settings.json`（跟著資料夾走），或使用者層級的 `~/.claude/settings.json`。
若要讓員工無法自行放寬，請改用組織的 managed settings（由 IT 派送，細節見官方文件）。

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Grep",
      "Glob"
    ],
    "ask": [
      "Edit",
      "Write",
      "Bash"
    ],
    "deny": [
      "WebFetch",
      "WebSearch",
      "Bash(curl *)",
      "Bash(wget *)",
      "Bash(ssh *)",
      "Bash(scp *)",
      "Bash(sftp *)",
      "Bash(rsync *)",
      "Bash(nc *)",
      "Bash(ncat *)",
      "Bash(telnet *)",
      "Bash(ftp *)",
      "Bash(git push *)",
      "Bash(git remote *)",
      "Bash(sudo *)",
      "Bash(rm -rf *)",
      "Bash(rm -r *)",
      "Bash(del /s *)",
      "Bash(rmdir /s *)",
      "Bash(format *)",
      "Bash(dd *)",
      "Bash(chmod -R *)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)",
      "Read(~/.config/gcloud/**)"
    ]
  }
}
```

### 三個區塊的意思

- **`allow`（直接放行）**：只放唯讀工具。讀檔、搜尋不會改動任何東西。
- **`ask`（每次詢問）**：會改檔案或執行指令的工具，每次都跳確認，讓使用者看過再按。
- **`deny`（一律拒絕，優先於 allow / ask）**：
  - 網路外連：`WebFetch`、`WebSearch`、`curl`、`wget`、`ssh`、`scp`、`rsync`、`nc` 等 — 這是資料外流的主要出口。
  - 破壞性操作：`sudo`、遞迴刪除、`dd`、格式化、`git push`。
  - 憑證檔：`.env`、`~/.ssh`、`~/.aws`。

### 依需求調整

- **要用網路搜尋**（例如查材料規格）：從 `deny` 拿掉 `WebSearch`，但風險自負；機密專案請維持封鎖。
- **要讓 AI 直接存檔**（例如產生報價草稿）：把 `Edit` / `Write` 限縮到工作資料夾，例如 `"Edit(./drafts/**)"`、`"Write(./drafts/**)"` 移到 `allow`，其餘仍 `ask`。
- **接了 ERP / MES 的 MCP 工具**：寫入型工具（建單、改單、扣料）請列入 `ask` 或 `deny`，只放行查詢型。工具名稱以實際 MCP server 回報的為準（格式 `mcp__<server>__<tool>`）。
- **Windows**：路徑與指令寫法不同（`del`、`rmdir`、PowerShell 的 `Remove-Item`），請依實際環境補上。

---

## 這個範本做不到的事（請誠實面對）

1. **`Bash(...)` 規則是字串比對，不是沙盒。** 有心人可以用 `python -c`、`node -e`、別名或管線繞過。它擋的是「模型被誘導時的常見動作」，不是完整防線。
2. **真正的隔離要靠網路層。** 若資料不得外流，請在防火牆 / proxy 層只放行必要網域，必要時用沒有對外網路的環境，而不是只靠這份設定。
3. **`Read` 預設可讀到使用者帳號能存取的任何檔案。** 若不想讓 AI 讀到整台電腦，請在專用資料夾開 Claude Code，並在 `deny` 補上不該讀的路徑。
4. **雲端模型仍會收到你貼上或附上的內容。** 權限設定管的是「Claude Code 能做什麼動作」，不是「哪些資料能送給模型」；資安通報與建議請見 [SECURITY.md](../SECURITY.md)。

---

## 驗證

1. 在設定好的資料夾開 Claude Code，輸入 `/permissions`，確認規則已載入。
2. 要求它「用 curl 抓一個網頁」→ 應被拒絕。
3. 要求它「讀取 `.env`」→ 應被拒絕。
4. 跑 `/quote @examples/sample-drawing/bracket.md` → 應能正常讀檔、產出報價（不需要 Bash）。

> 若第 4 步被擋，代表某條規則過嚴，請放寬後再測；調整完請把最終版本留存給稽核。
