# 顧問交付包（Consulting Kit）

> 給「拿這個 plugin 去客戶端導入」的人：把導入指南裡散在各處的做法，整理成可直接帶進客戶會議的六份文件。
> 全部是**範本**：金額一律是「範例」佔位、公司名一律用「客戶／甲方／乙方」、法律條款請**法務審閱**後才能使用。
> 本資料夾不含任何真實客戶資料，也不接受真實客戶資料（見 [SOW 範本](sow-template.md) 第 7 節）。

## 這是誰用的

| 讀者 | 怎麼用 |
| ---- | ------ |
| AI 導入顧問 / SI | 全套：工作坊 → 問卷 → SOW → pilot 一頁紙 → 交付物清單 |
| 內部專案負責人 | 略過 SOW 的費用與 IP 章節；用工作坊、問卷、一頁紙說服老闆與 IT |
| 客戶的 IT / 資安 | 直接看 [IT 資料流向問卷](it-data-flow-questionnaire.md)，那裡寫的是「repo 今天能誠實回答的」 |

## 檔案與導入階段的對應

導入階段沿用 [導入指南](../adoption-guide.md) 的 W0–W6；「團隊層」指 `team/` 分身 alpha 的 Wave 0 / Wave 1（選配；先照上方「帶去客戶前」確認 `team/` 在你手上的版本存在）。

| 階段（導入指南） | 目標 | 用哪份文件 |
| ---------------- | ---- | ---------- |
| W0 先決定要不要做 | 該不該做、做哪幾個職位、客戶 IT 能不能接受 | [探索工作坊](discovery-workshop-90min.md)、[IT 問卷](it-data-flow-questionnaire.md) |
| W0 末 | 簽約與簽 pilot 範圍 | [SOW 範本](sow-template.md)、[pilot 一頁紙](pilot-one-pager.md) |
| W1–W2 環境與安裝 | 裝好、被載入、合成資料 demo | [交付物清單](deliverables-checklist.md) 的 W1–W2 區 |
| W3–W4 客製與資料 | company-facts、閘門紀錄、去識別 | 交付物清單 W3–W4 區 |
| W5–W6 試跑與上線 | 六週 pilot、每週指標、稽核錨點簽收 | pilot 一頁紙、交付物清單 W5–W6 區 |

建議順序：**先工作坊，再問卷，簽完 SOW 才碰客戶環境**。工作坊的閘門若判「流程修正」，就不要進 SOW。

## 帶去客戶前：先確認你手上的版本

本套文件引用的檔案與行為會隨 repo 版本增減。**帶去客戶前，請在你手上的版本逐項確認**；確認不了就不要承諾，改用「規劃中」或「未交付」的說法。

| 要確認的事 | 怎麼確認 |
| ---------- | -------- |
| 安裝後 plugin 真的被 Claude Code 載入 | 安裝後執行 `claude plugin list`，確認看得到；安裝訊息顯示成功不等於已載入 |
| explainer 01 / 02 呈現的是真實資料流向 | 開啟 `docs/explainers/01`、`02`，確認寫的是「雲端預設、地端選配且未端到端驗證」，沒有「資料不出公司」「完全 air-gap」；`README.zh-TW.md`、`manufacturing.md` 同樣檢查。確認前不要把它們交給客戶的稽核員或 IT |
| 引用的檔案存在 | 文件裡寫到的路徑（例：`docs/data-classification.md`、`docs/permissions-template.md`、`examples/company-facts.template.md`、`adapters/generic/export.py`、`team/`、`infra/chat-gateway/`）逐一 `ls`；不存在就標「未交付」 |
| scheduler MCP 唯讀 | 用 `claude mcp list` 確認伺服器 `manufacturing-scheduler` 已註冊；它唯讀、讀 mock data，沒有寫入工具，也沒有接真實 MES |

## 這套文件不做的事

- 不替你報價：沒有任何一個數字是「建議價」；費用表只給結構。
- 不是法律文件：保密、責任上限、智慧財產、個資條款都只是提問清單，請法務審閱。
- 不保證 repo 沒有的能力：scheduler MCP（`manufacturing-scheduler`）唯讀、讀 mock data、未接真實 MES（用 `claude mcp list` 確認）；erp-connector 只有介面契約；沒有任何特定 ERP 的現成實作。
  報價時把 ERP / MES 串接當成「自寫 connector」另列，不要放進固定價。
- 不含「沖壓、食品等非機加廠」的專屬範本：`company-facts` 範本偏機加 / 壓鑄 / 射出，其他產業要自己補欄位（在工作坊就要講明）。
