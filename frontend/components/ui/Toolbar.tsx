import type { ReactNode } from "react";
import { cx } from "./util";

type Props = {
  left?: ReactNode;
  right?: ReactNode;
  className?: string;
};

/**
 * Barre d'outils de liste (gauche / droite) en tête d'une carte-tableau.
 * Pour une barre de filtres, préférer `FilterBar`.
 */
export function Toolbar({ left, right, className }: Props) {
  return (
    <div className={cx("sa-toolbar", className)}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>{left}</div>
      <span className="sa-toolbar__spacer" />
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>{right}</div>
    </div>
  );
}
