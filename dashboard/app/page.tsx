import Dashboard from "@/components/Dashboard";
import {
  apiErrorMessage,
  apiFetch,
  type ChannelTimeOut,
  type EngagementOut,
  type GameTimeOut,
  type GenreTimeOut,
  type UserOut,
  type VoiceTimeOut,
} from "@/lib/api";
import { presetRange, rangeToParams } from "@/lib/format";
import { ALL_GAMES_LIMIT, EMPTY_RANGE_DATA, type RangeData } from "@/lib/rangeData";

const DEFAULT_HOURS = 24;

export default async function Page() {
  const initialDateRange = presetRange(DEFAULT_HOURS);
  const { since } = rangeToParams(initialDateRange);

  let rangeData: RangeData = EMPTY_RANGE_DATA;
  let users: UserOut[] = [];
  let error: string | null = null;

  try {
    const [voice, channels, games, engagement, genres, fetchedUsers] = await Promise.all([
      apiFetch<VoiceTimeOut[]>("/stats/voice-time", { since }),
      apiFetch<ChannelTimeOut[]>("/stats/voice-channels", { since }),
      apiFetch<GameTimeOut[]>("/stats/top-games", { since, limit: ALL_GAMES_LIMIT }),
      apiFetch<EngagementOut[]>("/stats/engagement", { since }),
      apiFetch<GenreTimeOut[]>("/stats/top-genres", { since }),
      apiFetch<UserOut[]>("/users/"),
    ]);
    rangeData = { voice, channels, games, engagement, genres };
    users = fetchedUsers;
  } catch (err) {
    error = apiErrorMessage(err);
  }

  return (
    <Dashboard
      initialDateRange={initialDateRange}
      initialRangeData={rangeData}
      initialUsers={users}
      initialError={error}
    />
  );
}
