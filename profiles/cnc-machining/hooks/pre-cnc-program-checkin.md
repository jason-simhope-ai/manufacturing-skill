---
name: pre-cnc-program-checkin
displayName: G-code 進版控前自動檢查
trigger: before-checkin to NC program version control
profile: cnc-machining
---

# pre-cnc-program-checkin Hook

任何 G-code 要進版控（git / PLM / SVN）前，自動跑一次 `g-code-review` skill。

---

## 觸發條件

- `cnc-programmer` 完成程式
- 使用者執行 `git add *.nc` 或對等版控動作
- CAM 軟體 export 後自動觸發（如有整合）

---

## 動作

1. 對所有改動的 `.nc` / `.tap` / `.gcode` 檔案
2. 跑 `profiles/cnc-machining/skills/g-code-review.md` 的 4 階段檢查
3. 結果分級：
   - ✅ 全綠 → 允許進版控
   - ⚠️ 有警告 → 提示但允許進版控（commit message 自動帶警告摘要）
   - ❌ 有必改項 → 阻擋進版控

---

## 失敗訊息範例

```
🛑 pre-cnc-program-checkin 阻擋
檔案：O0123-bracket-rev2.nc

❌ 必改項：
  - 第 567 行 S=15000 超過刀具廠商建議（max 12000）
  - 第 234 行缺安全 Z 抬刀

修正後重試。
```

---

## 例外通行

只有以下情況可加 `--no-verify` 跳過（記錄於 commit message）：

- 試切階段的調整版（標 `[PROTOTYPE]`，不會發到生產線）
- 緊急修正（標 `[EMERGENCY]`，需主管事後簽核）

平日量產程式 **不允許跳過**。
