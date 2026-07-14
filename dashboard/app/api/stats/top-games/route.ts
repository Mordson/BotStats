import { NextRequest, NextResponse } from "next/server";
import { apiFetch, ApiError, GameTimeOut } from "@/lib/api";

export async function GET(request: NextRequest) {
  const since = request.nextUrl.searchParams.get("since") ?? undefined;
  const limit = request.nextUrl.searchParams.get("limit") ?? undefined;
  try {
    const data = await apiFetch<GameTimeOut[]>("/stats/top-games", { since, limit });
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Nieznany błąd API";
    return NextResponse.json({ message }, { status: 502 });
  }
}
