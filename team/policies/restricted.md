# T3 政策（高安規客製專案）

> Alpha 狀態：**只有政策與 lint，沒有執行期。** 任何 T3 內容、頻道或分身一律不在本版處理範圍。

## 定義

T3 = 高安規客製專案的任何資料，**包含該專案「是否存在」**（例：國防、航太、醫療器材客戶）。超過 T3 的等級不在任何 AI 系統的範圍內，本 repo 也不建模。

## Alpha 規則

1. **拒載**：`roster.json` 出現任何 `tier: T3` 的頻道或 `tierCeiling: T3` 的分身，gateway 直接 exit 3，不載入任何東西。
2. **追蹤檔不得出現 T3**：`teamctl check --ci`／`--strict` 遇到 T3 分身或頻道即報 `E043`。
3. **lint 底線**（`E043`，本機模式）：T3 分身只能綁 `mock` adapter、autonomy ≤ `draft`、`policy.cloudTierCeiling` 不得為 T3。
4. **不進 SaaS、不進雲端模型**：Slack、Discord 與雲端模型上限為 T1（T2 僅本機 mock）。
5. **不放進 repo**：T3 的任何字樣、專案代號、客戶名都只留在本機；repo 與 CI 只看得到「T3 被拒絕」這件事。
6. 內容疑似 T3 時，分身只回：「此內容可能屬 T3，不在本系統處理範圍，請依貴公司 T3 程序處理」。

## 往後（不在 alpha）

獨立主機、`<id>@<scope>` 實例、scope token、記憶牆、地端模型來源 allowlist、雙人核准，以及客戶書面同意與滲透測試，見 [設計 spec §14](../../docs/superpowers/specs/2026-10-05-digital-twin-team-design.md)。在那之前，高安規專案窗口只做規劃：把文件類型對應到 T2／T3，並確認 T3 不進 SaaS 與雲端。
