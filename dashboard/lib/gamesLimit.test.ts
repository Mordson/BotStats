import { describe, expect, it } from "vitest";
import { gamesLimitOptions, shownGamesLimit } from "./gamesLimit";

describe("gamesLimitOptions", () => {
  it("ends with the game count rounded up to a full ten", () => {
    expect(gamesLimitOptions(69)).toEqual([5, 10, 15, 20, 30, 40, 50, 60, 70]);
  });

  it("stops at the first option covering every game", () => {
    expect(gamesLimitOptions(12)).toEqual([5, 10, 15]);
  });

  it("ends exactly on a step when the count matches it", () => {
    expect(gamesLimitOptions(50)).toEqual([5, 10, 15, 20, 30, 40, 50]);
  });

  it("steps by 50 above 100 and ends with the rounded count", () => {
    expect(gamesLimitOptions(230)).toEqual([
      5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 230,
    ]);
  });

  it("rounds to a full ten when that's below the next step above 100", () => {
    expect(gamesLimitOptions(101).slice(-2)).toEqual([100, 110]);
  });

  it("offers a single option for very few or no games", () => {
    expect(gamesLimitOptions(3)).toEqual([5]);
    expect(gamesLimitOptions(0)).toEqual([5]);
  });
});

describe("shownGamesLimit", () => {
  it("keeps a choice that is among the options", () => {
    expect(shownGamesLimit(10, [5, 10, 15])).toBe(10);
  });

  it("falls back to the last option when the choice exceeds them", () => {
    expect(shownGamesLimit(50, [5, 10, 15])).toBe(15);
  });

  it("picks the next option up when the choice isn't offered", () => {
    expect(shownGamesLimit(30, [5, 10, 50, 100])).toBe(50);
  });
});
