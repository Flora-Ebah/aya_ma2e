"use client";
import { useState } from "react";
import { Icon } from "@/components/Icon";
import ListPagination from "../_ListPagination";
import { AUDIT_LABELS, fmtDateTime } from "./_constants";
import { SectionBlock } from "./_SectionBlock";

const PAGE_SIZE = 6;

type Props = { logs: any[] };

/** Historique & audit en timeline (`sa-timeline`), paginé. */
export default function AuditSection({ logs }: Props) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(logs.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const pageLogs = logs.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <SectionBlock
      id="audit"
      title="Historique & journal d'audit"
      subtitle="PRD §10.3 · append-only avec hash chaîné SHA-256"
    >
      {logs.length === 0 ? (
        <p className="sa-help" style={{ margin: 0 }}>Aucune entrée d&apos;audit pour ce dossier.</p>
      ) : (
        <ol className="sa-timeline">
          {pageLogs.map((log) => <AuditItem key={log.id} log={log} />)}
        </ol>
      )}

      <div style={{ margin: "0 calc(var(--spacing-5) * -1)" }}>
        <ListPagination page={safePage} pageSize={PAGE_SIZE} total={logs.length} onPageChange={setPage} />
      </div>

      <div className="sa-alert sa-alert--brand">
        <Icon name="shield-user" className="i" />
        <div className="sa-alert__body">
          <span className="sa-alert__title">Conformité ARTCI</span>
          <p className="sa-alert__text" style={{ margin: 0 }}>
            Consentements et événements signés <span className="sa-mono">HMAC-SHA256</span>, horodatés UTC,
            inscrits dans le journal d&apos;audit append-only avec hash chaîné SHA-256.
          </p>
        </div>
      </div>
    </SectionBlock>
  );
}

function AuditItem({ log }: { log: any }) {
  const meta = AUDIT_LABELS[log.action] || { label: log.action, icon: "file-01", dot: "" };
  const actor =
    log.actor_type === "end_user" ? "Sociétaire"
    : log.actor_type === "user" ? "Gestionnaire"
    : "Système";
  return (
    <li className="sa-timeline__item">
      <span className={`sa-timeline__dot ${meta.dot ? `sa-timeline__dot--${meta.dot}` : ""}`} aria-hidden="true">
        <Icon name={meta.icon} className="i" />
      </span>
      <div className="sa-timeline__content">
        <div className="sa-timeline__text sa-strong">{meta.label}</div>
        <div className="sa-timeline__meta">
          <span>{actor}</span>
          {log.details?.field && <span>champ {log.details.field}</span>}
          {log.details?.motive && <span>motif renseigné</span>}
          <time dateTime={log.created_at}>{fmtDateTime(log.created_at)}</time>
        </div>
      </div>
    </li>
  );
}
