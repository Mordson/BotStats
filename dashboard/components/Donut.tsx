import { fmtHours, GRAY } from "@/lib/format";

interface DonutProps<T> {
  items: T[];
  getLabel: (item: T) => string;
  getValue: (item: T) => number;
  getColor: (item: T, index: number) => string;
  centerLabel: string;
  periodLabel?: string;
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
  const donutSlices = items.slice(0, 8);
  const otherSeconds = items.slice(8).reduce((s, item) => s + getValue(item), 0);
  const soleItem = items.length === 1 ? items[0] : null;

  let acc = 0;
  const stops: string[] = [];
  donutSlices.forEach((item, i) => {
    const pct = totalAll ? (getValue(item) / totalAll) * 100 : 0;
    stops.push(`${getColor(item, i)} ${acc}% ${acc + pct}%`);
    acc += pct;
  });
  if (otherSeconds > 0) {
    const pct = totalAll ? (otherSeconds / totalAll) * 100 : 0;
    stops.push(`${GRAY} ${acc}% ${acc + pct}%`);
    acc += pct;
  }
  const background = stops.length
    ? `conic-gradient(${stops.join(", ")})`
    : "rgba(255,255,255,.06)";

  return (
    <div className="games-layout">
      <div className="donut-wrap">
        <div className="donut" style={{ background }}>
          <div className="donut-center">
            <div className="val">{fmtHours(totalAll)}</div>
            <div className="lbl">{soleItem ? getLabel(soleItem) : centerLabel}</div>
          </div>
        </div>
        {periodLabel && <div className="donut-period">{periodLabel}</div>}
      </div>
      <div className="legend">
        {donutSlices.map((item, i) => {
          const value = getValue(item);
          const pct = totalAll ? Math.round((value / totalAll) * 1000) / 10 : 0;
          return (
            <div className="legend-row" key={getLabel(item)}>
              <div className="dot" style={{ background: getColor(item, i) }} />
              <div className="name">{getLabel(item)}</div>
              <div className="hrs mono">{fmtHours(value)}</div>
              <div className="pct mono">{pct}%</div>
            </div>
          );
        })}
        {otherSeconds > 0 && (
          <div className="legend-row">
            <div className="dot" style={{ background: GRAY }} />
            <div className="name">Inne</div>
            <div className="hrs mono">{fmtHours(otherSeconds)}</div>
            <div className="pct mono">
              {totalAll ? Math.round((otherSeconds / totalAll) * 1000) / 10 : 0}%
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
