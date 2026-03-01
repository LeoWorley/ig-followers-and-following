const state = {
  selectedDay: null,
  defaultTz: document.body.dataset.defaultTz || "America/Hermosillo",
};

const $ = (id) => document.getElementById(id);

function readFilters() {
  return {
    target: $("target").value || "",
    type: $("listType").value || "both",
    days: Math.max(1, Math.min(365, Number($("days").value || 30))),
    tz: ($("tz").value || state.defaultTz).trim(),
  };
}

async function apiGet(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });
  const res = await fetch(url.toString());
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) msg = data.detail;
    } catch (_e) {}
    throw new Error(msg);
  }
  return res.json();
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    toast.hidden = true;
  }, 2800);
}

function renderHealth(data) {
  const entries = [
    ["DB OK", String(data.db_ok)],
    ["Tracker Running?", String(data.tracker_running_guess)],
    ["Last Run Status", data.last_run_status || "-"],
    ["Last Run Started", data.last_run_started_at || "-"],
    ["Last Run Finished", data.last_run_finished_at || "-"],
    ["Last Success", data.last_success_at || "-"],
    ["Minutes Since Success", data.minutes_since_success ?? "-"],
    ["Server Time", data.server_time_local || "-"],
  ];
  $("health").innerHTML = entries
    .map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`)
    .join("");
}

function setMetric(id, value) {
  $(id).textContent = String(value ?? 0);
}

function renderOverview(data) {
  setMetric("mCurrentFollowers", data.current_followers);
  setMetric("mCurrentFollowings", data.current_followings);
  setMetric("mNewFollowers", data.new_today_followers);
  setMetric("mLostFollowers", data.lost_today_followers);
  setMetric("mNewFollowings", data.new_today_followings);
  setMetric("mLostFollowings", data.lost_today_followings);
}

function renderDaily(data) {
  const body = $("dailyTable").querySelector("tbody");
  body.innerHTML = "";
  $("dailyMeta").textContent = `last ${data.days} day(s) | ${data.tz_used}`;

  for (const row of data.rows) {
    const tr = document.createElement("tr");
    tr.dataset.day = row.day;
    tr.innerHTML = `
      <td>${row.day}</td>
      <td>${row.new_followers ?? "-"}</td>
      <td>${row.lost_followers ?? "-"}</td>
      <td>${row.new_followings ?? "-"}</td>
      <td>${row.lost_followings ?? "-"}</td>
    `;
    tr.addEventListener("click", () => onSelectDay(row.day));
    body.appendChild(tr);
  }

  const fallbackDay = data.rows.length ? data.rows[0].day : null;
  state.selectedDay = state.selectedDay || fallbackDay;
  if (state.selectedDay) {
    markSelectedDay(state.selectedDay);
  }
}

function markSelectedDay(day) {
  const rows = $("dailyTable").querySelectorAll("tbody tr");
  rows.forEach((tr) => {
    tr.classList.toggle("is-selected", tr.dataset.day === day);
  });
}

function renderEvents(listId, rows, kind) {
  const list = $(listId);
  if (!rows.length) {
    list.innerHTML = "<li><span>No rows for this day.</span></li>";
    return;
  }
  list.innerHTML = rows
    .map((row) => {
      const cls = kind === "lost" ? "meta lost" : "meta";
      return `
        <li>
          <strong>${row.username}</strong>
          <span class="${cls}">${row.type} · ${row.timestamp_local || "-"}</span>
        </li>
      `;
    })
    .join("");
}

function renderCurrent(data) {
  const body = $("currentTable").querySelector("tbody");
  body.innerHTML = "";
  $("currentMeta").textContent = `${data.rows.length} rows | ${data.tz_used}`;
  for (const row of data.rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.username}</td>
      <td>${row.type}</td>
      <td>${row.first_seen_local || "-"}</td>
      <td>${row.last_seen_local || "-"}</td>
    `;
    body.appendChild(tr);
  }
}

async function loadTargets() {
  const filters = readFilters();
  const data = await apiGet("/api/v1/targets", { tz: filters.tz });
  const select = $("target");
  const prev = select.value;
  select.innerHTML = `<option value="">(all)</option>` +
    data.targets.map((t) => `<option value="${t}">${t}</option>`).join("");
  if ([...select.options].some((opt) => opt.value === prev)) {
    select.value = prev;
  }
}

async function loadDayDetails() {
  if (!state.selectedDay) {
    renderEvents("newList", [], "new");
    renderEvents("lostList", [], "lost");
    $("dayChosen").textContent = "-";
    return;
  }
  const filters = readFilters();
  const data = await apiGet("/api/v1/day", {
    date: state.selectedDay,
    target: filters.target,
    type: filters.type,
    tz: filters.tz,
  });
  $("dayChosen").textContent = data.date;
  renderEvents("newList", data.new, "new");
  renderEvents("lostList", data.lost, "lost");
}

async function onSelectDay(day) {
  state.selectedDay = day;
  markSelectedDay(day);
  try {
    await loadDayDetails();
  } catch (err) {
    showToast(`Day details error: ${err.message}`);
  }
}

async function refreshAll() {
  const filters = readFilters();
  try {
    const [health, overview, daily, current] = await Promise.all([
      apiGet("/api/v1/health", { tz: filters.tz }),
      apiGet("/api/v1/overview", { target: filters.target, tz: filters.tz }),
      apiGet("/api/v1/daily", {
        days: filters.days,
        target: filters.target,
        type: filters.type,
        tz: filters.tz,
      }),
      apiGet("/api/v1/current", {
        target: filters.target,
        type: filters.type,
        limit: 500,
        tz: filters.tz,
      }),
    ]);

    renderHealth(health);
    renderOverview(overview);
    renderDaily(daily);
    renderCurrent(current);
    await loadDayDetails();
  } catch (err) {
    showToast(`Refresh error: ${err.message}`);
  }
}

async function init() {
  try {
    await loadTargets();
    await refreshAll();
  } catch (err) {
    showToast(`Init error: ${err.message}`);
  }
}

$("refreshBtn").addEventListener("click", refreshAll);
init();
