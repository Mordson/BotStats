/**
 * Tracks which of several overlapping async requests is the latest one.
 * `begin()` starts a request and returns an `isStale()` check that turns true
 * as soon as a newer request has begun, so its result can be dropped.
 */
export function createLatestRequestTracker(): { begin: () => () => boolean } {
  let latest = 0;
  return {
    begin() {
      const id = ++latest;
      return () => id !== latest;
    },
  };
}
