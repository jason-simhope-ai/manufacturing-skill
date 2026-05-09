---
name: add-profile
description: 在現有 active set 上加一個 profile（v0.1.5+，與 /install-profile 互補）
allowed-tools: [Read, Bash]
argument-hint: "<profile 名稱>"
---

# /add-profile — 把一個 profile 加進 active set

`/install-profile` 是 **replace 語意**（給的清單蓋掉既有 active set）。`/add-profile` 是 **add 語意**（在既有 active set 上追加一個）。

例子：目前已 install `cnc-machining`，想再加上射出能力，但 CNC 那塊保留：

```bash
/add-profile injection-molding
# 等同於先讀 .installed 拿到 ["cnc-machining"]，
# 再執行 /install-profile cnc-machining,injection-molding
```

## 流程

1. 讀 `~/.claude/plugins/manufacturing-skill/.installed` 拿到目前的 `activeProfiles` 陣列
2. 把新 profile append 進去（若已在 list 內，warn 不重做）
3. 跑 `bash install.sh <list,with,new>` — 若有 conflict 會在這一步擋下，現有 install 不受影響（M5 atomicity）

## 與 conflict 互動

如果新加的 profile 跟現有任一 active profile 在 `<kind>/<basename>` 上撞名，install.sh **refuse**，現有 active set 完全不動。

跑前可以先 dry-run：

```bash
bash adapters/claude-code/install.sh --list-conflicts <existing>,<new>
```

## 移除 profile

目前**沒有** `/remove-profile`。要移除一個 profile，用 `/install-profile` 重新指定剩下的 profile（replace 語意）：

```bash
# 從 [cnc, injection] 移除 injection
/install-profile cnc-machining
```

未來如有需要可再加 `/remove-profile`，目前先靠 `/install-profile` replace。

## 不支援的情況

- `--core-only` 已 active 時呼叫 `/add-profile` → install.sh 會把 mode 從 core-only 切成 single-profile（接近 install 的 default 行為，但不會 silently 把 core-only 標記轉到 active set 外）
