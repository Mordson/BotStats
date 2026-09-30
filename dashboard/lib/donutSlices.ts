const BASE_SLICES = 8;
// Keep PALETTE in format.ts at MAX_SLICES + 1 colors so no slice repeats a color.
const MAX_SLICES = 12;
// An item past BASE_SLICES gets its own slice once it makes up this share of 'other'.
const OTHER_SHARE_THRESHOLD = 0.2;

/**
 * Decides how many leading items get their own donut slice; the rest is merged into 'other'.
 * `values` must be sorted descending.
 */
export function splitDonutSlices(values: number[]): { shownCount: number; otherTotal: number } {
  let shownCount = Math.min(BASE_SLICES, values.length);
  let otherTotal = values.slice(shownCount).reduce((s, v) => s + v, 0);

  while (shownCount < values.length && values[shownCount] > 0) {
    const onlyOneLeft = shownCount === values.length - 1;
    if (!onlyOneLeft) {
      if (shownCount >= MAX_SLICES) break;
      if (values[shownCount] < otherTotal * OTHER_SHARE_THRESHOLD) break;
    }
    otherTotal -= values[shownCount];
    shownCount++;
  }

  return { shownCount, otherTotal };
}
