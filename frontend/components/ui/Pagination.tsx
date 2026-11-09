"use client";
import { Icon } from "@/components/Icon";

type Props = {
  /** Page courante (1-based). */
  page: number;
  /** Nombre total d'éléments. */
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  /** Nom de l'élément pour l'info (« dossiers »). */
  noun?: string;
  className?: string;
};

/**
 * Barre de pagination : « 1-25 sur 120 » + boutons (précédent, pages, suivant).
 * Rien n'est rendu s'il n'y a qu'une page.
 */
export function Pagination({ page, total, pageSize, onPageChange, noun, className }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  const cur = Math.min(Math.max(1, page), pages);
  const start = (cur - 1) * pageSize + 1;
  const end = Math.min(total, cur * pageSize);
  const list = Array.from({ length: pages }, (_, k) => k + 1).filter((k) => k === 1 || k === pages || Math.abs(k - cur) <= 1);
  return (
    <div className={`sa-pagination-bar ${className ?? ""}`.trim()}>
      <span className="sa-pagination__info" aria-live="polite">
        {start}-{end} sur {total}
        {noun ? ` ${noun}` : ""}
      </span>
      <nav className="sa-pagination" aria-label="Pagination">
        <button type="button" className="sa-page-btn" disabled={cur === 1} aria-label="Page précédente" onClick={() => onPageChange(cur - 1)}>
          <Icon name="arrow-left-01" size={16} />
        </button>
        {list.map((k, j) => (
          <span key={k} style={{ display: "contents" }}>
            {j > 0 && k - list[j - 1] > 1 && <span className="sa-pagination__ellipsis">…</span>}
            <button type="button" className="sa-page-btn" aria-current={k === cur ? "page" : undefined} aria-label={`Page ${k}`} onClick={() => onPageChange(k)}>
              {k}
            </button>
          </span>
        ))}
        <button type="button" className="sa-page-btn" disabled={cur === pages} aria-label="Page suivante" onClick={() => onPageChange(cur + 1)}>
          <Icon name="arrow-right-01" size={16} />
        </button>
      </nav>
    </div>
  );
}
