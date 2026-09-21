"""從 Canvas 抓取資料：結構化的作業/quiz，以及需要交給 LLM 判讀的課程頁面（僅新增或有變動者）。"""
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://canvas.ics.hit-u.ac.jp"
COURSES = {1371: "MK", 1372: "FA", 1373: "OB", 1374: "ECON"}
# Planner 中屬於「學生要做的事」的類型（排除 announcement 等）
TODO_TYPES = {"assignment", "quiz", "discussion_topic"}

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
CACHE = ROOT / "data" / "page_cache.json"


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {os.environ['CANVAS_TOKEN']}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def to_text(body):
    """HTML 轉純文字，保留換行以利 LLM 閱讀。"""
    body = re.sub(r"<(br|/p|/li|/h\d|/div|/tr)[^>]*>", "\n", body or "")
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def fetch_canvas_items():
    start = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    items = []
    for p in get(f"/api/v1/planner/items?start_date={start}&per_page=100"):
        if p.get("course_id") not in COURSES or p["plannable_type"] not in TODO_TYPES:
            continue
        subs = p.get("submissions") or {}
        items.append({
            "id": f"canvas:{p['plannable_type']}:{p['plannable_id']}",
            "course": COURSES[p["course_id"]],
            "title": p["plannable"]["title"],
            "type": p["plannable_type"],
            "due": p.get("plannable_date"),
            "url": BASE + p["html_url"],
            "submitted": bool(subs.get("submitted")) if isinstance(subs, dict) else False,
            "source": "canvas",
        })
    return items


def fetch_pages():
    """回傳 (所有頁面的 {html_url: updated_at}, 需要重新判讀的頁面清單)。"""
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    current, changed = {}, []

    def check(url, updated_at, entry):
        current[url] = updated_at
        if cache.get(url, {}).get("updated_at") != updated_at:
            changed.append({"page_url": url, "updated_at": updated_at, **entry})

    for cid, code in COURSES.items():
        modules = get(f"/api/v1/courses/{cid}/modules?include[]=items&per_page=100")
        # 考試常只寫在 Module 名稱（如 ECON 的 Midterm / FINAL EXAM），把整門課的 Module 大綱當成一頁虛擬頁面；以大綱內容本身作為變動判斷依據
        outline = "\n".join(m["name"] for m in modules)
        check(f"{BASE}/courses/{cid}/modules", outline, {"course": code, "module": "(全部 Module 名稱)", "title": "Module 大綱", "text": outline})
        for m in modules:
            for it in m.get("items", []):
                if it["type"] != "Page":
                    continue
                try:
                    page = get(it["url"].removeprefix(BASE))
                except Exception as e:  # 老師鎖住的頁面會 403，略過即可
                    print("skip", it["title"], e)
                    continue
                check(it["html_url"], page["updated_at"],
                      {"course": code, "module": m["name"], "title": it["title"], "text": to_text(page.get("body"))})
    return current, changed


if __name__ == "__main__":
    WORK.mkdir(exist_ok=True)
    canvas_items = fetch_canvas_items()
    current, changed = fetch_pages()
    (WORK / "canvas_items.json").write_text(json.dumps(canvas_items, ensure_ascii=False, indent=1))
    (WORK / "current_pages.json").write_text(json.dumps(current, indent=1))
    (WORK / "pages_to_extract.json").write_text(json.dumps(changed, ensure_ascii=False, indent=1))
    # extracted.json 由 page-extractor 產生；先清掉舊的，避免沿用上次結果
    (WORK / "extracted.json").unlink(missing_ok=True)
    print(f"canvas items: {len(canvas_items)}, pages: {len(current)}, pages to extract: {len(changed)}")
