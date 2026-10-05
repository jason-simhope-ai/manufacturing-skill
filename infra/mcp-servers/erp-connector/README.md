# erp-connector

> Interface contract (Python ABC) for connecting AI agents to your ERP system (SAP / Oracle / 鼎新 / Workday / SAP Business One).

**v1 status: CONTRACT + MOCK ONLY — not an MCP server yet.** There is no `server.py` here and nothing to `claude mcp add`; see [Wrapping the connector as an MCP server](#wrapping-the-connector-as-an-mcp-server). Implementations are commercial / customer-specific.

---

## Why this is a contract, not a working server

Every ERP is different (vendor, version, custom fields, schema). Hard-coding for one ERP would break for everyone else.

Instead, this directory defines the **interface contract** — the tools your ERP connector should expose to manufacturing-skill agents — plus a mock and a conformance test suite. You implement the connector for your specific ERP.

---

## Required tools (interface contract)

介面定義在 [`contract.py`](contract.py)（Python 3.10+、僅標準函式庫、`ErpConnector` 為 ABC）。**所有工具的第一個參數都是 `ctx: CallContext`**；舊版自由字串 `operator` 已移除（字串可被偽造）。`CallContext` 由**可信的宿主程序**依已驗證的身分建立，絕不從模型或使用者輸入的文字取得：目前是包住 connector 的程式（例如單人 stdio MCP server 啟動時的設定——這只是便利設定，不是安全邊界）；等 chat gateway 的執行路徑上線後，由 gateway 每次請求建立。

### CallContext（每次呼叫都要帶）

| 欄位             | 型別          | 說明                                                                                   |
| ---------------- | ------------- | -------------------------------------------------------------------------------------- |
| `operator_id`    | `str`         | 請求人的**員工編號**（穩定 ID，絕不用顯示名稱）。gateway 自己的 audit 只留職位與 HMAC ref，執行時由 identities 名冊對照出員工編號 |
| `role`           | `str`         | 角色，例如 `sales-coordinator`；決定欄位遮罩與寫入權限                                 |
| `channel`        | `str`         | 來源通道 / 介面，例如 `chat:ch-qa-floor`、`cli`                                        |
| `request_id`     | `str`         | 每次請求唯一。**約定 = gateway audit 的 `event_id`**，gateway 的 hash chain 與 ERP audit 才有同一個 join key |
| `classification` | `Tier`        | 通道資料分級 T0–T3；與 gateway 的字串標籤互轉：`Tier["T2"]` / `tier.name`。gateway 不載入 T3 通道，connector 可另外拒絕 T3 的寫入 |
| `timestamp`      | `datetime`    | 請求時間，**必須帶時區**                                                               |
| `approval_token` | `str \| None` | 核准 token，格式見下方「核准 token」。寫入工具必填；`repr()` 與 audit 內**不會**出現   |

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

- `max_rows`：預設 **200**，硬上限 **1000**（超過會被截到 1000，不報錯）；`< 1` 或非整數 → `ValueError`。回傳的 `ListResult` 帶 `total_matched`、`max_rows_applied`、`truncated`（別名 `has_more`）。
- SQL 端用 `LIMIT cap + 1` 就知道 `truncated`，不必先撈全表。`total_matched` 可以是 `None`：只有在 `COUNT(*)` 便宜（有索引、view 不大）時才算，大 view 上就回 `None`。
- `fields`：欄位白名單。不給 = 回傳所有「沒被遮罩」的欄位；要了不存在的欄位 → `ValueError`；要了被遮罩的欄位 → 不回傳，並列在 `masked_fields`。

### 預設欄位遮罩

| 群組               | 欄位                                                                                            | 預設可看的角色                        |
| ------------------ | ----------------------------------------------------------------------------------------------- | ------------------------------------- |
| `price`            | `standard_cost`、`hourly_rate`、`setup_rate`、`unit_price`、`credit_limit`、`credit_used`、`available` | quote-specialist、sales-coordinator   |
| `customer_contact` | `contact_name`、`contact_phone`、`contact_email`                                                | sales-coordinator                     |

未列出的角色（含未知角色）**一律看不到**（deny by default）。被遮罩的欄位值為 `None`，並列在結果的 `masked_fields`，所以「沒有資料」與「被遮罩」可以分辨。各公司可覆寫 `role_grants`；縮小權限永遠安全，放寬請先過資安審查。

注意遮罩的範圍：

- **只遮「值」**。有哪些紀錄（客戶 id / 名稱清單、料號清單）本身不受遮罩；若某角色連清單都不該看到，請在你的 connector 依 `ctx.role` 直接拒絕該 list 工具。
- list 結果的 `masked_fields` 是**所有 row 的聯集**（這次查詢藏了哪些欄位），不是逐列標記。
- 自家客製欄位要歸入群組，覆寫 `sensitive_groups`（與 `role_grants` 一樣是 class attribute）：

```python
from contract import ErpConnector, SENSITIVE_GROUPS, PRICE_FIELDS, DEFAULT_ROLE_GRANTS

class MyConnector(ErpConnector):
    sensitive_groups = {
        **SENSITIVE_GROUPS,
        "price": PRICE_FIELDS | {"special_quote_price"},     # 併入既有群組
        "supplier_contact": frozenset({"supplier_tel"}),    # 新群組：預設沒有角色可看
    }
    role_grants = {**DEFAULT_ROLE_GRANTS,
                   "inventory-manager": frozenset({"supplier_contact"})}
```

### Write tools

| Tool                        | 動作                | 角色限制                          |
| --------------------------- | ------------------- | --------------------------------- |
| `create_sales_order`        | 建立 SO             | sales-coordinator                 |
| `create_purchase_request`   | 開立採購申請        | inventory-manager                 |
| `update_inventory_movement` | 進出料異動          | operator（透過 hook）、inventory-manager |
| `close_sales_order`         | 結案 SO（出貨確認） | sales-coordinator                 |

每個寫入工具：

- 必帶 **keyword-only `idempotency_key`**（1–128 個可列印字元）。同一個 key + 相同參數 → 回傳同一筆結果（`status="replayed"`），**不會重複建單**；同 key 但參數不同 → 拒絕 `idempotency_key_conflict`。
- 必須先呼叫 `authorize_write()`（內部呼叫你實作的 `verify_approval(token, action_hash)`），通過才可動 ERP。檢查順序：角色是否可用此工具 → 有無 token → token 驗證 → token 帶 `approval_id` → 核准人 ≠ 請求人（雙人核准）→ **核准人的角色可核准此工具**（`approver_roles[tool]`，預設 `DEFAULT_APPROVER_ROLES`，deny by default）。
- **一次核准只授權一筆寫入**：`authorize_write()` 是無狀態的，所以寫入路徑在查完冪等紀錄之後，若這個 `approval_id` 已經用另一個 key 寫過 → 拒絕 `approval_already_used`；第一次成功寫入時把 `approval_id` 記成已使用（跟冪等紀錄放在同一筆持久化資料，`approval_id` 加唯一索引）。同一個 key 重送仍是 `replayed`；驗證失敗、被拒絕的呼叫**不會**消耗核准。
- 回傳 `WriteResult`（不再是裸 `str` / `bool`）：`status` 為 `committed` / `replayed` / `refused`，`record_id` 為 SO / PR / 異動單號，並帶 audit 欄位（`operator_id`、`role`、`channel`、`request_id`、`classification`、`approver_id`、`approver_role`、`approval_id`、`action_hash`、`idempotency_key`、`timestamp`、`reason`）。`WriteResult.audit_record()` 產出可直接寫入 audit log 的 dict。
- 數量與金額用 `Decimal`（不要 `float`）；時間一律帶時區。

拒絕原因（`reason`，常數在 `contract.py` 的 `REASON_*`）：`role_not_permitted`、`approval_required`、`approval_malformed`、`approval_signature_invalid`、`approval_expired`、`self_approval`、`approver_role_not_permitted`、`approval_already_used`、`idempotency_key_conflict`，以及 connector 自己的 `validation:<原因>`。

### 核准 token（`verify_approval`）

**現況（誠實說明）**：目前**沒有任何程式會簽發這個 token**。chat gateway（`infra/chat-gateway/`，另一個 PR）只在聊天室貼出核准卡片（approval id + nonce + args hash），它的 `execute()` 執行路徑延後實作（gateway spec §14），也還不碰 ERP。因此**以本 connector 為準**：canonical 的 action hash 與 token 格式定義在 [`contract.py`](contract.py)，gateway 實作執行路徑時採用同一份定義（直接 import 這兩個函式，或照下列規格逐位元組重做並跑同一組 golden 向量）。在那之前，只有測試與 mock 會用 `issue_approval_token` 簽 token。

`verify_approval(token, action_hash) -> ApprovalDecision` 是你必須實作的 hook；最簡單的合規實作就是呼叫 `verify_approval_token(secret, token, action_hash, now=...)`。

**Action hash（canonical）**

```text
action_hash = "sha256:" + hex( sha256( utf8( json.dumps(
                  {"tool": <工具名>, "args": canonical_args(<args>)},
                  sort_keys=True, separators=(",", ":"), ensure_ascii=False) ) ) )
```

- 不含 `ctx` 與 `idempotency_key`；沒有 `default=`，無法表示的型別直接丟 `CanonicalArgsError`（`ValueError` 子類），不會被默默字串化。
- `args` 用**原生型別**傳（`datetime`、`Decimal`），不要自己先 `isoformat()` / `str()`：字串會原樣進 hash。

**線上表示規則（`canonical_args`，hash 之前套用）**

| 型別 | 表示 | 例 |
| --- | --- | --- |
| `int`、`Decimal` | 正規化十進位**字串**：無指數、去尾零、`-0` → `"0"` | `10`、`Decimal("10")`、`Decimal("10.00")` → `"10"`；`Decimal("0.50")` → `"0.5"` |
| `float` | **拒絕**（`CanonicalArgsError`，訊息含欄位路徑）。進來的 JSON 用 `json.loads(..., parse_float=Decimal)` 解析 | `{"qty": 10.0}` → error at `args.qty` |
| `datetime` | UTC ISO-8601，`Z` 結尾；naive → 拒絕 | `2026-05-20T08:00+08:00` → `"2026-05-20T00:00:00Z"` |
| `date` | `YYYY-MM-DD` | |
| `tuple` / `list` | JSON array | |
| `dict` | key 必須是 `str` | |
| `str`、`bool`、`None` | 原樣（字串 `"10.00"` 不會被正規化） | |

Golden 向量（`tests/mcp/test_erp_contract.py` 的 `test_golden_vector`）：`create_sales_order`、`{"customer_id": "C-A001", "items": [{"part_no": "BR-12345", "qty": Decimal("10.00")}], "delivery_date": 2026-05-20 08:00 Asia/Taipei, "po_reference": "PO-客戶-1"}` → `sha256:89dd2d286dd6ab1c90eac72608f640379a5820295bde8ac1233ebc36c3be71a5`。

**Token 格式（canonical，v1）**

```text
token = "v1|<approver_id>|<approver_role>|<approval_id>|<expiry>|<mac>"
mac   = hex( HMAC-SHA256(secret, utf8("v1|<approver_id>|<approver_role>|<approval_id>|<expiry>|<action_hash>")) )
```

`expiry` 為整數 Unix 秒；`approval_id` 每次核准唯一；欄位不得含 `|`。驗證條件：

- 簽章 / MAC 正確（常數時間比對）；
- **綁定這個 `action_hash`**（核准 10 件，就不能拿去下 10000 件）；
- 未過期（`DEFAULT_APPROVAL_TTL_SECONDS` = 900）；
- 帶有核准人 ID、核准人角色、`approval_id`。

驗不過一律回傳 `ApprovalDecision(False, reason=...)`，**不要丟例外、也不要放行**。

### 結果序列化與時區

結果型別是 dataclass，裡面有 `Decimal` 與 `datetime`，`json.dumps(asdict(...))` 會失敗。對外（MCP 工具輸出、log）一律用 `to_jsonable()`，規則與上表相同（`Decimal` → 正規化字串、`datetime` → UTC `Z`、tuple → list），但整數保持 JSON 數字；遇到 `float` 一樣拒絕：

```python
import json
from contract import to_jsonable

result = connector.get_customer(ctx, "C-A001")
print(json.dumps(to_jsonable(result), ensure_ascii=False))
# {"id": "C-A001", ..., "credit_limit": "5000000", "masked_fields": ["contact_email", ...]}
```

時區：`InventorySnapshot`、`MachineRate`、`PurchasePrice`、`WriteResult` 在建立時就拒絕 naive `datetime`。ERP 的 SQL view 若存本地時間，讀出來用 `aware(naive, "Asia/Taipei")` 補上時區（已帶時區的值原樣回傳）。經過 `to_jsonable()` 後一律是 UTC `Z`，與 scheduler-mcp 的格式一致。

### 參考實作

[`mock_connector.py`](mock_connector.py) 的 `MockErpConnector` 以 [`mock-data/erp_mock.json`](mock-data/erp_mock.json)（純合成資料）示範：欄位遮罩、筆數上限、idempotent 寫入、沒有有效 token 就拒絕、一次核准只寫一筆、核准人角色檢查、每次呼叫都有 audit 事件。它只用於測試與示範，**不要接真實 ERP**。測試：`python3 tests/mcp/test_erp_contract.py`。

### 用 conformance suite 驗收你自己的 connector

[`tests/mcp/test_erp_contract.py`](../../../tests/mcp/test_erp_contract.py) 的 `ConformanceSuite` 是 mixin，只用 `ErpConnector` 的公開 API（不讀 mock 內部的 `.sales_orders`、`.audit_log`，audit 是包住 `record_audit` 攔下來的）。你只要實作 `make_connector(clock)`：

- 讀取端要提供合成 fixture `mock-data/erp_mock.json` 的資料（例如灌進測試 DB / view）；
- token 到期與「最近 N 天」要用傳進來的 `clock`；
- token 用 canonical 格式（`verify_approval_token`）；若你的核准服務不同，覆寫 `issue_token`。
- 可選：覆寫 `written_count(tool)` / `assert_written(tool, record_id)`，讓 suite 也檢查你後端實際寫了幾筆。

```python
# tests/test_my_erp.py
import sys, unittest
sys.path.insert(0, "/path/to/manufacturing-skill/tests/mcp")
import test_erp_contract as erp   # 匯入模組（不要 from ... import *），mock 的 TestCase 才不會被一起收進來

class MyErpConformance(erp.ConformanceSuite, unittest.TestCase):
    def make_connector(self, clock):
        return MyErpConnector(approval_secret=erp.SECRET, clock=clock,
                              read_db=load_fixture_into_test_db(erp.FIXTURE_PATH))

if __name__ == "__main__":
    unittest.main()
```

執行：`python3 tests/test_my_erp.py`。只依賴 mock 行為的檢查（mock 自己的庫存驗證、記憶體內的單據狀態、1200 筆大資料）在 `MockSpecific` / `RowCaps`，不屬於 suite。

---

## How to implement for your ERP

1. Fork this directory → 命名為 `erp-connector-<your-erp>` (e.g. `erp-connector-sap`)
2. 繼承 `ErpConnector`，實作所有抽象方法與 `verify_approval`；Python 3.10+
3. Map tool input/output to your ERP's schema

### Implementation checklist（真實 ERP）

- [ ] **每個工具都收 `ctx: CallContext`**；不要從模型或使用者的自由文字取得操作人
- [ ] **讀取可走唯讀 view / read-only replica**，用唯讀服務帳號；**寫入一律走 ERP 官方 API 或單據介面**（REST / OData / 單據匯入），**絕不直接 INSERT / UPDATE 單據表**（會繞過 ERP 的商業邏輯、編號與簽核）。寫入服務帳號只給 connector，不給 agent / twin
- [ ] 每個寫入工具：驗 `idempotency_key` → `authorize_write()` → 查冪等紀錄（replay / conflict）→ 檢查 `approval_id` 未被使用 → 寫入 ERP → 標記完成並消耗 `approval_id` → 回傳 `WriteResult`
- [ ] 冪等紀錄（含 `approval_id`）要**持久化**，不是放記憶體；connector 重啟後重送同 key 仍不能重複建單
- [ ] 本地冪等表與 ERP API **不可能在同一個交易裡**，請用「先預留、帶外部單號寫入、再標完成」（見下方）
- [ ] `verify_approval` 驗簽、綁 `action_hash`、檢查到期，回傳 `approver_id`、`approver_role`、`approval_id`；token 不得出現在 log
- [ ] 所有 list 工具套用 `clamp_max_rows()` 與 `project_fields()`；SQL 端也要 `LIMIT`，不要先撈全表再截
- [ ] 欄位遮罩依 `ctx.role`；自家客製欄位（特殊報價、客戶聯絡人、成本）用 `sensitive_groups` 歸入 `price` / `customer_contact` 群組或新增群組（範例見上方）
- [ ] **每次呼叫**（讀、寫、被拒）都用 `ctx` 寫 audit。預設 `record_audit` 把每筆事件以一行 JSON 寫到 **stderr**（不會被默默丟掉）；正式環境請覆寫成 append-only 儲存
- [ ] 金額 / 數量用 `Decimal`；時間帶時區（naive 用 `aware()` 補）；對外輸出用 `to_jsonable()`
- [ ] 錯誤訊息不回傳 SQL、連線字串、堆疊
- [ ] 部署在內網；不要把 ERP 直接暴露到外網
- [ ] 用 `ConformanceSuite` 對你自己的類別跑驗收（見上方），再跑 manufacturing-skill demo flow

### 冪等寫入的參考模式（本地狀態 DB + ERP API）

ERP 寫入走 API，本地冪等表在自己的 DB，兩者不會在同一個交易裡。用 ERP 單據上的**外部單號欄位**（external reference，例如 `AI-<tool>-<idempotency_key>`）串起來：

1. **預留**：在本地狀態 DB 的交易 / 鎖內查 `(tool, idempotency_key)`：已 `done` → `replayed`；hash 不同 → `idempotency_key_conflict`；`approval_id` 已被別的 key 用過 → `approval_already_used`；否則寫一筆 `pending`（含 `action_hash`、`approval_id`）。唯一索引擋掉並行的第二個請求。
2. **寫入**：帶外部單號呼叫 ERP API（不在本地交易裡）。
3. **標完成**：拿到 ERP 單號後把該筆改成 `done` + `record_id`，`approval_id` 從此算已使用。
4. **回應遺失 / 逾時 / connector 重啟**：遇到 `pending` 的 key，**先用外部單號向 ERP 查**；查到就補標 `done` 並回傳該單號，查不到才重送。這樣「ERP 已建單但回應沒回來」不會變成兩張單。

如果 ERP 單據沒有可查詢的外部單號欄位，就做不到「回應遺失後安全重送」：請先請 ERP 端加欄位或用單據備註 + 查詢介面替代；在那之前 `pending` 的請求只能交給人工確認，不可自動重送。

---

## Common ERP integration patterns

| ERP                      | 通常透過               | 注意                                               |
| ------------------------ | ---------------------- | -------------------------------------------------- |
| SAP S/4 HANA             | OData / RFC            | Authorization 嚴，service user 要 SAP_ALL 是不行的 |
| Oracle EBS               | 寫：REST API；讀：REST 或 DB direct | DB direct 只限讀取，且要走 read-only replica |
| 鼎新 (TipTop / Workflow) | 讀：唯讀 view（MS SQL）；寫：官方 API / 單據介面 | 客製欄位多，schema 須對齊；不要直接寫單據表 |
| SAP Business One         | Service Layer (REST)   | One 的 schema 簡單，整合相對容易                   |
| Microsoft Dynamics 365   | OData / Power Automate | 適合 cloud-first 公司                              |

---

## Security & compliance

- 所有 ERP 連線走內網（不要過公網）
- **查詢一律用唯讀 service account**（不用個人帳號）；寫入帳號只給 connector
- **寫入工具需要「核准 token + 角色」雙重把關**：角色不在允許清單 → 拒絕；沒有 token、token 過期 / 簽章不符 / 不是這個動作的 token / 核准人就是請求人 → 拒絕。Connector 在 ERP 端再驗一次（defense in depth），不能只相信上游 gateway
- 每個寫入都要有 `idempotency_key`，重試不會重複建單
- 價格與客戶聯絡資料預設遮罩，只有被授權的角色看得到；list 工具有筆數上限，避免整表被拖走
- **寫入只走 ERP 官方 API / 單據介面**；DB direct 只用於讀取（唯讀 view / replica）
- **一次核准只授權一筆寫入**，且核准人的角色必須被允許核准該工具
- **每次呼叫都記錄 audit，並帶完整 `CallContext`**（誰 `operator_id`、角色、通道、`request_id`、分級、核准人與其角色、`approval_id`、`args_hash`、`idempotency_key`、結果 / 拒絕原因）；**不要記 `approval_token`**。預設寫 stderr，正式環境覆寫 `record_audit`
- 對 IATF / ISO 客戶稽核，AI agent 操作 ERP 要可追溯

---

## Wrapping the connector as an MCP server

**目前還沒有。** 這個目錄沒有 `server.py`，`profile.json` 把 `erp-connector` 列為推薦 MCP 只代表「接好之後該有它」。stdio JSON-RPC 的 plumbing 由 scheduler-mcp 的 PR 提供；為了不複製兩份，ERP 的 server 是**等 scheduler 的 protocol 落地之後的 follow-up**。預計長這樣：

```bash
python3 infra/mcp-servers/erp-connector/server.py --connector my_erp_connector:MyErpConnector
```

- 只先暴露**讀取與 list 工具**；輸出經 `to_jsonable()`。
- `CallContext` 來源：單人桌面 stdio = 啟動時的設定（便利設定，不是安全邊界）；多人共用要走 HTTP transport，由 gateway 依已驗證身分建立 ctx。
- 寫入工具**不會**讓模型傳 `approval_token`（token 會進對話與 transcript，模型也拿不到合法 token）；寫入要等核准服務（gateway 執行路徑）上線後，以 approval id 向核准服務取結果。

### 註冊時的 scope（`claude mcp add`）

等你有自己的 server 之後（或註冊任何 stdio MCP server 時），**一律用絕對路徑**：相對路徑只在註冊當下的目錄有效，換個目錄開 Claude Code 就會 `Failed to connect`。

```bash
claude mcp add -s project erp -- python3 /opt/manufacturing-skill/infra/mcp-servers/erp-connector/server.py \
  --connector my_erp_connector:MyErpConnector
```

| `-s` scope | 寫到哪裡 | 誰看得到 | 何時用 |
| --- | --- | --- | --- |
| `local`（預設） | `~/.claude.json` 裡該專案目錄的設定 | 只有你、只在**註冊時那個資料夾** | 個人試驗 |
| `project` | 專案根目錄的 `.mcp.json`（可進 git） | 整個團隊；成員第一次使用時要核准 | 團隊共用（建議） |
| `user` | `~/.claude.json` 的全域設定 | 只有你、所有資料夾 | 個人常用 |

用 `-e KEY=value` 設的環境變數會以明文存進上表的設定檔；不要把 ERP 密碼放在那裡，改用 OS 的 secret 機制或服務帳號設定檔。確切旗標以 `claude mcp add --help` 為準。

---

## v1 stub fallback

如果還沒接 ERP，agents 會自動降級用：

- `mock-data/` 內的 dummy 資料（`erp_mock.json`，純合成）
- 對於缺少的資料，產出 `[ASSUMED]` 標籤讓使用者知道哪裡是猜的

這樣 plugin 可以**先安裝、先試用**，不被 ERP 整合阻擋。
