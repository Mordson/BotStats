interface PanelBodyProps {
  loading: boolean;
  isEmpty: boolean;
  emptyText: React.ReactNode;
  children: React.ReactNode;
}

/** A panel's content, or its loading / empty placeholder. */
export default function PanelBody({ loading, isEmpty, emptyText, children }: PanelBodyProps) {
  if (loading) return <div className="loading-state">Ładowanie…</div>;
  if (isEmpty) return <div className="empty-state">{emptyText}</div>;
  return <>{children}</>;
}
