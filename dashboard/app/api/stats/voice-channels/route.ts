import { NextRequest, NextResponse } from "next/server";
import { apiFetch, ApiError, ChannelTimeOut } from "@/lib/api";

export async function GET(request: NextRequest) {
  const since = request.nextUrl.searchParams.get("since") ?? undefined;
  try {
    const data = await apiFetch<ChannelTimeOut[]>("/stats/voice-channels", { since });
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Nieznany błąd API";
    return NextResponse.json({ message }, { status: 502 });
  }
}
