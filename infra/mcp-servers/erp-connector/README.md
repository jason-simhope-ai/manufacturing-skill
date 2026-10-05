# erp-connector

> Template MCP server for connecting AI agents to your ERP system (SAP / Oracle / 鼎新 / Workday / SAP Business One).

**v1 status: TEMPLATE ONLY.** Implementations are commercial / customer-specific.

---

## Why this is a template, not a working server

Every ERP is different (vendor, version, custom fields, schema). Hard-coding for one ERP would break for everyone else.

Instead, this template defines the **interface contract** — the tools your ERP connector should expose to manufacturing-skill agents. You implement the connector for your specific ERP.

---

## Required tools (interface contract)

介面定義在 [`contract.py`](contract.py)（Python 3.10+、僅標準函式庫、`ErpConnector` 為 ABC）。**所有工具的第一個參數都是 `ctx: CallContext`**；舊版自由字串 `operator` 已移除（字串可被偽造，`CallContext` 由 gateway 依已驗證的身分建立）。

### CallContext（每次呼叫都要帶）

| 欄位             | 型別          | 說明                                                                                   |
| ---------------- | ------------- | -------------------------------------------------------------------------------------- |
| `operator_id`    | `str`         | 請求人的穩定 ID（不是顯示名稱）                                                        |
| `role`           | `str`         | 角色，例如 `sales-coordinator`；決定欄位遮罩與寫入權限                                 |
| `channel`        | `str`         | 來源通道 / 介面，例如 `chat:ch-qa-floor`、`cli`                                        |
| `request_id`     | `str`         | 每次請求唯一，用來對照 gateway 與 ERP 的 log                                           |
| `classification` | `Tier`        | 通道資料分級 T0–T3                                                                     |
| `timestamp`      | `datetime`    | 請求時間，**必須帶時區**                                                               |
| `approval_token` | `str \| None` | 核准 token（不透明字串）。寫入工具必填；`repr()` 與 audit 內**不會**出現               |

`CallContext` 是 frozen dataclass，建立時就驗證欄位（空字串、無時區的時間、非 `Tier` 的分級都會 `ValueError`）。

### Read tools

| Tool                                                | Returns                                  | Used by agent                       |
| --------------------------------------------------- | ---------------------------------------- | ----------------------------------- |
| `get_customer` (ctx, customer_id)                   | 客戶主檔 + 分級 + 信用額度               | quote-specialist, sales-coordinator |
| `get_part_master` (ctx, part_no)                    | 料號主檔 + 規格 + 標準成本               | all                                 |
| `get_inventory` (ctx, part_no)                      | 即時庫存 + 在途 + 安全庫存               | inventory-manager                   |
| `get_recent_purchase_price` (ctx, part_no, days)    | 最近 N 天採購單價                        | quote-specialist                    |
| `get_machine_rate` (ctx, machine)                   | 機台費率（含人工 + 折舊 + 管理）         | quote-specialist                    |
| `get_credit_status` (ctx, customer_id)              | 客戶當前信用使用情況                     | sales-coordinator                   |

### List / query tools（有筆數上限與欄位白名單）

| Tool                                                           | 說明             |
| -------------------------------------------------------------- | ---------------- |
| `list_customers` (ctx, \*, grade, max_rows, fields)            | 客戶清單         |
| `list_parts` (ctx, \*, abc_class, max_rows, fields)            | 料號清單         |
| `list_inventory` (ctx, \*, below_safety_stock, max_rows, fields) | 庫存清單       |

- `max_rows`：預設 **200**，硬上限 **1000**（超過會被截到 1000，不報錯）；`< 1` 或非整數 → `ValueError`。回傳的 `ListResult` 帶 `total_matched`、`max_rows_applied`、`truncated`。
- `fields`：欄位白名單。不給 = 回傳所有「沒被遮罩」的欄位；要了不存在的欄位 → `ValueError`；要了被遮罩的欄位 → 不回傳，並列在 `masked_fields`。

### 預設欄位遮罩

| 群組               | 欄位                                                                                            | 預設可看的角色                        |
| ------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------- |
| `price`            | `standard_cost`、`hourly_rate`、`setup_rate`、`unit_price`、`credit_limit`、`credit_used`、`available` | quote-specialist、sales-coordinator   |
| `customer_contact` | `contact_name`、`contact_phone`、`contact_email`                                                | sales-coordinator                     |

未列出的角色（含未知角色）**一律看不到**（deny by default）。被遮罩的欄位值為 `None`，並列在結果的 `masked_fields`，所以「沒有資料」與「被遮罩」可以分辨。各公司可覆寫 `role_grants`；縮小權限永遠安全，放寬請先過資安審查。

### Write tools

| Tool                        | 動作                | 角色限制                          |
| --------------------------- | ------------------- | --------------------------------- |
| `create_sales_order`        | 建立 SO             | sales-coordinator                 |
| `create_purchase_request`   | 開立採購申請        | inventory-manager                 |
| `update_inventory_movement` | 進出料異動          | operator（透過 hook）、inventory-manager |
| `close_sales_order`         | 結案 SO（出貨確認） | sales-coordinator                 |

每個寫入工具：

- 必帶 **keyword-only `idempotency_key`**（1–128 個可列印字元）。同一個 key + 相同參數 → 回傳同一筆結果（`status="replayed"`），**不會重複建單**；同 key 但參數不同 → 拒絕 `idempotency_key_conflict`。
- 必須先呼叫 `authorize_write()`（內部呼叫你實作的 `verify_approval(token, action_hash)`），通過才可動 ERP。檢查順序：角色是否可用此工具 → 有無 token → token 驗證 → 核准人 ≠ 請求人（雙人核准）。
- 回傳 `WriteResult`（不再是裸 `str` / `bool`）：`status` 為 `committed` / `replayed` / `refused`，`record_id` 為 SO / PR / 異動單號，並帶 audit 欄位（`operator_id`、`role`、`channel`、`request_id`、`classification`、`approver_id`、`action_hash`、`idempotency_key`、`timestamp`、`reason`）。`WriteResult.audit_record()` 產出可直接寫入 audit log 的 dict。
- 數量與金額用 `Decimal`（不要 `float`）；時間一律帶時區。

### 核准 token（`verify_approval`）

`verify_approval(token, action_hash) -> ApprovalDecision` 是你必須實作的 hook。`action_hash` 由 `compute_action_hash(tool, args)` 計算（`sha256:` + 排序後 canonical JSON；不含 `ctx` 與 `idempotency_key`）。Token 由 `infra/chat-gateway/` 的聊天 gateway 在人員於互動元件按下核准後簽發（HMAC）；契約本身與廠商無關，任何核准服務只要符合以下條件即可：

- 簽章 / MAC 正確（常數時間比對）；
- **綁定這個 `action_hash`**（核准 10 件，就不能拿去下 10000 件）；
- 未過期；
- 帶有核准人 ID。

驗不過一律回傳 `ApprovalDecision(False, reason=...)`，**不要丟例外、也不要放行**。

### 參考實作

[`mock_connector.py`](mock_connector.py) 的 `MockErpConnector` 以 [`mock-data/erp_mock.json`](mock-data/erp_mock.json)（純合成資料）示範：欄位遮罩、筆數上限、idempotent 寫入、沒有有效 token 就拒絕、每次呼叫都有 audit 事件。它只用於測試與示範，**不要接真實 ERP**。測試：`python3 tests/mcp/test_erp_contract.py`。

---

## How to implement for your ERP

1. Fork this directory → 命名為 `erp-connector-<your-erp>` (e.g. `erp-connector-sap`)
2. 繼承 `ErpConnector`，實作所有抽象方法與 `verify_approval`；Python 3.10+
3. Map tool input/output to your ERP's schema

### Implementation checklist（真實 ERP）

- [ ] **每個工具都收 `ctx: CallContext`**；不要從別處（自由文字、環境變數）取得操作人
- [ ] **讀取用唯讀服務帳號**；寫入用另一組寫入服務帳號，且只給 connector，不給 agent / twin
- [ ] 每個寫入工具：驗 `idempotency_key` → `authorize_write()` → 查重 → 寫入 ERP → 回傳 `WriteResult`
- [ ] 冪等紀錄要**持久化**（資料庫 / ERP 的外部單號欄位），不是放記憶體；connector 重啟後重送同 key 仍不能重複建單
- [ ] 查重與寫入要在同一個交易 / 鎖內，避免兩個並行請求同時通過
- [ ] `verify_approval` 驗簽、綁 `action_hash`、檢查到期、核准人 ≠ 請求人；token 不得出現在 log
- [ ] 所有 list 工具套用 `clamp_max_rows()` 與 `project_fields()`；SQL 端也要 `LIMIT`，不要先撈全表再截
- [ ] 欄位遮罩依 `ctx.role`；自家客製欄位（特殊報價、客戶聯絡人、成本）要歸入 `price` / `customer_contact` 群組或新增群組
- [ ] **每次呼叫**（讀、寫、被拒）都用 `ctx` 寫 audit（覆寫 `record_audit` 寫進 append-only 儲存）
- [ ] 金額 / 數量用 `Decimal`；時間帶時區；ERP 內部時區要明確轉換
- [ ] 錯誤訊息不回傳 SQL、連線字串、堆疊
- [ ] 部署在內網；不要把 ERP 直接暴露到外網
- [ ] 用 `tests/mcp/test_erp_contract.py` 的案例當驗收基準（遮罩、上限、冪等、拒絕、audit 欄位），再跑 manufacturing-skill demo flow

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
- **查詢一律用唯讀 service account**（不用個人帳號）；寫入帳號只給 connector
- **寫入工具需要「核准 token + 角色」雙重把關**：角色不在允許清單 → 拒絕；沒有 token、token 過期 / 簽章不符 / 不是這個動作的 token / 核准人就是請求人 → 拒絕。Connector 在 ERP 端再驗一次（defense in depth），不能只相信上游 gateway
- 每個寫入都要有 `idempotency_key`，重試不會重複建單
- 價格與客戶聯絡資料預設遮罩，只有被授權的角色看得到；list 工具有筆數上限，避免整表被拖走
- **每次呼叫都記錄 audit，並帶完整 `CallContext`**（誰 `operator_id`、角色、通道、`request_id`、分級、核准人、`args_hash`、`idempotency_key`、結果 / 拒絕原因）；**不要記 `approval_token`**
- 對 IATF / ISO 客戶稽核，AI agent 操作 ERP 要可追溯

---

## v1 stub fallback

如果還沒接 ERP，agents 會自動降級用：

- `mock-data/` 內的 dummy 資料（`erp_mock.json`，純合成）
- 對於缺少的資料，產出 `[ASSUMED]` 標籤讓使用者知道哪裡是猜的

這樣 plugin 可以**先安裝、先試用**，不被 ERP 整合阻擋。
