"use client";
import { useState } from "react";
import { Icon } from "@/components/Icon";
import { Drawer } from "@/components/ui/Drawer";
import type { AgentPerf, ChannelStat, Funnel, OcrQuality, RejectionReason } from "./_types";

const PREVIEW = 4;

/* ============================================================ */
/* Coque de widget                                               */
/* ============================================================ */
function CardShell({ title, subtitle, action, children, className = "" }: {
  title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={`sa-card ${className}`} aria-label={title} style={{ height: "100%" }}>
      <div className="flex items-start justify-between gap-3">
        <div style={{ minWidth: 0 }}>
          <h2 className="sa-card__title">{title}</h2>
          {subtitle && <p className="sa-card__subtitle" style={{ margin: 0 }}>{subtitle}</p>}
        </div>
        {action}
      </div>
      <div style={{ flex: 1 }}>{children}</div>
    </section>
  );
}

function MoreButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" className="sa-btn sa-btn--ghost sa-btn--sm" onClick={onClick} aria-label={label}>
      Afficher plus
      <Icon name="arrow-right-01" className="i" />
    </button>
  );
}

function EmptyMsg({ text }: { text: string }) {
  return <p className="sa-help" style={{ justifyContent: "center", padding: "var(--spacing-6) 0", margin: 0 }}>{text}</p>;
}

/** Barre de progression étiquetée (valeur + libellé toujours en texte). */
function Bar({ label, right, pct, color }: { label: string; right: React.ReactNode; pct: number; color?: string }) {
  return (
    <div className="sa-progress-field">
      <div className="sa-progress__head">
        <span>{label}</span>
        <span className="sa-text-soft">{right}</span>
      </div>
      <div className="sa-progress" role="img" aria-label={`${label} : ${Math.round(pct)} %`}>
        <span style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: color }} />
      </div>
    </div>
  );
}

/* ============================================================ */
/* Entonnoir                                                     */
/* ============================================================ */
export function FunnelCard({ funnel }: { funnel: Funnel }) {
  const steps = [
    { label: "Conversations démarrées", value: funnel.conversations_started, pct: 100, prev: null as number | null },
    { label: "Dossiers initiés", value: funnel.dossiers_created, pct: funnel.started_to_created_pct, prev: funnel.conversations_started },
    { label: "Soumis pour validation", value: funnel.dossiers_submitted, pct: funnel.created_to_submitted_pct, prev: funnel.dossiers_created },
    { label: "Validés", value: funnel.dossiers_validated, pct: funnel.submitted_to_validated_pct, prev: funnel.dossiers_submitted },
  ];
  return (
    <CardShell title="Entonnoir de conversion" subtitle="Du premier message à la validation">
      <div className="flex flex-col gap-3">
        {steps.map((s) => (
          <Bar
            key={s.label} label={s.label} pct={s.pct}
            color="rgb(var(--color-chart-1))"
            right={
              <>
                {s.value.toLocaleString("fr-FR")}
                {s.prev !== null && <span> ({s.pct} %)</span>}
              </>
            }
          />
        ))}
      </div>
      <div className="sa-row" style={{ justifyContent: "space-between", marginTop: "var(--spacing-4)", paddingTop: "var(--spacing-3)", borderTop: "1px solid rgb(var(--color-border-subtle))" }}>
        <span className="sa-text-soft">Taux de conversion global</span>
        <strong className="sa-strong">{funnel.overall_pct} %</strong>
      </div>
    </CardShell>
  );
}

/* ============================================================ */
/* Canaux                                                        */
/* ============================================================ */
export function ChannelsCard({ channels }: { channels: ChannelStat[] }) {
  const [open, setOpen] = useState(false);
  const rows = (list: ChannelStat[]) => (
    <div className="flex flex-col gap-3">
      {list.map((c) => (
        <Bar
          key={c.channel} label={c.channel.charAt(0).toUpperCase() + c.channel.slice(1)} pct={c.share_pct}
          color="rgb(var(--color-chart-1))"
          right={`${c.dossiers} dossiers · ${c.share_pct} %`}
        />
      ))}
    </div>
  );
  return (
    <CardShell
      title="Répartition par canal" subtitle="Dossiers par canal d'origine"
      action={channels.length > PREVIEW ? <MoreButton onClick={() => setOpen(true)} label="Afficher plus : répartition par canal" /> : undefined}
    >
      {channels.length === 0 ? <EmptyMsg text="Aucune donnée" /> : rows(channels.slice(0, PREVIEW))}
      <Drawer open={open} onClose={() => setOpen(false)} title="Répartition par canal">
        <div style={{ maxWidth: 720 }}>{rows(channels)}</div>
      </Drawer>
    </CardShell>
  );
}

/* ============================================================ */
/* Motifs de refus                                               */
/* ============================================================ */
export function ReasonsCard({ reasons }: { reasons: RejectionReason[] }) {
  const [open, setOpen] = useState(false);
  const list = (items: RejectionReason[]) => (
    <ol style={{ listStyle: "none", margin: 0, padding: 0 }} className="flex flex-col">
      {items.map((r, i) => (
        <li
          key={i}
          className="flex items-start justify-between gap-3"
          style={{ padding: "var(--spacing-2) 0", borderBottom: "1px solid rgb(var(--color-border-subtle))" }}
        >
          <span style={{ flex: 1, minWidth: 0, overflowWrap: "anywhere" }}>{r.motive}</span>
          <span className="sa-badge sa-badge--neutral sa-num">{r.count} · {r.share_pct} %</span>
        </li>
      ))}
    </ol>
  );
  return (
    <CardShell
      title="Top motifs de refus" subtitle="Motifs les plus fréquents"
      action={reasons.length > PREVIEW ? <MoreButton onClick={() => setOpen(true)} label="Afficher plus : motifs de refus" /> : undefined}
    >
      {reasons.length === 0 ? <EmptyMsg text="Aucun refus enregistré" /> : list(reasons.slice(0, PREVIEW))}
      <Drawer open={open} onClose={() => setOpen(false)} title="Top motifs de refus" subtitle={`${reasons.length} motifs`}>
        <div style={{ maxWidth: 720 }}>{list(reasons)}</div>
      </Drawer>
    </CardShell>
  );
}

/* ============================================================ */
/* Performance gestionnaires                                     */
/* ============================================================ */
export function AgentsCard({ agents }: { agents: AgentPerf[] }) {
  const [open, setOpen] = useState(false);
  const table = (items: AgentPerf[]) => (
    <div className="sa-table-wrap" style={{ overflowX: "visible" }}>
      <table className="sa-table">
        <caption className="sa-sr-only">Décisions par gestionnaire sur 90 jours</caption>
        <thead>
          <tr>
            <th scope="col">Gestionnaire</th>
            <th scope="col" className="is-num">Validés</th>
            <th scope="col" className="is-num">Refusés</th>
            <th scope="col" className="is-num">Total</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.agent_id}>
              <td className="sa-cell-main">{a.agent_name}</td>
              <td className="is-num">{a.validated}</td>
              <td className="is-num">{a.rejected}</td>
              <td className="is-num sa-strong">{a.total_decisions}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return (
    <CardShell
      title="Performance des gestionnaires" subtitle="Décisions sur 90 jours"
      action={agents.length > PREVIEW ? <MoreButton onClick={() => setOpen(true)} label="Afficher plus : performance des gestionnaires" /> : undefined}
    >
      {agents.length === 0 ? <EmptyMsg text="Pas encore de décisions" /> : table(agents.slice(0, PREVIEW))}
      <Drawer open={open} onClose={() => setOpen(false)} title="Performance des gestionnaires" subtitle="Décisions sur 90 jours">
        <div style={{ maxWidth: 840 }}>{table(agents)}</div>
      </Drawer>
    </CardShell>
  );
}

/* ============================================================ */
/* Qualité OCR                                                   */
/* ============================================================ */
export function OcrCard({ ocr }: { ocr: OcrQuality }) {
  if (ocr.total_pieces === 0) return null;
  const parts = [
    { label: "Haute (≥ 80 %)", pct: ocr.high_quality_pct, color: "rgb(var(--color-chart-1))", icon: "checkmark-circle-02" },
    { label: "Moyenne (50–80 %)", pct: ocr.medium_quality_pct, color: "rgb(var(--color-chart-4))", icon: "alert-circle" },
    { label: "Faible (< 50 %)", pct: ocr.low_quality_pct, color: "rgb(var(--color-chart-5))", icon: "cancel-circle" },
  ];
  return (
    <CardShell
      title="Qualité OCR"
      subtitle={`90 jours · ${ocr.total_pieces} pièces · score moyen ${ocr.average_confidence ? (ocr.average_confidence * 100).toFixed(1) + " %" : "—"}`}
    >
      <div
        role="img"
        aria-label={parts.map((p) => `${p.label} : ${p.pct} %`).join(", ")}
        style={{ display: "flex", height: 12, borderRadius: "var(--radius-full)", overflow: "hidden", background: "rgb(var(--color-bg-surface-hover))" }}
      >
        {parts.map((p) => (
          <div key={p.label} style={{ width: `${p.pct}%`, background: p.color }} title={`${p.label} : ${p.pct} %`} />
        ))}
      </div>
      <ul className="sa-row" style={{ listStyle: "none", margin: "var(--spacing-3) 0 0", padding: 0, gap: "var(--spacing-5)" }}>
        {parts.map((p) => (
          <li key={p.label} className="inline-flex items-center gap-2">
            <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 2, background: p.color }} />
            <Icon name={p.icon} className="i i-16" />
            <span>{p.label} · <strong className="sa-strong">{p.pct} %</strong></span>
          </li>
        ))}
      </ul>
    </CardShell>
  );
}

export { CardShell };
