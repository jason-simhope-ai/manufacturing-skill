# erp-connector

> Template MCP server for connecting AI agents to your ERP system (SAP / Oracle / 鼎新 / Workday / SAP Business One).

**v1 status: TEMPLATE ONLY.** Implementations are commercial / customer-specific.

---

## Why this is a template, not a working server

Every ERP is different (vendor, version, custom fields, schema). Hard-coding for one ERP would break for everyone else.

Instead, this template defines the **interface contract** — the tools your ERP connector should expose to manufacturing-skill agents. You implement the connector for your specific ERP.

---

## Required tools (interface contract)

Your connector must implement:

### Read tools

| Tool                                        | Returns                                  | Used by agent                       |
| ------------------------------------------- | ---------------------------------------- | ----------------------------------- |
| `get_customer` (id)                         | customer master record + 分級 + 信用額度 | quote-specialist, sales-coordinator |
| `get_part_master` (part_no)                 | part master + 規格 + 標準成本            | all                                 |
| `get_inventory` (part_no)                   | 即時庫存 + 在途 + 安全庫存               | inventory-manager                   |
| `get_recent_purchase_price` (part_no, days) | 最近 N 天採購單價                        | quote-specialist                    |
| `get_machine_rate` (machine)                | 機台費率（含人工 + 折舊 + 管理）         | quote-specialist                    |
| `get_sales_order` (so_id)                   | SO 詳細                                  | sales-coordinator                   |
| `list_open_pos` ()                          | 未交 PO 清單                             | inventory-manager                   |
| `get_credit_status` (customer_id)           | 客戶當前信用使用情況                     | sales-coordinator                   |

### Write tools

| Tool                        | 動作                | 角色限制             |
| --------------------------- | ------------------- | -------------------- |
| `create_sales_order`        | 建立 SO             | sales-coordinator    |
| `create_purchase_request`   | 開立採購申請        | inventory-manager    |
| `update_inventory_movement` | 進出料異動          | operator (透過 hook) |
| `close_sales_order`         | 結案 SO（出貨確認） | sales-coordinator    |

---

## How to implement for your ERP

1. Fork this directory → 命名為 `erp-connector-<your-erp>` (e.g. `erp-connector-sap`)
2. Implement tools in `server.py` connecting to your ERP API / DB
3. Map tool input/output to your ERP's schema
4. Add auth (most ERPs require service account)
5. Test against the manufacturing-skill demo flow
6. Deploy as on-prem MCP server (security: 不要把 ERP 直接暴露到外網)

---

## Common ERP integration patterns

| ERP                      | 通常透過               | 注意                                               |
| ------------------------ | ---------------------- | -------------------------------------------------- |
| SAP S/4 HANA             | OData / RFC            | Authorization 嚴，service user 要 SAP_ALL 是不行的 |
| Oracle EBS               | REST API / DB direct   | DB direct 要走 read-only replica                   |
| 鼎新 (TipTop / Workflow) | DB direct (MS SQL)     | 客製欄位多，schema 須對齊                          |
| SAP Business One         | Service Layer (REST)   | One 的 schema 簡單，整合相對容易                   |
| Microsoft Dynamics 365   | OData / Power Automate | 適合 cloud-first 公司                              |

---

## Security & compliance

- 所有 ERP 連線走內網（不要過公網）
- AI agent 對 ERP 只用 **service account**（不用個人帳號）
- 所有 write 動作要記錄到 audit log（誰、何時、什麼動作、ERP 回應）
- 對 IATF / ISO 客戶稽核，AI agent 操作 ERP 要可追溯

---

## v1 stub fallback

如果還沒接 ERP，agents 會自動降級用：

- `mock-data/` 內的 dummy 資料
- 對於缺少的資料，產出 `[ASSUMED]` 標籤讓使用者知道哪裡是猜的

這樣 plugin 可以**先安裝、先試用**，不被 ERP 整合阻擋。
