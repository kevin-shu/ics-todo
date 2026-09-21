"""合併 Canvas 結構化項目與頁面抽取結果，更新 data/page_cache.json，寫出網頁用的 data.json。"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
CACHE = ROOT / "data" / "page_cache.json"
OUT = ROOT / "data.json"


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def norm(s):
    """標題正規化：只留小寫英數字，用來比對頁面作業與 Canvas 作業是否為同一項。"""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def update_cache():
    """把本次抽取結果寫進快取，並移除 Canvas 上已不存在的頁面。"""
    cache = load(CACHE, {})
    current = load(WORK / "current_pages.json", {})
    extracted = load(WORK / "extracted.json", {})
    for p in load(WORK / "pages_to_extract.json", []):
        # page：{items: [...]}；canvas_item：{summary}
        out = extracted[p["page_url"]]
        body = {"items": out} if p["kind"] == "page" else {"summary": out.get("summary", "")}
        cache[p["page_url"]] = {"updated_at": p["updated_at"], "kind": p["kind"], "course": p["course"], "title": p["title"], **body}
    cache = {url: v for url, v in cache.items() if url in current}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return cache


def build(cache):
    items = load(WORK / "canvas_items.json", [])
    for i in items:
        i["summary"] = cache.get(i["url"], {}).get("summary", "")
    canvas_titles = {(i["course"], norm(i["title"])) for i in items}
    for src, page in cache.items():
        if page["kind"] != "page":
            continue
        for it in page["items"]:
            # 頁面上的項目若已出現在 Canvas（同課、標題互相包含），以 Canvas 為準（有繳交狀態）
            if any(
                c == page["course"] and (norm(it["title"]) in t or t in norm(it["title"])) for c, t in canvas_titles
            ):
                continue
            items.append({
                "id": f"page:{src}#{norm(it['title'])}",
                "course": page["course"],
                "title": it["title"],
                "type": it["type"],
                "due": it["due"],
                "url": it.get("url"),  # 資源本身的連結，可能為 None
                "summary": it.get("summary", ""),
                "source_url": src,  # 出處（課程頁面）
                "source_title": page["title"],
                "submitted": False,
                "note": it.get("note", ""),
                "source": "page",
            })

    # 沿用上一版的 first_seen，新項目記錄為現在時間（網頁據此顯示 NEW）
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen = {i["id"]: i["first_seen"] for i in load(OUT, {"items": []})["items"]}
    for i in items:
        i["first_seen"] = seen.get(i["id"], now)
    OUT.write_text(json.dumps({"generated_at": now, "items": items}, ensure_ascii=False, indent=1))
    print(f"data.json: {len(items)} items")


if __name__ == "__main__":
    build(update_cache())
