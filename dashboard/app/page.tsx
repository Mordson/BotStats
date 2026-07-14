import Dashboard from "@/components/Dashboard";
import { apiFetch, ApiError, type GameTimeOut, type UserOut, type VoiceTimeOut } from "@/lib/api";
import { sinceIso } from "@/lib/format";

const DEFAULT_HOURS = 24;

export default async function Page() {
  const since = sinceIso(DEFAULT_HOURS);

  let voiceData: VoiceTimeOut[] = [];
  let gamesData: GameTimeOut[] = [];
  let users: UserOut[] = [];
  let error: string | null = null;

  try {
    [voiceData, gamesData, users] = await Promise.all([
      apiFetch<VoiceTimeOut[]>("/stats/voice-time", { since }),
      apiFetch<GameTimeOut[]>("/stats/top-games", { since, limit: 1000 }),
      apiFetch<UserOut[]>("/users/"),
    ]);
  } catch (err) {
    error = err instanceof ApiError ? err.message : "Nieznany błąd API";
  }

  return (
    <Dashboard
      initialSinceHours={DEFAULT_HOURS}
      initialVoiceData={voiceData}
      initialGamesData={gamesData}
      initialUsers={users}
      initialError={error}
    />
  );
}
