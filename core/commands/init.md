---
name: init
description: 互動式安裝引導 — 第一次使用者不知道從哪開始時用這個
allowed-tools: [Read, Bash, Glob]
argument-hint: ""
---

# /manufacturing init — 互動式安裝引導

第一次裝 manufacturing-skill 不知道從哪開始？打 `/manufacturing init`，AI 會引導你 4 個問題、3 分鐘搞定。

---

## 引導對話流程

### 問題 1：你的工廠主要做什麼？

```
A) CNC 精密加工 / 金屬切削                ✅ v1 完整支援
B) PCB 組裝 / 電子產品                   🚧 stub
C) 塑膠射出成型 / 模具                   🚧 stub
D) 食品加工 / 飲料 / 烘焙                🚧 stub
E) 製藥 / 生技                          🚧 stub（合規敏感）
F) 多元化 / 還沒決定 / 想先試試框架       → core-only 模式
G) 其他（板金、紡織、化工、模具...）       → 引導 fork CNC profile 客製
```

### 問題 2：你的工廠有 ERP / MES 嗎？

```
A) 有 SAP / Oracle / 鼎新 / Workday      → 後續引導接 erp-connector
B) 有 ERP 但不在以上清單                 → 引導用 erp-connector contract 自己接
C) 沒有 / 還在用 Excel + 紙本             → 先用 mock data 試跑
```

### 問題 3：你的資安需求？

```
A) 客戶會稽核（IATF / ISO / 醫材）        → 建議地端 Ollama + 完全 air-gap
B) 一般商務、不外流就好                  → 雲端 Claude 即可，先試再說
C) 完全不在乎 / 純試玩                   → 雲端 Claude，最快有東西
```

### 問題 4：你想先看什麼？

```
A) 直接 demo /quote 跑一輪              → 載入 examples/sample-drawing/bracket.md
B) 看架構圖卡（4 張）                    → 開 docs/explainers/
C) 讀導入顧問 playbook                  → 開 docs/adoption-guide.md
D) 開始客製化我的 profile                → 開 docs/profile-development.md
```

---

## 引導完成後 AI 會：

1. 根據答案輸出**個人化建議**：

   ```
   你選了：CNC + 鼎新 ERP + IATF 客戶 + 直接 demo

   建議流程：
   1. ✅ 已 install 好 cnc-machining profile
   2. 🔧 接 erp-connector：fork erp-connector/ 改成 erp-connector-tiptop
   3. 🛡️ 設定 .gitignore 排除圖紙、設定 Ollama 本地（後續再做）
   4. 🚀 現在馬上試：/quote @examples/sample-drawing/bracket.md
   ```

2. 寫入 `~/.claude/plugins/manufacturing-skill/.user-profile.json` 記錄選擇
3. 之後每次叫 `/manufacturing` 都會優先顯示對你的下一步建議

---

## 跳過引導

如果你已經知道要什麼：

- `bash adapters/claude-code/install.sh <profile>` — 直接 install
- `bash adapters/claude-code/install.sh --core-only` — 跳過 profile，先試框架
- `/install-profile <name>` — install 後切換 profile
