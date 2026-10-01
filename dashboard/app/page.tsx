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

const DEFAULT_HOURS = 24;

export default async function Page() {
  const initialDateRange = presetRange(DEFAULT_HOURS);
  const { since } = rangeToParams(initialDateRange);

  let voiceData: VoiceTimeOut[] = [];
  let channelsData: ChannelTimeOut[] = [];
  let gamesData: GameTimeOut[] = [];
  let engagementData: EngagementOut[] = [];
  let genresData: GenreTimeOut[] = [];
  let users: UserOut[] = [];
  let error: string | null = null;

  try {
    [voiceData, channelsData, gamesData, engagementData, genresData, users] = await Promise.all([
      apiFetch<VoiceTimeOut[]>("/stats/voice-time", { since }),
      apiFetch<ChannelTimeOut[]>("/stats/voice-channels", { since }),
      apiFetch<GameTimeOut[]>("/stats/top-games", { since, limit: 1000 }),
      apiFetch<EngagementOut[]>("/stats/engagement", { since }),
      apiFetch<GenreTimeOut[]>("/stats/top-genres", { since }),
      apiFetch<UserOut[]>("/users/"),
    ]);
  } catch (err) {
    error = apiErrorMessage(err);
  }

  return (
    <Dashboard
      initialDateRange={initialDateRange}
      initialVoiceData={voiceData}
      initialChannelsData={channelsData}
      initialGamesData={gamesData}
      initialEngagementData={engagementData}
      initialGenresData={genresData}
      initialUsers={users}
      initialError={error}
    />
  );
}
