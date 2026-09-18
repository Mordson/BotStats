"use client";

import { useState } from "react";
import RankingList from "./RankingList";
import Donut from "./Donut";
import TimeRangePicker from "./TimeRangePicker";
import { colorFor, fmtHours, formatRangeLabel, rangeKey, rangeToParams, type DateRange } from "@/lib/format";
import type {
  ChannelTimeOut,
  EngagementOut,
  GameTimeOut,
  UserGameTimeOut,
  UserOut,
  VoiceTimeOut,
} from "@/lib/api";

type Tab = "voice" | "games" | "user" | "engagement";

interface DashboardProps {
  initialDateRange: DateRange;
  initialVoiceData: VoiceTimeOut[];
  initialChannelsData: ChannelTimeOut[];
  initialGamesData: GameTimeOut[];
  initialEngagementData: EngagementOut[];
  initialUsers: UserOut[];
  initialError: string | null;
}

const GAMES_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const CONNECTION_ERROR = "Nie można połączyć się z API. Upewnij się, że bot i API są uruchomione.";

export default function Dashboard({
  initialDateRange,
  initialVoiceData,
  initialChannelsData,
  initialGamesData,
  initialEngagementData,
  initialUsers,
  initialError,
}: DashboardProps) {
  const [dateRange, setDateRange] = useState<DateRange>(initialDateRange);
  const [activeTab, setActiveTab] = useState<Tab>("voice");
  const [voiceData, setVoiceData] = useState(initialVoiceData);
  const [channelsData, setChannelsData] = useState(initialChannelsData);
  const [gamesData, setGamesData] = useState(initialGamesData);
  const [engagementData, setEngagementData] = useState(initialEngagementData);
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
    const params = new URLSearchParams(rangeToParams(range) as Record<string, string>);
    const gamesParams = new URLSearchParams({ ...rangeToParams(range), limit: "1000" } as Record<string, string>);
    try {
      const [voiceResp, channelsResp, gamesResp, engagementResp] = await Promise.all([
        fetch(`/api/stats/voice-time?${params}`),
        fetch(`/api/stats/voice-channels?${params}`),
        fetch(`/api/stats/top-games?${gamesParams}`),
        fetch(`/api/stats/engagement?${params}`),
      ]);
      if (!voiceResp.ok || !channelsResp.ok || !gamesResp.ok || !engagementResp.ok) throw new Error("http");
      setVoiceData(await voiceResp.json());
      setChannelsData(await channelsResp.json());
      setGamesData(await gamesResp.json());
      setEngagementData(await engagementResp.json());
      setError(null);
    } catch {
      setError(CONNECTION_ERROR);
      setVoiceData([]);
      setChannelsData([]);
      setGamesData([]);
      setEngagementData([]);
    } finally {
      setRangeLoading(false);
    }
  }

  async function loadUsers() {
    try {
      const resp = await fetch("/api/users/");
      if (!resp.ok) throw new Error("http");
      const data: UserOut[] = await resp.json();
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
      const params = new URLSearchParams(rangeToParams(range) as Record<string, string>);
      const resp = await fetch(`/api/users/${userId}/games?${params}`);
      if (!resp.ok) throw new Error("http");
      const data: UserGameTimeOut[] = await resp.json();
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

  const voiceTotal = voiceData.reduce((sum, u) => sum + u.total_seconds, 0);
  const activePlayers = voiceData.filter((u) => u.total_seconds > 0).length;
  const topGame = gamesData[0]?.activity_name ?? "–";
  const trackedGames = gamesData.length;
  const topChannel = channelsData[0]?.channel_name ?? "–";
  const gamesTotal = gamesData.reduce((sum, g) => sum + g.total_seconds, 0);
  const periodLabel = formatRangeLabel(dateRange);

  const shownGames = gamesData.slice(0, gamesLimit);
  const selectedUserGames = selectedUserId
    ? userGamesCache[userGamesCacheKey(selectedUserId, dateRange)]
    : undefined;
  const selectedUser = users.find((u) => u.id === selectedUserId);
  const selectedUserVoiceSeconds =
    voiceData.find((v) => v.user_id === selectedUserId)?.total_seconds ?? 0;

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
          <div className="card">
            <div className="card-label">Czas głosowy</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : fmtHours(voiceTotal)}
            </div>
          </div>
          <div className="card">
            <div className="card-label">Łączny czas na grach</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : fmtHours(gamesTotal)}
            </div>
          </div>
          <div className="card">
            <div className="card-label">Najpopularniejsza gra</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : topGame}
            </div>
          </div>
          <div className="card">
            <div className="card-label">Aktywni gracze</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : activePlayers.toLocaleString("pl-PL")}
            </div>
          </div>
          <div className="card">
            <div className="card-label">Śledzone gry</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : trackedGames.toLocaleString("pl-PL")}
            </div>
          </div>
          <div className="card">
            <div className="card-label">Najczęściej odwiedzany kanał</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : topChannel}
            </div>
          </div>
        </section>

        <nav className="tabs">
          <button
            className={`tab${activeTab === "voice" ? " active" : ""}`}
            onClick={() => handleTabChange("voice")}
          >
            🔊 Czas głosowy
          </button>
          <button
            className={`tab${activeTab === "games" ? " active" : ""}`}
            onClick={() => handleTabChange("games")}
          >
            🕹️ Top gry
          </button>
          <button
            className={`tab${activeTab === "user" ? " active" : ""}`}
            onClick={() => handleTabChange("user")}
          >
            👤 Użytkownik
          </button>
          <button
            className={`tab${activeTab === "engagement" ? " active" : ""}`}
            onClick={() => handleTabChange("engagement")}
          >
            🎙️ Zaangażowanie
          </button>
        </nav>

        <main>
          <section className="panel" hidden={activeTab !== "voice"}>
            <div className="panel-head">
              <h2>Ranking - czas na kanałach głosowych</h2>
            </div>
            {rangeLoading ? (
              <div className="loading-state">Ładowanie…</div>
            ) : voiceData.length === 0 ? (
              <div className="empty-state">
                Brak danych - bot jeszcze nie zarejestrował żadnych sesji głosowych.
              </div>
            ) : (
              <>
                <Donut
                  items={voiceData}
                  getLabel={(u) => u.display_name}
                  getValue={(u) => u.total_seconds}
                  getColor={(u, i) => colorFor(u.display_name, i)}
                  centerLabel="łącznie"
                  periodLabel={periodLabel}
                />
                <div className="games-list-title">Ranking użytkowników</div>
                <RankingList
                  items={voiceData}
                  getLabel={(u) => u.display_name}
                  getValue={(u) => u.total_seconds}
                  getColor={(u, i) => colorFor(u.display_name, i)}
                  useAvatar
                />
              </>
            )}
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
            {rangeLoading ? (
              <div className="loading-state">Ładowanie…</div>
            ) : gamesData.length === 0 ? (
              <div className="empty-state">
                Brak danych - bot jeszcze nie zarejestrował żadnych aktywności.
              </div>
            ) : (
              <>
                <Donut
                  items={gamesData}
                  getLabel={(g) => g.activity_name}
                  getValue={(g) => g.total_seconds}
                  getColor={(g, i) => colorFor(g.activity_name, i)}
                  centerLabel="łącznie"
                  periodLabel={periodLabel}
                />
                <div className="games-list-title">Ranking gier</div>
                <RankingList
                  items={shownGames}
                  getLabel={(g) => g.activity_name}
                  getValue={(g) => g.total_seconds}
                  getColor={(g, i) => colorFor(g.activity_name, i)}
                />
              </>
            )}
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
            ) : userGamesLoading || selectedUserGames === undefined ? (
              <div className="loading-state">Ładowanie…</div>
            ) : selectedUserGames.length === 0 ? (
              selectedUserVoiceSeconds > 0 ? (
                <>
                  <div className="user-voice-stat">
                    <span className="user-voice-stat-label">🔊 Czas na kanałach głosowych</span>
                    <span className="user-voice-stat-value">{fmtHours(selectedUserVoiceSeconds)}</span>
                  </div>
                  <div className="empty-state">
                    {selectedUser ? selectedUser.display_name : "Użytkownik"} był aktywny na
                    kanałach głosowych, ale nie ma jeszcze żadnych zarejestrowanych gier.
                  </div>
                </>
              ) : (
                <div className="empty-state">
                  {selectedUser ? selectedUser.display_name : "Użytkownik"} nie ma jeszcze
                  żadnych zarejestrowanych aktywności.
                </div>
              )
            ) : (
              <>
                <div className="user-voice-stat">
                  <span className="user-voice-stat-label">🔊 Czas na kanałach głosowych</span>
                  <span className="user-voice-stat-value">{fmtHours(selectedUserVoiceSeconds)}</span>
                </div>
                <Donut
                  items={[...selectedUserGames].sort((a, b) => b.total_seconds - a.total_seconds)}
                  getLabel={(g) => g.activity_name}
                  getValue={(g) => g.total_seconds}
                  getColor={(g, i) => colorFor(g.activity_name, i)}
                  centerLabel="łącznie"
                  periodLabel={periodLabel}
                />
                <div className="games-list-title">Ranking gier</div>
                <RankingList
                  items={[...selectedUserGames].sort((a, b) => b.total_seconds - a.total_seconds)}
                  getLabel={(g) => g.activity_name}
                  getValue={(g) => g.total_seconds}
                  getColor={(g, i) => colorFor(g.activity_name, i)}
                />
              </>
            )}
          </section>

          <section className="panel" hidden={activeTab !== "engagement"}>
            <div className="panel-head">
              <h2>Zaangażowanie - % czasu głosowego z mikrofonem/słuchawkami włączonymi</h2>
            </div>
            {rangeLoading ? (
              <div className="loading-state">Ładowanie…</div>
            ) : engagementData.length === 0 ? (
              <div className="empty-state">
                Brak danych - żaden śledzony użytkownik nie miał jeszcze czasu na kanale głosowym.
              </div>
            ) : (
              <div className="engagement-columns">
                <div>
                  <div className="games-list-title">🎙️ Mikrofon (niewyciszony)</div>
                  <RankingList
                    items={[...engagementData].sort((a, b) => b.unmuted_percent - a.unmuted_percent)}
                    getLabel={(e) => e.display_name}
                    getValue={(e) => e.unmuted_percent}
                    getDisplayValue={(e) => `${e.unmuted_percent}%`}
                    getColor={(e) => colorFor(e.display_name)}
                    useAvatar
                  />
                </div>
                <div>
                  <div className="games-list-title">🎧 Słuchawki (nieogłuszone)</div>
                  <RankingList
                    items={[...engagementData].sort(
                      (a, b) => b.undeafened_percent - a.undeafened_percent,
                    )}
                    getLabel={(e) => e.display_name}
                    getValue={(e) => e.undeafened_percent}
                    getDisplayValue={(e) => `${e.undeafened_percent}%`}
                    getColor={(e) => colorFor(e.display_name)}
                    useAvatar
                  />
                </div>
              </div>
            )}
          </section>
        </main>
      </div>

      <footer>Dashboard aktywności serwera "Piwo i Rzygowiny"</footer>
    </>
  );
}
