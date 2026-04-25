---
name: install-profile
description: 啟用 / 切換 vertical profile（CNC / PCB / 射出 / 食品 / 製藥）
allowed-tools: [Read, Bash]
argument-hint: "[profile 名稱]"
---

# /install-profile — 啟用 vertical profile

切換目前作用中的 vertical profile。同時間只能有一個 profile 活躍。

## 可用 profile

| profile             | 狀態    | 說明                    |
| ------------------- | ------- | ----------------------- |
| `cnc-machining`     | ✅ 完整 | CNC 精密加工（v1 預設） |
| `pcb-assembly`      | 🚧 stub | PCB 組裝（社群協作中）  |
| `injection-molding` | 🚧 stub | 射出成型                |
| `food-processing`   | 🚧 stub | 食品加工                |
| `pharma`            | 🚧 stub | 製藥（GMP）             |

## 流程

1. 讀取 `profiles/<name>/profile.json`
2. 將 profile 內 agents / skills / know-how / hooks 註冊到目前 session
3. 同名檔案 override core 預設
4. 顯示啟用後的能力清單

## 使用範例

```
/install-profile cnc-machining
/install-profile pcb-assembly
/install-profile        # 不帶參數：列出目前啟用的 profile
```

詳細邏輯：`docs/profile-development.md`
