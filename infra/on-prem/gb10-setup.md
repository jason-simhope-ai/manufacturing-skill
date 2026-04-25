# 地端 LLM 安裝指南：GB10 + Ollama

> 給 IT 部門的硬體規格 + 軟體部署指南。
> 目標：圖紙與所有資料**完全不出公司**，AI 在自家伺服器跑。

---

## 為什麼要地端

| 雲端 LLM               | 地端 LLM                                  |
| ---------------------- | ----------------------------------------- |
| 資料要傳出去           | 資料不出公司                              |
| 客戶稽核可能擋         | 過 IATF / ISO 稽核無痛                    |
| 月費（每 token 計）    | 一次硬體投資、長期免費                    |
| 模型強（GPT-4 / Opus） | 模型中等（Qwen 2.5 / Llama 3 / DeepSeek） |
| 網路斷就掛             | 工廠停網仍可用                            |

對製造業（特別是接 OEM 客戶）：地端**幾乎是必選**。

---

## 推薦硬體：NVIDIA DGX Spark (GB10)

### 規格

| 項目   | 規格                                  |
| ------ | ------------------------------------- |
| GPU    | NVIDIA Grace Blackwell GB10 Superchip |
| 記憶體 | 128 GB unified memory                 |
| 儲存   | 4 TB NVMe SSD                         |
| 網路   | 10 GbE + WiFi                         |
| 形狀   | 桌上型（Mac mini 大小）               |
| 功耗   | < 200W（一般辦公插座可用）            |
| OS     | Ubuntu 24.04 ARM64 (DGX OS)           |
| 價格   | ~ NT$120,000（2026 Q1 行情）          |

**為什麼推 GB10**：

- 128 GB unified memory 跑得動 70B 模型
- 桌上型體積、辦公室插座可用、不需機房
- ARM 架構低功耗
- 一次投資、5 年攤提下來比雲端便宜

---

## 替代方案

| 預算        | 硬體                       | 模型上限  |
| ----------- | -------------------------- | --------- |
| < NT$30,000 | RTX 4070（消費級）         | ~13B 模型 |
| NT$50,000   | RTX 4090                   | ~30B 模型 |
| NT$120,000  | **DGX Spark GB10**（推薦） | ~70B 模型 |
| NT$300,000+ | DGX Station / 多卡         | 70B+ 模型 |

> 中小工廠：GB10 一台 fits all.

---

## 軟體部署（GB10）

### 1. 系統初始化

```bash
# 接電源、接網路、接螢幕
# 開機跑 DGX OS 初始設定（一次）
sudo apt update && sudo apt upgrade -y
```

### 2. 安裝 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 3. 下載推薦模型

```bash
# 一般用途（回應快）
ollama pull qwen2.5:14b

# 較強（回應慢但答得好）
ollama pull qwen2.5:32b
ollama pull deepseek-coder:33b

# 高階（GB10 最大可跑）
ollama pull qwen2.5:72b
```

### 4. 驗證跑得起來

```bash
ollama run qwen2.5:14b
>>> 報價的 6 個基本步驟是什麼？
```

### 5. 設定為 Claude Code 的 fallback LLM

`~/.claude/settings.json`：

```json
{
  "llm": {
    "primary": "anthropic", // 線上時用 Claude
    "fallback": {
      "type": "ollama",
      "endpoint": "http://localhost:11434",
      "model": "qwen2.5:32b"
    }
  }
}
```

---

## 網路架構

```
工廠網路
  ├─ ERP / MES (內網)
  ├─ GB10 (內網, 192.168.X.X) ← Ollama
  ├─ 工程師電腦 (內網) ← Claude Code
  └─ 防火牆
       └─ 外網 (Anthropic API 線上時用)

最敏感場景（圖紙絕不外流）：
  - 把 Claude Code 的 primary 改成 ollama
  - 防火牆封禁 anthropic.com 流量
  - 完全 air-gapped
```

---

## 資安檢查清單（給 IT 稽核用）

- [ ] GB10 在工廠內網，無公網 IP
- [ ] Ollama 只 listen on localhost (`OLLAMA_HOST=127.0.0.1:11434`) 或內網段
- [ ] 模型權重落在加密 SSD（DGX OS 預設啟用 LUKS）
- [ ] AI 生成的所有 record 寫入 audit log
- [ ] 圖紙、BOM 等敏感檔案 `.gitignore` 確實排除
- [ ] 定期備份：權重、自訂 fine-tune（如有）
- [ ] 漏洞管理：Ollama / 模型版本定期更新
- [ ] 物理安全：GB10 放上鎖機櫃 / 有監視

---

## 效能基準（GB10 + qwen2.5:32b）

| 任務                     | 預期時間 |
| ------------------------ | -------- |
| `/quote` 一份簡單件報價  | 30~60 秒 |
| `/order-status` 查單狀態 | 5~15 秒  |
| `/inspect` FQC 結果分析  | 20~40 秒 |
| 一段 G-code review       | 10~30 秒 |

> 如果 > 2 分鐘，檢查是否吃到 swap（RAM 不夠），降模型大小。

---

## Troubleshooting

| 症狀                      | 原因                     | 解法                                        |
| ------------------------- | ------------------------ | ------------------------------------------- |
| Ollama 跑超慢             | 模型超過 unified memory  | 降模型大小（72b → 32b）                     |
| Claude Code 連不到 Ollama | endpoint 設錯            | 確認 `http://localhost:11434/api/tags` 能回 |
| 模型答非所問              | 模型太小 / prompt 太複雜 | 升模型 / 簡化 prompt                        |
| 機台溫度爆                | 散熱不良                 | 確保進出風口暢通、室溫 < 28°C               |

---

## 維運成本估算

| 項目                                  | 月成本            |
| ------------------------------------- | ----------------- |
| 電費（200W × 24h × 30d × NT$3.5/kWh） | ~ NT$500          |
| 折舊（120,000 / 60 個月）             | NT$2,000          |
| 維護（年保險）                        | ~ NT$500/月       |
| **總計**                              | **~ NT$3,000/月** |

對比雲端 Claude API：100 萬 token/月 ≈ NT$5,000/月，且資料外流。

---

## 接下來

- 看 `infra/mcp-servers/scheduler-mcp/README.md` 把生產資料接上
- 看 `infra/mcp-servers/erp-connector/README.md` 接你的 ERP
- 看 `docs/adoption-guide.md` 完整導入順序
