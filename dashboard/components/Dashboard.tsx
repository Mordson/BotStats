"use client";

import { useState } from "react";
import RankingList from "./RankingList";
import Donut from "./Donut";
import { TIME_RANGES, colorFor, fmtHours, sinceIso } from "@/lib/format";
import type { ChannelTimeOut, GameTimeOut, UserGameTimeOut, UserOut, VoiceTimeOut } from "@/lib/api";

type Tab = "voice" | "games" | "user";

interface DashboardProps {
  initialSinceHours: number;
  initialVoiceData: VoiceTimeOut[];
  initialChannelsData: ChannelTimeOut[];
  initialGamesData: GameTimeOut[];
  initialUsers: UserOut[];
  initialError: string | null;
}

const GAMES_LIMIT_OPTIONS = [5, 10, 15, 20, 30, 50];
const CONNECTION_ERROR = "Nie można połączyć się z API. Upewnij się, że bot i API są uruchomione.";

export default function Dashboard({
  initialSinceHours,
  initialVoiceData,
  initialChannelsData,
  initialGamesData,
  initialUsers,
  initialError,
}: DashboardProps) {
  const [sinceHours, setSinceHours] = useState(initialSinceHours);
  const [activeTab, setActiveTab] = useState<Tab>("voice");
  const [voiceData, setVoiceData] = useState(initialVoiceData);
  const [channelsData, setChannelsData] = useState(initialChannelsData);
  const [gamesData, setGamesData] = useState(initialGamesData);
  const [users, setUsers] = useState(initialUsers);
  const [gamesLimit, setGamesLimit] = useState(10);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(
    initialUsers[0]?.id ?? null,
  );
  const [userGamesCache, setUserGamesCache] = useState<Record<string, UserGameTimeOut[]>>({});
  const [userGamesLoading, setUserGamesLoading] = useState(false);
  const [rangeLoading, setRangeLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialError);

  const userGamesCacheKey = (userId: string, hours: number) => `${userId}:${hours}`;

  async function loadRangeData(hours: number) {
    setRangeLoading(true);
    const since = sinceIso(hours);
    try {
      const [voiceResp, channelsResp, gamesResp] = await Promise.all([
        fetch(`/api/stats/voice-time?since=${encodeURIComponent(since)}`),
        fetch(`/api/stats/voice-channels?since=${encodeURIComponent(since)}`),
        fetch(`/api/stats/top-games?since=${encodeURIComponent(since)}&limit=1000`),
      ]);
      if (!voiceResp.ok || !channelsResp.ok || !gamesResp.ok) throw new Error("http");
      setVoiceData(await voiceResp.json());
      setChannelsData(await channelsResp.json());
      setGamesData(await gamesResp.json());
      setError(null);
    } catch {
      setError(CONNECTION_ERROR);
      setVoiceData([]);
      setChannelsData([]);
      setGamesData([]);
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

  async function loadUserGames(userId: string, hours: number) {
    setUserGamesLoading(true);
    try {
      const since = sinceIso(hours);
      const resp = await fetch(
        `/api/users/${userId}/games?since=${encodeURIComponent(since)}`,
      );
      if (!resp.ok) throw new Error("http");
      const data: UserGameTimeOut[] = await resp.json();
      setUserGamesCache((prev) => ({ ...prev, [userGamesCacheKey(userId, hours)]: data }));
      setError(null);
    } catch {
      setError("Nie udało się pobrać danych użytkownika.");
    } finally {
      setUserGamesLoading(false);
    }
  }

  function handleTimeRangeChange(hours: number) {
    setSinceHours(hours);
    void loadRangeData(hours);
    if (activeTab === "user" && selectedUserId) void loadUserGames(selectedUserId, hours);
  }

  function handleTabChange(tab: Tab) {
    setActiveTab(tab);
    if (tab === "user" && selectedUserId && !userGamesCache[userGamesCacheKey(selectedUserId, sinceHours)]) {
      void loadUserGames(selectedUserId, sinceHours);
    }
  }

  function handleUserChange(userId: string) {
    setSelectedUserId(userId);
    if (!userGamesCache[userGamesCacheKey(userId, sinceHours)]) void loadUserGames(userId, sinceHours);
  }

  function handleRefresh() {
    setUserGamesCache({});
    void loadRangeData(sinceHours);
    void loadUsers();
    if (activeTab === "user" && selectedUserId) void loadUserGames(selectedUserId, sinceHours);
  }

  const voiceTotal = voiceData.reduce((sum, u) => sum + u.total_seconds, 0);
  const activePlayers = voiceData.filter((u) => u.total_seconds > 0).length;
  const topGame = gamesData[0]?.activity_name ?? "–";
  const trackedGames = gamesData.length;
  const topChannel = channelsData[0]?.channel_name ?? "–";
  const gamesTotal = gamesData.reduce((sum, g) => sum + g.total_seconds, 0);
  const periodLabel = TIME_RANGES.find((r) => r.hours === sinceHours)?.label ?? "";

  const shownGames = gamesData.slice(0, gamesLimit);
  const selectedUserGames = selectedUserId
    ? userGamesCache[userGamesCacheKey(selectedUserId, sinceHours)]
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
            <div className="logo">◆</div>
            <div className="brand-text">
              <h1>Discord Activity Dashboard</h1>
              <p>Statystyki aktywności serwera "Piwo i Rzygowiny"</p>
            </div>
          </div>
          <div className="topbar-controls">
            <div>
              <span className="field-label">Przedział czasowy</span>
              <select
                value={sinceHours}
                onChange={(e) => handleTimeRangeChange(Number(e.target.value))}
              >
                {TIME_RANGES.map((r) => (
                  <option key={r.hours} value={r.hours}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
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
            <div className="card-label">Aktywni gracze</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : activePlayers.toLocaleString("pl-PL")}
            </div>
          </div>
          <div className="card">
            <div className="card-label">Najpopularniejsza gra</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : topGame}
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
          <div className="card">
            <div className="card-label">Łączny czas na grach</div>
            <div className={`card-value${rangeLoading ? " skeleton" : ""}`}>
              {rangeLoading ? "–" : fmtHours(gamesTotal)}
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
        </main>
      </div>

      <footer>Dashboard aktywności serwera "Piwo i Rzygowiny"</footer>
    </>
  );
}
