---
name: install-profile
description: 啟用 / 切換 vertical profile（v0.1.5+ 支援多 profile 同時 active）
allowed-tools: [Read, Bash]
argument-hint: "<profile> 或 <p1>,<p2>,..."
---

# /install-profile — 啟用 vertical profile（replace 語意）

切換目前作用中的 vertical profile。**v0.1.5 起支援多 profile 同時 active**（CNC + 射出同廠、EMS 含塑膠殼等橫跨 vertical 的工廠用）。

`/install-profile <list>` 是 **replace 語意**：給的清單覆蓋既有 active set。要在現有 active set 上**追加**單一 profile，用 `/add-profile`。

## 可用 profile

| profile             | 狀態     | 說明                    |
| ------------------- | -------- | ----------------------- |
| `cnc-machining`     | ✅ 完整  | CNC 精密加工（v1 預設） |
| `injection-molding` | 🧪 alpha | 塑膠射出成型            |
| `pcb-assembly`      | 🚧 stub  | PCB 組裝                |
| `food-processing`   | 🚧 stub  | 食品加工                |
| `pharma`            | 🚧 stub  | 製藥（GMP）             |

## 使用範例

```bash
# 單 profile（v0.1.x 行為，仍支援）
/install-profile cnc-machining

# 多 profile 同時 active（v0.1.5+）
/install-profile cnc-machining,injection-molding

# 不帶參數：列出目前 active 的 profile(s)
/install-profile
```

## 多 profile 衝突規則

兩個 profile 若各自包含同名 `<kind>/<basename>.md`（譬如都有自己的 `agents/quote-specialist.md`），install.sh 會 **refuse-on-conflict**：明確列出衝突檔，要求人決定。詳：[`docs/profile-development.md`](../../docs/profile-development.md) 的 _多 profile 同時 active_ 段。

## Dry-run conflict scan

不確定某組合會不會衝突，先試：

```bash
bash adapters/claude-code/install.sh --list-conflicts cnc-machining,injection-molding
# 或：bash adapters/claude-code/install.sh --list-conflicts
#   （無參數 → 掃描所有 profile pair）
```

## 流程

1. 解析 comma-separated profile list；validate 每個都存在
2. 跨 profile 進行 conflict scan（多 profile 才跑）；任何衝突 → 不裝
3. 備份既有 install
4. Stage 1 core layer，Stage 2 依序 overlay 各 profile
5. 寫 `active-profiles.json`（aggregated manifest）+ `.installed`（含 `activeProfiles` 陣列）

詳細邏輯：[`docs/profile-development.md`](../../docs/profile-development.md)
