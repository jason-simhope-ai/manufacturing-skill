# Synthetic Sample Drawing — Bracket BR-12345

> 這是合成 demo 資料。**真實圖紙請放公司內部、不要進這個 repo**。
> 此檔案以 markdown 模擬一張圖紙的 metadata，方便 demo `/quote` 流程而不需要真實 CAD 檔。

---

## Drawing metadata

| 欄位             | 值                                   |
| ---------------- | ------------------------------------ |
| 件號 (Part No.)  | BR-12345                             |
| 件名 (Part Name) | 不鏽鋼支架 / Stainless Steel Bracket |
| 版本 (Revision)  | rev2                                 |
| 客戶 (Customer)  | 客戶A (synthetic)                    |
| 圖紙日期         | 2026-04-20                           |
| 設計者           | (synthetic)                          |

---

## Material

- 牌號：SUS304（AISI 304）
- 規格：板材 50mm × 30mm × 10mm
- Mill cert 要求：是

---

## 主要尺寸

```
       ┌─────────────────┐
       │       50.00     │
       │ ┌──┐         ┌──┐│
       │ │ ●│         │● ││  ← φ6 通孔 × 4
       │ └──┘         └──┘│  孔距：50.00 ± 0.05
       │                  │  孔距：30.00 ± 0.05
       │ ┌──┐         ┌──┐│
       │ │ ●│         │● ││
       │ └──┘         └──┘│
       └──────────────────┘
        (10mm 厚)
```

| 尺寸     | 值       | 公差                |
| -------- | -------- | ------------------- |
| 長       | 50.00 mm | ± 0.05              |
| 寬       | 30.00 mm | ± 0.05              |
| 厚       | 10.00 mm | ± 0.10              |
| 4 × 孔徑 | φ6.00    | H7 (φ6.00 ~ +0.012) |
| 孔距 X   | 50.00    | ± 0.05              |
| 孔距 Y   | 30.00    | ± 0.05              |
| 倒角     | C0.5     | 各邊                |

---

## 表面處理

- 全面陽極氧化 II 級（黑色）
- 厚度：≥ 10 μm

---

## 表面粗糙度

- 加工面：Ra 1.6
- 非加工面：Ra 3.2

---

## 熱處理

- 無

---

## 訂單需求

- 數量：100 件
- 客戶要求交期：2026-05-15
- 付款條件：T/T 30
- 包裝：紙箱、每箱 50 件、防銹油

---

## 預期 demo 輸出

跑 `/quote @bracket.md` 後，`quote-specialist` 應該：

1. 觸發 `pre-quote` hook 確認以上資料齊全 → 通過
2. 認出是 CNC 件，dispatch `cnc-programmer`
3. cnc-programmer 提供加工方案（見 `cnc-programmer.md` 的 output 範例）
4. quote-specialist 整合報價
5. 產出格式：見 `examples/sample-quote-output.md`
