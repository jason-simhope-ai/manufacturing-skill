---
name: post-order
displayName: 接單後通知與排程觸發
trigger: after-order-skill (SO 建立完成)
---

# post-order Hook

SO 建立完成後自動觸發，確保「客戶 PO 變成內部行動」不漏接。

---

## 觸發動作

並行執行：

### 1. 通知 production-planner

- 提醒生管 / MES 操作員把新 SO 加入待排隊列（`manufacturing-scheduler` 唯讀，AI 只準備要建立的資料）
- 自動跑一次 `capacity-planning` 評估能否準時
- 如果預估 > 客戶交期 → 立即標紅，回報 sales-coordinator

### 2. 通知 inventory-manager

- 自動跑 BOM 展開
- 對缺料項建立採購建議
- 缺料 + 長 lead time 的料 → 立即提報採購

### 3. 通知客戶

- **產生**PO 收件確認草稿（email / Telegram 文字），**不自動寄出**
- 草稿內附初估開工日（基於 capacity-planning）
- 由業助檢視、必要時修改，**人工確認後才送出**（對外通知會代表公司承諾交期與數量，須有人負責）

### 4. 紀錄

- 寫入 `logs/orders/SO-XXXX.json`（traceability）
- 連結 PO 原檔、Quote、SO

---

## 失敗處理

任何子動作失敗：

- production-planner 排不下 → 升級給生產主管
- 採購提報失敗 → 升級給採購主管
- 客戶通知草稿產生失敗 → 業助手動撰寫並寄出

**不能因為 hook 失敗就讓 SO 卡在中間狀態**。
