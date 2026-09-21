# MEMO

## 執行方式
- 本機手動更新：在此資料夾開 Claude Code，執行 `/update-todo`（token 讀 `.env` 的 `CANVAS_TOKEN`）。
- 雲端排程：routine「ICS 課程待辦每日更新」（https://claude.ai/code/routines/trig_01FBGyPmMuY8DtfWaVKAYnEh），每天 19:00 JST（cron `0 10 * * *` UTC），環境 `ics-todo`（放 `CANVAS_TOKEN`、網路 Custom 允許 `canvas.ics.hit-u.ac.jp`）。
- 網頁：https://kevin-shu.github.io/ics-todo/（GitHub Pages，main 根目錄）。
- 本機預覽：`python3 -m http.server` 後開 `http://localhost:8000/`。

## 遇到的問題
- 課程頁面沒有 Canvas 的 to-do date，預習只寫在 Page 內文 → 交給 page-extractor（page-extractor）判讀，並以 `updated_at` 快取，只讀有變動的頁面。
- 各課上課日期格式不一，Python 難以解析 → 日期判斷也交給 page-extractor。
- ECON 的考試只寫在 Module 名稱 → 每門課加一頁「Module 大綱」虛擬頁面。
- OB 頁面只有日期沒有時間 → 每頁附上 Syllabus 前 1000 字，由其中的固定上課時間補上；仍找不到才用 00:00 並標 `time TBD`（網頁顯示 before class）。
- Haiku 會把 Canvas 已有的 quiz 從頁面再抽一次 → build.py 去重不限類型，同課標題相符就以 Canvas 為準。
- 在同一個 Claude Code session 中新建的 `.claude/agents/*` 不會被載入，要重開 session 才能用 `subagent_type: page-extractor`。
- 雲端環境只能從 claude.ai/code 輸入框上方的雲朵圖示 → Add cloud environment 建立，CLI 無法建立；新建環境後要重新載入 `/schedule` 才拿得到 environment id。
- Claude Code session 載入過 `.claude/agents/*.md` 後會快取該版本，之後修改檔案不會生效 → 本機測試改用 general-purpose + model haiku 並要求它先讀 page-extractor.md；雲端每次是新 session 不受影響。
- Haiku 會在 summary 自行擴寫縮寫（如 LLH）→ 指示中明訂只根據原文。
- Haiku 不穩定：會編造摘要內容、重跑時漏抓考試 → page-extractor 改用 Sonnet（只讀變動頁面，額度影響小）。
- 雲端 Sonnet 曾用 `${CANVAS_TOKEN:-no}` 把 token 印進 run log → SKILL.md 明訂不得輸出 token。
