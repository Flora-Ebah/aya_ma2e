"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";
import { EmptyState, PageHeader, Spinner } from "@/components/ui";

type AuditLog = {
  id: string;
  action: string;
  actor_type: string;
  actor_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  details: any;
  created_at: string;
};

/** Action = icône + texte (jamais la couleur seule). */
const ACTION_META: Record<string, { label: string; cls: string; icon: string }> = {
  dossier_created: { label: "Dossier créé", cls: "sa-badge--neutral", icon: "folder-01" },
  dossier_submitted: { label: "Dossier soumis", cls: "sa-badge--info", icon: "upload-02" },
  dossier_validated: { label: "Dossier validé", cls: "sa-badge--ok", icon: "checkmark-circle-02" },
  dossier_rejected: { label: "Dossier rejeté", cls: "sa-badge--error", icon: "cancel-circle" },
  dossier_complement_requested: { label: "Complément demandé", cls: "sa-badge--warn", icon: "alert-circle" },
  piece_uploaded: { label: "Pièce téléversée", cls: "sa-badge--accent", icon: "attachment-01" },
  piece_ocr_completed: { label: "OCR effectué", cls: "sa-badge--info", icon: "file-01" },
  piece_viewed: { label: "Pièce consultée", cls: "sa-badge--neutral", icon: "view" },
  consent_given: { label: "Consentement signé", cls: "sa-badge--ok", icon: "signature" },
  consent_refused: { label: "Consentement refusé", cls: "sa-badge--error", icon: "cancel-circle" },
  consent_revoked: { label: "Consentement révoqué", cls: "sa-badge--error", icon: "cancel-circle" },
};

const ACTOR_LABEL: Record<string, string> = {
  user: "Gestionnaire",
  end_user: "Sociétaire",
  system: "Système",
};

const PAGE_SIZES = [10, 20, 50, 100];

export default function AuditPage() {
  const toast = useToast();
  const [actionFilter, setActionFilter] = useState<string>("");
  const [actorFilter, setActorFilter] = useState<string>("");
  const [pageSize, setPageSize] = useState<number>(50);

  const { data: logs = [], loading, refetch } = useApi<AuditLog[]>(
    () => api.listAuditLogs(actionFilter || undefined, actorFilter || undefined),
  );
  const { data: stats } = useApi<any>(() => api.auditStats());

  async function applyFilter(next: { action?: string; actor?: string }) {
    if (next.action !== undefined) setActionFilter(next.action);
    if (next.actor !== undefined) setActorFilter(next.actor);
    // Le refetch est déclenché explicitement pour capturer les nouvelles valeurs
    try {
      await refetch();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  const displayed = pageSize === 0 ? (logs || []) : (logs || []).slice(0, pageSize);
  const totalStat = stats?.total ?? 0;

  return (
    <div>
      <PageHeader
        eyebrow="Conformité ARTCI"
        title="Journal d'audit"
        subtitle="Append-only · hash chaîné SHA-256 · conforme art. 31 loi 2013-450"
        actions={
          <span className="sa-badge sa-badge--brand" aria-label={`Total des événements : ${totalStat}`}>
            <Icon name="check-list" className="i" />
            Total événements : <span className="sa-num">{totalStat}</span>
          </span>
        }
      />
      <section className="sa-card sa-card--flush" aria-label="Journal d'audit">
        <FilterBar
          actionFilter={actionFilter}
          actorFilter={actorFilter}
          pageSize={pageSize}
          totalLogs={(logs || []).length}
          displayedCount={displayed.length}
          onActionChange={(v) => applyFilter({ action: v })}
          onActorChange={(v) => applyFilter({ actor: v })}
          onPageSizeChange={setPageSize}
        />
        <LogTable logs={displayed} loading={loading} />
      </section>
      <p className="sa-help" style={{ justifyContent: "center", marginTop: 16, textAlign: "center" }}>
        API limitée aux 100 derniers événements — utilisez le bouton « Exporter CSV »
        pour récupérer l&apos;intégralité du journal filtré.
      </p>
    </div>
  );
}

/** Filtres sur UNE ligne : action, acteur, taille de page, compteur, export. */
function FilterBar(props: {
  actionFilter: string;
  actorFilter: string;
  pageSize: number;
  totalLogs: number;
  displayedCount: number;
  onActionChange: (v: string) => void;
  onActorChange: (v: string) => void;
  onPageSizeChange: (v: number) => void;
}) {
  return (
    <div className="sa-toolbar" style={{ flexWrap: "nowrap", alignItems: "center" }} role="search">
      <select
        className="sa-select" style={{ flex: "1 1 200px", minWidth: 0 }}
        value={props.actionFilter} onChange={(e) => props.onActionChange(e.target.value)}
        aria-label="Filtrer par action"
      >
        <option value="">Toutes les actions</option>
        {Object.keys(ACTION_META).map((k) => (
          <option key={k} value={k}>{ACTION_META[k].label}</option>
        ))}
      </select>
      <select
        className="sa-select" style={{ flex: "1 1 170px", minWidth: 0 }}
        value={props.actorFilter} onChange={(e) => props.onActorChange(e.target.value)}
        aria-label="Filtrer par acteur"
      >
        <option value="">Tous les acteurs</option>
        <option value="user">Gestionnaires</option>
        <option value="end_user">Sociétaires</option>
        <option value="system">Système</option>
      </select>
      <select
        className="sa-select" style={{ flex: "0 1 150px", minWidth: 0 }}
        value={props.pageSize} onChange={(e) => props.onPageSizeChange(Number(e.target.value))}
        aria-label="Nombre de lignes affichées"
      >
        {PAGE_SIZES.map((n) => (
          <option key={n} value={n} disabled={n > props.totalLogs && props.totalLogs > 0}>
            {n} lignes
          </option>
        ))}
        <option value={0}>Tout ({props.totalLogs})</option>
      </select>
      <span className="sa-micro sa-text-soft" style={{ flex: "none", whiteSpace: "nowrap" }} aria-live="polite">
        {props.displayedCount} / {props.totalLogs}
      </span>
      <button
        type="button"
        className="sa-btn sa-btn--outline"
        style={{ flex: "none" }}
        onClick={() => { window.location.href = api.exportAuditUrl({
          action: props.actionFilter || undefined,
          actor_type: props.actorFilter || undefined,
        }); }}
      >
        <Icon name="download-02" className="i" />
        <span className="hidden sm:inline">Exporter CSV</span>
      </button>
    </div>
  );
}

function LogTable({ logs, loading }: { logs: AuditLog[]; loading: boolean }) {
  if (loading) {
    return <div className="py-14 text-center"><Spinner /></div>;
  }
  if (logs.length === 0) {
    return (
      <EmptyState
        title="Aucun événement"
        description="Aucun événement ne correspond aux filtres sélectionnés."
      />
    );
  }
  return (
    <div className="sa-table-wrap">
      <table className="sa-table sa-table--compact sa-table--cards">
        <thead>
          <tr>
            <th scope="col">Action</th>
            <th scope="col">Acteur</th>
            <th scope="col">Ressource</th>
            <th scope="col">Détails</th>
            <th scope="col">Date</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => <LogRow key={log.id} log={log} />)}
        </tbody>
      </table>
    </div>
  );
}

function LogRow({ log }: { log: AuditLog }) {
  const meta = ACTION_META[log.action] || { label: log.action, cls: "sa-badge--neutral", icon: "file-01" };
  const detailsStr = Object.keys(log.details || {}).length > 0
    ? Object.entries(log.details).slice(0, 3).map(([k, v]: any) => `${k}=${String(v).slice(0, 30)}`).join(" · ")
    : "—";
  return (
    <tr>
      <td data-label="Action">
        <span className={`sa-badge ${meta.cls}`}>
          <Icon name={meta.icon} className="i" />
          {meta.label}
        </span>
      </td>
      <td data-label="Acteur">{ACTOR_LABEL[log.actor_type] || log.actor_type}</td>
      <td data-label="Ressource" className="sa-mono">
        {log.resource_type && log.resource_id ? (
          <>
            <span className="sa-text-soft">{log.resource_type}</span>
            {" : "}
            {log.resource_id.slice(0, 8)}…
          </>
        ) : "—"}
      </td>
      <td data-label="Détails" className="sa-mono sa-text-soft" style={{ fontSize: 12 }}>
        {detailsStr}
      </td>
      <td data-label="Date" className="sa-text-soft" style={{ whiteSpace: "nowrap" }}>
        {new Date(log.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "medium" })}
      </td>
    </tr>
  );
}
