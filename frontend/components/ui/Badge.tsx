import type { ReactNode } from "react";
import { Icon } from "@/components/Icon";
import { cx } from "./util";

export type BadgeTone = "neutral" | "success" | "info" | "warning" | "danger" | "accent" | "brand";

const TONE_CLASS: Record<BadgeTone, string> = {
  neutral: "sa-badge--neutral",
  success: "sa-badge--ok",
  info: "sa-badge--info",
  warning: "sa-badge--warn",
  danger: "sa-badge--error",
  accent: "sa-badge--accent",
  brand: "sa-badge--brand",
};

const TONE_ICON: Record<BadgeTone, string | null> = {
  neutral: null,
  success: "checkmark-circle-02",
  info: "information-circle",
  warning: "alert-02",
  danger: "alert-circle",
  accent: null,
  brand: null,
};

type Props = {
  /** Tonalité sémantique. Défaut : neutral. */
  tone?: BadgeTone;
  /** Nom d'icône du sprite ; par défaut une icône selon la tonalité (jamais la couleur seule). `false` = aucune. */
  icon?: string | false;
  /** `outline` (défaut) ou `solid` (fond plein). */
  variant?: "outline" | "solid";
  children: ReactNode;
  className?: string;
};

/**
 * Badge : MAJUSCULES, `nowrap`, jamais coupé. Icône + texte.
 *   <Badge tone="success">Actif</Badge>
 *   <Badge tone="danger" icon="cancel-circle">Bloqué</Badge>
 */
export function Badge({ tone = "neutral", icon, variant = "outline", children, className }: Props) {
  const ic = icon === false ? null : (icon ?? TONE_ICON[tone]);
  return (
    <span className={cx("sa-badge", variant === "outline" ? "sa-badge--outline" : "sa-badge--solid", TONE_CLASS[tone], className)}>
      {ic && <Icon name={ic} />}
      {children}
    </span>
  );
}

/* ------------------------------ StatusBadge ------------------------------ */

type StatusDef = { tone: BadgeTone; icon: string; label: string };

/** Statuts connus (dossiers MA2E + statuts génériques du design system). */
export const STATUS_MAP: Record<string, StatusDef> = {
  // Dossiers MA2E
  en_cours: { tone: "neutral", icon: "clock-01", label: "En cours" },
  soumis: { tone: "brand", icon: "inbox", label: "Soumis" },
  en_validation: { tone: "warning", icon: "hourglass", label: "En validation" },
  valide: { tone: "success", icon: "checkmark-circle-02", label: "Validé" },
  rejete: { tone: "danger", icon: "cancel-circle", label: "Rejeté" },
  complement_requis: { tone: "accent", icon: "alert-02", label: "Complément" },
  // Génériques
  nouveau: { tone: "brand", icon: "inbox", label: "Nouveau" },
  affecte: { tone: "info", icon: "user-check-01", label: "Affecté" },
  resolu: { tone: "success", icon: "checkmark-circle-02", label: "Résolu" },
  cloture: { tone: "success", icon: "checkmark-circle-02", label: "Clôturé" },
  annule: { tone: "neutral", icon: "cancel-circle", label: "Annulé" },
  brouillon: { tone: "neutral", icon: "edit-02", label: "Brouillon" },
  ok: { tone: "success", icon: "checkmark-circle-02", label: "Réussi" },
  partiel: { tone: "warning", icon: "alert-02", label: "Partiel" },
  erreur: { tone: "danger", icon: "alert-circle", label: "Erreur" },
  echec: { tone: "danger", icon: "cancel-circle", label: "Échec" },
  actif: { tone: "success", icon: "checkmark-circle-02", label: "Actif" },
  inactif: { tone: "neutral", icon: "pause-circle", label: "Désactivé" },
  en_attente: { tone: "warning", icon: "hourglass", label: "En attente" },
  a_traiter: { tone: "warning", icon: "hourglass", label: "À traiter" },
  traite: { tone: "success", icon: "checkmark-circle-02", label: "Traité" },
  envoye: { tone: "info", icon: "tick-02", label: "Envoyé" },
  lu: { tone: "success", icon: "view", label: "Lu" },
};

/**
 * Badge de statut (icône + texte). Clés connues : voir `STATUS_MAP`.
 * Une clé inconnue s'affiche en neutre avec la clé comme libellé.
 *   <StatusBadge status="valide" />   <StatusBadge status="custom" label="Spécial" tone="info" />
 */
export function StatusBadge({ status, label, tone, icon, className }: { status: string; label?: string; tone?: BadgeTone; icon?: string; className?: string }) {
  const def = STATUS_MAP[status] ?? { tone: "neutral" as BadgeTone, icon: "information-circle", label: status };
  return (
    <Badge tone={tone ?? def.tone} icon={icon ?? def.icon} className={className}>
      {label ?? def.label}
    </Badge>
  );
}

/* ----------------------------- PriorityBadge ----------------------------- */

export type Priority = "p1" | "p2" | "p3" | "p4";
const PRIO_LABEL: Record<Priority, string> = { p1: "Critique", p2: "Haute", p3: "Normale", p4: "Basse" };
const PRIO_ALIAS: Record<string, Priority> = { critique: "p1", urgent: "p1", haute: "p2", high: "p2", normale: "p3", normal: "p3", moyenne: "p3", basse: "p4", low: "p4" };

/** Priorité : drapeau + libellé. Accepte `p1`…`p4` ou critique/haute/normale/basse. */
export function PriorityBadge({ priority, label, className }: { priority: Priority | string; label?: string; className?: string }) {
  const p = (PRIO_ALIAS[priority] ?? (priority as Priority)) as Priority;
  const level: Priority = PRIO_LABEL[p] ? p : "p3";
  return (
    <span className={cx("sa-prio", `sa-prio--${level}`, className)}>
      <Icon name={level === "p1" ? "fire" : level === "p2" ? "arrow-up-double" : "flag-01"} />
      {label ?? PRIO_LABEL[level]}
    </span>
  );
}

/* ----------------------------- DeadlineBadge ----------------------------- */

export type DeadlineState = "ok" | "watch" | "risk" | "late" | "paused" | "done-ok" | "done-late";
const DL: Record<DeadlineState, { icon: string; label: string }> = {
  ok: { icon: "clock-01", label: "Dans les temps" },
  watch: { icon: "timer-01", label: "À surveiller" },
  risk: { icon: "alarm-clock", label: "Échéance proche" },
  late: { icon: "alert-02", label: "En retard" },
  paused: { icon: "pause-circle", label: "En pause" },
  "done-ok": { icon: "checkmark-circle-02", label: "Respecté" },
  "done-late": { icon: "alert-02", label: "Hors délai" },
};

/** Calcule l'état d'un délai à partir d'une échéance (ISO) : retard, < 24 h, < 3 j, sinon ok. */
export function deadlineFromDate(due: string | Date, now: Date = new Date()): { state: DeadlineState; time: string } {
  const d = typeof due === "string" ? new Date(due) : due;
  const ms = d.getTime() - now.getTime();
  const abs = Math.abs(ms);
  const h = Math.floor(abs / 3_600_000);
  const days = Math.floor(h / 24);
  const time = days >= 1 ? `${days} j` : `${Math.max(h, 0)} h`;
  if (ms < 0) return { state: "late", time: `+${time}` };
  if (ms < 24 * 3_600_000) return { state: "risk", time };
  if (ms < 3 * 24 * 3_600_000) return { state: "watch", time };
  return { state: "ok", time };
}

/**
 * Délai : icône + état + temps restant (jamais la couleur seule).
 *   <DeadlineBadge due={dossier.echeance} />   <DeadlineBadge state="late" time="+2 j" />
 */
export function DeadlineBadge({ due, state, time, size, className }: { due?: string | Date | null; state?: DeadlineState; time?: string; size?: "sm" | "md"; className?: string }) {
  let s = state;
  let t = time;
  if (!s && due) {
    const r = deadlineFromDate(due);
    s = r.state;
    t = t ?? r.time;
  }
  if (!s) s = "paused";
  const def = DL[s];
  return (
    <span className={cx("sa-sla", `sa-sla--${s}`, size === "sm" && "sa-sla--sm", className)}>
      <Icon name={def.icon} />
      <span className="sa-sla__state">{def.label}</span>
      {t && (
        <>
          <span className="sa-sla__sep" aria-hidden="true">·</span>
          <span className="sa-sla__time">{t}</span>
        </>
      )}
    </span>
  );
}
