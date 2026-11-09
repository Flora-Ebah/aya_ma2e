"use client";
import type { ReactNode } from "react";
import { cx } from "./util";

type ChipProps = {
  children: ReactNode;
  /** État pressé (filtre actif). */
  pressed?: boolean;
  count?: number | string;
  onClick?: () => void;
  disabled?: boolean;
};

/** Puce-filtre (`aria-pressed`). */
export function Chip({ children, pressed = false, count, onClick, disabled }: ChipProps) {
  return (
    <button type="button" className="sa-chip" aria-pressed={pressed} onClick={onClick} disabled={disabled}>
      {children}
      {count !== undefined && <span className="sa-chip__count">{count}</span>}
    </button>
  );
}

type ChipGroupProps<T extends string> = {
  options: Array<{ id: T; label: string; count?: number | string }>;
  value: T;
  onChange: (v: T) => void;
  label?: string;
};

/** Groupe de puces à choix unique. */
export function ChipGroup<T extends string>({ options, value, onChange, label = "Filtres" }: ChipGroupProps<T>) {
  return (
    <div className="sa-chips" role="group" aria-label={label}>
      {options.map((o) => (
        <Chip key={o.id} pressed={o.id === value} count={o.count} onClick={() => onChange(o.id)}>
          {o.label}
        </Chip>
      ))}
    </div>
  );
}

/**
 * Barre de filtres sur UNE ligne alignée (recherche + sélecteurs + actions).
 * `end` se place à droite (export, réinitialiser). Replie proprement en mobile.
 *
 *   <FilterBar end={<Button variant="outline" size="sm">Exporter</Button>}>
 *     <SearchInput … /><Select …/><ChipGroup … />
 *   </FilterBar>
 */
export function FilterBar({ children, end, className }: { children: ReactNode; end?: ReactNode; className?: string }) {
  return (
    <div className={cx("sa-toolbar", "sa-filterbar", className)} role="search">
      {children}
      {end && (
        <>
          <span className="sa-toolbar__spacer" />
          {end}
        </>
      )}
    </div>
  );
}
