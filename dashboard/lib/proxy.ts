import "server-only";
import { NextRequest, NextResponse } from "next/server";
import { apiErrorMessage, apiFetch } from "./api";

/**
 * Backs the dashboard's `/api/*` route handlers: forwards a GET to the internal
 * API at `path`, passing through only the `forwardedParams` query params, and
 * turns an API failure into a 502 with a user-facing message.
 */
export async function proxyGet(
  request: NextRequest,
  path: string,
  forwardedParams: readonly string[] = ["since", "until"],
): Promise<NextResponse> {
  const params = Object.fromEntries(
    forwardedParams.map((key) => [key, request.nextUrl.searchParams.get(key) ?? undefined]),
  );
  try {
    return NextResponse.json(await apiFetch<unknown>(path, params));
  } catch (err) {
    return NextResponse.json({ message: apiErrorMessage(err) }, { status: 502 });
  }
}
