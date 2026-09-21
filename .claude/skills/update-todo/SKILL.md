---
name: update-todo
description: 從 ICS Canvas 抓取 FA、OB、MK、ECON 四門課的作業、quiz、考試與預習，更新 data.json 並 push 到 main，讓 GitHub Pages 上的待辦網頁同步更新。每日排程或手動更新待辦時使用。
---

# 更新 ICS 課程待辦

在 repo 根目錄依序執行以下步驟。任何一步失敗就印出錯誤訊息並停止，不要自行修改程式碼或資料來繞過。

1. **抓取 Canvas 資料**

   ```bash
   [ -z "$CANVAS_TOKEN" ] && [ -f .env ] && set -a && . ./.env && set +a
   python3 scripts/fetch.py
   ```

   本機會從 `.env` 讀取 `CANVAS_TOKEN`；雲端 routine 則由環境變數提供。

2. **判讀課程頁面**：讀 `work/pages_to_extract.json`。
   - 如果是空陣列 `[]`，跳過此步驟。
   - 否則用 Agent 工具呼叫 `page-extractor` 子代理，prompt 為：「處理 work/pages_to_extract.json，輸出 work/extracted.json」。
   - 完成後確認 `work/extracted.json` 存在，且包含每一個輸入頁面的 `page_url`。

3. **產生網頁資料**

   ```bash
   python3 scripts/build.py
   ```

4. **Commit 並 push**

   ```bash
   git add data.json data/page_cache.json
   git diff --cached --quiet || git commit -m "chore: update todo $(TZ=Asia/Tokyo date +%F)"
   git push origin HEAD:main
   ```

5. 回報：`data.json` 的項目數，以及本次新增的項目（`first_seen` 等於本次 `generated_at` 者）。
