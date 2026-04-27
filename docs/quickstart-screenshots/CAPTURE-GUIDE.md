# 新手指南截圖庫狀態

> 給 Jason 的工作清單。完成度：**4 真實截圖（待你存檔）+ 3 mockup（已生）+ 1 hero 警告圖**。

---

## 截圖總覽

| #   | 檔名                                | 狀態          | 來源                    |
| --- | ----------------------------------- | ------------- | ----------------------- |
| 0   | `step0-claude-code-hero.png`        | ✅ 已抓       | headless Chrome 自動抓  |
| 1   | `step1-download-page.png`           | ⏳ **待你存** | 你貼在 chat 的 Image 3  |
| 2   | `step2-first-launch-windows.png`    | ⏳ **待你存** | 你貼在 chat 的 Image 2  |
| 3   | `step3-sign-in.png`                 | ⏳ **待你存** | 你貼在 chat 的 Image 1  |
| 4   | `step4-main-window-mockup.png`      | ✅ Mockup     | playwright 從 HTML 渲染 |
| 5   | `step5-install-selector-mockup.png` | ✅ Mockup     | 同上                    |
| 6   | `step6-quote-success-mockup.png`    | ✅ Mockup     | 同上                    |

---

## ⏳ 你還需要做：把 3 張 chat 截圖存成檔案

你在 chat 貼了 3 張真實截圖（Sign In、Claude for Windows、Download Claude）。我這端只能看到，沒有檔案存取權限。請：

1. **從 chat 把 3 張圖另存到本地**
2. **照下面命名搬到 `docs/quickstart-screenshots/` 資料夾**

| 你貼的 chat image             | 對應檔名                         | 內容描述                                                |
| ----------------------------- | -------------------------------- | ------------------------------------------------------- |
| Image 1（Sign In）            | `step3-sign-in.png`              | 「Continue with Google」/ 「Continue with email」登入頁 |
| Image 2（Claude for Windows） | `step2-first-launch-windows.png` | 桌面 app 第一次開啟的「Get started」splash 畫面         |
| Image 3（Download Claude）    | `step1-download-page.png`        | 「Download Claude」頁，含 macOS/Windows 下載按鈕        |

---

## ✅ 已生 mockup（Step 4 / 5 / 6）

我用 HTML + playwright 渲染了 3 張擬真 mockup（dark theme + 1080p retina），左上角有「示意圖 / MOCKUP」小標。原始 HTML 在 `docs/quickstart-screenshots/mockups/` 隨時可改。

### Step 4：Claude Code 主畫面 + terminal 標示

- 檔案：`step4-main-window-mockup.png`（1440×980 retina）
- 內容：左側 sidebar、上方 chat、下方 terminal、紅色註解標箭頭
- 為什麼是 mockup：你還沒登入截到自己 app 主畫面 — 等你截到真實版可替換

### Step 5：install.sh 安裝選單

- 檔案：`step5-install-selector-mockup.png`（1280×720 retina）
- 內容：完整 macOS 風格 terminal，cursor 在 `Select [0-5]:` 後閃爍
- 為什麼是 mockup：跟真實 terminal output 1:1，可信度足夠；想替換成真截圖也歡迎

### Step 6：`/quote` 跑成功的 output

- 檔案：`step6-quote-success-mockup.png`（1280×1280 retina）
- 內容：完整 Claude chat 對話，含「規格衝突」alert 框 + 3 個替代方案 + 報價結算表
- 內容來源：`docs/demo/real-claude-response.md`（你之前 captured 的真實 Opus 4.7 回應）所以文字 100% 真實，只是 UI 是 mockup

---

## 📷 後製小工具推薦

| 需求                  | Windows                                           | Mac               |
| --------------------- | ------------------------------------------------- | ----------------- |
| 區域截圖              | `Win + Shift + S`（內建）                         | `Cmd + Shift + 4` |
| 畫紅框 / 寫文字       | 小畫家 / [ShareX](https://getsharex.com/)（推薦） | 預覽程式 / Skitch |
| 馬賽克 / 打碼帳號資訊 | ShareX                                            | Skitch / 預覽程式 |
| 全頁截圖              | Chrome DevTools                                   | Chrome DevTools   |

---

## 想重新生 mockup？

3 張 mockup 的原始 HTML 在 `docs/quickstart-screenshots/mockups/`。改完內容後重新渲染：

```bash
# 從 repo root
py -c "
from playwright.sync_api import sync_playwright
slides = [
    ('step5-install-selector', 1280, 720),
    ('step4-main-window', 1440, 980),
    ('step6-quote-success', 1280, 1280),
]
with sync_playwright() as p:
    browser = p.chromium.launch()
    for name, w, h in slides:
        page = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2).new_page()
        page.goto(f'http://localhost:8765/quickstart-screenshots/mockups/{name}.html', wait_until='networkidle')
        page.wait_for_timeout(1500)
        page.screenshot(path=f'docs/quickstart-screenshots/{name}-mockup.png', full_page=True, type='png')
    browser.close()
"
```

需先啟動 dev server：`py -m http.server 8765 --directory docs`
