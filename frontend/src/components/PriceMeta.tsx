import { formatDate } from "../lib/format";

type Priced = {
  id: string;
  /** Display name; falls back to the id. */
  name?: string;
  effective_date: string;
  valid_until?: string | null;
  stale: boolean;
  notes?: string | null;
};

/** Warnings a reader must see before trusting a figure: stale prices, notes. */
export function PriceNotices({ items }: { items: Priced[] }) {
  const stale = items.filter((i) => i.stale);
  const notes = items.filter((i) => i.notes);
  if (stale.length === 0 && notes.length === 0) return null;

  return (
    <div className="notices">
      {stale.length > 0 && (
        <p className="notice notice-warning" role="status">
          <span aria-hidden="true">⚠</span>{" "}
          <strong>Prices may be out of date</strong> for{" "}
          {stale.map((i) => i.name ?? i.id).join(", ")}. Check the provider's
          pricing page.
        </p>
      )}
      {notes.map((i) => (
        <p key={i.id} className="notice">
          <span aria-hidden="true">ⓘ</span> <strong>{i.name ?? i.id}:</strong>{" "}
          {i.notes}
        </p>
      ))}
    </div>
  );
}

export function CheckedDate({ item }: { item: Priced }) {
  return (
    <>
      {formatDate(item.effective_date)}
      {item.valid_until && (
        <span className="muted"> · until {formatDate(item.valid_until)}</span>
      )}
      {item.stale && <span className="badge badge-warning">Out of date</span>}
    </>
  );
}
