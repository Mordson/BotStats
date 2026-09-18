import { NextRequest, NextResponse } from "next/server";
import { apiFetch, ApiError, EngagementOut } from "@/lib/api";

export async function GET(request: NextRequest) {
  const since = request.nextUrl.searchParams.get("since") ?? undefined;
  const until = request.nextUrl.searchParams.get("until") ?? undefined;
  try {
    const data = await apiFetch<EngagementOut[]>("/stats/engagement", { since, until });
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Nieznany błąd API";
    return NextResponse.json({ message }, { status: 502 });
  }
}
