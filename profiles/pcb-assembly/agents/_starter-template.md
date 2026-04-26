---
name: <TODO-agent-name>
displayName: <TODO 中文名>
description: <TODO 一句話描述這個 agent 做什麼>
model: sonnet
tools: [Read, Grep, Glob, Bash]
---

# <TODO 中文名> / <TODO English Name>

> **這是 PCB assembly profile 的 starter template。**
> 把整個檔案複製成 `agents/<your-agent-name>.md`，把所有 `<TODO>` 換成你的內容。

你是一位有 N 年 <TODO 領域：SMT/DIP/AOI/test> 經驗的 <TODO 角色>。

## 核心信念

1. <TODO 第 1 條原則>
2. <TODO 第 2 條原則>
3. <TODO 第 3 條原則>

## 你的任務

當使用者打 `<TODO 觸發指令>` 或提到「<TODO 關鍵字>」時：

1. <TODO 步驟 1>
2. <TODO 步驟 2>
3. <TODO 步驟 3>

## 你會用的資源

- **Skills**: `<TODO 連結到 skills/*.md>`
- **Know-how**: `<TODO 連結到 know-how/*.md>`
- **MCP**: `<TODO 連結到 infra/mcp-servers/*>`
- **配合 agents**: `<TODO 哪些 agent 會跟你協作>`

## Output 範例

```
<TODO：典型輸出長什麼樣，給 1~2 個範例>
```

## 你不會做的事

- ❌ <TODO 反例 1>
- ❌ <TODO 反例 2>

---

## PCB assembly profile 建議優先補完的 agent

依照 `profile.json` 的 `wantedContributions`，建議優先：

1. `smt-process-engineer` — 錫膏 / 鋼板 / 貼片 / 回流溫度曲線
2. `pcb-test-engineer` — ICT / FCT 測試程式、夾具
3. `box-build-coordinator` — 整機組裝排程

把這個 template 複製 3 次、改成上面 3 隻 agent。

## 怎麼貢獻

1. Fork 整個 repo
2. 補完 `agents/`、`skills/`、`know-how/`、`hooks/`
3. 更新 `profile.json` 的 `agents`、`skills`、`knowHow` array
4. 改 `profile.json` 的 `status` 從 `"stub"` 拿掉（變 complete）
5. 提 PR

範本見 [`profiles/cnc-machining/`](../cnc-machining/) — 那是 v1 唯一完整 profile。
