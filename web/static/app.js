const LANGUAGE_STORAGE_KEY = "ig-tracker-language";

const translations = {
  en: {
    pageTitle: "Instagram Activity Dashboard",
    heroEyebrow: "Instagram activity dashboard",
    heroSubtitle: "See who follows, unfollows, and who each account follows.",
    targetLabel: "Instagram account",
    listTypeLabel: "Show",
    daysLabel: "Look back (days)",
    refreshBtn: "Refresh",
    refreshLoading: "Refreshing...",
    lastRefreshed: "Last refreshed {time}",
    notRefreshed: "Not refreshed yet",
    openTargetBtn: "Open Instagram profile",
    healthTitle: "Update status",
    healthHelp: "Data availability and last successful tracker run.",
    overviewTitle: "Today at a glance",
    overviewHelp: "Current totals and movement recorded today.",
    dailyTitle: "Changes by day",
    dailyHelp: "Select a row to inspect additions and removals.",
    newTitle: "Added on selected day",
    newHelp: "New relationships recorded for the selected day.",
    lostTitle: "Removed on selected day",
    lostHelp: "Relationships removed on the selected day.",
    currentTitle: "Current followers and following",
    currentHelp: "Currently active relationships from the latest snapshot.",
    currentSearchLabel: "Search usernames",
    currentSearchPlaceholder: "Search @username",
    metricCurrentFollowers: "Followers now",
    metricCurrentFollowings: "Following now",
    metricNewFollowers: "New followers today",
    metricLostFollowers: "Lost followers today",
    metricNewFollowings: "Started following today",
    metricLostFollowings: "Stopped following today",
    dailyDayHeader: "Day",
    dailyNewFollowersHeader: "New followers",
    dailyLostFollowersHeader: "Lost followers",
    dailyNewFollowingsHeader: "Started following",
    dailyLostFollowingsHeader: "Stopped following",
    currentTargetHeader: "Account",
    currentUsernameHeader: "Username",
    currentTypeHeader: "Relationship",
    currentFirstSeenHeader: "Tracking since",
    currentLastSeenHeader: "Last seen",
    allAccounts: "(all accounts)",
    listTypeBoth: "Followers and following",
    listTypeFollowers: "Followers only",
    listTypeFollowings: "Following only",
    healthDataReady: "Data available",
    healthUpdatingNow: "Updating now",
    healthLastUpdate: "Last update",
    statusAvailable: "Available",
    statusUnavailable: "Unavailable",
    yes: "Yes",
    no: "No",
    noUpdateYet: "No update yet",
    notAvailable: "Not available",
    currentRelationFollower: "Follows this account",
    currentRelationFollowing: "Followed by this account",
    emptyNew: "No new changes for this day.",
    emptyLost: "No removed changes for this day.",
    emptyCurrent: "No accounts match this view right now.",
    dailyMeta: "Showing the last {days} days",
    currentMeta: "Showing {count} accounts",
    currentMetaFiltered: "Showing {count} of {total} accounts",
    selectTargetFirst: "Choose an Instagram account first.",
    emptyCurrentSearch: "No accounts match this search.",
    dayDetailsError: "Could not load that day: {message}",
    refreshError: "Could not refresh the dashboard: {message}",
    initError: "Could not load the dashboard: {message}",
    thisAccount: "this account",
    eventFollowerNewSelected: "{username} started following this account.",
    eventFollowerLostSelected: "{username} stopped following this account.",
    eventFollowingNewSelected: "This account started following {username}.",
    eventFollowingLostSelected: "This account stopped following {username}.",
    eventFollowerNewAll: "{username} started following {target}.",
    eventFollowerLostAll: "{username} stopped following {target}.",
    eventFollowingNewAll: "{target} started following {username}.",
    eventFollowingLostAll: "{target} stopped following {username}.",
  },
  es: {
    pageTitle: "Panel de actividad de Instagram",
    heroEyebrow: "Panel de actividad de Instagram",
    heroSubtitle: "Mira quien sigue, deja de seguir y a quien sigue cada cuenta.",
    targetLabel: "Cuenta de Instagram",
    listTypeLabel: "Mostrar",
    daysLabel: "Dias hacia atras",
    refreshBtn: "Actualizar",
    refreshLoading: "Actualizando...",
    lastRefreshed: "Actualizado por ultima vez {time}",
    notRefreshed: "Aun no se actualiza",
    openTargetBtn: "Abrir perfil de Instagram",
    healthTitle: "Estado de actualizacion",
    healthHelp: "Disponibilidad de datos y ultima ejecucion exitosa.",
    overviewTitle: "Resumen de hoy",
    overviewHelp: "Totales actuales y movimiento registrado hoy.",
    dailyTitle: "Cambios por dia",
    dailyHelp: "Selecciona una fila para revisar agregados y eliminados.",
    newTitle: "Agregado en el dia seleccionado",
    newHelp: "Relaciones nuevas registradas para el dia seleccionado.",
    lostTitle: "Eliminado en el dia seleccionado",
    lostHelp: "Relaciones eliminadas en el dia seleccionado.",
    currentTitle: "Seguidores y seguidos actuales",
    currentHelp: "Relaciones activas segun la captura mas reciente.",
    currentSearchLabel: "Buscar usuarios",
    currentSearchPlaceholder: "Buscar @usuario",
    metricCurrentFollowers: "Seguidores ahora",
    metricCurrentFollowings: "Siguiendo ahora",
    metricNewFollowers: "Nuevos seguidores hoy",
    metricLostFollowers: "Seguidores perdidos hoy",
    metricNewFollowings: "Empezo a seguir hoy",
    metricLostFollowings: "Dejo de seguir hoy",
    dailyDayHeader: "Dia",
    dailyNewFollowersHeader: "Nuevos seguidores",
    dailyLostFollowersHeader: "Seguidores perdidos",
    dailyNewFollowingsHeader: "Empezo a seguir",
    dailyLostFollowingsHeader: "Dejo de seguir",
    currentTargetHeader: "Cuenta",
    currentUsernameHeader: "Usuario",
    currentTypeHeader: "Relacion",
    currentFirstSeenHeader: "Se sigue desde",
    currentLastSeenHeader: "Visto por ultima vez",
    allAccounts: "(todas las cuentas)",
    listTypeBoth: "Seguidores y seguidos",
    listTypeFollowers: "Solo seguidores",
    listTypeFollowings: "Solo seguidos",
    healthDataReady: "Datos disponibles",
    healthUpdatingNow: "Actualizando ahora",
    healthLastUpdate: "Ultima actualizacion",
    statusAvailable: "Disponible",
    statusUnavailable: "No disponible",
    yes: "Si",
    no: "No",
    noUpdateYet: "Aun no hay actualizacion",
    notAvailable: "No disponible",
    currentRelationFollower: "Sigue esta cuenta",
    currentRelationFollowing: "Esta cuenta le sigue",
    emptyNew: "No hay cambios nuevos para este dia.",
    emptyLost: "No hay cambios eliminados para este dia.",
    emptyCurrent: "No hay cuentas para mostrar en esta vista ahora.",
    dailyMeta: "Mostrando los ultimos {days} dias",
    currentMeta: "Mostrando {count} cuentas",
    currentMetaFiltered: "Mostrando {count} de {total} cuentas",
    selectTargetFirst: "Primero elige una cuenta de Instagram.",
    emptyCurrentSearch: "No hay cuentas que coincidan con esta busqueda.",
    dayDetailsError: "No se pudo cargar ese dia: {message}",
    refreshError: "No se pudo actualizar el panel: {message}",
    initError: "No se pudo cargar el panel: {message}",
    thisAccount: "esta cuenta",
    eventFollowerNewSelected: "{username} empezo a seguir esta cuenta.",
    eventFollowerLostSelected: "{username} dejo de seguir esta cuenta.",
    eventFollowingNewSelected: "Esta cuenta empezo a seguir a {username}.",
    eventFollowingLostSelected: "Esta cuenta dejo de seguir a {username}.",
    eventFollowerNewAll: "{username} empezo a seguir a {target}.",
    eventFollowerLostAll: "{username} dejo de seguir a {target}.",
    eventFollowingNewAll: "{target} empezo a seguir a {username}.",
    eventFollowingLostAll: "{target} dejo de seguir a {username}.",
  },
};

const state = {
  selectedDay: null,
  defaultTz: document.body.dataset.defaultTz || "America/Hermosillo",
  language: "en",
  data: {
    health: null,
    overview: null,
    daily: null,
    current: null,
    day: null,
  },
  lastFilters: null,
  isRefreshing: false,
  lastRefreshedAt: null,
};

const $ = (id) => document.getElementById(id);

function escapeHtml(raw) {
  return String(raw ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeInstagramUsername(raw) {
  let value = String(raw ?? "").trim();
  while (value.startsWith("@")) {
    value = value.slice(1);
  }
  return value;
}

function instagramProfileUrl(rawUsername) {
  const username = normalizeInstagramUsername(rawUsername);
  if (!username) {
    return null;
  }
  return `https://www.instagram.com/${encodeURIComponent(username)}/`;
}

function instagramUsernameLink(rawUsername) {
  const username = normalizeInstagramUsername(rawUsername);
  const url = instagramProfileUrl(username);
  if (!url) {
    return escapeHtml(rawUsername || "");
  }
  return `<a class="ig-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">@${escapeHtml(username)}</a>`;
}

function detectInitialLanguage() {
  const saved = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (saved === "en" || saved === "es") {
    return saved;
  }
  const browserLanguage = (navigator.language || "en").toLowerCase();
  return browserLanguage.startsWith("es") ? "es" : "en";
}

function t(key, vars = {}) {
  const catalog = translations[state.language] || translations.en;
  const template = catalog[key] ?? translations.en[key] ?? key;
  return Object.entries(vars).reduce(
    (value, [name, replacement]) => value.replaceAll(`{${name}}`, String(replacement)),
    template,
  );
}

function setLanguage(lang, persist = true) {
  if (!translations[lang]) {
    return;
  }
  state.language = lang;
  document.documentElement.lang = lang;
  document.title = t("pageTitle");
  if (persist) {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
  }
  updateLanguageButtons();
  localizeStaticText();
  rerenderFromState();
}

function updateLanguageButtons() {
  document.querySelectorAll(".lang-btn").forEach((button) => {
    const isActive = button.dataset.lang === state.language;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
}

function localizeStaticText() {
  $("heroEyebrow").textContent = t("heroEyebrow");
  $("heroSubtitle").textContent = t("heroSubtitle");
  $("targetLabel").textContent = t("targetLabel");
  $("listTypeLabel").textContent = t("listTypeLabel");
  $("daysLabel").textContent = t("daysLabel");
  $("refreshBtn").textContent = state.isRefreshing ? t("refreshLoading") : t("refreshBtn");
  $("lastRefreshMeta").textContent = state.lastRefreshedAt
    ? t("lastRefreshed", { time: formatDateTime(state.lastRefreshedAt) })
    : t("notRefreshed");
  $("openTargetBtn").textContent = t("openTargetBtn");
  $("healthTitle").textContent = t("healthTitle");
  $("healthHelp").textContent = t("healthHelp");
  $("overviewTitle").textContent = t("overviewTitle");
  $("overviewHelp").textContent = t("overviewHelp");
  $("dailyTitle").textContent = t("dailyTitle");
  $("dailyHelp").textContent = t("dailyHelp");
  $("newTitle").textContent = t("newTitle");
  $("newHelp").textContent = t("newHelp");
  $("lostTitle").textContent = t("lostTitle");
  $("lostHelp").textContent = t("lostHelp");
  $("currentTitle").textContent = t("currentTitle");
  $("currentHelp").textContent = t("currentHelp");
  $("currentSearchLabel").textContent = t("currentSearchLabel");
  $("currentSearch").placeholder = t("currentSearchPlaceholder");
  $("mCurrentFollowersLabel").textContent = t("metricCurrentFollowers");
  $("mCurrentFollowingsLabel").textContent = t("metricCurrentFollowings");
  $("mNewFollowersLabel").textContent = t("metricNewFollowers");
  $("mLostFollowersLabel").textContent = t("metricLostFollowers");
  $("mNewFollowingsLabel").textContent = t("metricNewFollowings");
  $("mLostFollowingsLabel").textContent = t("metricLostFollowings");
  $("dailyDayHeader").textContent = t("dailyDayHeader");
  $("dailyNewFollowersHeader").textContent = t("dailyNewFollowersHeader");
  $("dailyLostFollowersHeader").textContent = t("dailyLostFollowersHeader");
  $("dailyNewFollowingsHeader").textContent = t("dailyNewFollowingsHeader");
  $("dailyLostFollowingsHeader").textContent = t("dailyLostFollowingsHeader");
  $("currentTargetHeader").textContent = t("currentTargetHeader");
  $("currentUsernameHeader").textContent = t("currentUsernameHeader");
  $("currentTypeHeader").textContent = t("currentTypeHeader");
  $("currentFirstSeenHeader").textContent = t("currentFirstSeenHeader");
  $("currentLastSeenHeader").textContent = t("currentLastSeenHeader");
  localizeFilterOptions();
}

function localizeFilterOptions() {
  const target = $("target");
  if (target && target.options.length > 0) {
    target.options[0].textContent = t("allAccounts");
  }
  const listType = $("listType");
  if (!listType) {
    return;
  }
  const labels = {
    both: t("listTypeBoth"),
    followers: t("listTypeFollowers"),
    followings: t("listTypeFollowings"),
  };
  [...listType.options].forEach((option) => {
    option.textContent = labels[option.value] || option.value;
  });
}

function formatDateTime(value) {
  if (!value) {
    return t("notAvailable");
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat(state.language, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatDay(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat(state.language, {
    dateStyle: "medium",
  }).format(date);
}

function formatCount(value) {
  return new Intl.NumberFormat(state.language).format(Number(value || 0));
}

function normalizeSearchValue(raw) {
  return normalizeInstagramUsername(raw).toLowerCase();
}

function readFilters() {
  return {
    target: $("target").value || "",
    type: $("listType").value || "both",
    days: Math.max(1, Math.min(365, Number($("days").value || 30))),
    tz: state.defaultTz,
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
    if (res.status === 401) {
      window.location.assign("/login");
      throw new Error("Login required");
    }
    let msg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) {
        msg = data.detail;
      }
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
  }, 3200);
}

function updateOpenTargetButton() {
  const button = $("openTargetBtn");
  if (!button) {
    return;
  }
  const targetRaw = $("target").value;
  const targetName = normalizeInstagramUsername(targetRaw);
  const url = instagramProfileUrl(targetName);
  if (!url) {
    button.disabled = true;
    button.dataset.profileUrl = "";
    return;
  }
  button.disabled = false;
  button.dataset.profileUrl = url;
}

function openSelectedTargetProfile() {
  const button = $("openTargetBtn");
  const url = button ? button.dataset.profileUrl : "";
  if (!url) {
    showToast(t("selectTargetFirst"));
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function badgeHtml(value, tone) {
  return `<span class="status-badge ${tone ? `is-${tone}` : ""}">${escapeHtml(value)}</span>`;
}

function renderHealth(data) {
  const entries = [
    [t("healthDataReady"), badgeHtml(data.db_ok ? t("statusAvailable") : t("statusUnavailable"), data.db_ok ? "good" : "danger")],
    [t("healthUpdatingNow"), badgeHtml(data.tracker_running_guess ? t("yes") : t("no"), data.tracker_running_guess ? "warn" : "")],
    [t("healthLastUpdate"), escapeHtml(data.last_success_at ? formatDateTime(data.last_success_at) : t("noUpdateYet"))],
  ];
  $("health").innerHTML = entries
    .map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${value}</dd>`)
    .join("");
}

function setMetric(id, value) {
  $(id).textContent = formatCount(value);
}

function renderOverview(data) {
  setMetric("mCurrentFollowers", data.current_followers);
  setMetric("mCurrentFollowings", data.current_followings);
  setMetric("mNewFollowers", data.new_today_followers);
  setMetric("mLostFollowers", data.lost_today_followers);
  setMetric("mNewFollowings", data.new_today_followings);
  setMetric("mLostFollowings", data.lost_today_followings);
}

function applyDailyColumnVisibility(listType) {
  const showFollowers = listType !== "followings";
  const showFollowings = listType !== "followers";
  $("dailyNewFollowersHeader").hidden = !showFollowers;
  $("dailyLostFollowersHeader").hidden = !showFollowers;
  $("dailyNewFollowingsHeader").hidden = !showFollowings;
  $("dailyLostFollowingsHeader").hidden = !showFollowings;
}

function buildDailyCells(row, listType) {
  const cells = [`<td>${escapeHtml(formatDay(row.day))}</td>`];
  if (listType !== "followings") {
    cells.push(`<td>${escapeHtml(row.new_followers == null ? "-" : formatCount(row.new_followers))}</td>`);
    cells.push(`<td>${escapeHtml(row.lost_followers == null ? "-" : formatCount(row.lost_followers))}</td>`);
  }
  if (listType !== "followers") {
    cells.push(`<td>${escapeHtml(row.new_followings == null ? "-" : formatCount(row.new_followings))}</td>`);
    cells.push(`<td>${escapeHtml(row.lost_followings == null ? "-" : formatCount(row.lost_followings))}</td>`);
  }
  return cells.join("");
}

function renderDaily(data) {
  const body = $("dailyTable").querySelector("tbody");
  body.innerHTML = "";
  $("dailyMeta").textContent = t("dailyMeta", { days: formatCount(data.days) });
  applyDailyColumnVisibility(data.type);

  for (const row of data.rows) {
    const tr = document.createElement("tr");
    tr.dataset.day = row.day;
    tr.innerHTML = buildDailyCells(row, data.type);
    tr.addEventListener("click", () => onSelectDay(row.day));
    body.appendChild(tr);
  }

  const availableDays = new Set(data.rows.map((row) => row.day));
  const fallbackDay = data.rows.length ? data.rows[0].day : null;
  if (!state.selectedDay || !availableDays.has(state.selectedDay)) {
    state.selectedDay = fallbackDay;
  }
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

function eventMessageHtml(row, kind, targetFilter) {
  const usernameLink = instagramUsernameLink(row.username);
  const targetLink = instagramUsernameLink(row.target || targetFilter || "");
  const isAllTargets = !targetFilter;
  if (row.type === "follower") {
    if (kind === "new") {
      return isAllTargets
        ? t("eventFollowerNewAll", { username: usernameLink, target: targetLink })
        : t("eventFollowerNewSelected", { username: usernameLink });
    }
    return isAllTargets
      ? t("eventFollowerLostAll", { username: usernameLink, target: targetLink })
      : t("eventFollowerLostSelected", { username: usernameLink });
  }
  if (kind === "new") {
    return isAllTargets
      ? t("eventFollowingNewAll", { username: usernameLink, target: targetLink })
      : t("eventFollowingNewSelected", { username: usernameLink });
  }
  return isAllTargets
    ? t("eventFollowingLostAll", { username: usernameLink, target: targetLink })
    : t("eventFollowingLostSelected", { username: usernameLink });
}

function renderEvents(listId, rows, kind) {
  const list = $(listId);
  const filters = state.lastFilters || readFilters();
  if (!rows.length) {
    list.innerHTML = `<li><span class="event-copy">${escapeHtml(kind === "lost" ? t("emptyLost") : t("emptyNew"))}</span></li>`;
    return;
  }
  list.innerHTML = rows
    .map((row) => {
      const timestamp = escapeHtml(formatDateTime(row.timestamp_local));
      const messageHtml = eventMessageHtml(row, kind, filters.target);
      return `
        <li>
          <p class="event-copy">${messageHtml}</p>
          <span class="meta">${timestamp}</span>
        </li>
      `;
    })
    .join("");
}

function renderCurrent(data) {
  const body = $("currentTable").querySelector("tbody");
  body.innerHTML = "";
  const filters = state.lastFilters || readFilters();
  const showTarget = !filters.target;
  const searchValue = normalizeSearchValue($("currentSearch").value);
  const rows = searchValue
    ? data.rows.filter((row) => {
        const username = normalizeSearchValue(row.username);
        const target = normalizeSearchValue(row.target);
        return username.includes(searchValue) || target.includes(searchValue);
      })
    : data.rows;
  $("currentTargetHeader").hidden = !showTarget;
  $("currentMeta").textContent = searchValue
    ? t("currentMetaFiltered", { count: formatCount(rows.length), total: formatCount(data.rows.length) })
    : t("currentMeta", { count: formatCount(data.rows.length) });

  if (!rows.length) {
    const tr = document.createElement("tr");
    const colCount = showTarget ? 5 : 4;
    tr.innerHTML = `<td colspan="${colCount}">${escapeHtml(searchValue ? t("emptyCurrentSearch") : t("emptyCurrent"))}</td>`;
    body.appendChild(tr);
    return;
  }

  for (const row of rows) {
    const tr = document.createElement("tr");
    const cells = [];
    if (showTarget) {
      cells.push(`<td>${instagramUsernameLink(row.target)}</td>`);
    }
    cells.push(`<td>${instagramUsernameLink(row.username)}</td>`);
    cells.push(
      `<td>${escapeHtml(
        row.type === "follower" ? t("currentRelationFollower") : t("currentRelationFollowing"),
      )}</td>`,
    );
    cells.push(`<td>${escapeHtml(formatDateTime(row.first_seen_local))}</td>`);
    cells.push(`<td>${escapeHtml(formatDateTime(row.last_seen_local))}</td>`);
    tr.innerHTML = cells.join("");
    body.appendChild(tr);
  }
}

function rerenderFromState() {
  if (state.data.health) {
    renderHealth(state.data.health);
  }
  if (state.data.overview) {
    renderOverview(state.data.overview);
  }
  if (state.data.daily) {
    renderDaily(state.data.daily);
  }
  if (state.data.current) {
    renderCurrent(state.data.current);
  }
  if (state.data.day) {
    $("dayChosen").textContent = formatDay(state.data.day.date);
    renderEvents("newList", state.data.day.new, "new");
    renderEvents("lostList", state.data.day.lost, "lost");
  } else {
    $("dayChosen").textContent = "-";
    renderEvents("newList", [], "new");
    renderEvents("lostList", [], "lost");
  }
}

async function loadTargets() {
  const filters = readFilters();
  const data = await apiGet("/api/v1/targets", { tz: filters.tz });
  const select = $("target");
  const previousValue = select.value;
  select.innerHTML = "";

  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = t("allAccounts");
  select.appendChild(allOption);

  for (const targetName of data.targets) {
    const option = document.createElement("option");
    option.value = targetName;
    option.textContent = targetName;
    select.appendChild(option);
  }

  if ([...select.options].some((option) => option.value === previousValue)) {
    select.value = previousValue;
  }
  updateOpenTargetButton();
}

async function loadDayDetails() {
  if (!state.selectedDay) {
    state.data.day = null;
    rerenderFromState();
    return;
  }
  const filters = readFilters();
  const data = await apiGet("/api/v1/day", {
    date: state.selectedDay,
    target: filters.target,
    type: filters.type,
    tz: filters.tz,
  });
  state.data.day = data;
  $("dayChosen").textContent = formatDay(data.date);
  renderEvents("newList", data.new, "new");
  renderEvents("lostList", data.lost, "lost");
}

async function onSelectDay(day) {
  state.selectedDay = day;
  markSelectedDay(day);
  try {
    await loadDayDetails();
  } catch (err) {
    showToast(t("dayDetailsError", { message: err.message }));
  }
}

function setRefreshLoading(isLoading) {
  state.isRefreshing = isLoading;
  const refreshButton = $("refreshBtn");
  refreshButton.disabled = isLoading;
  refreshButton.textContent = isLoading ? t("refreshLoading") : t("refreshBtn");
}

function updateLastRefreshMeta() {
  $("lastRefreshMeta").textContent = state.lastRefreshedAt
    ? t("lastRefreshed", { time: formatDateTime(state.lastRefreshedAt) })
    : t("notRefreshed");
}

async function refreshAll() {
  if (state.isRefreshing) {
    return;
  }
  const filters = readFilters();
  state.lastFilters = { ...filters };
  setRefreshLoading(true);
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

    state.data.health = health;
    state.data.overview = overview;
    state.data.daily = daily;
    state.data.current = current;
    renderHealth(health);
    renderOverview(overview);
    renderDaily(daily);
    renderCurrent(current);
    await loadDayDetails();
    state.lastRefreshedAt = new Date().toISOString();
    updateLastRefreshMeta();
  } catch (err) {
    showToast(t("refreshError", { message: err.message }));
  } finally {
    setRefreshLoading(false);
  }
}

async function init() {
  setLanguage(detectInitialLanguage(), false);
  try {
    await loadTargets();
    await refreshAll();
    updateOpenTargetButton();
  } catch (err) {
    showToast(t("initError", { message: err.message }));
  }
}

$("refreshBtn").addEventListener("click", refreshAll);
$("openTargetBtn").addEventListener("click", openSelectedTargetProfile);
$("target").addEventListener("change", updateOpenTargetButton);
$("currentSearch").addEventListener("input", () => {
  if (state.data.current) {
    renderCurrent(state.data.current);
  }
});
document.querySelectorAll(".lang-btn").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.lang));
});

init();
