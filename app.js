// 讀取 data.json，依現在時間把項目分成「To do / Overdue / Done」三區顯示
const TYPE_LABEL = { assignment: "Assignment", quiz: "Quiz", discussion_topic: "Discussion", prep: "Prep", exam: "Exam" };
// 可在 Canvas 繳交的類型，過期未交才列入「Overdue」
const SUBMITTABLE = new Set(["assignment", "quiz", "discussion_topic"]);
const HOUR = 3600e3;

// 手動勾選狀態只存在本機瀏覽器；storage 不可用時忽略
const checked = (id) => { try { return localStorage.getItem("done:" + id) === "1"; } catch { return false; } };
const setChecked = (id, v) => { try { v ? localStorage.setItem("done:" + id, "1") : localStorage.removeItem("done:" + id); } catch {} };

// 一律以 JST 顯示，例如「Tue 9/22 09:45」；時間未定則顯示「Tue 9/22 · before class」
const fmt = (iso, tbd) => {
  if (!iso) return "TBD";
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.weekday} ${p.month}/${p.day} ` + (tbd ? "· before class" : `${p.hour}:${p.minute}`);
};

// 文字一律經 textContent 放入，避免 Canvas 內容中的 HTML 被執行
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; };
const link = (href, text) => { const a = el("a", "", text); a.href = href; a.target = "_blank"; a.rel = "noopener"; return a; };

function section(item, now) {
  const due = item.due ? new Date(item.due).getTime() : Infinity;
  if (item.submitted || checked(item.id)) return "done";
  if (due < now) return SUBMITTABLE.has(item.type) ? "overdue" : "done";
  return "pending";
}

function card(it, name, now, data) {
  const t = it.due ? new Date(it.due).getTime() : Infinity;
  const li = el("li");
  if (name === "pending" && t - now < 48 * HOUR) li.className = "urgent";
  li.style.borderLeftColor = `var(--${it.course})`;

  const box = el("input");
  box.type = "checkbox";
  box.checked = checked(it.id) || it.submitted;
  box.disabled = it.submitted;
  box.onchange = (e) => { setChecked(it.id, e.target.checked); render(data); };

  const body = el("div", "body");
  // 標題連到資源本身；沒有資源連結則為純文字
  const title = el("div", "title");
  title.append(it.url ? link(it.url, it.title) : it.title);
  body.append(title);
  if (it.summary) body.append(el("div", "summary", it.summary));

  const meta = el("div", "meta");
  const course = el("span", "course", it.course);
  course.style.background = `var(--${it.course})`;
  meta.append(course, el("span", "", TYPE_LABEL[it.type] || it.type), el("span", "due", fmt(it.due, it.note === "time TBD")));
  if (it.note && it.note !== "time TBD") meta.append(el("span", "", it.note));
  if (now - new Date(it.first_seen).getTime() < 24 * HOUR) meta.append(el("span", "new", "NEW"));
  body.append(meta);

  // 出處（課程頁面）放最後一行
  if (it.source_url) {
    const src = el("div", "source");
    src.append("(source: ", link(it.source_url, it.source_title), ")");
    body.append(src);
  }
  li.append(box, body);
  return li;
}

function render(data) {
  const now = Date.now();
  document.getElementById("updated").textContent = "Last updated: " + fmt(data.generated_at);
  const lists = { pending: [], overdue: [], done: [] };
  for (const it of data.items) lists[section(it, now)].push(it);
  const t = (it) => (it.due ? new Date(it.due).getTime() : Infinity);
  lists.pending.sort((a, b) => t(a) - t(b));
  lists.overdue.sort((a, b) => t(a) - t(b));
  lists.done.sort((a, b) => t(b) - t(a));

  for (const [name, items] of Object.entries(lists)) {
    const ul = document.getElementById(name);
    ul.replaceChildren(...(items.length ? items.map((it) => card(it, name, now, data)) : [el("p", "empty", "Nothing here")]));
  }
}

fetch("data.json", { cache: "no-store" }).then((r) => r.json()).then(render);
