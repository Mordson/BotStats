import { describe, expect, it } from "vitest";
import { createLatestRequestTracker } from "./latestRequest";

describe("createLatestRequestTracker", () => {
  it("keeps a request current until a newer one begins", () => {
    const tracker = createLatestRequestTracker();
    const first = tracker.begin();
    expect(first()).toBe(false);

    const second = tracker.begin();
    expect(first()).toBe(true);
    expect(second()).toBe(false);
  });

  it("keeps trackers independent", () => {
    const a = createLatestRequestTracker();
    const b = createLatestRequestTracker();
    const isAStale = a.begin();
    b.begin();
    expect(isAStale()).toBe(false);
  });
});
