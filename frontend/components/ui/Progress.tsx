import { cx } from "./util";

type Tone = "default" | "ok" | "warn" | "danger" | "info";

type BarProps = {
  /** 0–100. */
  value: number;
  label?: string;
  tone?: Tone;
  size?: "sm" | "md";
  /** Affiche « 42 % » à droite du libellé. */
  showValue?: boolean;
  className?: string;
};

const clamp = (v: number) => Math.max(0, Math.min(100, v));

/** Barre de progression (`role=progressbar`). */
export function ProgressBar({ value, label, tone = "default", size = "md", showValue = true, className }: BarProps) {
  const v = clamp(value);
  return (
    <div className={cx("sa-progress-field", className)}>
      {(label || showValue) && (
        <div className="sa-progress__head">
          <span>{label}</span>
          {showValue && <span className="sa-progress__value">{Math.round(v)} %</span>}
        </div>
      )}
      <div
        className={cx("sa-progress", size === "sm" && "sa-progress--sm", tone !== "default" && `sa-progress--${tone}`)}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(v)}
        aria-label={label ?? "Progression"}
      >
        <span style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

type GaugeProps = {
  /** Valeur courante (même unité que `max` et `threshold`). */
  value: number;
  max?: number;
  /** Seuil contractuel : repère vertical. */
  threshold?: number;
  thresholdLabel?: string;
  label: string;
  /** Texte de valeur (« 92 % »). */
  display?: string;
  /** `higherIsBetter` : le vert est au-dessus du seuil (défaut), sinon en dessous. */
  higherIsBetter?: boolean;
  className?: string;
};

/** Jauge avec seuil (état vert/orange/rouge : couleur + texte, jamais la couleur seule). */
export function Gauge({ value, max = 100, threshold, thresholdLabel, label, display, higherIsBetter = true, className }: GaugeProps) {
  const pct = clamp((value / max) * 100);
  const tPct = threshold !== undefined ? clamp((threshold / max) * 100) : undefined;
  let tone: "ok" | "warn" | "danger" | undefined;
  let stateText = "";
  if (threshold !== undefined) {
    const good = higherIsBetter ? value >= threshold : value <= threshold;
    const near = higherIsBetter ? value >= threshold * 0.9 : value <= threshold * 1.1;
    tone = good ? "ok" : near ? "warn" : "danger";
    stateText = good ? "Objectif atteint" : near ? "À surveiller" : "Seuil non atteint";
  }
  return (
    <div className={cx("sa-gauge", className)} role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} aria-valuetext={`${display ?? value}${stateText ? ` — ${stateText}` : ""}`}>
      <div className="sa-gauge__track">
        <div className={cx("sa-gauge__fill", tone && `sa-gauge__fill--${tone}`)} style={{ width: `${pct}%` }} />
      </div>
      {tPct !== undefined && (
        <div className="sa-gauge__threshold" style={{ left: `${tPct}%` }}>
          <span>{thresholdLabel ?? `Seuil ${threshold}`}</span>
        </div>
      )}
      <div className="sa-gauge__scale">
        <span>{display ?? value}</span>
        {stateText && <span>{stateText}</span>}
      </div>
    </div>
  );
}
