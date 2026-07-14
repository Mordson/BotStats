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
