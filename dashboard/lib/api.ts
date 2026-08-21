import "server-only";

const API_INTERNAL_URL = process.env.API_INTERNAL_URL ?? "http://api:8000";

export interface UserOut {
  id: string;
  username: string;
  display_name: string;
  first_seen: string;
}

export interface VoiceTimeOut {
  user_id: string;
  display_name: string;
  total_seconds: number;
}

export interface ChannelTimeOut {
  channel_id: string;
  channel_name: string;
  total_seconds: number;
}

export interface GameTimeOut {
  activity_name: string;
  total_seconds: number;
}

export type UserGameTimeOut = GameTimeOut;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(path, API_INTERNAL_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }

  let resp: Response;
  try {
    resp = await fetch(url.toString(), { cache: "no-store" });
  } catch {
    throw new ApiError(`Nie można połączyć się z API (${API_INTERNAL_URL}).`);
  }

  if (!resp.ok) {
    throw new ApiError(`Błąd API: ${resp.status} ${resp.statusText}`, resp.status);
  }
  return resp.json() as Promise<T>;
}
