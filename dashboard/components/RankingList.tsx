import { fmtHours } from "@/lib/format";

interface RankingListProps<T> {
  items: T[];
  getLabel: (item: T) => string;
  getValue: (item: T) => number;
  getColor: (item: T, idx: number) => string;
  useAvatar?: boolean;
}

export default function RankingList<T>({
  items,
  getLabel,
  getValue,
  getColor,
  useAvatar = false,
}: RankingListProps<T>) {
  const max = Math.max(...items.map(getValue), 1);

  return (
    <div className="ranking-list">
      {items.map((item, i) => {
        const label = getLabel(item);
        const value = getValue(item);
        const color = getColor(item, i);
        return (
          <div className="rank-row" key={`${label}-${i}`}>
            <div className="rank-index mono">#{i + 1}</div>
            {useAvatar ? (
              <div className="avatar" style={{ background: color }}>
                {(label[0] || "?").toUpperCase()}
              </div>
            ) : (
              <div className="dot" style={{ background: color }} />
            )}
            <div className="rank-main">
              <div className="rank-top">
                <div className="rank-name">{label}</div>
                <div className="rank-value mono">{fmtHours(value)}</div>
              </div>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${(value / max) * 100}%`, background: color }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
