import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

type GridProps = {
  /**
   * - `cards2` : 2 cartes par ligne (1 en mobile), même hauteur, jamais d'orpheline.
   * - `stats3` : petits groupes de 3 stats par ligne (répartition équilibrée pour 1 à 8 éléments).
   * - `kpi`    : tuiles KPI, 2 par ligne (1 en mobile).
   */
  variant?: "cards2" | "stats3" | "kpi";
  children: ReactNode;
  className?: string;
};

/**
 * Grille de cartes à hauteur égale. La dernière carte impaire occupe toute la
 * ligne (pas de carte orpheline seule).
 *
 *   <Grid variant="stats3"><KpiCard … /><KpiCard … /><KpiCard … /></Grid>
 *   <Grid variant="cards2"><Card …/><Card …/></Grid>
 */
export function Grid({ variant = "cards2", children, className }: GridProps) {
  const cls = variant === "stats3" ? "sa-grid--stats-3" : variant === "kpi" ? "sa-grid--kpi" : "sa-grid--2";
  return <div className={cx("sa-grid", cls, className)}>{children}</div>;
}

type KpiProps = {
  label: string;
  /** Valeur affichée en Sora (nombre ou texte formaté). */
  value: ReactNode;
  /** Unité accolée à la valeur (« j », « % »…). */
  unit?: string;
  /** Nom d'icône du sprite pour la tuile. */
  icon?: string;
  iconTone?: "neutre" | "marque" | "brand" | "accent" | "ok" | "warn" | "error" | "info";
  /** Variation : delta numérique (+/−) ou texte libre. */
  trend?: { delta: number; /** vrai si une hausse est une bonne nouvelle (défaut) */ goodWhenUp?: boolean; format?: (v: number) => string } | null;
  /** Ligne d'info sous la valeur (période, comparaison). */
  meta?: ReactNode;
  valueTone?: "default" | "brand" | "danger";
  href?: string;
  /** Rend la carte cliquable (bouton) — ex. filtre de liste. */
  onClick?: () => void;
  /** État « filtre actif » (aria-pressed + contour de marque). */
  active?: boolean;
  className?: string;
};

/**
 * Tuile KPI : libellé, tuile d'icône, valeur Sora, tendance (icône + texte).
 *   <KpiCard label="Dossiers validés" value={128} icon="checkmark-circle-02" iconTone="ok" trend={{ delta: 12 }} meta="vs. mois dernier" />
 */
export function KpiCard({ label, value, unit, icon = "dashboard-speed-01", iconTone = "brand", trend, meta, valueTone = "default", href, onClick, active, className }: KpiProps) {
  const Tag = href ? "a" : onClick ? "button" : "article";
  const tile = iconTone === "brand" || iconTone === "marque" ? "" : `sa-icon-tile--${iconTone}`;
  return (
    <Tag
      {...(href ? { href } : {})}
      {...(onClick ? { type: "button", onClick, "aria-pressed": !!active } : {})}
      className={cx("sa-kpi", onClick && "sa-kpi--click", active && "sa-kpi--active", className)}
    >
      <div className="sa-kpi__top">
        <span className="sa-kpi__label">{label}</span>
        <span className={cx("sa-icon-tile", tile)}>
          <Icon name={icon} />
        </span>
      </div>
      <div className={cx("sa-kpi__value", valueTone === "brand" && "sa-kpi__value--brand", valueTone === "danger" && "sa-kpi__value--danger")}>
        {value}
        {unit && <small>{unit}</small>}
      </div>
      {(trend || meta) && (
        <div className="sa-kpi__meta">
          {trend && <Trend {...trend} />}
          {meta}
        </div>
      )}
    </Tag>
  );
}

/** Tendance : flèche + valeur signée (jamais la couleur seule). */
export function Trend({ delta, goodWhenUp = true, format }: { delta: number; goodWhenUp?: boolean; format?: (v: number) => string }) {
  if (!delta) {
    return (
      <span className="sa-trend sa-trend--neutral">
        <Icon name="minus-sign" size={12} />
        stable
      </span>
    );
  }
  const good = goodWhenUp ? delta > 0 : delta < 0;
  const f = format ?? ((v: number) => String(v));
  return (
    <span className={cx("sa-trend", good ? "sa-trend--good" : "sa-trend--bad")}>
      <Icon name={delta > 0 ? "chart-increase" : "chart-decrease"} size={12} />
      {delta > 0 ? "+" : "−"}
      {f(Math.abs(delta))}
    </span>
  );
}
