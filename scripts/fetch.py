"""從 Canvas 抓取資料：結構化的作業/quiz，以及需要交給 LLM 判讀的課程頁面與作業說明（僅新增或有變動者）。"""
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://canvas.ics.hit-u.ac.jp"
COURSES = {1371: "MK", 1372: "FA", 1373: "OB", 1374: "ECON"}
# Planner 中屬於「學生要做的事」的類型（排除 announcement 等），對應取得說明文字的 API 路徑與欄位
TODO_TYPES = {
    "assignment": ("assignments", "description"),
    "quiz": ("quizzes", "description"),
    "discussion_topic": ("discussion_topics", "message"),
}

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
CACHE = ROOT / "data" / "page_cache.json"


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {os.environ['CANVAS_TOKEN']}"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def to_text(body):
    """HTML 轉純文字，保留換行；超連結轉成 [文字](URL) 讓 LLM 取得資源網址。"""
    body = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", body or "", flags=re.S)
    body = re.sub(r"<(br|/p|/li|/h\d|/div|/tr)[^>]*>", "\n", body)
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
            # 取得作業說明用的 API 路徑，寫檔前移除
            "api": f"/api/v1/courses/{p['course_id']}/{TODO_TYPES[p['plannable_type']][0]}/{p['plannable_id']}",
        })
    return items


def fetch_pages(canvas_items):
    """回傳 (所有頁面與作業的 {url: updated_at}, 需要重新判讀的清單)。"""
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    current, changed = {}, []

    def check(url, updated_at, entry):
        current[url] = updated_at
        if cache.get(url, {}).get("updated_at") != updated_at:
            changed.append({"page_url": url, "updated_at": updated_at, **entry})

    # Canvas 作業/quiz 的說明，交給 LLM 產生一句話摘要
    for it in canvas_items:
        a = get(it.pop("api"))
        check(it["url"], a.get("updated_at"),
              {"kind": "canvas_item", "course": it["course"], "title": it["title"], "text": to_text(a.get(TODO_TYPES[it["type"]][1]))})

    for cid, code in COURSES.items():
        # Syllabus 常寫有上課時間（如 OB 的 Tuesdays / Fridays 0945-1145），供頁面缺時間時參考
        syllabus = to_text(get(f"/api/v1/courses/{cid}?include[]=syllabus_body").get("syllabus_body"))[:1000]
        modules = get(f"/api/v1/courses/{cid}/modules?include[]=items&per_page=100")
        # 考試常只寫在 Module 名稱（如 ECON 的 Midterm / FINAL EXAM），把整門課的 Module 大綱當成一頁虛擬頁面；以大綱內容本身作為變動判斷依據
        outline = "\n".join(m["name"] for m in modules)
        # 課程表：所有 Module 名稱與其下 Page 標題（上課日期寫在其中之一），讓 LLM 查「Session N」是哪天，以抽出頁面中交代給之後課堂的預習
        schedule = "\n".join(
            "\n".join([m["name"]] + [f"  - {it['title']}" for it in m.get("items", []) if it["type"] == "Page"]) for m in modules
        )
        check(f"{BASE}/courses/{cid}/modules", outline,
              {"kind": "page", "course": code, "module": "(all module names)", "title": "Module outline", "syllabus": syllabus, "text": outline})
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
                      {"kind": "page", "course": code, "module": m["name"], "title": it["title"], "syllabus": syllabus, "schedule": schedule, "text": to_text(page.get("body"))})
    return current, changed


if __name__ == "__main__":
    WORK.mkdir(exist_ok=True)
    canvas_items = fetch_canvas_items()
    current, changed = fetch_pages(canvas_items)
    (WORK / "canvas_items.json").write_text(json.dumps(canvas_items, ensure_ascii=False, indent=1))
    (WORK / "current_pages.json").write_text(json.dumps(current, indent=1))
    (WORK / "pages_to_extract.json").write_text(json.dumps(changed, ensure_ascii=False, indent=1))
    # extracted.json 由 page-extractor 產生；先清掉舊的，避免沿用上次結果
    (WORK / "extracted.json").unlink(missing_ok=True)
    print(f"canvas items: {len(canvas_items)}, pages: {len(current)}, pages to extract: {len(changed)}")
