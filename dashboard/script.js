(() => {
  const API_URL = 'https://api.amordka.com';

  const PALETTE = ['#00e5ff', '#8b5cff', '#ff2d95', '#22d3a8', '#ffb020', '#4f8cff', '#ff6fae', '#b6ff3f'];
  const GRAY = '#4a5568';

  const TIME_RANGES = [
    { label: 'Ostatnie 24H', hours: 24 },
    { label: 'Ostatni tydzień', hours: 24 * 7 },
    { label: 'Ostatni miesiąc', hours: 24 * 30 },
    { label: 'Ostatnie pół roku', hours: 24 * 182 },
    { label: 'Ostatni rok', hours: 24 * 365 },
  ];

  const state = {
    sinceHours: TIME_RANGES[0].hours,
    activeTab: 'voice',
    users: [],
    selectedUserId: null,
    userGamesCache: {},
    voiceData: [],
    gamesData: [],
    gamesLimit: 10,
  };

  const $ = (sel) => document.querySelector(sel);

  function colorFor(str, idx) {
    if (idx !== undefined) return PALETTE[idx % PALETTE.length];
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }

  function fmtHours(s) {
    const totalMinutes = Math.round(s / 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return `${h} h ${String(m).padStart(2, '0')} min`;
  }

  function sinceIso(hours) {
    return new Date(Date.now() - hours * 3600 * 1000).toISOString();
  }

  // ---------- banner ----------
  function showBanner(text) {
    $('#bannerText').textContent = text;
    $('#banner').classList.add('show');
  }
  function hideBanner() {
    $('#banner').classList.remove('show');
  }
  $('#bannerClose').addEventListener('click', hideBanner);

  // ---------- fetch ----------
  async function apiFetch(path, params) {
    const url = new URL(API_URL + path);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) url.searchParams.set(k, v);
      });
    }
    let resp;
    try {
      resp = await fetch(url.toString());
    } catch (e) {
      throw { type: 'connection', message: `Nie można połączyć się z API (${API_URL}). Upewnij się, że bot i API są uruchomione.` };
    }
    if (!resp.ok) {
      throw { type: 'http', message: `Błąd API: ${resp.status} ${resp.statusText}` };
    }
    return resp.json();
  }

  // ---------- rendering helpers ----------
  function rankingList(items, { getLabel, getValue, getColor, useAvatar }) {
    if (!items.length) return null;
    const max = Math.max(...items.map(getValue), 1);
    const wrap = document.createElement('div');
    wrap.className = 'ranking-list';
    items.forEach((item, i) => {
      const label = getLabel(item);
      const value = getValue(item);
      const color = getColor(item, i);
      const row = document.createElement('div');
      row.className = 'rank-row';

      const idx = document.createElement('div');
      idx.className = 'rank-index mono';
      idx.textContent = `#${i + 1}`;
      row.appendChild(idx);

      if (useAvatar) {
        const av = document.createElement('div');
        av.className = 'avatar';
        av.style.background = color;
        av.textContent = (label[0] || '?').toUpperCase();
        row.appendChild(av);
      } else {
        const dot = document.createElement('div');
        dot.className = 'dot';
        dot.style.background = color;
        row.appendChild(dot);
      }

      const main = document.createElement('div');
      main.className = 'rank-main';
      const top = document.createElement('div');
      top.className = 'rank-top';
      const name = document.createElement('div');
      name.className = 'rank-name';
      name.textContent = label;
      const val = document.createElement('div');
      val.className = 'rank-value mono';
      val.textContent = fmtHours(value);
      top.appendChild(name);
      top.appendChild(val);
      const track = document.createElement('div');
      track.className = 'bar-track';
      const fill = document.createElement('div');
      fill.className = 'bar-fill';
      fill.style.width = `${(value / max) * 100}%`;
      fill.style.background = color;
      track.appendChild(fill);
      main.appendChild(top);
      main.appendChild(track);
      row.appendChild(main);
      wrap.appendChild(row);
    });
    return wrap;
  }

  function emptyState(text) {
    const el = document.createElement('div');
    el.className = 'empty-state';
    el.textContent = text;
    return el;
  }

  // ---------- overview cards ----------
  function renderCards() {
    const voiceTotal = state.voiceData.reduce((sum, u) => sum + u.total_seconds, 0);
    const activePlayers = state.voiceData.filter((u) => u.total_seconds > 0).length;
    const topGame = state.gamesData[0]?.activity_name ?? '–';
    const trackedGames = state.gamesData.length;

    const cardVoice = $('#cardVoiceTime');
    cardVoice.textContent = fmtHours(voiceTotal);
    cardVoice.classList.remove('skeleton');

    const cardActive = $('#cardActivePlayers');
    cardActive.textContent = activePlayers.toLocaleString('pl-PL');
    cardActive.classList.remove('skeleton');

    const cardTop = $('#cardTopGame');
    cardTop.textContent = topGame;
    cardTop.classList.remove('skeleton');

    const cardTracked = $('#cardTrackedGames');
    cardTracked.textContent = trackedGames.toLocaleString('pl-PL');
    cardTracked.classList.remove('skeleton');
  }

  // ---------- voice tab ----------
  function renderVoiceTab() {
    const content = $('#voiceContent');
    content.innerHTML = '';
    if (!state.voiceData.length) {
      content.appendChild(emptyState('Brak danych — bot jeszcze nie zarejestrował żadnych sesji głosowych.'));
      return;
    }
    const list = rankingList(state.voiceData, {
      getLabel: (u) => u.display_name,
      getValue: (u) => u.total_seconds,
      getColor: (u) => colorFor(u.display_name),
      useAvatar: true,
    });
    content.appendChild(list);
  }

  // ---------- games tab ----------
  function renderGamesTab() {
    const content = $('#gamesContent');
    content.innerHTML = '';
    if (!state.gamesData.length) {
      content.appendChild(emptyState('Brak danych — bot jeszcze nie zarejestrował żadnych aktywności.'));
      return;
    }

    const shown = state.gamesData.slice(0, state.gamesLimit);
    const totalAll = state.gamesData.reduce((s, g) => s + g.total_seconds, 0);

    const donutSlices = state.gamesData.slice(0, 8);
    const otherSeconds = state.gamesData.slice(8).reduce((s, g) => s + g.total_seconds, 0);

    const layout = document.createElement('div');
    layout.className = 'games-layout';

    // donut
    const donutWrap = document.createElement('div');
    donutWrap.className = 'donut-wrap';
    const donut = document.createElement('div');
    donut.className = 'donut';

    let acc = 0;
    const stops = [];
    donutSlices.forEach((g, i) => {
      const pct = totalAll ? (g.total_seconds / totalAll) * 100 : 0;
      const color = colorFor(g.activity_name, i);
      stops.push(`${color} ${acc}% ${acc + pct}%`);
      acc += pct;
    });
    if (otherSeconds > 0) {
      const pct = totalAll ? (otherSeconds / totalAll) * 100 : 0;
      stops.push(`${GRAY} ${acc}% ${acc + pct}%`);
      acc += pct;
    }
    donut.style.background = stops.length ? `conic-gradient(${stops.join(', ')})` : 'rgba(255,255,255,.06)';

    const center = document.createElement('div');
    center.className = 'donut-center';
    center.innerHTML = `<div class="val">${fmtHours(totalAll)}</div><div class="lbl">łącznie</div>`;
    donut.appendChild(center);
    donutWrap.appendChild(donut);
    layout.appendChild(donutWrap);

    // legend
    const legend = document.createElement('div');
    legend.className = 'legend';
    donutSlices.forEach((g, i) => {
      const pct = totalAll ? Math.round((g.total_seconds / totalAll) * 1000) / 10 : 0;
      const row = document.createElement('div');
      row.className = 'legend-row';
      row.innerHTML = `
        <div class="dot" style="background:${colorFor(g.activity_name, i)}"></div>
        <div class="name">${g.activity_name}</div>
        <div class="hrs mono">${fmtHours(g.total_seconds)}</div>
        <div class="pct mono">${pct}%</div>`;
      legend.appendChild(row);
    });
    if (otherSeconds > 0) {
      const pct = totalAll ? Math.round((otherSeconds / totalAll) * 1000) / 10 : 0;
      const row = document.createElement('div');
      row.className = 'legend-row';
      row.innerHTML = `
        <div class="dot" style="background:${GRAY}"></div>
        <div class="name">Inne</div>
        <div class="hrs mono">${fmtHours(otherSeconds)}</div>
        <div class="pct mono">${pct}%</div>`;
      legend.appendChild(row);
    }
    layout.appendChild(legend);
    content.appendChild(layout);

    // full ranking list (respecting selected limit)
    const listTitle = document.createElement('div');
    listTitle.className = 'games-list-title';
    listTitle.textContent = 'Ranking gier';
    content.appendChild(listTitle);

    const list = rankingList(shown, {
      getLabel: (g) => g.activity_name,
      getValue: (g) => g.total_seconds,
      getColor: (g, i) => colorFor(g.activity_name, i),
      useAvatar: false,
    });
    content.appendChild(list);
  }

  // ---------- user tab ----------
  function populateUserSelect() {
    const select = $('#userSelect');
    select.innerHTML = '';
    if (!state.users.length) {
      const opt = document.createElement('option');
      opt.textContent = 'Brak użytkowników';
      select.appendChild(opt);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    state.users.forEach((u) => {
      const opt = document.createElement('option');
      opt.value = u.id;
      opt.textContent = u.display_name;
      select.appendChild(opt);
    });
    if (state.selectedUserId === null) state.selectedUserId = state.users[0].id;
    select.value = state.selectedUserId;
  }

  async function renderUserTab() {
    const content = $('#userContent');
    if (!state.users.length) {
      content.innerHTML = '';
      content.appendChild(emptyState('Brak użytkowników w bazie.'));
      return;
    }
    content.innerHTML = '<div class="loading-state">Ładowanie…</div>';

    const userId = state.selectedUserId;
    const user = state.users.find((u) => u.id === userId);
    let games = state.userGamesCache[userId];
    if (!games) {
      try {
        games = await apiFetch(`/users/${userId}/games`);
        state.userGamesCache[userId] = games;
      } catch (err) {
        showBanner(err.message);
        content.innerHTML = '';
        content.appendChild(emptyState('Nie udało się pobrać danych użytkownika.'));
        return;
      }
    }

    content.innerHTML = '';
    if (!games.length) {
      content.appendChild(emptyState(`${user ? user.display_name : 'Użytkownik'} nie ma jeszcze żadnych zarejestrowanych aktywności.`));
      return;
    }
    const sorted = [...games].sort((a, b) => b.total_seconds - a.total_seconds);
    const list = rankingList(sorted, {
      getLabel: (g) => g.activity_name,
      getValue: (g) => g.total_seconds,
      getColor: (g, i) => colorFor(g.activity_name, i),
      useAvatar: false,
    });
    content.appendChild(list);
  }

  // ---------- tab switching ----------
  function setActiveTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll('.tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.panel').forEach((panel) => {
      panel.hidden = panel.id !== `panel-${tab}`;
    });
    if (tab === 'user') renderUserTab();
  }

  document.querySelectorAll('.tab').forEach((btn) => {
    btn.addEventListener('click', () => setActiveTab(btn.dataset.tab));
  });

  // ---------- data loading ----------
  async function loadRangeData() {
    $('#voiceContent').innerHTML = '<div class="loading-state">Ładowanie…</div>';
    $('#gamesContent').innerHTML = '<div class="loading-state">Ładowanie…</div>';

    const since = sinceIso(state.sinceHours);
    try {
      const [voiceData, gamesData] = await Promise.all([
        apiFetch('/stats/voice-time', { since }),
        apiFetch('/stats/top-games', { since, limit: 1000 }),
      ]);
      state.voiceData = voiceData;
      state.gamesData = gamesData;
      hideBanner();
    } catch (err) {
      showBanner(err.message);
      state.voiceData = [];
      state.gamesData = [];
    }

    renderCards();
    renderVoiceTab();
    renderGamesTab();
  }

  async function loadUsers() {
    try {
      state.users = await apiFetch('/users/');
      hideBanner();
    } catch (err) {
      showBanner(err.message);
      state.users = [];
    }
    populateUserSelect();
    if (state.activeTab === 'user') renderUserTab();
  }

  // ---------- init controls ----------
  function initTimeRangeSelect() {
    const select = $('#timeRange');
    TIME_RANGES.forEach((r) => {
      const opt = document.createElement('option');
      opt.value = r.hours;
      opt.textContent = r.label;
      select.appendChild(opt);
    });
    select.value = state.sinceHours;
    select.addEventListener('change', () => {
      state.sinceHours = Number(select.value);
      loadRangeData();
    });
  }

  function initGamesLimit() {
    const select = $('#gamesLimit');
    select.addEventListener('change', () => {
      state.gamesLimit = Number(select.value);
      renderGamesTab();
    });
  }

  function initUserSelect() {
    const select = $('#userSelect');
    select.addEventListener('change', () => {
      state.selectedUserId = Number(select.value);
      renderUserTab();
    });
  }

  $('#refreshBtn').addEventListener('click', () => {
    state.userGamesCache = {};
    loadRangeData();
    loadUsers();
  });

  // ---------- boot ----------
  $('#apiUrlLabel').textContent = API_URL;

  initTimeRangeSelect();
  initGamesLimit();
  initUserSelect();
  loadRangeData();
  loadUsers();
})();
