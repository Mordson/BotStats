"use client";

import { useState } from "react";
import RankingList from "./RankingList";
import DonutRanking from "./DonutRanking";
import PanelBody from "./PanelBody";
import TimeRangePicker from "./TimeRangePicker";
import { colorFor, fmtHours, formatRangeLabel, rangeKey, rangeQuery, type DateRange } from "@/lib/format";
import type {
  ChannelTimeOut,
  EngagementOut,
  GameTimeOut,
  GenreTimeOut,
  UserGameTimeOut,
  UserOut,
  VoiceTimeOut,
} from "@/lib/api";
import { ALL_GAMES_LIMIT, EMPTY_RANGE_DATA, type RangeData } from "@/lib/rangeData";

type Tab = "voice" | "games" | "genres" | "user" | "engagement";

interface DashboardProps {
  initialDateRange: DateRange;
  initialRangeData: RangeData;
  initialUsers: UserOut[];
  initialError: string | null;
}

const TABS: { id: Tab; label: string }[] = [
  { id: "voice", label: "🔊 Czas głosowy" },
  { id: "games", label: "🕹️ Top gry" },
  { id: "genres", label: "🏷️ Gatunki" },
  { id: "user", label: "👤 Użytkownik" },
  { id: "engagement", label: "🎙️ Zaangażowanie" },
];

const GAMES_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 40, 50];
const CONNECTION_ERROR = "Nie można połączyć się z API. Upewnij się, że bot i API są uruchomione.";

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json() as Promise<T>;
}

export default function Dashboard({
  initialDateRange,
  initialRangeData,
  initialUsers,
  initialError,
}: DashboardProps) {
  const [dateRange, setDateRange] = useState<DateRange>(initialDateRange);
  const [activeTab, setActiveTab] = useState<Tab>("voice");
  const [rangeData, setRangeData] = useState<RangeData>(initialRangeData);
  const [users, setUsers] = useState(initialUsers);
  const [gamesLimit, setGamesLimit] = useState(10);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(
    initialUsers[0]?.id ?? null,
  );
  const [userGamesCache, setUserGamesCache] = useState<Record<string, UserGameTimeOut[]>>({});
  const [userGamesLoading, setUserGamesLoading] = useState(false);
  const [rangeLoading, setRangeLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError);

  const userGamesCacheKey = (userId: string, range: DateRange) => `${userId}:${rangeKey(range)}`;

  async function loadRangeData(range: DateRange) {
    setRangeLoading(true);
    const query = rangeQuery(range);
    try {
      const [voice, channels, games, engagement, genres] = await Promise.all([
        fetchJson<VoiceTimeOut[]>(`/api/stats/voice-time?${query}`),
        fetchJson<ChannelTimeOut[]>(`/api/stats/voice-channels?${query}`),
        fetchJson<GameTimeOut[]>(`/api/stats/top-games?${rangeQuery(range, { limit: ALL_GAMES_LIMIT })}`),
        fetchJson<EngagementOut[]>(`/api/stats/engagement?${query}`),
        fetchJson<GenreTimeOut[]>(`/api/stats/top-genres?${query}`),
      ]);
      setRangeData({ voice, channels, games, engagement, genres });
      setError(null);
    } catch {
      setError(CONNECTION_ERROR);
      setRangeData(EMPTY_RANGE_DATA);
    } finally {
      setRangeLoading(false);
    }
  }

  async function loadUsers() {
    try {
      const data = await fetchJson<UserOut[]>("/api/users/");
      setUsers(data);
      setError(null);
      setSelectedUserId((current) => current ?? data[0]?.id ?? null);
    } catch {
      setError(CONNECTION_ERROR);
      setUsers([]);
    }
  }

  async function loadUserGames(userId: string, range: DateRange) {
    setUserGamesLoading(true);
    try {
      const data = await fetchJson<UserGameTimeOut[]>(`/api/users/${userId}/games?${rangeQuery(range)}`);
      setUserGamesCache((prev) => ({ ...prev, [userGamesCacheKey(userId, range)]: data }));
      setError(null);
    } catch {
      setError("Nie udało się pobrać danych użytkownika.");
    } finally {
      setUserGamesLoading(false);
    }
  }

  function handleTimeRangeChange(range: DateRange) {
    setDateRange(range);
    void loadRangeData(range);
    if (activeTab === "user" && selectedUserId) void loadUserGames(selectedUserId, range);
  }

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    if (tab === "user" && selectedUserId && !userGamesCache[userGamesCacheKey(selectedUserId, dateRange)]) {
      void loadUserGames(selectedUserId, dateRange);
    }
  }

  function handleUserChange(userId: string) {
    setSelectedUserId(userId);
    if (!userGamesCache[userGamesCacheKey(userId, dateRange)]) void loadUserGames(userId, dateRange);
  }

  function handleRefresh() {
    setUserGamesCache({});
    void loadRangeData(dateRange);
    void loadUsers();
    if (activeTab === "user" && selectedUserId) void loadUserGames(selectedUserId, dateRange);
  }

  const { voice: voiceData, channels: channelsData, games: gamesData, engagement: engagementData, genres: genresData } =
    rangeData;
  const periodLabel = formatRangeLabel(dateRange);

  const cards: { label: string; value: string }[] = [
    { label: "Czas głosowy", value: fmtHours(voiceData.reduce((sum, u) => sum + u.total_seconds, 0)) },
    { label: "Łączny czas na grach", value: fmtHours(gamesData.reduce((sum, g) => sum + g.total_seconds, 0)) },
    { label: "Najpopularniejsza gra", value: gamesData[0]?.activity_name ?? "–" },
    {
      label: "Aktywni gracze",
      value: voiceData.filter((u) => u.total_seconds > 0).length.toLocaleString("pl-PL"),
    },
    { label: "Śledzone gry", value: gamesData.length.toLocaleString("pl-PL") },
    { label: "Najczęściej odwiedzany kanał", value: channelsData[0]?.channel_name ?? "–" },
  ];

  // Already sorted by play time, descending, by the API.
  const selectedUserGames = selectedUserId
    ? userGamesCache[userGamesCacheKey(selectedUserId, dateRange)]
    : undefined;
  const selectedUserName = users.find((u) => u.id === selectedUserId)?.display_name ?? "Użytkownik";
  const selectedUserVoiceSeconds =
    voiceData.find((v) => v.user_id === selectedUserId)?.total_seconds ?? 0;
  const selectedUserVoiceStat = (
    <div className="user-voice-stat">
      <span className="user-voice-stat-label">🔊 Czas na kanałach głosowych</span>
      <span className="user-voice-stat-value">{fmtHours(selectedUserVoiceSeconds)}</span>
    </div>
  );

  const engagementColumns: {
    key: "unmuted" | "undeafened";
    title: string;
    percent: (e: EngagementOut) => number;
    estimated: (e: EngagementOut) => boolean;
    tooltip: string;
  }[] = [
    {
      key: "unmuted",
      title: "🎙️ Mikrofon (niewyciszony)",
      percent: (e) => e.unmuted_percent,
      estimated: (e) => e.unmuted_estimated,
      tooltip: "Częściowo szacowane - brak danych o mikrofonie sprzed wdrożenia tej funkcji.",
    },
    {
      key: "undeafened",
      title: "🎧 Słuchawki (aktywne)",
      percent: (e) => e.undeafened_percent,
      estimated: (e) => e.undeafened_estimated,
      tooltip: "Częściowo szacowane - brak danych o słuchawkach sprzed wdrożenia tej funkcji.",
    },
  ];

  return (
    <>
      <div id="banner" className={error ? "show" : undefined}>
        <span>{error}</span>
        <button aria-label="Zamknij" onClick={() => setError(null)}>
          &times;
        </button>
      </div>

      <div className="page">
        <header className="topbar">
          <div className="brand">
            <img className="logo" src="/icon.svg" alt="" width={28} height={28} />
            <div className="brand-text">
              <h1>Discord Activity Dashboard</h1>
              <p>Statystyki aktywności serwera "Piwo i Rzygowiny"</p>
            </div>
          </div>
          <div className="topbar-controls">
            <TimeRangePicker value={dateRange} onChange={handleTimeRangeChange} />
            <button className="icon-btn" title="Odśwież" onClick={handleRefresh}>
              ⟳
            </button>
          </div>
        </header>

        <section className="cards">
          {cards.map((card) => (
            <div className="card" key={card.label}>
              <div className="card-label">{card.label}</div>
              <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
                {rangeLoading ? "–" : card.value}
              </div>
            </div>
          ))}
        </section>

        <nav className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab${activeTab === tab.id ? " active" : ""}`}
              onClick={() => handleTabChange(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <main>
          <section className="panel" hidden={activeTab !== "voice"}>
            <div className="panel-head">
              <h2>Ranking - czas na kanałach głosowych</h2>
            </div>
            <PanelBody
              loading={rangeLoading}
              isEmpty={voiceData.length === 0}
              emptyText="Brak danych - bot jeszcze nie zarejestrował żadnych sesji głosowych."
            >
              <DonutRanking
                items={voiceData}
                rankingTitle="Ranking użytkowników"
                periodLabel={periodLabel}
                getLabel={(u) => u.display_name}
                getValue={(u) => u.total_seconds}
                getColor={(u, i) => colorFor(u.display_name, i)}
                useAvatar
              />
            </PanelBody>
          </section>

          <section className="panel" hidden={activeTab !== "games"}>
            <div className="panel-head">
              <h2>Ranking gier - łączny czas wszystkich użytkowników</h2>
              <div>
                <span className="field-label">Liczba gier</span>
                <select
                  value={gamesLimit}
                  onChange={(e) => setGamesLimit(Number(e.target.value))}
                >
                  {GAMES_LIMIT_OPTIONS.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <PanelBody
              loading={rangeLoading}
              isEmpty={gamesData.length === 0}
              emptyText="Brak danych - bot jeszcze nie zarejestrował żadnych aktywności."
            >
              <DonutRanking
                items={gamesData}
                rankingItems={gamesData.slice(0, gamesLimit)}
                rankingTitle="Ranking gier"
                periodLabel={periodLabel}
                getLabel={(g) => g.activity_name}
                getValue={(g) => g.total_seconds}
                getColor={(g, i) => colorFor(g.activity_name, i)}
              />
            </PanelBody>
          </section>

          <section className="panel" hidden={activeTab !== "genres"}>
            <div className="panel-head">
              <h2>Gatunki gier - łączny czas wszystkich użytkowników</h2>
            </div>
            <PanelBody
              loading={rangeLoading}
              isEmpty={genresData.length === 0}
              emptyText="Brak danych - w tym okresie nie zarejestrowano żadnych gier przypisanych do gatunków."
            >
              <DonutRanking
                items={genresData}
                rankingTitle="Ranking gatunków"
                periodLabel={periodLabel}
                getLabel={(g) => g.genre}
                getValue={(g) => g.total_seconds}
                getColor={(g, i) => colorFor(g.genre, i)}
                getSubtitle={(g) => g.top_games.map((game) => game.activity_name).join(", ")}
              />
            </PanelBody>
          </section>

          <section className="panel" hidden={activeTab !== "user"}>
            <div className="panel-head">
              <h2>Statystyki użytkownika</h2>
              <div>
                <span className="field-label">Wybierz użytkownika</span>
                <select
                  value={selectedUserId ?? ""}
                  disabled={users.length === 0}
                  onChange={(e) => handleUserChange(e.target.value)}
                >
                  {users.length === 0 ? (
                    <option>Brak użytkowników</option>
                  ) : (
                    users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.display_name}
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>
            {users.length === 0 ? (
              <div className="empty-state">Brak użytkowników w bazie.</div>
            ) : (
              <PanelBody
                loading={userGamesLoading || selectedUserGames === undefined}
                isEmpty={selectedUserGames?.length === 0 && selectedUserVoiceSeconds === 0}
                emptyText={`${selectedUserName} nie ma jeszcze żadnych zarejestrowanych aktywności.`}
              >
                {selectedUserVoiceStat}
                {selectedUserGames?.length === 0 ? (
                  <div className="empty-state">
                    {selectedUserName} był aktywny na kanałach głosowych, ale nie ma jeszcze żadnych
                    zarejestrowanych gier.
                  </div>
                ) : (
                  <DonutRanking
                    items={selectedUserGames ?? []}
                    rankingTitle="Ranking gier"
                    periodLabel={periodLabel}
                    getLabel={(g) => g.activity_name}
                    getValue={(g) => g.total_seconds}
                    getColor={(g, i) => colorFor(g.activity_name, i)}
                  />
                )}
              </PanelBody>
            )}
          </section>

          <section className="panel" hidden={activeTab !== "engagement"}>
            <div className="panel-head">
              <h2>Zaangażowanie - % czasu głosowego z mikrofonem/słuchawkami włączonymi</h2>
            </div>
            <PanelBody
              loading={rangeLoading}
              isEmpty={engagementData.length === 0}
              emptyText="Brak danych - żaden śledzony użytkownik nie miał jeszcze czasu na kanale głosowym."
            >
              <div className="engagement-columns">
                {engagementColumns.map((col) => (
                  <div key={col.key}>
                    <div className="games-list-title">{col.title}</div>
                    <RankingList
                      items={[...engagementData].sort((a, b) => col.percent(b) - col.percent(a))}
                      getLabel={(e) => e.display_name}
                      getValue={col.percent}
                      getDisplayValue={(e) => `${col.percent(e)}%${col.estimated(e) ? "*" : ""}`}
                      getTooltip={(e) => (col.estimated(e) ? col.tooltip : undefined)}
                      getColor={(e) => colorFor(e.display_name)}
                      useAvatar
                    />
                  </div>
                ))}
              </div>
              {engagementData.some((e) => e.unmuted_estimated || e.undeafened_estimated) && (
                <p className="engagement-legend">
                  * częściowo szacowane - okres sprzed wdrożenia tej funkcji liczony jako 100%.
                </p>
              )}
            </PanelBody>
          </section>
        </main>
      </div>

      <footer>Dashboard aktywności serwera "Piwo i Rzygowiny"</footer>
    </>
  );
}
