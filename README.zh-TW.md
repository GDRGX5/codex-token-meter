# Codex Token Meter

[English README](README.md)

這是一個不需要第三方套件、只在本機執行的 Codex token 用量儀表板。它能依日期及
模型統計 Codex Desktop／CLI 工作階段，拆分快取與推理 token，並以 OpenAI 標準
API 單價換算等值成本。

> API 等值是估算，不是 ChatGPT 訂閱帳單。

## 功能

- 本機網頁儀表板，支援英文與繁體中文
- 終端機報表支援英文與繁體中文
- 依日期、模型統計輸入、快取、快取寫入、輸出、推理及總 token
- API 等值成本統一以美元（USD）顯示
- 正確處理重複快照、續接工作階段與 Windows 正在寫入的紀錄檔
- 可輸出 JSON 供其他程式使用
- 不需要 API Key 或第三方 Python 套件
- 不解析、不顯示、不上傳聊天內容

## 快速開始

需要 Python 3.10 或更新版本。

### 本機網頁儀表板

Windows 解壓縮後，直接雙擊：

```text
RUN_WEB_DASHBOARD.cmd
```

macOS 或 Linux：

```bash
python3 chatgpt_usage.py --web
```

瀏覽器會開啟 `http://127.0.0.1:8765`。要停止時，在終端機按 `Ctrl+C`。

### 終端機報表

Windows：

```cmd
RUN_TOKEN_METER.cmd --days 7 --lang zh-TW
```

其他平台：

```bash
python3 chatgpt_usage.py --days 7 --lang zh-TW
```

常用範例：

```bash
# 今天
python3 chatgpt_usage.py --lang zh-TW

# 最近 30 天
python3 chatgpt_usage.py --days 30 --lang zh-TW

# 指定日期
python3 chatgpt_usage.py --date 2026-08-30 --lang zh-TW

# 全部本機紀錄（可能需要較長時間）
python3 chatgpt_usage.py --all --lang zh-TW

# JSON 輸出
python3 chatgpt_usage.py --days 7 --json
```

語言可選擇 `--lang auto`、`--lang en` 或 `--lang zh-TW`；自動模式會依作業系統
語系選擇。

## 統計方式

程式讀取以下位置的 `token_count` 中繼資料：

- `~/.codex/sessions`
- `~/.codex/archived_sessions`

Codex 會記錄累積用量，有時只因為速率限制資訊改變而重複寫入相同快照。本工具會
先依工作階段移除重複累積快照，再使用伺服器提供的 `last_token_usage` 增量。因此即使
工作階段分支、續接、匯入或累積計數器回退，也不會把整段累積量重複計算。

「輸入」包含快取輸入與快取寫入；推理 token 是輸出的子集合，不會重複收費。總量
可能遠高於肉眼看到的對話文字，因為代理每次執行工具後再次呼叫模型，都需要重新處理
目前上下文。

## 為什麼網頁版必須在本機執行？

一般託管網站（包括 GitHub Pages）受瀏覽器安全限制，不能自動讀取 `~/.codex`。
因此本專案使用只綁定 `127.0.0.1` 的小型 Python 伺服器。瀏覽器只向本機程式取得
彙整結果，原始聊天內容不會離開電腦。

純靜態網站可以要求使用者手動選擇匯出的紀錄檔，但多 GB 歷史的效能較差，也無法
可靠監控目前仍被 Codex 寫入的檔案。

## 價格與範圍

費率放在 [`prices.json`](prices.json)，不必修改程式即可更新。目前涵蓋 GPT-5.5、
GPT-5.6 Sol、Terra 與 Luna，包括快取輸入、GPT-5.6 快取寫入及長上下文倍率。

所有成本估算統一以美元（USD）顯示。估算只包含文字 token，不包含工具呼叫、
Web 搜尋、Computer Use、圖片、影片、語音、儲存、區域處理或其他費用。未知模型
會保持未計價，不會猜測。

這個工具只統計本機 Codex Desktop／CLI 工作階段，不是整個 ChatGPT 帳號的用量
計量器；未出現在 Codex JSONL 的一般 ChatGPT 網頁、手機或 Desktop 對話不會包含。

## 測試

```bash
python3 -m unittest discover -s tests -v
```

## 授權

[MIT](LICENSE)
