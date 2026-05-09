---
name: manufacturing
description: Plugin meta 指令 — 顯示目前載入的 agents / skills / know-how / profile 狀態
allowed-tools: [Read, Bash, Glob]
---

# /manufacturing — Plugin 狀態

顯示 manufacturing-skill 目前載入的所有資源。

## 顯示內容

讀 `~/.claude/plugins/manufacturing-skill/.installed`：

- `activeProfiles`（v0.1.5+，陣列）優先；若不存在則 fallback 讀 `activeProfile`（v0.1.x 單一字串）
- 接著讀 `active-profiles.json`（v0.1.5+ aggregated 視圖）顯示彙總後的 capability

範例（單 profile，v0.1.x 行為）：

```
manufacturing-skill v0.1.5
├── 啟用 profile：cnc-machining
├── Agents（6 + 4 = 10）
│   Core: quote-specialist, sales-coordinator, ...
│   CNC:  cnc-programmer, tool-life-engineer, ...
├── Skills（11 + 3 = 14）
├── Know-how（8 + 4 = 12）
├── Hooks（4 + 1 = 5）
└── Infra
    ├── MCP servers: scheduler-mcp, erp-connector
    └── On-prem LLM: Ollama @ GB10 (offline)
```

範例（多 profile，v0.1.5+）：

```
manufacturing-skill v0.1.5
├── 啟用 profiles：cnc-machining, injection-molding（primary: cnc-machining）
├── Agents（6 + 4 + 1 = 11）
│   Core:      quote-specialist, sales-coordinator, ...
│   CNC:       cnc-programmer, tool-life-engineer, ...
│   Injection: mold-designer
├── Skills（11 + 3 + 1 = 15）
├── Know-how（8 + 4 + 2 = 14）
├── Hooks（4 + 1 = 5）
└── Infra
    └── MCP servers: scheduler-mcp, erp-connector
```

## 子指令

```
/manufacturing               # 顯示全部
/manufacturing agents        # 只顯示 agents
/manufacturing skills        # 只顯示 skills
/manufacturing profile       # 顯示目前 profile 細節
/manufacturing version       # 顯示版本
/manufacturing doctor        # 健檢：MCP 連線、LLM runtime、檔案完整度
```
