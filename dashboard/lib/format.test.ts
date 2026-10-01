// The dashboard's users are in Poland; pin the zone so the local-date tests
// exercise a non-UTC offset regardless of where the tests run.
process.env.TZ = "Europe/Warsaw";

import { describe, expect, it } from "vitest";
import { localDateInput, rangeQuery } from "./format";

describe("localDateInput", () => {
  it("uses the local calendar day, not the UTC one, just after midnight", () => {
    // 00:30 in Warsaw (CET) is still the previous day in UTC.
    expect(localDateInput(new Date(2026, 0, 5, 0, 30))).toBe("2026-01-05");
  });

  it("zero-pads month and day", () => {
    expect(localDateInput(new Date(2026, 2, 7, 12, 0))).toBe("2026-03-07");
  });
});

describe("rangeQuery", () => {
  it("encodes a custom range as since/until for whole local days", () => {
    const query = rangeQuery({ kind: "custom", sinceDate: "2026-01-05", untilDate: "2026-01-06" });
    expect(query.get("since")).toBe(new Date(2026, 0, 5, 0, 0, 0).toISOString());
    expect(query.get("until")).toBe(new Date(2026, 0, 6, 23, 59, 59, 999).toISOString());
  });

  it("omits until for a preset range", () => {
    const query = rangeQuery({ kind: "preset", hours: 24 });
    expect(query.has("since")).toBe(true);
    expect(query.has("until")).toBe(false);
  });

  it("appends extra params", () => {
    const query = rangeQuery({ kind: "preset", hours: 24 }, { limit: "1000" });
    expect(query.get("limit")).toBe("1000");
  });
});
