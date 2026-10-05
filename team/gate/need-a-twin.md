# 「需要分身嗎？」閘門

流程修正能解決的，就不開分身。由 `/team gate <position>` 逐題引導 G1–G6；**G7 不在對話中問**，由人在下方 roster 片段的註解裡自己填 yes／no。全部通過才可填 `result: twin`。每季複審一次。

## 問卷

| # | 問題 | 不通過 → |
| - | ---- | -------- |
| G1 | 這個痛點每週耗幾小時？（要說得出數字） | `defer` |
| G2 | 根因是表單、權責、流程斷點，或資料尚未數位化嗎？ | `process-fix` |
| G3 | 偶爾用一次既有的 `/command`（例如 `/inspect`、`/quote`）就能解決嗎？ | `use-command` |
| G4 | 在職者願意每週花 15 分鐘 review 嗎？ | `defer` |
| G5 | 需要的資料都可讀（已數位化、可匯出）嗎？ | `defer` |
| G6 | 實際在做事的人（常是下屬）已訪談，`today` 已填嗎？ | `defer` |
| G7 | 涉及 T3（高安規客製專案）嗎？**紙上自行確認，不要輸入任何聊天或 AI 對話**（答「有，某某國防案」本身就洩漏）。在 roster 片段的 G7 註解填 yes／no | yes → alpha 不開，`result` 只能是 `defer`，見 `team/policies/restricted.md` |

G2、G3 答「是」就走對應的出口，不再往下問。G7 是人自己填的 yes／no，工具與分身都不問、不記。

## 結果與去向

| `result` | 意義 |
| -------- | ---- |
| `twin` | 可以在 roster 設 `enabled: true` |
| `process-fix` | 先修流程；修完再問一次 |
| `use-command` | 用既有指令，不開分身 |
| `defer` | 條件未備，列出缺什麼、下季再評 |
| `retire` | 複審後判定停用 |

## 輸出：貼進 roster 的片段

```yaml
# G7 涉及 T3？ 請你自己在這裡填 yes / no（不要在聊天回答）：____    yes → result 改 defer，alpha 不開
needsTwinGate:
  result: twin
  rationale: 一句話寫出痛點、已訪談誰、資料在哪
  reviewedOn: "YYYY-MM-DD"   # 超過 120 天未複審會出現 W004
```

## 季複審清單

- 週 review 出席率與「🧭 修改率」（> 0 是健康的）。
- 分類分布：有沒有把 outsource 標成強化？有爭議一律判 outsource。
- 已喚醒的 outsource：teach-back 與人工練習有沒有做？`reviewBy` 是否到期？
- 這個分身還需要嗎？不需要就判 `retire`。

技能保留紀錄與使用指標只用於改善分身，**不作為人力或績效依據**。
