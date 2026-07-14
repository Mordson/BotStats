import { NextResponse } from "next/server";
import { apiFetch, ApiError, UserOut } from "@/lib/api";

export async function GET() {
  try {
    const data = await apiFetch<UserOut[]>("/users/");
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Nieznany błąd API";
    return NextResponse.json({ message }, { status: 502 });
  }
}
