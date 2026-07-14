import type { GameTimeOut } from "@/lib/api";
import { colorFor, fmtHours, GRAY } from "@/lib/format";

export default function GamesDonut({ games }: { games: GameTimeOut[] }) {
  const totalAll = games.reduce((s, g) => s + g.total_seconds, 0);
  const donutSlices = games.slice(0, 8);
  const otherSeconds = games.slice(8).reduce((s, g) => s + g.total_seconds, 0);

  let acc = 0;
  const stops: string[] = [];
  donutSlices.forEach((g, i) => {
    const pct = totalAll ? (g.total_seconds / totalAll) * 100 : 0;
    stops.push(`${colorFor(g.activity_name, i)} ${acc}% ${acc + pct}%`);
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
            <div className="lbl">łącznie</div>
          </div>
        </div>
      </div>
      <div className="legend">
        {donutSlices.map((g, i) => {
          const pct = totalAll ? Math.round((g.total_seconds / totalAll) * 1000) / 10 : 0;
          return (
            <div className="legend-row" key={g.activity_name}>
              <div className="dot" style={{ background: colorFor(g.activity_name, i) }} />
              <div className="name">{g.activity_name}</div>
              <div className="hrs mono">{fmtHours(g.total_seconds)}</div>
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
