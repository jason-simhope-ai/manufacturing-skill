# examples/

> 合成 demo 資料。**不要放真實客戶資料**。

---

## 內容

| 檔案                         | 用途                                            |
| ---------------------------- | ----------------------------------------------- |
| `sample-drawing/bracket.md`  | 模擬一張 CNC 件圖紙 metadata（不需要真 CAD 檔） |
| `sample-bom/bracket-bom.csv` | 對應的 BOM 範例                                 |
| `sample-quote-output.md`     | `/quote` 流程跑完後的預期輸出格式               |

---

## 為什麼不放真 CAD 檔（.dwg / .step / .pdf 圖紙）

- **合規**：真實圖紙是客戶機密，IATF 16949 / 客戶 NDA 通常禁止外流
- **可讀性**：markdown 文字版方便所有 LLM / 人類閱讀，跨平台
- **示範性**：讓使用者一眼看懂 demo 預期長什麼樣，比對自己的真實情境

正式部署時，把真實 CAD 檔放：

- 公司內部 PLM 系統 → 透過 MCP 連
- 或 Local 資料夾 → `.gitignore` 排除

---

## 跑 demo

```bash
# 在 Claude Code 內
/quote @examples/sample-drawing/bracket.md

# 預期：30~60 秒內看到類似 examples/sample-quote-output.md 的輸出
```

---

## 想 contribute 更多 example？

歡迎 PR：

- 不同 vertical 的範例（PCB BOM、射出件圖紙、食品配方）
- 不同情境的範例（複雜件、急件、開發件、量產件）

**唯一規則：合成資料、不可有真實客戶 / 廠商資訊**。
