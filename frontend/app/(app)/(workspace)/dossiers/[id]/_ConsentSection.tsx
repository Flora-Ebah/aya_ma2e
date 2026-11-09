"use client";
import { GATE_LABELS } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { fmtDateTime } from "./_constants";
import { SectionBlock } from "./_SectionBlock";

type Props = { consents: any[] };

export default function ConsentSection({ consents }: Props) {
  const signedCount = consents.filter((c) => c.decision === "accepte").length;

  return (
    <SectionBlock
      id="consentements"
      title="Consentements ARTCI"
      subtitle="Loi 2013-450 · signés HMAC-SHA256"
    >
      {consents.length === 0 ? (
        <p className="sa-help" style={{ margin: 0 }}>Aucun consentement enregistré.</p>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
          {consents.map((c) => {
            const ok = c.decision === "accepte";
            return (
              <li
                key={c.id}
                className="flex items-start gap-3 flex-wrap"
                style={{ padding: "var(--spacing-3) 0", borderBottom: "1px solid rgb(var(--color-border-subtle))" }}
              >
                <span className={`sa-icon-tile sa-icon-tile--${ok ? "ok" : "error"}`} style={{ width: 32, height: 32 }}>
                  <Icon name={ok ? "checkmark-circle-02" : "cancel-circle"} className="i" />
                </span>
                <div style={{ flex: "1 1 220px", minWidth: 0 }}>
                  <div className="sa-strong">{GATE_LABELS[c.gate] || c.gate}</div>
                  <div className="sa-cell-sub sa-mono" style={{ overflowWrap: "anywhere" }}>
                    v{c.texte_version} · sig : {c.signature}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1" style={{ marginLeft: "auto" }}>
                  <span className={`sa-badge ${ok ? "sa-badge--ok" : "sa-badge--error"}`}>
                    {ok ? "Accepté" : "Refusé"}
                  </span>
                  <span className="sa-cell-sub">{fmtDateTime(c.created_at)}</span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <div className="sa-row" style={{ justifyContent: "space-between" }}>
        <span className="sa-section-title__label">Statut conformité</span>
        <span className={`sa-badge ${signedCount >= 3 ? "sa-badge--ok" : "sa-badge--warn"}`}>
          <Icon name={signedCount >= 3 ? "checkmark-circle-02" : "alert-circle"} className="i" />
          {signedCount} / 3 signés
        </span>
      </div>
    </SectionBlock>
  );
}
