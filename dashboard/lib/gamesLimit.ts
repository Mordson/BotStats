const BASE_LIMIT_STEPS = [5, 10, 15, 20, 30, 40, 50];

/** Endless "Liczba gier" steps: 5…50 as listed, then every 10 up to 100, then every 50. */
function* limitSteps(): Generator<number> {
  yield* BASE_LIMIT_STEPS;
  for (let n = 60; n <= 100; n += 10) yield n;
  for (let n = 150; ; n += 50) yield n;
}

/**
 * "Liczba gier" options for a range with `gameCount` games: the steps below
 * the count, then one option covering every game - the next step, or the count
 * rounded up to a full ten if that's smaller (69 games → …, 60, 70).
 */
export function gamesLimitOptions(gameCount: number): number[] {
  const count = Math.max(gameCount, 1);
  const options: number[] = [];
  for (const step of limitSteps()) {
    if (step >= count) {
      options.push(Math.min(step, Math.ceil(count / 10) * 10));
      break;
    }
    options.push(step);
  }
  return options;
}

/**
 * The option to show for the user's choice, which is kept across range
 * changes even when the current range doesn't offer it: the first option at
 * least as large, or the last one (which already covers every game).
 */
export function selectedGamesLimit(choice: number, options: number[]): number {
  return options.find((n) => n >= choice) ?? options[options.length - 1];
}
