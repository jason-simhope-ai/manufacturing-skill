---
name: pre-ship
displayName: 出貨前最後檢查
trigger: before-ship-skill (OQC 通過後)
---

# pre-ship Hook

OQC 通過後、出貨前最後一道閘門。一旦東西出去就追不回來，所以這關要嚴。

---

## 檢查清單

- [ ] OQC 報告已產出且簽核
- [ ] 包裝符合客戶規範（如有 packaging spec）
- [ ] 標籤資訊正確：料號、批號、數量、客戶 PO、製造日期
- [ ] 隨貨文件齊全：
  - [ ] Packing List
  - [ ] 商業發票
  - [ ] COA / Mill Cert / 檢驗報告（依客戶要求）
  - [ ] Form A / CO（出口）
  - [ ] MSDS（化學品）
- [ ] INCOTERMS 確認
- [ ] 收貨人 / 地址 / 電話正確（與 SO 比對）
- [ ] 貨運安排確認（公司、車次、預計到貨日）

---

## 失敗處理

任一項缺：

```
🛑 出貨暫停 — 缺少：
- COA 未附（客戶 IATF 16949 必備）
- 標籤批號錯（標 LOT2026042100 但工單是 W2026042100123）

修正後重新觸發 pre-ship。
```

---

## 通過動作

- 寫入出貨紀錄到 ERP
- 發出貨通知給客戶（email / Telegram）
- 更新 scheduler-mcp，將 SO 標 closed
- 觸發應收帳款開立流程（依付款條件）
