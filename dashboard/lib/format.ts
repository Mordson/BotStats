export const PALETTE = [
  "#00e5ff",
  "#8b5cff",
  "#ff2d95",
  "#22d3a8",
  "#ffb020",
  "#4f8cff",
  "#ff6fae",
  "#b6ff3f",
];
export const GRAY = "#4a5568";

export interface TimeRange {
  label: string;
  hours: number;
}

export const TIME_RANGES: TimeRange[] = [
  { label: "Ostatnie 24H", hours: 24 },
  { label: "Ostatni tydzień", hours: 24 * 7 },
  { label: "Ostatni miesiąc", hours: 24 * 30 },
  { label: "Ostatnie pół roku", hours: 24 * 182 },
  { label: "Ostatni rok", hours: 24 * 365 },
];

export const CUSTOM_RANGE_VALUE = "custom";

/**
 * Either one of the system-proposed presets (`hours` ago until now) or a
 * user-picked [since, until] range. Everything downstream of selection
 * (data fetching, cache keys, the period label) goes through this type
 * instead of a bare hour count, so a custom range is a first-class case
 * rather than something bolted onto the preset path.
 */
export type DateRange =
  | { kind: "preset"; hours: number }
  | { kind: "custom"; sinceDate: string; untilDate: string };

export function presetRange(hours: number): DateRange {
  return { kind: "preset", hours };
}

/** Stable string key for a range, for use in caches/effect deps. */
export function rangeKey(range: DateRange): string {
  return range.kind === "preset" ? `preset:${range.hours}` : `custom:${range.sinceDate}:${range.untilDate}`;
}

/** Query params ({ since, until }) to send to the stats API for this range. */
export function rangeToParams(range: DateRange): { since: string; until?: string } {
  if (range.kind === "preset") return { since: sinceIso(range.hours) };
  return {
    since: new Date(`${range.sinceDate}T00:00:00`).toISOString(),
    until: new Date(`${range.untilDate}T23:59:59.999`).toISOString(),
  };
}

export function formatRangeLabel(range: DateRange): string {
  if (range.kind === "preset") {
    return TIME_RANGES.find((r) => r.hours === range.hours)?.label ?? "";
  }
  const fmt = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("pl-PL");
  return `${fmt(range.sinceDate)} – ${fmt(range.untilDate)}`;
}

export function colorFor(str: string, idx?: number): string {
  if (idx !== undefined) return PALETTE[idx % PALETTE.length];
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

export function fmtHours(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return `${h} h ${String(m).padStart(2, "0")} min`;
}

export function sinceIso(hours: number): string {
  return new Date(Date.now() - hours * 3600 * 1000).toISOString();
}
