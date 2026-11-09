"use client";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { Button } from "./Button";
import { DropdownMenu } from "./Popover";
import type { MenuItem } from "./Popover";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";
import { Skeleton } from "./Skeleton";
import { cx } from "./util";

/* ------------------------------ RowActions ------------------------------- */

type PrimaryAction = { label: string; icon?: string; onClick?: () => void; href?: string; disabled?: boolean };

/**
 * Actions d'une ligne : UNE action principale visible + menu « ⋯ ».
 *   <RowActions primary={{ label: "Ouvrir", icon: "view", href: `/dossiers/${id}` }}
 *               menu={[{ label: "Modifier", icon: "edit-02", onClick: edit }, { separator: true }, { label: "Supprimer", icon: "delete-02", danger: true, onClick: del }]} />
 */
export function RowActions({ primary, menu, menuLabel = "Autres actions" }: { primary?: PrimaryAction; menu?: MenuItem[]; menuLabel?: string }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 4, justifyContent: "flex-end" }}>
      {primary &&
        (primary.href && !primary.disabled ? (
          <Link href={primary.href} className="sa-btn sa-btn--outline sa-btn--sm">
            {primary.icon && <Icon name={primary.icon} />}
            {primary.label}
          </Link>
        ) : (
          <Button variant="outline" size="sm" icon={primary.icon} onClick={primary.onClick} disabled={primary.disabled}>
            {primary.label}
          </Button>
        ))}
      {menu && menu.length > 0 && <DropdownMenu items={menu} label={menuLabel} />}
    </div>
  );
}

/* ------------------------------- DataTable ------------------------------- */

export type Column<T> = {
  /** Clé unique de colonne (et clé de tri côté serveur). */
  key: string;
  header: string;
  /** Rendu de la cellule (défaut : `row[key]`). */
  render?: (row: T, index: number) => ReactNode;
  /** Valeur de tri / d'export (défaut : `row[key]`). */
  accessor?: (row: T) => string | number | boolean | null | undefined;
  sortable?: boolean;
  /** Colonne numérique : alignée à droite, chiffres tabulaires. */
  numeric?: boolean;
  /** Colonne étroite sans retour à la ligne (statuts, dates, actions). */
  tight?: boolean;
  /** Police mono (identifiants). */
  mono?: boolean;
  /** Masquer dans la vue « cartes » mobile. */
  hideOnMobile?: boolean;
  className?: string;
};

export type SortState = { key: string; dir: "asc" | "desc" } | null;

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string | number;
  /** Légende accessible (masquée visuellement). */
  caption: string;
  loading?: boolean;
  /** État vide personnalisé. */
  empty?: { icon?: string; title: string; description?: ReactNode; action?: ReactNode };
  /** Taille de page (défaut 25 ; 0 = pas de pagination). */
  pageSize?: number;
  /** Pagination pilotée par le serveur : fournir `page`, `total` et `onPageChange` (les lignes ne sont alors pas découpées). */
  page?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  /** Tri piloté par le serveur : fournir `sort` et `onSortChange`. Sinon tri local. */
  sort?: SortState;
  onSortChange?: (s: SortState) => void;
  defaultSort?: SortState;
  /** Clic sur une ligne (en plus des liens/boutons de la ligne). */
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string | undefined;
  /** Colonne d'actions finale : une action principale + menu ⋯. */
  actions?: (row: T) => { primary?: PrimaryAction; menu?: MenuItem[] };
  /** Hauteur max du conteneur : active le défilement vertical interne (en-têtes sticky). */
  maxHeight?: string | number;
  /** Cartes compactes sous 768 px (défaut true). */
  cards?: boolean;
  /** Noun pour la pagination (« dossiers »). */
  noun?: string;
  className?: string;
};

function cmp(a: unknown, b: unknown): number {
  if (a == null) return b == null ? 0 : 1;
  if (b == null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "fr", { numeric: true, sensitivity: "base" });
}

/**
 * Tableau de données du design system : en-têtes sticky, lignes alternées,
 * tri (local ou serveur), pagination, état vide/chargement, repli en cartes
 * sur mobile, colonne d'actions « 1 principale + ⋯ ». Pas de scroll horizontal :
 * prévoir ≤ 5-6 colonnes, des colonnes `tight` pour les badges/dates.
 *
 *   <DataTable caption="Dossiers" rows={rows} rowKey={(r) => r.id}
 *     columns={[{ key: "ref", header: "N°", mono: true, sortable: true }, { key: "statut", header: "Statut", tight: true, render: (r) => <StatusBadge status={r.statut} /> }]}
 *     actions={(r) => ({ primary: { label: "Ouvrir", href: `/dossiers/${r.id}` } })} />
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
  loading,
  empty = { title: "Aucun résultat", description: "Modifiez les filtres ou la recherche." },
  pageSize = 25,
  page: pageProp,
  total: totalProp,
  onPageChange,
  sort: sortProp,
  onSortChange,
  defaultSort = null,
  onRowClick,
  rowClassName,
  actions,
  maxHeight,
  cards = true,
  noun,
  className,
}: Props<T>) {
  const [sortLocal, setSortLocal] = useState<SortState>(defaultSort);
  const [pageLocal, setPageLocal] = useState(1);
  const serverSort = onSortChange !== undefined;
  const serverPage = onPageChange !== undefined;
  const sort = serverSort ? (sortProp ?? null) : sortLocal;

  const sorted = useMemo(() => {
    if (serverSort || !sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const get = col.accessor ?? ((r: T) => (r as Record<string, unknown>)[col.key] as never);
    const out = [...rows].sort((a, b) => cmp(get(a), get(b)));
    return sort.dir === "desc" ? out.reverse() : out;
  }, [rows, sort, columns, serverSort]);

  const total = serverPage ? (totalProp ?? rows.length) : sorted.length;
  const page = serverPage ? (pageProp ?? 1) : Math.min(pageLocal, Math.max(1, Math.ceil(total / (pageSize || 1))));
  const visible = serverPage || !pageSize ? sorted : sorted.slice((page - 1) * pageSize, page * pageSize);

  function toggleSort(key: string) {
    const next: SortState = sort?.key === key ? (sort.dir === "asc" ? { key, dir: "desc" } : null) : { key, dir: "asc" };
    if (serverSort) onSortChange?.(next);
    else setSortLocal(next);
    if (!serverPage) setPageLocal(1);
  }
  function changePage(p: number) {
    if (serverPage) onPageChange?.(p);
    else setPageLocal(p);
  }

  const colCount = columns.length + (actions ? 1 : 0);
  const wrapStyle = maxHeight ? { maxHeight, overflowY: "auto" as const } : undefined;

  if (loading) {
    return (
      <div className={className} aria-busy="true" aria-label="Chargement en cours">
        <div className="sa-table-wrap" style={wrapStyle}>
          <table className="sa-table">
            <caption className="sa-sr-only">{caption}</caption>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c.key} scope="col" className={cx(c.numeric && "is-num", c.tight && "is-tight")}>
                    {c.header}
                  </th>
                ))}
                {actions && <th scope="col" className="is-tight"><span className="sa-sr-only">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 5 }, (_, i) => (
                <tr key={i}>
                  {Array.from({ length: colCount }, (_, j) => (
                    <td key={j}>
                      <Skeleton width={j === 0 ? "70%" : "55%"} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (total === 0 && rows.length === 0) {
    return (
      <div className={className}>
        <EmptyState compact icon={empty.icon ?? "inbox"} title={empty.title} description={empty.description} action={empty.action} />
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="sa-table-wrap" style={wrapStyle}>
        <table className={cx("sa-table", cards && "sa-table--cards")}>
          <caption className="sa-sr-only">{caption}</caption>
          <thead>
            <tr>
              {columns.map((c) => {
                const active = sort?.key === c.key;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={c.sortable ? (active ? (sort!.dir === "asc" ? "ascending" : "descending") : "none") : undefined}
                    className={cx(c.numeric && "is-num", c.tight && "is-tight")}
                  >
                    {c.sortable ? (
                      <button type="button" onClick={() => toggleSort(c.key)}>
                        {c.header}
                        <Icon name={active ? (sort!.dir === "asc" ? "arrow-up-01" : "arrow-down-01") : "sorting-01"} size={12} />
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
              {actions && (
                <th scope="col" className="is-tight">
                  <span className="sa-sr-only">Actions</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, i) => {
              const a = actions?.(row);
              return (
                <tr
                  key={rowKey(row, i)}
                  className={rowClassName?.(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={onRowClick ? { cursor: "pointer" } : undefined}
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      data-label={c.header}
                      className={cx(c.numeric && "is-num", c.tight && "is-tight", c.mono && "sa-mono", c.className)}
                      data-hide-mobile={c.hideOnMobile || undefined}
                    >
                      {c.render ? c.render(row, i) : (((row as Record<string, unknown>)[c.key] as ReactNode) ?? "—")}
                    </td>
                  ))}
                  {actions && (
                    <td className="is-tight" data-label="Actions" onClick={(e) => e.stopPropagation()}>
                      {a && (a.primary || a.menu) ? <RowActions primary={a.primary} menu={a.menu} /> : null}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pageSize > 0 || serverPage ? <Pagination page={page} total={total} pageSize={pageSize || total || 1} onPageChange={changePage} noun={noun} /> : null}
    </div>
  );
}
