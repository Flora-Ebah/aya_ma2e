import { Icon } from "@/components/Icon";
import { Grid, KpiCard } from "@/components/ui";
import type { KPIDelta, Overview } from "./_types";

type Props = { overview: Overview };

export default function KpiSection({ overview }: Props) {
  return (
    <>
      <AlertsBanner alerts={overview.alerts ?? []} />

      <section aria-label="Indicateurs clés"><Grid variant="stats3">
        <Kpi
          label="Total dossiers" value={overview.total_dossiers.toLocaleString("fr-FR")}
          hint={`+${overview.total_period} sur ${overview.period_days} j`}
          icon="folder-01" delta={overview.deltas?.total_period}
        />
        <Kpi
          label="Taux de validation" value={formatPct(overview.validation_rate)}
          hint={`${overview.validated} validés · ${overview.rejected} refusés`}
          icon="checkmark-circle-02" tone="ok" delta={overview.deltas?.validation_rate}
        />
        <Kpi
          label="Temps moyen de validation"
          value={overview.avg_validation_hours ? `${overview.avg_validation_hours} h` : "—"}
          hint="De la soumission à la décision" icon="clock-01" tone="info"
        />
        <Kpi
          label="Auto-complétion" value={formatPct(overview.auto_complete_rate)}
          hint="Validés sans complément demandé" icon="user-check-01"
        />
        <Kpi label="En cours" value={overview.in_progress} hint="Pas encore soumis" icon="hourglass" tone="warn" />
        <Kpi label="À traiter" value={overview.submitted} hint="Soumis + en validation" icon="alert-circle" tone="error" />
        <Kpi
          label="Conversations" value={overview.total_conversations.toLocaleString("fr-FR")}
          hint={`Sur ${overview.period_days} j`} icon="message-01" tone="info"
        />
        <Kpi
          label="Messages échangés" value={overview.total_messages.toLocaleString("fr-FR")}
          hint={`Sur ${overview.period_days} j`} icon="comment-01"
        />
      </Grid></section>
    </>
  );
}

function AlertsBanner({ alerts }: { alerts: NonNullable<Overview["alerts"]> }) {
  if (alerts.length === 0) return null;
  return (
    <div className="flex flex-col gap-2" style={{ marginBottom: "var(--spacing-4)" }}>
      {alerts.map((a, i) => (
        <div
          key={i}
          role="alert"
          className={`sa-alert sa-alert--compact ${a.severity === "danger" ? "sa-alert--error" : "sa-alert--warning"}`}
        >
          <Icon name={a.severity === "danger" ? "alert-02" : "alert-circle"} className="i" />
          <div className="sa-alert__body">
            <p className="sa-alert__text" style={{ margin: 0 }}>
              <strong>{a.severity === "danger" ? "Critique" : "Alerte"}</strong> · KPI{" "}
              <code className="sa-mono">{a.kpi}</code> = <strong>{a.value}</strong> {a.op} seuil {a.threshold}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function formatPct(rate: number): string {
  return `${(rate * 100).toFixed(1)} %`;
}

function Kpi({ label, value, hint, icon, delta, tone }: {
  label: string;
  value: number | string;
  hint: string;
  icon: string;
  delta?: KPIDelta | null;
  tone?: "neutre" | "marque" | "ok" | "warn" | "error" | "info";
}) {
  // US-26 AC2 — variation par rapport à la période précédente
  const pct = delta?.delta_pct;
  const showDelta = pct !== null && pct !== undefined;
  return (
    <KpiCard
      label={label}
      value={value}
      icon={icon}
      iconTone={tone ?? "marque"}
      meta={hint}
      trend={showDelta ? { delta: pct as number, format: (v) => `${v} %` } : null}
    />
  );
}
