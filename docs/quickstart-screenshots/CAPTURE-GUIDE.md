# 截圖捕捉指南

> 給 Jason 補新手指南截圖用的工作清單。明天 demo 完之後再補也行，但補上後新手指南完成度會大幅上升。

每張截圖的目標、推薦尺寸、要框的範圍、要避開的東西，都列在下方。

存檔規範：

- **位置**：`docs/quickstart-screenshots/`（這個資料夾）
- **檔名**：照下面的命名（已附建議檔名）
- **格式**：PNG 優先（截 retina 也 OK）
- **隱私**：截圖前**清除個人帳號資訊**（email、信用卡末四碼、電話）

---

## ✅ Step 1：官方下載頁（已抓 / 可重抓）

| 屬性     | 內容                                                                                                    |
| -------- | ------------------------------------------------------------------------------------------------------- |
| 檔名     | `step1-download-page.png`（已抓 — 用 headless Chrome 截，dark theme）                                   |
| 推薦尺寸 | 1440×900 或更大                                                                                         |
| 要框     | 整個 hero 區塊：`Built for developers` 標題 + `irm ... \| iex` install 命令框 + 「Get Claude Code」按鈕 |
| 要避開   | 個人帳號 avatar（如有登入請先登出）                                                                     |

**重點**：要捕捉到 `irm https://claude.ai/install.ps1 | iex` 這行命令 — 這就是新手指南 Step 1-2 表格裡提到的「一行 install 指令」原始來源。

> 💡 如果你想重抓彩色 light mode 版本：用一般瀏覽器到 https://claude.com/claude-code，截整個 viewport（按 F12 開 DevTools → Cmd/Ctrl+Shift+P → 輸入「screenshot」→ 選 Capture full size screenshot）。

---

## 📸 Step 2：「Download Claude for desktop」按鈕位置

| 屬性     | 內容                                                                                                                            |
| -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 檔名     | `step1b-desktop-download-button.png`                                                                                            |
| 推薦尺寸 | 1440×900                                                                                                                        |
| 要框     | 同個官網頁面，**往下捲**到「Use Claude Code where you work」區塊，框 **Desktop** 那欄 + 「**Download Claude for desktop**」按鈕 |
| 要避開   | 同上                                                                                                                            |

**為什麼要這張**：新手指南開頭就警告讀者「不要被 Built for developers 嚇到，要往下捲找桌面 app」 — 這張截圖證明確實有桌面 app 路徑。

---

## 📸 Step 3：Claude Code 桌面版首次開啟 / 登入畫面

| 屬性     | 內容                                                                                            |
| -------- | ----------------------------------------------------------------------------------------------- |
| 檔名     | `step2-login-screen.png`                                                                        |
| 推薦尺寸 | 桌面 app 視窗滿版（你的螢幕解析度）                                                             |
| 要框     | Claude Code 桌面 app 的登入畫面 — 要看到「Continue with Google」、「Continue with email」等選項 |
| 要避開   | **絕對不要框到你的 email、Google 帳號縮圖。** 截圖前先登出，截「未登入狀態」                    |

**怎麼操作**：

1. 如果你已經登入，先在 Claude Code 設定裡找「Sign out」
2. 完全關掉 Claude Code
3. 重新打開（會跳登入畫面）
4. 截圖

---

## 📸 Step 4：Claude Code 主畫面 + terminal 位置標示

| 屬性     | 內容                                                                                                                   |
| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| 檔名     | `step3-main-window-with-terminal.png`                                                                                  |
| 推薦尺寸 | 桌面 app 視窗滿版                                                                                                      |
| 要框     | 登入後的主畫面 — **上方對話框** + **下方 terminal 區**都要看到                                                         |
| 後製     | 用任何畫圖軟體（Windows 小畫家 / Mac 預覽程式）在「對話框」跟「terminal」位置加紅框 + 文字標示「對話框」、「terminal」 |
| 要避開   | 個人對話歷史（如有先清除）                                                                                             |

**目的**：新手指南 Step 3 開頭說「主畫面有兩塊：上方對話框 + 下方 terminal」 — 這張截圖直接視覺證明位置。

---

## 📸 Step 5：install.sh 安裝選單跑出來的瞬間

| 屬性     | 內容                                                                                                |
| -------- | --------------------------------------------------------------------------------------------------- |
| 檔名     | `step3-install-selector.png`                                                                        |
| 推薦尺寸 | terminal 那塊放大截，至少 800×600                                                                   |
| 要框     | 跑完 `bash adapters/claude-code/install.sh` 之後跳出的選單（cnc-machining / stub / core-only 那段） |
| 要避開   | 上面 `git clone` 的個人系統路徑（如有 `C:/Users/<你的名字>/...` 在輸出中，截圖時手動把名字打碼）    |

**怎麼操作**：

1. 在 terminal 跑 `bash adapters/claude-code/install.sh`
2. 跑到「Select [0-5]:」那個 prompt 停下
3. **不要**先按 Enter，先截圖
4. 截完再選 1 按 Enter 繼續

---

## 📸 Step 6：`/quote` 跑完的成功 output

| 屬性     | 內容                                                                                                                      |
| -------- | ------------------------------------------------------------------------------------------------------------------------- |
| 檔名     | `step4-quote-success.png`                                                                                                 |
| 推薦尺寸 | 對話框那塊滿版截，至少 1200×900                                                                                           |
| 要框     | 完整 `/quote @examples/sample-drawing/bracket.md` 的成功 output — 至少要看到 AI 抓到「不鏽鋼陽極」矛盾 + 提替代方案的部分 |
| 後製建議 | 太長的話分成 2 張：(a) AI 思考過程開頭 (b) 最終報價單。或者用一張長截圖（Chrome 的 full size screenshot 可以做到）        |

**怎麼操作**：

1. 在 Claude Code 對話框打 `/quote @examples/sample-drawing/bracket.md` 按 Enter
2. 等 AI 跑完整段（約 30 秒到 2 分鐘）
3. 看到完整 output 後截圖
4. 如果太長，先截最有戲劇張力的一段（AI 抓到矛盾、提替代方案那段）

---

## 截好後

把 6 張 PNG 放到這個資料夾後，告訴 Jason（或自己）做兩件事：

1. **編輯 `docs/quickstart-for-beginners.zh-TW.md`** — 把 6 處 `📸 _截圖待補：..._` 提示換成實際的 markdown 圖片連結：
   ```markdown
   ![截圖描述](../quickstart-screenshots/step1-download-page.png)
   ```
2. **commit + push** — 訊息建議 `docs(quickstart): add 6 screenshots for beginner guide`

---

## 後製小工具推薦

| 需求                  | Windows                                           | Mac               |
| --------------------- | ------------------------------------------------- | ----------------- |
| 區域截圖              | `Win + Shift + S`（內建）                         | `Cmd + Shift + 4` |
| 畫紅框 / 寫文字       | 小畫家 / [ShareX](https://getsharex.com/)（推薦） | 預覽程式 / Skitch |
| 馬賽克 / 打碼帳號資訊 | ShareX                                            | Skitch / 預覽程式 |
| 全頁截圖              | Chrome DevTools                                   | Chrome DevTools   |
