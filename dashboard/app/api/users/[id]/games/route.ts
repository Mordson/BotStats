import { NextResponse } from "next/server";
import { apiFetch, ApiError, UserGameTimeOut } from "@/lib/api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  try {
    const data = await apiFetch<UserGameTimeOut[]>(`/users/${id}/games`);
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Nieznany błąd API";
    return NextResponse.json({ message }, { status: 502 });
  }
}
