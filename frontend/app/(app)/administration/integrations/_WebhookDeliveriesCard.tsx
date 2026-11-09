"use client";
import { useEffect, useId, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";

type Delivery = {
  id: string;
  event_type: string;
  resource_type: string;
  resource_id: string;
  target_url: string;
  status: "pending" | "success" | "failed" | "retrying";
  response_status: number | null;
  response_body: string | null;
  error_message: string | null;
  attempts: number;
  created_at: string;
  last_attempt_at: string | null;
};

/** Statut = icône + texte (jamais la couleur seule). */
const STATUS_META: Record<string, { label: string; cls: string; icon: string }> = {
  success: { label: "Succès", cls: "sa-badge--ok", icon: "checkmark-circle-02" },
  failed: { label: "Échec", cls: "sa-badge--error", icon: "cancel-circle" },
  retrying: { label: "Nouvel essai", cls: "sa-badge--warn", icon: "refresh" },
  pending: { label: "En attente", cls: "sa-badge--neutral", icon: "clock-01" },
};

export default function WebhookDeliveriesCard() {
  const toast = useToast();
  const uid = useId();
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => { void reload(); }, []);

  async function reload() {
    try {
      setDeliveries(await api.webhookDeliveries(20));
    } catch (e: any) {
      console.warn("deliveries indispo :", e.message);
    }
  }

  async function sendTest() {
    setSending(true);
    try {
      const r = await api.webhookTest();
      if (r.sent) {
        toast({
          tone: r.status === "success" ? "success" : "info",
          title: "Test envoyé",
          message: `Statut : ${r.status}${r.response_status ? " · HTTP " + r.response_status : ""}`,
        });
      } else {
        toast({ tone: "info", title: "Pas envoyé", message: r.reason });
      }
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setSending(false);
    }
  }

  async function retry(d: Delivery) {
    try {
      await api.webhookRetry(d.id);
      toast({ tone: "info", title: "Retry lancé", message: d.event_type });
      await reload();
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    }
  }

  return (
    <section className="sa-card sa-card--flush" aria-labelledby={`${uid}-t`}>
      <div className="sa-card__header">
        <div>
          <h2 className="sa-card__title" id={`${uid}-t`}>Historique des webhooks</h2>
          <p className="sa-card__subtitle">{deliveries.length} envoi(s) récents</p>
        </div>
        <button type="button" className="sa-btn sa-btn--outline sa-btn--sm" onClick={sendTest} disabled={sending}>
          <Icon name="upload-02" className="i" />
          {sending ? "Envoi…" : "Envoyer un test"}
        </button>
      </div>
      {deliveries.length === 0 ? <EmptyPanel /> : <DeliveriesTable deliveries={deliveries} onRetry={retry} />}
    </section>
  );
}

function EmptyPanel() {
  return (
    <div className="sa-empty sa-empty--compact">
      <Icon name="link-square-02" className="i" />
      <div className="sa-empty__title">Aucun envoi</div>
      <div className="sa-empty__text">
        Configurez l&apos;URL puis cliquez sur « Envoyer un test ».
      </div>
    </div>
  );
}

function DeliveriesTable({ deliveries, onRetry }: {
  deliveries: Delivery[]; onRetry: (d: Delivery) => void;
}) {
  return (
    <div className="sa-table-wrap">
      <table className="sa-table sa-table--compact sa-table--cards">
        <thead>
          <tr>
            <th>Événement</th>
            <th>Statut</th>
            <th>HTTP · essais</th>
            <th>Quand</th>
            <th className="is-tight"><span className="sa-sr-only">Action</span></th>
          </tr>
        </thead>
        <tbody>
          {deliveries.map((d) => <DeliveryRow key={d.id} d={d} onRetry={onRetry} />)}
        </tbody>
      </table>
    </div>
  );
}

function DeliveryRow({ d, onRetry }: { d: Delivery; onRetry: (d: Delivery) => void }) {
  const meta = STATUS_META[d.status] || STATUS_META.pending;
  return (
    <tr>
      <td data-label="Événement">
        <div className="sa-cell-main">{d.event_type}</div>
        <div className="sa-cell-sub sa-mono">{d.resource_type}/{d.resource_id.slice(0, 8)}</div>
      </td>
      <td data-label="Statut">
        <span className={`sa-badge ${meta.cls}`}>
          <Icon name={meta.icon} className="i" />
          {meta.label}
        </span>
      </td>
      <td data-label="HTTP · essais" className="sa-mono">
        {d.response_status ?? "—"} · {d.attempts}
      </td>
      <td data-label="Quand" className="sa-text-soft">
        {new Date(d.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}
      </td>
      <td className="is-tight">
        {(d.status === "failed" || d.status === "retrying") && (
          <button type="button" className="sa-btn sa-btn--ghost sa-btn--sm" onClick={() => onRetry(d)}>
            <Icon name="refresh" className="i" />
            Relancer
          </button>
        )}
      </td>
    </tr>
  );
}
