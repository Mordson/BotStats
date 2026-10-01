import Donut from "./Donut";
import RankingList from "./RankingList";

interface DonutRankingProps<T> {
  /** All items, sorted descending - the donut always shows the full breakdown. */
  items: T[];
  /** Items for the ranking under the donut; defaults to `items`. */
  rankingItems?: T[];
  rankingTitle: string;
  periodLabel: string;
  getLabel: (item: T) => string;
  getValue: (item: T) => number;
  getColor: (item: T, index: number) => string;
  getSubtitle?: (item: T) => string | undefined;
  useAvatar?: boolean;
}

/** The "donut + ranking list" pair shared by the dashboard's time-breakdown panels. */
export default function DonutRanking<T>({
  items,
  rankingItems = items,
  rankingTitle,
  periodLabel,
  getLabel,
  getValue,
  getColor,
  getSubtitle,
  useAvatar,
}: DonutRankingProps<T>) {
  return (
    <>
      <Donut
        items={items}
        getLabel={getLabel}
        getValue={getValue}
        getColor={getColor}
        centerLabel="łącznie"
        periodLabel={periodLabel}
      />
      <div className="games-list-title">{rankingTitle}</div>
      <RankingList
        items={rankingItems}
        getLabel={getLabel}
        getValue={getValue}
        getColor={getColor}
        getSubtitle={getSubtitle}
        useAvatar={useAvatar}
      />
    </>
  );
}
