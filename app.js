// 讀取 data.json，依現在時間把項目分成「未完成 / 已過期未交 / 已完成」三區顯示
const TYPE_LABEL = { assignment: "作業", quiz: "Quiz", discussion_topic: "討論", prep: "預習", exam: "考試" };
// 可在 Canvas 繳交的類型，過期未交才列入「已過期未交」
const SUBMITTABLE = new Set(["assignment", "quiz", "discussion_topic"]);
const HOUR = 3600e3;

// 手動勾選狀態只存在本機瀏覽器；storage 不可用時忽略
const checked = (id) => { try { return localStorage.getItem("done:" + id) === "1"; } catch { return false; } };
const setChecked = (id, v) => { try { v ? localStorage.setItem("done:" + id, "1") : localStorage.removeItem("done:" + id); } catch {} };

// 一律以 JST 顯示，例如「9/28（一）09:30」
const fmt = (iso) => {
  if (!iso) return "未定";
  const p = Object.fromEntries(new Intl.DateTimeFormat("zh-TW", {
    timeZone: "Asia/Tokyo", month: "numeric", day: "numeric", weekday: "narrow", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.month}/${p.day}（${p.weekday}）${p.hour}:${p.minute}`;
};

function section(item, now) {
  const due = item.due ? new Date(item.due).getTime() : Infinity;
  if (item.submitted || checked(item.id)) return "done";
  if (due < now) return SUBMITTABLE.has(item.type) ? "overdue" : "done";
  return "pending";
}

function render(data) {
  const now = Date.now();
  document.getElementById("updated").textContent = "最後更新：" + fmt(data.generated_at);
  const lists = { pending: [], overdue: [], done: [] };
  for (const it of data.items) lists[section(it, now)].push(it);
  const t = (it) => (it.due ? new Date(it.due).getTime() : Infinity);
  lists.pending.sort((a, b) => t(a) - t(b));
  lists.overdue.sort((a, b) => t(a) - t(b));
  lists.done.sort((a, b) => t(b) - t(a));

  for (const [name, items] of Object.entries(lists)) {
    const ul = document.getElementById(name);
    ul.innerHTML = items.length ? "" : '<p class="empty">沒有項目</p>';
    for (const it of items) {
      const li = document.createElement("li");
      if (name === "pending" && t(it) - now < 48 * HOUR) li.className = "urgent";
      const isNew = now - new Date(it.first_seen).getTime() < 24 * HOUR;
      li.innerHTML = `
        <input type="checkbox" ${checked(it.id) || it.submitted ? "checked" : ""} ${it.submitted ? "disabled" : ""}>
        <div class="body">
          <a href="${it.url}" target="_blank" rel="noopener"></a>
          <div class="meta">
            <span class="course" style="color:var(--${it.course})">${it.course}</span>
            <span>${TYPE_LABEL[it.type] || it.type}</span>
            <span class="due">${fmt(it.due)}</span>
            ${it.note ? `<span>${it.note}</span>` : ""}
            ${isNew ? '<span class="new">NEW</span>' : ""}
          </div>
        </div>`;
      li.querySelector("a").textContent = it.title;
      li.querySelector("input").onchange = (e) => { setChecked(it.id, e.target.checked); render(data); };
      ul.appendChild(li);
    }
  }
}

fetch("data.json", { cache: "no-store" }).then((r) => r.json()).then(render);
