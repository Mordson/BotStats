import { NextRequest } from "next/server";
import { proxyGet } from "@/lib/proxy";

export function GET(request: NextRequest) {
  return proxyGet(request, "/users/", []);
}
