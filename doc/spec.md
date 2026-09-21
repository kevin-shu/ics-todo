# ICS 課程待辦 — Spec

## 目的

每天自動從 ICS Canvas（`https://canvas.ics.hit-u.ac.jp`）抓取 MK、FA、OB、ECON 四門課中「學生需要做的事」（作業、quiz、考試、預習），連同 deadline 顯示在 GitHub Pages 網頁上。

| 代號 | Course ID |
|---|---|
| MK | 1371 |
| FA | 1372 |
| OB | 1373 |
| ECON | 1374 |

## 架構

```
雲端 routine（每天 19:00 JST，Sonnet 5）
  └─ /update-todo skill
       1. scripts/fetch.py        Canvas API → work/*.json
       2. page-extractor（Haiku）  頁面文字 → work/extracted.json
       3. scripts/build.py        合併 → data.json、data/page_cache.json
       4. git commit + push main  → GitHub Pages 更新
網頁：index.html + app.js 讀 data.json
```

## 資料來源

1. **結構化項目**：Planner API `GET /api/v1/planner/items?start_date=<今天-14天>`，只保留上述 4 門課，且 `plannable_type` 為 `assignment` / `quiz` / `discussion_topic`（排除公告）。繳交狀態取自 `submissions.submitted`。
2. **非結構化項目**：預習、只寫在頁面中的作業與考試。來源為各課 Modules 中的 Page 內文，以及每門課的「Module 大綱」虛擬頁面（所有 Module 名稱，用來抓只寫在 Module 名稱的考試）。
   - 只有新出現或 `updated_at` 改變的頁面才交給 Haiku 判讀（大綱頁以大綱文字本身當作 `updated_at`）。
   - 判讀結果存在 `data/page_cache.json`，未變動的頁面沿用快取。

## 檔案

| 路徑 | 內容 | 寫入者 | 讀取者 |
|---|---|---|---|
| `work/canvas_items.json` | Planner 結構化項目 | fetch.py | build.py |
| `work/current_pages.json` | 目前所有頁面 `{page_url: updated_at}` | fetch.py | build.py（清除已刪頁面） |
| `work/pages_to_extract.json` | 需判讀的頁面（含內文） | fetch.py | page-extractor、build.py |
| `work/extracted.json` | `{page_url: [{title, type, due, note}]}` | page-extractor | build.py |
| `data/page_cache.json` | `{page_url: {updated_at, course, items}}`，跨日記憶 | build.py | fetch.py、build.py |
| `data.json` | `{generated_at, items: [...]}` 網頁資料 | build.py | app.js、build.py（沿用 first_seen） |

`work/` 為每次執行的暫存，不進 git。

### data.json 項目欄位

`id`、`course`、`title`、`type`（assignment / quiz / discussion_topic / prep / exam）、`due`（ISO，可為 null）、`url`、`submitted`、`note`、`source`（canvas / page）、`first_seen`。

- `id`：Canvas 項目為 `canvas:<type>:<plannable_id>`；頁面項目為 `page:<page_url>#<正規化標題>`。
- 去重：頁面抽出的項目（不論類型）若與同課 Canvas 項目標題（小寫英數字）互相包含，丟棄頁面那筆。
- `first_seen`：沿用上一版 `data.json`，新項目為本次執行時間。

## 網頁顯示規則（app.js）

- **未完成**：依 deadline 排序；距 deadline < 48 小時標紅。
- **已過期未交**：過了 deadline 且未繳交的 assignment / quiz / discussion_topic。
- **已完成 / 已結束**：Canvas 顯示已繳交、手動勾選，或已過時間的預習與考試（預設收合）。
- `first_seen` 在 24 小時內顯示 NEW。
- 勾選狀態存在瀏覽器 localStorage（`done:<id>`），只在該瀏覽器有效。
- 介面繁中，作業標題保留原文，時間一律 JST，格式「9/28（一）09:30」。

## 執行環境

- **雲端 routine**：repo `kevin-shu/ics-todo`，model Sonnet 5，每天 19:00 JST，prompt「執行 /update-todo」。
- **環境變數** `CANVAS_TOKEN`：Canvas 個人 Access Token，設定在 claude.ai/code 的雲端環境中，絕不進 repo。
- **網路**：Custom，加上 `canvas.ics.hit-u.ac.jp`，並保留預設清單。
- **本機**：`.env` 放 `CANVAS_TOKEN`（已 gitignore），在 Claude Code 中執行 `/update-todo`。
