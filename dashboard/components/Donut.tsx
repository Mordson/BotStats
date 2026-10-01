import { splitDonutSlices } from "@/lib/donutSlices";
import { fmtHours, GRAY } from "@/lib/format";

interface DonutProps<T> {
  items: T[];
  getLabel: (item: T) => string;
  getValue: (item: T) => number;
  getColor: (item: T, index: number) => string;
  centerLabel: string;
  periodLabel?: string;
}

interface Slice {
  label: string;
  value: number;
  color: string;
}

export default function Donut<T>({
  items,
  getLabel,
  getValue,
  getColor,
  centerLabel,
  periodLabel,
}: DonutProps<T>) {
  const totalAll = items.reduce((s, item) => s + getValue(item), 0);
  const { shownCount, otherTotal } = splitDonutSlices(items.map(getValue));
  const slices: Slice[] = items.slice(0, shownCount).map((item, i) => ({
    label: getLabel(item),
    value: getValue(item),
    color: getColor(item, i),
  }));
  if (otherTotal > 0) slices.push({ label: "Inne", value: otherTotal, color: GRAY });

  const percentOf = (value: number) => (totalAll ? (value / totalAll) * 100 : 0);

  let acc = 0;
  const stops = slices.map(({ value, color }) => {
    const start = acc;
    acc += percentOf(value);
    return `${color} ${start}% ${acc}%`;
  });
  const background = stops.length
    ? `conic-gradient(${stops.join(", ")})`
    : "rgba(255,255,255,.06)";

  return (
    <div className="games-layout">
      <div className="donut-wrap">
        <div className="donut" style={{ background }}>
          <div className="donut-center">
            <div className="val">{fmtHours(totalAll)}</div>
            <div className="lbl">{centerLabel}</div>
          </div>
        </div>
        {periodLabel && <div className="donut-period">{periodLabel}</div>}
      </div>
      <div className="legend">
        {/* Keyed by position: labels (e.g. display names) aren't guaranteed unique. */}
        {slices.map(({ label, value, color }, i) => (
          <div className="legend-row" key={i}>
            <div className="dot" style={{ background: color }} />
            <div className="name">{label}</div>
            <div className="hrs mono">{fmtHours(value)}</div>
            <div className="pct mono">
              {totalAll ? Math.round((value / totalAll) * 1000) / 10 : 0}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
