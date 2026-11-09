import type { CSSProperties } from "react";
import { cx } from "./util";

type Props = {
  variant?: "text" | "title" | "sm" | "block" | "circle" | "btn";
  width?: number | string;
  height?: number | string;
  className?: string;
  style?: CSSProperties;
};

/** Bloc de chargement animé (désactivé si `prefers-reduced-motion`). */
export function Skeleton({ variant = "text", width, height, className, style }: Props) {
  return <div className={cx("sa-skeleton", `sa-skeleton--${variant}`, className)} style={{ width, height, ...style }} aria-hidden="true" />;
}

/** Squelette de carte-liste (titre + n lignes). */
export function SkeletonCard({ lines = 6 }: { lines?: number }) {
  return (
    <div className="sa-card" aria-busy="true" aria-label="Chargement en cours">
      <Skeleton variant="title" width="40%" />
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} />
      ))}
    </div>
  );
}

/** Squelette de rangée de KPI. */
export function SkeletonKpis({ count = 4 }: { count?: number }) {
  return (
    <div className="sa-grid sa-grid--kpi" aria-busy="true" aria-label="Chargement en cours">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="sa-kpi">
          <Skeleton variant="sm" width="50%" />
          <Skeleton variant="title" width="70%" />
          <Skeleton variant="sm" width="40%" />
        </div>
      ))}
    </div>
  );
}
