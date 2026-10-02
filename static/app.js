"use strict";
const $ = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat().format(n ?? 0);
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let user,
  media = [],
  logs = [],
  daily = [],
  summary,
  chart,
  progressChart;
let days = 30,
  offset = 0,
  searchOffset = 0,
  searchQuery = "",
  importPreview = null;
let searchHasMore = false;
let linkingMedia = null;
let heatYear = null,
  heatData = [],
  heatRequest = 0;
let noticeTimer;
const colors = [
  "#d6a338",
  "#d49b29",
  "#4e76bb",
  "#ad5279",
  "#689740",
  "#6e60a1",
  "#357e9a",
];
function icons() {
  window.lucide?.createIcons();
}
function notify(text, error = false) {
  clearTimeout(noticeTimer);
  $("notice").textContent = text;
  $("notice").classList.toggle("error", error);
  $("notice").hidden = false;
  noticeTimer = setTimeout(
    () => ($("notice").hidden = true),
    error ? 12000 : 5000,
  );
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Reading-Site": "1",
      ...options.headers,
    },
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      `Server returned ${response.status}; check the server log.`,
    );
  }
  if (!response.ok) {
    if (response.status === 401 && user) {
      user = null;
      showAuth();
    }
    const detail = Array.isArray(data.detail)
      ? data.detail.map((x) => `${x.loc.at(-1)}: ${x.msg}`).join("; ")
      : data.detail;
    const retry = response.headers.get("Retry-After");
    throw new Error(
      (detail || "Request failed") +
        (retry ? ` Retry after ${retry} seconds.` : ""),
    );
  }
  return data;
}
function on(id, event, fn) {
  $(id).addEventListener(event, async (e) => {
    if (event === "submit") e.preventDefault();
    const button = e.submitter || e.target.closest("button");
    if (button) button.disabled = true;
    try {
      await fn(e);
    } catch (err) {
      notify(err.message, true);
    } finally {
      if (button) button.disabled = false;
      $("history-prev").disabled = offset === 0;
      $("history-next").disabled = logs.length < 50;
      $("search-prev").disabled = searchOffset === 0;
      $("search-next").disabled = !searchHasMore;
    }
  });
}
function showAuth() {
  $("auth-view").hidden = false;
  $("app-view").hidden = true;
  $("account").hidden = true;
  $("signed-out-title").hidden = false;
  document.querySelectorAll("dialog[open]").forEach((d) => d.close());
  $("token-value").value = "";
  $("token-label").hidden = true;
}
function tab(name) {
  if (name === "library") name = "dashboard";
  document
    .querySelectorAll(".view")
    .forEach((el) => (el.hidden = el.id !== name));
  document.querySelectorAll("[data-tab]").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === name);
    if (el.dataset.tab === name) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  if (name === "tools") requestAnimationFrame(renderChart);
}
async function refresh() {
  [media, summary, daily, logs] = await Promise.all([
    api("/api/media"),
    api("/api/stats/summary"),
    api("/api/stats/daily?days=365"),
    api(`/api/logs?offset=${offset}&limit=50`),
  ]);
  $("auth-view").hidden = true;
  $("app-view").hidden = false;
  $("account").hidden = false;
  $("signed-out-title").hidden = true;
  $("username").textContent = user.username;
  renderStats();
  renderMedia();
  renderHistory();
  renderSettings();
  renderQuickLog();
  icons();
  await loadHeatmap(heatYear ?? Number(summary.today.slice(0, 4)));
}
function renderStats() {
  $("today-count").textContent = fmt(summary.today_chars);
  $("total-count").textContent = fmt(summary.total_chars);
  $("reading-streak").textContent = fmt(summary.reading_streak);
  $("today-progress").max = user.daily_goal;
  $("today-progress").value = summary.today_chars;
  $("today-goal").textContent = fmt(user.daily_goal);
  const values = [
    ["Goal streak", `${fmt(summary.goal_streak)} days`],
    ["Reading days", fmt(summary.reading_days)],
    ["This week", `${fmt(summary.weekly_chars)} / ${fmt(user.weekly_goal)}`],
    ["This month", `${fmt(summary.monthly_chars)} / ${fmt(user.monthly_goal)}`],
    [
      "Best day",
      `${fmt(summary.best_day_chars)}${summary.best_day ? ` (${summary.best_day})` : ""}`,
    ],
    ["Average / calendar day", fmt(summary.average_calendar_day)],
    ["Average / reading day", fmt(summary.average_reading_day)],
    [
      "Characters / hour",
      summary.chars_per_hour == null
        ? "No timed sessions"
        : fmt(summary.chars_per_hour),
    ],
  ];
  $("more-stats").innerHTML = values
    .map(
      ([a, b]) => `<div><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`,
    )
    .join("");
  if (!$("tools").hidden) renderChart();
}
function renderQuickLog() {
  const selected = $("quick-media").value;
  $("quick-media").innerHTML =
    '<option value="">Choose a title</option><option value="new">Enter new media...</option>' +
    media
      .map(
        (m) =>
          `<option value="${m.id}">${esc(m.title)} (${mediaType(m)})</option>`,
      )
      .join("");
  if (media.some((m) => String(m.id) === selected))
    $("quick-media").value = selected;
  else if (media.length === 1) $("quick-media").value = media[0].id;
  $("quick-media").disabled = false;
  $("quick-submit").disabled = !media.length;
  $("quick-date").value ||= summary.today;
  $("quick-date").max = summary.today;
  $("quick-goal").value = user.daily_goal;
}
async function loadHeatmap(year) {
  if (!Number.isInteger(year) || year < 1900 || year > 9998)
    throw new Error("Choose a year between 1900 and 9998.");
  const request = ++heatRequest;
  const rows = await api(`/api/stats/daily?year=${year}`);
  if (request !== heatRequest || !user) return;
  heatYear = year;
  heatData = rows;
  $("heat-year").value = year;
  $("year-prev").disabled = year <= 1900;
  $("year-next").disabled = year >= 9998;
  const padding = (new Date(`${rows[0].date}T12:00:00Z`).getUTCDay() + 6) % 7;
  $("heatmap").setAttribute(
    "aria-label",
    `Reading activity for ${year}, ${rows.length} days`,
  );
  $("heatmap").innerHTML =
    '<span class="blank" aria-hidden="true"></span>'.repeat(padding) +
    rows
      .map((d) => {
        const level = !d.chars
          ? 0
          : d.chars < user.daily_goal * 0.5
            ? 1
            : d.chars < user.daily_goal
              ? 2
              : d.chars < user.daily_goal * 2
                ? 3
                : 4;
        const future = d.date > summary.today;
        const label = `${d.date}: ${future ? "Future date" : `${fmt(d.chars)} characters`}`;
        return `<button type="button" data-heat="${esc(label)}" data-date="${d.date}" data-level="${level}" class="${future ? "future" : ""}" title="${esc(label)}" aria-label="${esc(label)}" ${future ? "disabled" : ""}></button>`;
      })
      .join("");
  $("heat-months").innerHTML = rows
    .map((d, i) =>
      d.date.endsWith("-01")
        ? `<span style="grid-column:${Math.floor((i + padding) / 7) + 1}">${new Date(`${d.date}T12:00:00Z`).toLocaleDateString("en", { month: "short", timeZone: "UTC" })}</span>`
        : "",
    )
    .join("");
  $("heat-selection").textContent =
    `${rows.filter((d) => d.chars > 0).length} reading days in ${year}`;
}
function renderChart() {
  if (!window.Chart) return;
  chart?.destroy();
  const rows = daily.slice(-days);
  const active = media.filter((m) => rows.some((r) => r.media[m.id]));
  chart = new Chart($("daily-chart"), {
    type: "bar",
    data: {
      labels: rows.map((r) => r.date),
      datasets: [
        ...active.map((m, i) => ({
          label: m.title,
          data: rows.map((r) => r.media[m.id] || 0),
          backgroundColor: colors[i % colors.length],
          stack: "reading",
          borderRadius: 2,
        })),
        {
          type: "line",
          label: "Daily goal",
          data: rows.map(() => user.daily_goal),
          borderColor: "#a65c38",
          borderDash: [5, 5],
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
          stack: "goal",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { maxTicksLimit: 10, maxRotation: 0 },
        },
        y: { stacked: true, beginAtZero: true },
      },
    },
  });
}
function action(icon, label, kind, id) {
  return `<button type="button" class="icon quiet" data-${kind}="${id}" title="${label}" aria-label="${label}"><i data-lucide="${icon}"></i></button>`;
}
function renderMedia() {
  const filter = $("status-filter").value;
  const query = $("library-query").value.trim().toLocaleLowerCase();
  const items = media.filter(
    (m) =>
      (filter === "all" || m.status === filter) &&
      m.title.toLocaleLowerCase().includes(query),
  );
  $("media-list").innerHTML = items.length
    ? items
        .map(
          (m) =>
            `<article class="book book-${esc(m.status)}"><button class="book-cover" type="button" data-progress="${m.id}" title="${esc(m.title)}" aria-label="Open ${esc(m.title)}"><span class="cover-fallback" aria-hidden="true">${esc(m.title)}</span>${coverImage(m)}</button><span class="book-type">${mediaType(m)}</span><span class="book-title" title="${esc(m.title)}">${esc(m.title)}</span><span class="book-mark"><i data-lucide="${m.status === "finished" ? "check" : "bookmark"}"></i>${esc(m.status)}</span><small>${m.total_chars ? `${Math.min(100, Math.round((m.read_chars / m.total_chars) * 100))}% read` : `${fmt(m.read_chars)} chars`}</small></article>`,
        )
        .join("")
    : `<div class="empty-library"><i data-lucide="book-open"></i><p>${media.length ? "No matching titles." : "Your next chapter starts here."}</p>${media.length ? "" : '<button type="button" class="secondary" data-new-title>Add your first title</button>'}</div>`;
  icons();
}
function mediaType(item) {
  return (
    {
      novel: "Novel",
      visual_novel: "Visual novel",
      manga: "Manga",
      other: "Other",
    }[item.media_type] || "Other"
  );
}
function coverImage(item) {
  try {
    const url = new URL(item.cover_url);
    if (url.protocol !== "https:" || url.username || url.password) return "";
    return `<img class="jiten-cover" src="${esc(url.href)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">`;
  } catch {
    return "";
  }
}
document.addEventListener(
  "error",
  (event) => {
    if (
      event.target instanceof HTMLImageElement &&
      event.target.classList.contains("jiten-cover")
    )
      event.target.remove();
  },
  true,
);
function renderHistory() {
  $("log-rows").innerHTML = logs.length
    ? logs
        .map(
          (log) =>
            `<tr><td>${esc(log.date)}</td><td>${esc(media.find((m) => m.id === log.media_id)?.title)}</td><td>${fmt(log.chars)}</td><td>${log.minutes ?? ""}</td><td>${action("pencil", "Edit reading", "edit-log", log.id)}${action("trash-2", "Delete reading", "delete-log", log.id)}</td></tr>`,
        )
        .join("")
    : '<tr><td colspan="5" class="empty">No reading logs yet.</td></tr>';
  $("history-page").textContent = `Page ${offset / 50 + 1}`;
  $("history-prev").disabled = offset === 0;
  $("history-next").disabled = logs.length < 50;
  icons();
}
function renderSettings() {
  const form = $("settings-form");
  for (const key of ["daily_goal", "weekly_goal", "monthly_goal", "timezone"])
    form.elements[key].value = user[key];
  form.elements.public_profile.checked = user.public_profile;
  $("profile-link").hidden = !user.public_profile;
  $("profile-link").href = `/profile/${encodeURIComponent(user.username)}`;
}
function openLog(log = null, mediaId = null) {
  if (!media.length) {
    tab("library");
    openMedia();
    notify("Add a title first.");
    return;
  }
  const form = $("log-form");
  form.reset();
  form.elements.media_id.innerHTML = media
    .map((m) => `<option value="${m.id}">${esc(m.title)}</option>`)
    .join("");
  form.elements.id.value = log?.id || "";
  form.elements.date.value = log?.date || summary.today;
  form.elements.date.max = summary.today;
  form.elements.chars.value = log?.chars || "";
  form.elements.minutes.value = log?.minutes || "";
  if (log || mediaId) form.elements.media_id.value = log?.media_id || mediaId;
  $("log-heading").textContent = log ? "Edit reading" : "Log reading";
  $("log-dialog").showModal();
}
function openMedia(item = null) {
  const form = $("media-form");
  form.reset();
  form.elements.id.value = item?.id || "";
  for (const key of ["title", "total_chars", "media_type", "status"])
    if (item) form.elements[key].value = item[key] ?? "";
  $("media-heading").textContent = item ? "Edit title" : "Add title";
  $("media-dialog").showModal();
}
async function search() {
  const result = await api(
    `/api/jiten/search?q=${encodeURIComponent(searchQuery)}&offset=${searchOffset}&media_type=${$("search-type").value}`,
  );
  searchHasMore = result.has_more;
  $("search-results").hidden = false;
  $("search-results").innerHTML = result.items.length
    ? result.items
        .map(
          (m) =>
            `<div class="search-row"><div class="search-cover"><span class="cover-fallback" aria-hidden="true">${mediaType(m)}</span>${coverImage(m)}</div><div class="grow"><strong>${esc(m.title)}</strong><small>${mediaType(m)} &middot; ${fmt(m.total_chars)} characters &middot; Difficulty ${esc(m.difficulty ?? "n/a")}</small></div><button data-add-jiten="${m.jiten_id}" data-jiten-title="${esc(m.title)}" ${!linkingMedia && media.some((x) => x.jiten_id === m.jiten_id) ? "disabled" : ""}>${linkingMedia ? "Link" : media.some((x) => x.jiten_id === m.jiten_id) ? "Added" : "Add"}</button></div>`,
        )
        .join("")
    : '<p class="empty">No matching titles found.</p>';
  $("search-pages").hidden = false;
  $("search-prev").disabled = !searchOffset;
  $("search-next").disabled = !result.has_more;
}
on("auth-form", "submit", async (e) => {
  const form = new FormData(e.target);
  user = await api(`/api/${e.submitter.value}`, {
    method: "POST",
    body: JSON.stringify({
      username: form.get("username"),
      password: form.get("password"),
    }),
  });
  e.target.reset();
  offset = 0;
  tab("dashboard");
  await refresh();
});
on("logout", "click", async () => {
  await api("/api/logout", { method: "POST" });
  user = null;
  media = [];
  logs = [];
  daily = [];
  importPreview = null;
  showAuth();
});
on("quick-log-form", "submit", async (e) => {
  const values = Object.fromEntries(new FormData(e.target));
  await api("/api/logs", {
    method: "POST",
    body: JSON.stringify({
      media_id: Number(values.media_id),
      date: values.date,
      chars: Number(values.chars),
      minutes: null,
    }),
  });
  $("quick-chars").value = "";
  offset = 0;
  await refresh();
  notify("Reading logged!");
});
on("quick-goal-form", "submit", async () => {
  const { daily_goal, weekly_goal, monthly_goal, timezone, public_profile } =
    user;
  const nextGoal = Number($("quick-goal").value);
  if (nextGoal === daily_goal) return;
  user = await api("/api/me", {
    method: "PATCH",
    body: JSON.stringify({
      daily_goal: nextGoal,
      weekly_goal,
      monthly_goal,
      timezone,
      public_profile,
    }),
  });
  await refresh();
  notify("Daily goal saved.");
});
function openJitenSearch(item = null) {
  linkingMedia = item;
  $("search-dialog").querySelector("h2").textContent = item
    ? `Link to Jiten: ${item.title}`
    : "Enter new media";
  $("search-results").hidden = true;
  $("search-results").innerHTML = "";
  $("search-pages").hidden = true;
  $("search-query").value = item?.title || "";
  $("search-type").value =
    item?.media_type === "visual_novel" ? "visual_novel" : "novel";
  searchOffset = 0;
  $("search-dialog").showModal();
  $("search-query").focus();
}
on("find-title", "click", () => openJitenSearch());
on("quick-media", "change", () => {
  if ($("quick-media").value !== "new") return;
  $("quick-media").value = "";
  openJitenSearch();
});
on("search-type", "change", async () => {
  searchOffset = 0;
  searchQuery = $("search-query").value.trim();
  if (searchQuery) await search();
});
on("library-query", "input", renderMedia);
on("heat-year", "change", () => loadHeatmap(Number($("heat-year").value)));
on("year-prev", "click", () => loadHeatmap(heatYear - 1));
on("year-next", "click", () => loadHeatmap(heatYear + 1));
on("history-log", "click", () => openLog());
on("manual-add", "click", () => openMedia());
on("status-filter", "change", renderMedia);
on("log-form", "submit", async (e) => {
  const f = Object.fromEntries(new FormData(e.target));
  const id = f.id;
  delete f.id;
  f.media_id = Number(f.media_id);
  f.chars = Number(f.chars);
  f.minutes = f.minutes ? Number(f.minutes) : null;
  await api(`/api/logs${id ? `/${id}` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(f),
  });
  $("log-dialog").close();
  offset = 0;
  await refresh();
  notify("Reading saved.");
});
on("media-form", "submit", async (e) => {
  const f = Object.fromEntries(new FormData(e.target));
  const id = f.id;
  delete f.id;
  f.total_chars = f.total_chars ? Number(f.total_chars) : null;
  await api(`/api/media${id ? `/${id}` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(f),
  });
  $("media-dialog").close();
  await refresh();
  notify("Title saved.");
});
on("history-prev", "click", async () => {
  offset = Math.max(0, offset - 50);
  logs = await api(`/api/logs?offset=${offset}`);
  renderHistory();
});
on("history-next", "click", async () => {
  offset += 50;
  logs = await api(`/api/logs?offset=${offset}`);
  renderHistory();
});
on("search-form", "submit", async () => {
  searchQuery = $("search-query").value.trim();
  searchOffset = 0;
  await search();
});
on("search-prev", "click", async () => {
  searchOffset = Math.max(0, searchOffset - 50);
  await search();
});
on("search-next", "click", async () => {
  searchOffset += 50;
  await search();
});
on("settings-form", "submit", async (e) => {
  const data = Object.fromEntries(new FormData(e.target));
  for (const key of ["daily_goal", "weekly_goal", "monthly_goal"])
    data[key] = Number(data[key]);
  data.public_profile = e.target.elements.public_profile.checked;
  user = await api("/api/me", { method: "PATCH", body: JSON.stringify(data) });
  await refresh();
  notify("Settings saved.");
});
on("count-form", "submit", async () => {
  const result = await api("/api/count", {
    method: "POST",
    body: JSON.stringify({ text: $("count-text").value }),
  });
  $("count-result").textContent =
    `${fmt(result.chars)} Japanese characters including punctuation`;
});
for (const id of ["import-file", "source-user", "import-goal"])
  on(id, "change", () => {
    importPreview = null;
    $("apply-import").hidden = true;
    $("import-result").textContent = "";
  });
on("import-form", "submit", async () => {
  const file = $("import-file").files[0];
  if (!file) throw new Error("Choose a JSON file.");
  if (file.size > 5 * 1024 * 1024)
    throw new Error("Choose a file smaller than 5 MB.");
  const body = await file.text();
  JSON.parse(body);
  const source = $("source-user").value.trim();
  const path = `/api/import/bot-json?source_user=${encodeURIComponent(source)}&import_goal=${$("import-goal").checked}`;
  const result = await api(`${path}&dry_run=true`, { method: "POST", body });
  importPreview = { path, body };
  $("import-result").textContent =
    `${result.logs} logs across ${result.titles} titles, ${fmt(result.total_chars)} characters. ${result.daily_goal == null ? "Daily goal unchanged." : `Daily goal: ${fmt(result.current_daily_goal)} to ${fmt(result.daily_goal)}.`}`;
  $("apply-import").hidden = false;
});
on("apply-import", "click", async () => {
  if (!importPreview) return;
  const result = await api(`${importPreview.path}&dry_run=false`, {
    method: "POST",
    body: importPreview.body,
  });
  importPreview = null;
  $("apply-import").hidden = true;
  $("import-result").textContent = `${result.logs} logs imported.`;
  user = await api("/api/me");
  offset = 0;
  await refresh();
});
on("create-token", "click", async () => {
  const result = await api("/api/token", { method: "POST" });
  $("token-value").value = result.token;
  $("token-label").hidden = false;
});
on("revoke-token", "click", async () => {
  await api("/api/token", { method: "DELETE" });
  $("token-value").value = "";
  $("token-label").hidden = true;
  notify("Token revoked.");
});
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  const d = b.dataset;
  if (d.tab) {
    tab(d.tab);
    return;
  }
  if (d.close) {
    $(d.close).close();
    return;
  }
  if (d.days) {
    days = Number(d.days);
    document
      .querySelectorAll("[data-days]")
      .forEach((x) => x.classList.toggle("active", x === b));
    renderChart();
    return;
  }
  if (d.heat) {
    $("heat-selection").textContent = d.heat;
    document
      .querySelectorAll("[data-heat]")
      .forEach((el) => el.classList.toggle("selected", el === b));
    return;
  }
  if ("newTitle" in d) {
    openMedia();
    return;
  }
  if (
    ![
      "logMedia",
      "editMedia",
      "deleteMedia",
      "editLog",
      "deleteLog",
      "refresh",
      "progress",
      "addJiten",
      "linkMedia",
    ].some((k) => k in d)
  )
    return;
  b.disabled = true;
  try {
    if (d.linkMedia) {
      $("progress-dialog").close();
      openJitenSearch(media.find((m) => m.id === Number(d.linkMedia)));
    }
    if (d.logMedia) {
      $("progress-dialog").close();
      openLog(null, Number(d.logMedia));
    }
    if (d.editMedia) {
      $("progress-dialog").close();
      openMedia(media.find((m) => m.id === Number(d.editMedia)));
    }
    if (d.editLog) openLog(logs.find((l) => l.id === Number(d.editLog)));
    if (d.deleteLog && confirm("Delete this reading log?")) {
      await api(`/api/logs/${d.deleteLog}`, { method: "DELETE" });
      await refresh();
    }
    if (
      d.deleteMedia &&
      confirm("Delete this title? Titles with reading logs cannot be deleted.")
    ) {
      await api(`/api/media/${d.deleteMedia}`, { method: "DELETE" });
      $("progress-dialog").close();
      await refresh();
    }
    if (d.refresh) {
      await api(`/api/media/${d.refresh}/refresh`, { method: "POST" });
      $("progress-dialog").close();
      await refresh();
      notify("Jiten cover, type and stats refreshed.");
    }
    if (d.addJiten) {
      const source = linkingMedia;
      const existing = media.find(
        (m) => m.jiten_id === Number(d.addJiten) && m.id !== source?.id,
      );
      if (
        source &&
        !confirm(
          existing
            ? `Combine "${source.title}" with "${existing.title}"? All reading logs will be kept under the existing Jiten title, with its current reading status. The old library entry will be removed. Logs are not deduplicated.`
            : `Link "${source.title}" to "${d.jitenTitle}"? Its title, type, cover and statistics will be updated. All reading logs and reading status will be kept.`,
        )
      )
        return;
      const added = await api(
        source
          ? `/api/media/${source.id}/link-jiten/${d.addJiten}?merge=${Boolean(existing)}`
          : `/api/media/from-jiten/${d.addJiten}`,
        { method: "POST" },
      );
      await refresh();
      $("quick-media").value = String(added.id);
      $("search-dialog").close();
      $("quick-chars").focus();
      linkingMedia = null;
      notify(
        source
          ? `${added.title} linked. Reading history preserved.`
          : `${added.title} added to your library.`,
      );
    }
    if (d.progress) {
      const item = media.find((m) => m.id === Number(d.progress));
      const points = await api(`/api/stats/media/${item.id}`);
      $("progress-title").textContent = item.title;
      const facts = [
        ["Read", `${fmt(item.read_chars)} characters`],
        ["Total", item.total_chars ? fmt(item.total_chars) : "Not set"],
        ["Status", item.status],
        ["Difficulty", item.difficulty ?? "Not available"],
        [
          "Unique words",
          item.unique_words == null ? "Not available" : fmt(item.unique_words),
        ],
        [
          "Unique kanji",
          item.unique_kanji == null ? "Not available" : fmt(item.unique_kanji),
        ],
      ];
      $("title-details").innerHTML =
        `<div class="title-facts">${facts.map(([label, value]) => `<div><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("")}</div>${item.total_chars ? `<progress class="title-progress" value="${item.read_chars}" max="${item.total_chars}" aria-label="Title progress"></progress>` : ""}${item.jiten_id ? `<a href="https://jiten.moe/decks/${item.jiten_id}" target="_blank" rel="noopener">View on Jiten</a>` : ""}`;
      $("title-actions").innerHTML =
        `<button data-log-media="${item.id}"><i data-lucide="plus"></i>Log reading</button><button data-link-media="${item.id}"><i data-lucide="link"></i>${item.jiten_id ? "Change Jiten link" : "Link to Jiten"}</button>${action("pencil", "Edit title", "edit-media", item.id)}${item.jiten_id ? action("refresh-cw", "Refresh Jiten stats", "refresh", item.id) : ""}${action("trash-2", "Delete title", "delete-media", item.id)}`;
      icons();
      $("finish-estimate").textContent =
        item.status === "finished"
          ? "Marked finished"
          : item.estimated_finish
            ? `Estimated finish: ${item.estimated_finish}`
            : "No finish estimate yet";
      $("progress-dialog").showModal();
      progressChart?.destroy();
      if (window.Chart)
        progressChart = new Chart($("progress-chart"), {
          type: "line",
          data: {
            labels: points.map((p) => p.date),
            datasets: [
              {
                label: "Characters read",
                data: points.map((p) => p.chars),
                borderColor: colors[0],
                backgroundColor: "#d6a33825",
                fill: true,
                tension: 0.1,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: { beginAtZero: true },
              x: { ticks: { maxTicksLimit: 6, maxRotation: 0 } },
            },
          },
        });
    }
  } catch (err) {
    notify(err.message, true);
  } finally {
    b.disabled = false;
  }
});
(async () => {
  icons();
  if (!window.Chart || !window.lucide)
    notify(
      "Chart or icon assets are missing. Run the asset download step in the setup guide.",
      true,
    );
  try {
    user = await api("/api/me");
    await refresh();
  } catch (error) {
    showAuth();
    if (error.message !== "Please sign in") notify(error.message, true);
  }
})();
