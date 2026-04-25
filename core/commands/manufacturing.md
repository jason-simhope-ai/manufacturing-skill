---
name: manufacturing
description: Plugin meta 指令 — 顯示目前載入的 agents / skills / know-how / profile 狀態
allowed-tools: [Read, Bash, Glob]
---

# /manufacturing — Plugin 狀態

顯示 manufacturing-plugin 目前載入的所有資源。

## 顯示內容

```
manufacturing-plugin v0.1.0
├── 啟用 profile：cnc-machining
├── Agents（5 + 4 = 9）
│   Core: quote-specialist, sales-coordinator, production-planner,
│         quality-inspector, inventory-manager
│   CNC:  cnc-programmer, tool-life-engineer, fixture-designer,
│         prototype-coordinator
├── Skills（9 + 3 = 12）
│   Core: 01-報價 → 06-出貨, bom-management, capacity-planning, spc-basics
│   CNC:  g-code-review, cutting-parameter-calc, fixture-design-patterns
├── Know-how（4 + 4 = 8）
├── Hooks（4 + 1 = 5）
└── Infra
    ├── MCP servers: scheduler-mcp, erp-connector
    └── On-prem LLM: Ollama @ GB10 (offline)
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
