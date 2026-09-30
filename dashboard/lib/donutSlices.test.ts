import { describe, expect, it } from "vitest";
import { splitDonutSlices } from "./donutSlices";

const hours = (...h: number[]) => h.map((x) => x * 3600);

describe("splitDonutSlices", () => {
  it("shows every item without 'other' when there are at most 8", () => {
    expect(splitDonutSlices(hours(50, 40, 30, 20, 10, 5, 3, 1))).toEqual({
      shownCount: 8,
      otherTotal: 0,
    });
  });

  it("pulls the 9th item out of 'other' when it is at least 20% of it", () => {
    // 9th = 18h, 'other' = 18 + 13 * 4h = 70h -> ~26%
    const values = hours(100, 90, 80, 70, 60, 50, 40, 30, 18, ...Array(13).fill(4));
    expect(splitDonutSlices(values)).toEqual({ shownCount: 9, otherTotal: 52 * 3600 });
  });

  it("keeps 8 slices + 'other' when the 9th item is below 20% of 'other'", () => {
    const values = hours(100, 90, 80, 70, 60, 50, 40, 30, 5, 5, 5, 5, 5, 5);
    expect(splitDonutSlices(values)).toEqual({ shownCount: 8, otherTotal: 30 * 3600 });
  });

  it("stops pulling items out at 12 slices", () => {
    // every item past the 8th is >= 20% of the remaining 'other'; only the cap stops it
    const values = hours(100, 90, 80, 70, 60, 50, 45, 42, 40, 35, 30, 25, 10, 10, 10);
    expect(splitDonutSlices(values)).toEqual({ shownCount: 12, otherTotal: 30 * 3600 });
  });

  it("shows all items when only one would be left in 'other'", () => {
    const values = hours(100, 90, 80, 70, 60, 50, 40, 30, 20, 19, 18, 17, 1);
    expect(splitDonutSlices(values)).toEqual({ shownCount: 13, otherTotal: 0 });
  });

  it("does not pull zero-value items out of 'other'", () => {
    const values = hours(100, 90, 80, 70, 60, 50, 40, 30, 0, 0, 0);
    expect(splitDonutSlices(values)).toEqual({ shownCount: 8, otherTotal: 0 });
  });
});
