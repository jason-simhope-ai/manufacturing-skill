# 數位分身團隊 — 10 分鐘說明

> 每個職位有一個副駕分身。**副駕不是替身**：判斷永遠是人做，分身讓你看得更多、更快發現漏洞。
>
> **人類讀者從這份開始。** 根目錄的 [TEAM.md](../TEAM.md) 是給 AI agent 的啟動檔（位元組預算、錯誤碼、演算法），不必讀。前線同仁（檢驗員、業助、生管）請看一頁版：[分身與我](for-frontline.zh-TW.md)。
> 狀態：v0.2.0-alpha，實驗性；只在測試工作區與合成／已去識別資料上試。

## 先看這裡：誰不該現在導入

先確認五件事，**任何一項是「否」就先不要導入**（第一天只能先暫答，其中兩位主管、去識別、接受上雲幾項要到逐日表指定的日子補齊；金鑰保管人第一天就要指定），改用既有的 `/command`（例如 `/inspect`、`/quote`）並跑「需要分身嗎？」閘門（`team/gate/need-a-twin.md`，紙上就能做）：

| 要有 | 說明 |
| ---- | ---- |
| Slack 或 Discord 工作區 | 目前只支援 Slack、Discord 與本機 mock；**不支援 LINE、Teams**。不要把 LINE 或 Teams 的內容複製貼上到分身頻道代替，那等於繞過分級 |
| 一台常駐主機、一位金鑰保管人 | gateway 要一直開著；token 與金鑰只放環境變數，由 IT 或管理部保管，不是導入負責人 |
| 至少兩位主管，每週各 15 分鐘 review | 沒有 review，分身只是多一個沒人檢查的訊息來源 |
| 資料已數位化，且能先去識別成 T1 | 見下方「資料餵入」。流程還在紙本，先做流程修正 |
| 公司接受「T1 內容送到雲端模型」 | 見下方「T0–T3」。客戶合約（NDA、客戶規範）不允許第三方 AI 看的資料，先查合約，不要先試 |
| 「AI 賦能原則」已簽署，簽署日期貼在分身頻道的說明 | 範本見導入指南。**沒有簽就不要導入**：前線同仁沒有任何依據相信「不會取代我」 |

另外：老闆期待「裝了就省人力」的，不要導入；分身的指標不是省時間（見 [導入指南](../docs/adoption-guide.md) 的團隊段）。**分身也不是空缺的替代**：職位空著就去補人；空缺職位的分身只到 `observe`，要啟用還得由升級梯上的人簽 `vacancyApprovedBy`／`vacancyApprovedOn`（`E064`）。

## 0–2 分：一張圖

```
職位（例：品保部主管）──▶ 分身（品保部主管分身）──▶ 頻道（例：qa-floor，T1）
   在職者本人做判斷          能力清單 × 分類 × autonomy       只在被 @ 時回答
```

- 一個職位一個分身；人事異動時換掉本機設定即可，分身本身不變。
- 分身只**引用**既有的 agents、skills、know-how，不複製、不覆寫。
- 你的檔案長這樣：`roster`（誰、哪些頻道）、`twins/*.md`（職責與能力）、`policies/`（共用規則）。

## 2–5 分：一天的例子

- **07:50**　生產部主管分身在頻道貼出提醒：「請先貼出 3 個今日重點。」主管寫下三點後，分身再用排程資料挑戰：「第 2 點提到的工單 `WO-EX-014` 與缺料清單重疊，你要不要先看？」插單或加班，由主管決定。
- **09:30**　品保部主管分身在 NCR 的 thread 補上兩件相似案與一個反例：「你先前判『中』，以下兩點可能推翻。」回覆末段的 `🧭 需要你判斷` 列出嚴重度與是否升級 8D，由品保部主管選。
- 每則回覆都附依據、`[ASSUMED]` 假設、未查證項目與信心（只有「中」或「低」）。
- 離線 demo（`python3 infra/chat-gateway/demo.py`）裡的回覆是**預錄**的，不是模型推論；它示範流程與防線，不證明分身答得準。

## 5–8 分：資料分級 T0–T3（給人看的版本）

| 級別 | 白話 | 車間例子 | 能進哪裡（alpha） |
| ---- | ---- | -------- | ----------------- |
| **T0 公開** | 本來就公開的 | 產品型錄、公開的規範與標準、官網上的公司介紹 | 任何頻道 |
| **T1 內部** | 對外不公開，但外洩了損失有限 | SOP、排程摘要（工單號、機台、交期餘裕、保養時段）、已去識別的 NCR（客戶是 `CUST-xx`、沒有人名） | Slack／Discord／mock；**內容會送到雲端模型** |
| **T2 機密** | 外洩會傷到客戶或公司 | 圖紙、BOM、報價與金額、客戶名、人名與電話、統一編號 | **只能在本機 mock**；alpha 不能上 Slack／Discord，也不能給雲端模型（把 `cloudTierCeiling`／`saasTierCeiling` 設到 T2 以上，`teamctl check` 報 `E047`，gateway 拒載） |
| **T3 高安規** | 國防、航太、醫療器材等客戶專案的**任何**資料，連「有這個專案」都算 | 專案代號、客戶名單、管制清單、外銷許可 | 不處理（見下） |

三條規則：**拿不準就往上一級**；頻道的分級就是內容的分級，只升不降；T3 與 T2 的判斷靠人與流程，工具只是補一道告警。

**T3 實際上是怎麼擋的**（兩道，都不是「理解內容」）：

1. 設定層：roster 裡出現任何 T3 頻道或 T3 分身，gateway 啟動就拒絕（exit 3），什麼都不載入。
2. 字樣層（DLP 關鍵字告警）：訊息含下列字樣時，gateway 擋下、不送進模型，並回「此內容可能屬 T3，不在本系統處理範圍，請依貴公司 T3 程序處理」。
   - 視為 T3（與 `patterns.py` 完全一致）：中文 `受限`、`國防`、`航太`、`軍工`、`軍規`、`醫材`、`醫療器材`、`外銷許可`、`管制`，英文只有 `RESTRICTED`、`ITAR`、`EAR`、`CUI`。`不受限制`、`將軍規模`、`管制圖`、`文件管制`、`製程管制` 等日常用語不算。**英文同義詞（defense、aerospace、medical device、export permit、Mil-Spec）與混淆字元（例如西里爾字母的 `ІТАR`）不擋。** 補法：把 `team/tools/denylist.starter.txt`（通用中英同義詞、保密約定、金額寫法；`T3:` 開頭的行命中視為 T3）併入 `team/local/names.denylist`。pilot 審查的 7 句實測句子，沒載入時全部通過、載入後全部擋下；仍然只是字樣比對。
   - 視為 T2（送進 T1 頻道會被擋）：`機密`／`CONFIDENTIAL`、統一編號（只有前後 12 字內出現「統編」「統一編號」「VAT」「公司」「股份」「發票」且檢查碼正確才擋，單獨一串 8 位數字不擋）、身分證字號、`NT$`／`US$`／`USD` 金額、`萬元`／`千元`、email、手機號碼、有分隔的市話（`02-1234-5678`），以及你自己放進 `team/local/names.denylist` 的客戶名、圖號、專案代號。**人名不擋**（只有放進 denylist 的才擋；`deid.py` 會掃「姓＋職稱」，gateway 不會）。回覆裡出現的 email／手機另外會被遮成 `[REDACTED:email]`／`[REDACTED:tw-mobile]`。
   - **這是字樣比對，不是內容理解**：換個說法、縮寫、圖號、客戶代號、照片裡的文字都擋不到；`受限` 也會誤擋「不受限制」。所以不要對同仁說「T3 一律不處理」，要說「T3 不准進來，系統只會擋明顯字樣，其餘靠你自己」。同仁自己要先判斷，不要把 T3 話題丟進任何分身頻道。

**模型在雲端**：T1 內容會由 gateway 以 `claude -p` 送到 Anthropic API（用營運者自己的 API 金鑰），同時也留在 Slack／Discord 上。保留期限、資料區域與零留存條款取決於你和供應商的合約，本 repo 不替你保證。全 repo 的資料流向頁正在準備中，在那之前請以這張表為準。

## 資料餵入：分身怎麼讀到排程／NCR 資料

Wave 1 的價值（「用排程資料挑戰並補漏」、「補相似 NCR 與反例」）取決於分身讀得到資料。設計很單純：**一個資料夾，由人匯出，分身只讀。**

| 項目 | 做法 |
| ---- | ---- |
| 放哪 | 一個**已存在的資料夾**，路徑設在環境變數 `MFG_TEAM_DATA_T1`（建議絕對路徑、放在 repo 外，絕對不要 commit）。沒設就是沒有資料：分身只剩 `team/.build/ref/` 的參考文字 |
| 只對真模型有效 | 這個資料夾只在 `--driver claude-code` 時交給模型（以 `--add-dir`，工具只有 `Read`／`Grep`／`Glob`，不能寫）；`--driver mock`（含 demo）的預錄回覆完全不讀它 |
| 誰匯出 | 該部門的資料窗口，在**來源端**匯出：生管匯排程、品保工程師匯 NCR。是人匯出、人放進去，分身不會自己去連 MES／ERP，也不會寫回 |
| 放什麼 | 只放 **T1 以下**：排程摘要（工單號、機台、交期餘裕、保養時段）、已去識別的 NCR（客戶 `CUST-xx`、無人名、無聯絡方式）。不放：圖紙、BOM、報價與金額、客戶名、人名、電話、email |
| 先去識別 | 匯出後、放進資料夾前，先跑 `team/tools/deid.py`（指令見 `team/local/README.md`）。它對殘留**一律失敗**：有任何命中就不寫輸出檔、exit 1。但它只掃通用樣式（email、電話、人名加職稱、金額與統編、上面的 DLP 字樣）加你的 `team/local/names.denylist`；**英文客戶別名、圖號若沒進 denylist 或對照表，它掃不到**。所以每次匯出都要由匯出者抽查幾列，再放進資料夾 |
| 格式 | 沒有固定 schema：分身用 `Grep`／`Read` 讀文字檔。建議 UTF-8 CSV、第一列欄名、欄名人看得懂。範例：排程 `work_order,machine,due_date,slack_days,maintenance_window,snapshot_date`；NCR `ncr_no,date,part_family,defect,disposition,snapshot_date`。檔內放 `snapshot_date`（或檔名含日期），回覆才說得出資料多舊 |
| 多久更新 | 由人決定，分身只讀檔案當下的內容。建議早會前（例如 07:30，早於 07:50 的排程貼文）匯出覆蓋同一檔 |
| 看得到的範圍 | 這個資料夾對**該 gateway 服務的所有分身與頻道**都可見。想分開，就用不同的 gateway 與資料夾；不要把某個部門才該看的東西放進共用資料夾 |
| 內容掃描 | gateway 啟動時與每次呼叫前掃描資料夾（≤ 2 MB 的文字檔，DLP 字樣＋你的 denylist，只重讀有變動的檔）：T3 命中拒絕啟動（exit 3）或拒絕該次呼叫；T2 命中只告警；超過 5,000 個檔、含 symlink 或 roster 檔一律拒絕。二進位檔與大檔不掃，仍要人抽查 |
| 怎麼確認讀到 | `python3 -m chat_gateway self-check --driver claude-code`（需 `PYTHONPATH=infra/chat-gateway`）會檢查資料夾存在並掃描內容。再問一個答案只在檔案裡的問題（例：「WO-EX-0412 的交期餘裕？」），用 `grep WO-EX-0412 "$MFG_TEAM_DATA_T1"/*.csv` 對照回覆的依據 |

## 8–10 分：三分類、五級 autonomy、不做的事

| 分類 | 意思 | 例 |
| ---- | ---- | -- |
| `strengthen` 強化既有優勢 | 人仍親手判斷，分身補資料與反例 | 人先寫 D4，分身找反例 |
| `create` 創造新能力 | 以前沒人做 | 每日 SPC 趨勢提醒 |
| `outsource` 外包既有工作 | 今天有人在做，上線後那個人不再做 | 8D 排版、簡報資料包 |

outsource 預設休眠；要喚醒必須在 roster opt-in，每分身最多一項、上限 `draft`、90 天內複審，並要求 teach-back 與人工練習。分類有爭議一律判 outsource。

| autonomy | 能做 |
| -------- | ---- |
| `observe` | 回答事實問題（附出處） |
| `suggest` | 給選項、理由與 🧭 決策點 |
| `draft` | 在回覆中產出標 `DRAFT` 的草稿 |
| `act-with-approval`、`act` | 定義保留；alpha 不開放 |

**分身永遠不做**：替你做決定、寫入任何系統、對外發送、冒充你、評比個人、讀整個頻道、保留長期記憶（只帶入本頻道最近 10 則被 @ 的問答，**含他人的提問**，重啟即清空）。

**FAQ：會不會取代我？** 以公司簽署的「AI 賦能原則」為準；沒有簽就不要導入。工具這邊做得到的是：每項能力都寫明「今天誰在做」與「上線後你還親手做什麼」，做事的人不是本職位時要本人簽 `doerAckedOn`；你可以隨時用「我先說」讓自己先判斷。

**FAQ：分身答錯，誰負責？** 分身的答案是參考。沒有人會因為「分身這樣說」而被追責，也沒有人會因為沒用分身而被追責；簽字採用結論的人負責結論。

## 前線同仁能做的事（gateway 程式支援）

| 在頻道裡說（先 @ 分身） | 系統做什麼 | 限制 |
| ----------------------- | ---------- | ---- |
| 「我不同意」／「分身錯了」 | 不再呼叫模型；回一句收到；稽核寫 `human_override`，**只記頻道、分身、能力**，不記 event、thread、使用者 | 聊天平台本身仍看得到誰發的；只認這兩個字串 |
| 「我親手做了」 | 稽核寫 `practice_checkin`（同樣不記人），給 `manualRepsPerMonth` 對帳 | **自報**，只計數，系統無法驗證真的做了 |
| 不用分身日 | roster `channels[].twinFreeDays: [15]`（每月第幾天，依 `org.timezone`）：非緊急的提問回「今天請自己判斷」，稽核寫 `twin_free_day`；排程貼文也停。訊息含「緊急」照常回答 | 只是「每月幾號」的清單，沒有工作日曆、假日判斷 |
| 學習者 `learners` | roster `channels[].learners: [職位 id]`：可 @ 分身但不在 `askers`；回覆標「學習模式」，上限 `suggest`，只給相似案與反例（prompt 規則，非程式保證）；他們的對話不進頻道窗，主管的回答看不到 | 學習頻道請不要加主管；`predictFirstDefault: true` 讓學習者預設「我先說」，說「這次直接給」可跳過一次 |

`teamctl audit-verify` 會印出這三種計數（依頻道／能力加總，**不按人拆**），季複審時讀。

## 這些承諾，工具擋得住什麼

**`teamctl check`（lint）檢查結構，不檢查真偽。** 下表把「系統強制」和「靠人」分開寫：

| 承諾 | 工具實際做的 | 擋不住的 |
| ---- | ------------ | -------- |
| 每項能力標分類、寫 `today`／`humanStillDoes` | 缺漏是硬錯誤；`strengthen`／`create` 的 `humanStillDoes` 任一職位那行只剩審閱類字眼（`REVIEW_ONLY_WORDS`：審閱、確認、看過、沒問題就送出、若有意見再補充…）會被擋（`E038`）；`today` 有人在做卻沒列 `affectedRoles`（`E061`）；`today` 寫「無人」只准 `create`（`E062`）；`affectedRoles` 有本職位以外的人，就要那個人簽 `doerAckedOn`（`E063`，喚醒 outsource 時也查） | 字表可以換說法繞過；`affectedRoles` 可以亂填本職位（`today` 提到「工程師」「生管」等時只會 `W009` 警告）；做事的人簽了之後再改分類，lint 也看不出來。真偽靠做事的人簽名、季審與「有爭議判 outsource」 |
| outsource 休眠、≤ 1 項、≤ `draft`、90 天複審 | lint 檢查結構；gateway 不會呼叫休眠能力，並把 outsource 限制在 `draft` | **`reviewBy` 到期由 lint 發現，不是執行期強制**：只有人跑 `teamctl check` 才看得到（本機 roster 過期是錯誤，CI 只警告，且 CI 看不到你的本機 roster）；gateway 執行期不看 `reviewBy` |
| teach-back 與人工練習 | `manualRepsPerMonth` 只驗證是 ≥ 1 的整數；當事人在頻道說「我親手做了」會記一筆 `practice_checkin`（只計數） | **自報制**：沒有提醒、沒有驗證，計數不記是誰，也無法證明真的做了。文件寫「要求」，不是系統強制 |
| 決策點 🧭、信心只有「中／低」 | gateway 程式強制（模型沒列決策點時補上通用句） | `/team ask` 預覽路徑不經 gateway，沒有頁尾 |
| 人先寫 D4、「我先說」 | 「我先說」由 gateway 偵測；學習者在設了 `predictFirstDefault` 的頻道預設先說。人先寫 D4 只寫在 prompt 裡 | 主管不說就沒有；沒有「誰先說了」的紀錄（刻意不記） |
| 「我不同意」、不用分身日 | gateway 程式：不呼叫模型、匿名計數（見上方「前線同仁能做的事」） | 只認固定字串；不用分身日只是「每月幾號」，沒有假日邏輯 |
| 成功指標（人修改 🧭 的比例、人先寫 D4 的比例、週 review 出席率） | 無；系統不收集 | 要由導入負責人每週手工記錄（表格見導入指南） |
| 每分身在 `roster.json` 的項目 ≤ 600 B | 本機 roster 超過是警告 `W008`；只有 CI 檢查出貨範例 roster 時才是錯誤 `E050` | 警告不會擋你，但代表 `roster.json` 越來越肥（出貨的範例品保分身有 3 項啟用能力、3 個頻道，已是 597 B）；想再多啟用一項時，縮短能力 id 或職稱，或少啟用一項。**這是大小預算，不是分類檢查**：曾經只有它在「把 outsource 改標 strengthen」時跳出來，別依賴它 |

分類相關的 lint 碼（完整表在 `team/tools/teamlib/schema.py` 的 `CODES`）：

| 碼 | 什麼時候出現 | 怎麼修 |
| -- | ------------ | ------ |
| `E038` | `strengthen`／`create` 的 `humanStillDoes` 某一行只剩看、審、確認、送出 | 寫出那個人仍親手做的事（「先寫下嚴重度與理由」「親手寫 D4」） |
| `E061` | `today` 有人在做，卻沒有 `affectedRoles` | 列出今天做這件事的職位 id 或稱呼（例：`[品保工程師]`） |
| `E062` | `strengthen`／`outsource` 的 `today` 寫「無人」 | 真的沒人做就是 `create`；有人做就寫出是誰 |
| `E063` | `affectedRoles` 有本職位以外的人，卻沒有 `doerAckedOn`（或日期在未來） | 拿 `today`／`humanStillDoes` 給那個人看，同意後填日期；不同意就改寫，或把那一行拆成休眠的 outsource |
| `E064` | `VACANT` 職位的分身 `enabled: true`，缺 `vacancyApprovedBy`／`vacancyApprovedOn` 或核准人不在升級梯 | 先問為什麼空著；分身不是補人的方法 |
| `W009` | `today` 提到「工程師」「生管」「檢驗員」等，`affectedRoles` 卻只有本職位 | 確認做事的人是不是漏列了 |

## 怎麼開始

0. 取得程式碼：`git clone <本 repo 網址>`（或下載 ZIP 解壓），然後 `cd manufacturing-skill`。**本文所有指令都從 repo 根目錄執行**（路徑都是 `team/…`、`infra/…`）；`bash install.sh` 裝出來的 plugin 副本只供閱讀，跑不了這些工具。
1. 跑「需要分身嗎？」閘門（`team/gate/need-a-twin.md`）：流程修正或既有指令能解決的，就不開分身。閘門裡「涉及 T3 嗎」那題（G7）**請自己確認：寫在紙上，或填在閘門 roster 片段的註解裡的 yes／no；不要把答案打進任何聊天或 AI 對話**，`/team gate` 也不會問（回答「有，某某國防案」本身就洩漏了 T3 的存在）。
2. 前置：Python 3.11+、`pip install pyyaml`。指令用 `python3`（Windows 未驗證）。
3. 複製 `team/roster.example.yaml` 到 `team/local/roster.local.yaml`，改成自己的部門與職位（只放職稱，不放姓名；本機設定見 `team/local/README.md`）。
4. `python3 team/tools/teamctl.py check` 通過後，用 `python3 team/tools/build.py --summary` 編譯；離線試玩：`python3 infra/chat-gateway/demo.py`。
5. 誰核准？outsource 的核准人必須在該部門的升級梯上、且不是本人。
6. **兩週與逐日做法**：見 [導入指南](../docs/adoption-guide.md) 團隊段的「兩週逐日表」，含「AI 賦能原則」與部署檢核表範本。檢核表第一項是：原則已簽、**簽署日期已貼在分身頻道的說明**。
7. 把 [分身與我](for-frontline.zh-TW.md) 印給會被分身影響的同仁（不只是會用它的主管）；`python3 infra/chat-gateway/demo.py --plain` 是給他們看的 3 段精簡示範（中文、沒有 token 與稽核行）。

> **給主管**
> - 不要用使用次數、修改率、「我不同意」次數去評價任何人；這些數字只用來改善分身。
> - 報表只到公司層級，或至少 5 人的群組；小廠一個部門 2–3 人時，部門彙總就等於個人，不要做。
> - `teamctl audit-verify` 的輸出只有分級與「頻道／能力」的計數，不按使用者拆；不要另外寫程式把稽核紀錄的 `operator_ref` 對回人。
> - 分身答錯不是用的人的錯；簽字採用結論的人負責結論。

**不要把秘密放進任何檔案**：token、金鑰只放環境變數（`MFG_TEAM_*`、`ANTHROPIC_API_KEY`）；真名、平台 id、客戶名只放 `team/local/*`（不進版控）。CI 只掃追蹤檔，`team/local` 靠本機 pre-commit（`team/local/README.md`）。

## 名詞

| 詞 | 意思 |
| -- | ---- |
| 分身 | 一個職位的副駕 AI 角色：一份 `team/twins/<id>.md` 加上 roster 的設定。不是人的替身，不做決定、不寫入系統 |
| roster | 名冊檔：有哪些部門、職位、哪些職位有分身、綁哪些頻道。範例是 `team/roster.example.yaml`，真實的放 `team/local/` |
| 決策點（🧭） | 該由人選的問題（分身檔的 `decisionPoints`、`decisionRights`）。分身遇到就停下，列出選項與取捨，不替人選 |
| 三分類 | 每項能力必標 `strengthen`（強化既有優勢）、`create`（創造新能力）、`outsource`（外包既有工作），見上表 |
| autonomy 等級 | 分身能做到哪：`observe`（答事實）＜`suggest`（給選項）＜`draft`（寫標 DRAFT 的草稿）＜`act-with-approval`＜`act`；alpha 最高 `draft`，後兩級不開放 |
| gateway | 把聊天工作區接到分身的小程式（`infra/chat-gateway/`）：驗身分、檢查分級、限流、寫稽核紀錄 |
| adapter | gateway 接特定平台的接頭：`mock`（本機）、`slack`、`discord` |
| 稽核錨點 | gateway 自動維護一個簽章過的檢查點檔 `audit/checkpoint.json`（每個分級的紀錄筆數與最後一筆的雜湊）。「稽核錨點」就是這個檔（或 `audit-verify` 印出的 head）**另存在別處的複本**，每週由導入負責人以外的人簽收；有它，才抓得到「日誌與檢查點被一起回退」。日誌只存雜湊、不存訊息文字，所以出事時要靠 Slack／雲端平台端的紀錄還原內容 |
| teach-back | 在職者定期用自己的話向同事講清楚被 outsource 的那件事怎麼做、為什麼；加上每月的人工練習次數。目前由人自報 |
| dormant | 休眠：能力寫在分身檔裡，但 roster 沒有 opt-in，就不會被呼叫 |
| T0–T3 | 資料分級，見上表 |

給 agent 的入口在根目錄的 [TEAM.md](../TEAM.md)。
