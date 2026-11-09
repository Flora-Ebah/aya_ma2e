"use client";
import { Icon } from "@/components/Icon";

type Props = {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
};

/** Pagination de la liste (pages numérotées avec ellipses + compteur). */
export default function ListPagination({ page, pageSize, total, onPageChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);

  const items: (number | "…")[] = [];
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - page) <= 1) items.push(p);
    else if (items[items.length - 1] !== "…") items.push("…");
  }

  return (
    <nav className="sa-pagination-bar" aria-label="Pagination" style={{ padding: "var(--spacing-4) var(--spacing-5)", borderTop: "1px solid rgb(var(--color-border-subtle))" }}>
      <span className="sa-pagination__info">{from}–{to} sur {total}</span>
      <div className="sa-pagination">
        <button
          type="button" className="sa-page-btn" disabled={page <= 1}
          onClick={() => onPageChange(page - 1)} aria-label="Page précédente"
        >
          <Icon name="arrow-left-01" className="i" />
        </button>
        {items.map((it, i) =>
          it === "…" ? (
            <span key={`e${i}`} className="sa-pagination__ellipsis" aria-hidden="true">…</span>
          ) : (
            <button
              key={it} type="button" className="sa-page-btn"
              aria-current={it === page ? "page" : undefined}
              aria-label={`Page ${it}`}
              onClick={() => onPageChange(it)}
            >
              {it}
            </button>
          ),
        )}
        <button
          type="button" className="sa-page-btn" disabled={page >= pages}
          onClick={() => onPageChange(page + 1)} aria-label="Page suivante"
        >
          <Icon name="arrow-right-01" className="i" />
        </button>
      </div>
    </nav>
  );
}
