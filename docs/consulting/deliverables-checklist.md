# 交付物清單（逐階段打勾）

> 每項寫明「由哪個 repo 成品產生」。**交付前先確認該檔案在你手上的版本存在**（`ls` 即可），
> 不存在就把該項標「未交付（此版本沒有該成品）」並告知客戶，不要用手寫替代再說是 repo 的功能。
> 驗收編號（A1–A6）對應 [SOW 範本](sow-template.md) 第 3 節。

## W0 評估

| ☐ | 交付物 | 產生來源 |
| - | ------ | -------- |
| ☐ | 工作坊紀錄、候選清單（三分類） | [探索工作坊](discovery-workshop-90min.md) |
| ☐ | 閘門紀錄 × N 個職位（A3） | `team/gate/need-a-twin.md` 的「輸出：貼進 roster 的片段」；團隊層以外用工作坊的 6 題表 |
| ☐ | IT 問卷答覆（含客戶決定欄） | [IT 問卷](it-data-flow-questionnaire.md) |
| ☐ | 資料分級表（候選清單每項標 T0–T3） | `docs/data-classification.md` |
| ☐ | 已簽 SOW 與 pilot 一頁紙 | [SOW 範本](sow-template.md)、[pilot 一頁紙](pilot-one-pager.md) |

## W1–W2 安裝驗證

| ☐ | 交付物 | 產生來源 |
| - | ------ | -------- |
| ☐ | 安裝成功紀錄（A1：`claude plugin list` 顯示已載入，附截圖） | `adapters/claude-code/install.sh`；以 `claude plugin list` 的實際輸出為準 |
| ☐ | `/quote` 合成資料 demo 紀錄（A2） | `examples/sample-drawing/bracket.md`、`examples/sample-bom/bracket-bom.csv` |
| ☐ | 權限設定檔（allow / ask / deny）與限制說明 | `docs/permissions-template.md` |
| ☐ | 給老闆與現場的說明卡 | `docs/explainers/03`、`04`（可交付，頁尾印的是原作者聯絡方式，白標要自行更換）；`01`、`02` 交付前先確認 explainer 顯示的是真實資料流向（雲端預設、地端選配未驗證），沒有「不外流」「完全 air-gap」宣稱，**確認前不交** |
| ☐ | 通用 export 包（給非 Claude 工具；選配） | `python3 adapters/generic/export.py --profiles <p> --out <dir> --format bundle --reproducible`（含 Claude Code 專屬指令，不是給老闆看的） |

## W3–W4 客製與資料

| ☐ | 交付物 | 產生來源 |
| - | ------ | -------- |
| ☐ | `company-facts.md`（客戶自存、放 repo 外、不 commit）；§8 核准表已填 | `examples/company-facts.template.md`；非機加廠需自行補欄位 |
| ☐ | T2 雲端核准單（若客戶允許）：核准人、合約條款、方案與確認日、保存期限 | IT 問卷第二節的「客戶決定」；格式由客戶訂 |
| ☐ | 私有 profile fork 差異清單（不含真名與單價） | `docs/profile-development.md`；上游同步做法由乙方寫入結案報告 |
| ☐ | 去識別流程與抽查紀錄（無真名、客戶名、圖號） | `team/tools/deid.py`、`team/local/README.md` |
| ☐ | 部署檢核表 A–I 區（A5，團隊層） | `docs/adoption-guide.md` 團隊段的「部署檢核表」 |
| ☐ | 角色指派：核准人、金鑰保管人、簽收人（互不兼任、皆非顧問） | pilot 一頁紙第 7 欄 |

## W5–W6 試跑與上線

| ☐ | 交付物 | 產生來源 |
| - | ------ | -------- |
| ☐ | 每週指標記錄 × N 週（A4：修改比例、人先寫比例、review 出席率） | 導入指南團隊段的「每週記錄表」 |
| ☐ | 每週稽核檢查點簽收（A6）：`audit verify: OK`、head 比對、簽名日期 | `python3 team/tools/teamctl.py audit-verify <MFG_TEAM_STATE_DIR>/audit` |
| ☐ | 自檢通過紀錄 | `python3 team/tools/teamctl.py check`；`python3 -m chat_gateway self-check --driver claude-code` |
| ☐ | 部門訓練紀錄（N 場，附出席） | 乙方自備 |
| ☐ | 結案報告：指標原始數字、錯誤回答、限制、續行 / 調整 / 停用建議；停止條件是否曾觸發 | 乙方撰寫；不寫「省多少」 |
| ☐ | 下架（若停用）：撤銷 bot 與 token、更換 API 金鑰、資料處理確認 | 部署檢核表 I 區 |

## 交付前自查（顧問）

- [ ] 客戶資料沒有進任何 git 工作目錄與公開 fork（`git status` 與 `git log -p` 抽查）。
- [ ] 沒對客戶說過「資料不出公司」「air-gap」「100% 準確」「不會裁員 / 一定省人」。
- [ ] 每個「產生來源」檔案，已確認存在，或已告知客戶「未交付」。
