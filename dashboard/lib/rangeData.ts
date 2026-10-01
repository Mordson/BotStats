import type { ChannelTimeOut, EngagementOut, GameTimeOut, GenreTimeOut, VoiceTimeOut } from "./api";

/** Everything on the dashboard that depends only on the selected date range. */
export interface RangeData {
  voice: VoiceTimeOut[];
  channels: ChannelTimeOut[];
  games: GameTimeOut[];
  engagement: EngagementOut[];
  genres: GenreTimeOut[];
}

export const EMPTY_RANGE_DATA: RangeData = { voice: [], channels: [], games: [], engagement: [], genres: [] };

/** The top-games request fetches every game; the "Liczba gier" select only trims the ranking. */
export const ALL_GAMES_LIMIT = "1000";
