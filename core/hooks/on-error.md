---
name: on-error
displayName: 異常統一升級處理
trigger: any-skill-error / quality-failure / production-exception
---

# on-error Hook

統一處理生產過程中的異常。

---

## 異常分類與升級表

| 異常類型                   | 嚴重度 | 立即升級對象                 | SLA           |
| -------------------------- | ------ | ---------------------------- | ------------- |
| 機台故障                   | 🔴 高  | 設備課 + production-planner  | 立即          |
| 連續 3 件 NG               | 🔴 高  | quality-inspector + 啟動 8D  | 立即停線      |
| 客戶客訴                   | 🔴 高  | sales-coordinator + 業務主管 | 4 小時內回應  |
| 缺料導致停線               | 🟠 中  | inventory-manager + 採購     | 1 小時內      |
| IPQC 異常（單件 NG）       | 🟠 中  | quality-inspector            | 30 分鐘內判定 |
| 進度落後 > 20%             | 🟠 中  | production-planner           | 當日內        |
| 文件變更（圖紙、BOM 改版） | 🟡 低  | 影響到的 agent + 工程        | 24 小時內同步 |
| 校驗工具過期               | 🟡 低  | quality-inspector + 校驗單位 | 7 天內        |

---

## 標準動作

無論哪種異常，都要做：

1. **記錄**：寫入 `logs/exceptions/EXC-YYYYMMDD-NNN.json`
   - 時間、人員、機台、工單、現象、量測值、現場照片
2. **隔離**：物理上把不良品 / 異常件分開
3. **升級**：依上表通知對應 agent / 人
4. **停止損失**：必要時停線、停接受新單
5. **根因分析**：5 Why（簡單）或 Fishbone（複雜）
6. **對策**：暫時對策（D3）+ 永久對策（D5）
7. **預防**：更新 SOP / 防呆 / 培訓 / SPC 規則

---

## 升級規則

如果 30 分鐘內負責 agent 無回應 → 自動升級給上一級主管。
2 小時內無人處理 → 通知廠長 + sales-coordinator（客戶可能受影響）。

---

## 與 ISO 9001 的對應

`on-error` hook 的所有紀錄就是 ISO 9001 / IATF 16949 稽核時的 **Corrective Action Records**。每筆都要可追溯。
